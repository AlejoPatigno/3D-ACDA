from __future__ import annotations

from pathlib import Path

import pytest
import torch

from acda3d.exceptions import ConfigurationError
from acda3d.publication.binary_runtime import (
    BINARY_PUBLICATION_METHODS,
    BinaryPublicationRuntime,
    load_binary_publication_config,
)

CONFIG_PATH = Path("configs/publication/phase18b_binary.yaml")


def test_binary_runtime_loads_exact_task_contract_and_methods() -> None:
    config = load_binary_publication_config(CONFIG_PATH)

    assert config.task_id == "cn_vs_impaired"
    assert config.task_type == "binary_classification"
    assert config.class_order == ("CN", "Impaired")
    assert config.class_to_index == {"CN": 0, "Impaired": 1}
    assert config.mapping_contract == "phase-18b-binary-v1"
    assert config.n_classes == 2
    assert config.methods == BINARY_PUBLICATION_METHODS
    assert config.validate_only is True


def test_historical_three_class_config_is_rejected_by_binary_entry_point(tmp_path: Path) -> None:
    historical = tmp_path / "historical.yaml"
    historical.write_text(
        """
experiment:
  method: source_only
model:
  name: 3D-ACDA
  num_classes: 3
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="binary|task|three-class"):
        load_binary_publication_config(historical)


def test_validate_only_runtime_builds_all_five_binary_models() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    report = runtime.validate_all()

    assert tuple(report) == BINARY_PUBLICATION_METHODS
    for method in BINARY_PUBLICATION_METHODS:
        result = report[method]
        assert result["method"] == method
        assert tuple(result["latent_logits_shape"]) == (2, 2)
        assert tuple(result["concept_logits_shape"]) == (2, 2)
        assert tuple(result["concepts_shape"]) == (2, 2)
        assert tuple(result["alpha_shape"]) == (2, 2)
        assert result["device"] == "cpu"
        assert result["validate_only"] is True
        assert result["real_run"] is False


def test_binary_source_coral_and_mmd_use_two_logit_ce_and_z_adaptation_only() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    for method in ("source_only", "coral", "mmd"):
        result = runtime.validate_method(method)
        assert result["classification_loss"] >= 0.0
        assert result["classification_loss_name"] == "CrossEntropyLoss"
        assert result["adaptation_feature"] == "z"
        assert result["classifier_cardinality"] == 2


def test_cdan_runtime_dimensions_and_gradients_cover_both_required_cases() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    for z_dim, expected in ((128, 256), (64, 128)):
        z = torch.randn(3, z_dim, requires_grad=True)
        p = torch.softmax(torch.randn(3, 2, requires_grad=True), dim=-1)
        conditional = runtime.conditional_features(z, p)
        assert conditional.shape == (3, expected)
        loss = conditional.square().mean()
        loss.backward()
        assert z.grad is not None and torch.any(z.grad != 0)
        assert p.grad_fn is not None

    result = runtime.validate_method("cdan")
    assert result["conditional_dimension"] == result["z_dimension"] * 2
    assert result["grl_schedule"] == "constant"
    assert result["domain_loss_name"] == "BCEWithLogitsLoss"
    assert result["gradient_reaches_z"] is True
    assert result["gradient_reaches_p"] is True


def test_prototype_pseudo_handles_absent_classes_and_empty_accepted_set() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    absent_zero = runtime.validate_prototype_batch(
        source_labels=torch.tensor([1, 1]),
        target_logits=torch.tensor([[8.0, -8.0], [-8.0, 8.0]]),
    )
    absent_one = runtime.validate_prototype_batch(
        source_labels=torch.tensor([0, 0]),
        target_logits=torch.tensor([[8.0, -8.0], [-8.0, 8.0]]),
    )
    assert absent_zero["valid_source"] == [False, True]
    assert absent_one["valid_source"] == [True, False]

    empty = runtime.validate_pseudo_batch(
        torch.zeros(3, 2), tau=0.99
    )
    assert empty["accepted_count"] == 0
    assert empty["loss"] == 0.0
    assert empty["loss_name"] == "CrossEntropyLoss"


def test_binary_runtime_has_no_real_run_authorization() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    assert runtime.config.authorization == {
        "freeze_approved": False,
        "real_execution_authorized": False,
        "publication_authorized": False,
        "phase_19_forbidden": True,
    }
    with pytest.raises(ConfigurationError, match="validate-only|real|training"):
        runtime.run()
