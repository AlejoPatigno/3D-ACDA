from __future__ import annotations

from pathlib import Path

import pytest
import torch

from pada3dacb.binary import (
    BINARY_ABLATIONS,
    BINARY_BASELINES,
    BINARY_CLASS_ORDER,
    BinaryLabelError,
    binary_prediction_from_logits,
    build_binary_ablation,
    build_binary_baseline,
    build_binary_identity,
    validate_binary_baseline,
)
from pada3dacb.exceptions import ConfigurationError
from pada3dacb.publication.binary_runtime import BinaryPublicationRuntime

CONFIG_PATH = Path("configs/publication/phase18b_binary.yaml")


def _baseline_config(name: str) -> dict[str, object]:
    config: dict[str, object] = {
        "task_id": "cn_vs_impaired",
        "task_type": "binary_classification",
        "class_order": list(BINARY_CLASS_ORDER),
        "class_ids": {"CN": 0, "Impaired": 1},
        "model": {"num_classes": 2},
    }
    if name == "aagn":
        config["roi_masks"] = torch.ones(2, 2, 2, 2)
    return config


def test_task_scoped_binary_baselines_emit_two_logits_without_mutating_historical_registry() -> None:
    assert BINARY_BASELINES == ("aagn", "faster_snn")
    for name in BINARY_BASELINES:
        model = build_binary_baseline(name, _baseline_config(name))
        x = torch.randn(2, 1, 17, 17, 17)
        output = model(x)
        assert output["logits"].shape == (2, 2)
        assert model.binary_metadata["task_id"] == "cn_vs_impaired"
        assert model.binary_metadata["identity_hash"] != ""


def test_binary_baseline_validation_is_cpu_validate_only_and_prediction_schema_is_binary() -> None:
    for name in BINARY_BASELINES:
        result = validate_binary_baseline(name, _baseline_config(name))
        assert result["logits_shape"] == (2, 2)
        assert result["device"] == "cpu"
        assert result["validate_only"] is True
        assert result["real_run"] is False
        assert result["prediction_keys"] == ("prob_cn", "prob_impaired")


def test_historical_baseline_registry_and_configs_remain_three_class_and_reject_binary_entry_point() -> None:
    from pada3dacb.models.baselines import build_baseline, get_baseline_spec

    assert get_baseline_spec("aagn").output_classes == 3
    assert get_baseline_spec("faster_snn").output_classes == 3
    with pytest.raises(ValueError, match="exactly 3"):
        build_baseline("faster_snn", {"n_classes": 2})
    with pytest.raises(BinaryLabelError, match="cn_vs_impaired"):
        build_binary_baseline("faster_snn", {"n_classes": 2})


def test_all_six_binary_ablations_use_binary_class_order_and_preserve_interventions() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    assert tuple(BINARY_ABLATIONS) == ("no_proto", "no_pl", "no_cons", "no_concept", "no_anat", "mean_pool")
    report = runtime.validate_all_ablations()
    assert tuple(report) == BINARY_ABLATIONS
    for candidate in BINARY_ABLATIONS:
        model = build_binary_ablation(candidate, runtime._model_payload())
        output = model(torch.randn(2, 1, 16, 16, 16), torch.ones(2, 2, 2, 2))
        assert output.latent_logits.shape == (2, 2)
        assert output.concept_logits.shape == (2, 2)
        assert report[candidate]["class_order"] == BINARY_CLASS_ORDER
        assert report[candidate]["intervention"]
        assert report[candidate]["validate_only"] is True
        assert report[candidate]["real_run"] is False


def test_historical_and_excluded_ablation_variants_are_rejected() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    for candidate in ("no_domain_adaptation", "no_ctx_encoder", "full", "lambda_proto_0.2", "mean_pooling"):
        with pytest.raises((ConfigurationError, BinaryLabelError), match="approved|blocked|unsupported|alias|binary"):
            runtime.validate_ablation(candidate)
    with pytest.raises(BinaryLabelError, match="three-class|historical"):
        build_binary_ablation("no_proto", {"task_id": "cn_vs_impaired", "num_classes": 3})


def test_binary_prediction_schema_and_identity_are_task_bound() -> None:
    prediction = binary_prediction_from_logits(torch.tensor([[2.0, 0.0]]))
    assert set(prediction) == {"prob_cn", "prob_impaired", "predicted_label"}
    assert prediction["predicted_label"] == 0
    assert "prob_mci" not in prediction and "prob_ad" not in prediction
    binary_identity = build_binary_identity("ablation", {"candidate_id": "no_proto"})
    assert binary_identity["phase"] == "18B"
    assert binary_identity["task_id"] == "cn_vs_impaired"
    with pytest.raises(BinaryLabelError, match="historical"):
        build_binary_identity("ablation", {"candidate_id": "no_proto", "class_order": ["CN", "MCI", "AD"]})


def test_binary_baseline_and_ablation_entry_points_never_authorize_real_execution() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    with pytest.raises(ConfigurationError, match="validate-only|real|training"):
        runtime.run()
    with pytest.raises(ConfigurationError, match="validate-only|authorization"):
        runtime.validate_ablation("no_proto", execute=True)
