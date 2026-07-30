from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import torch
import yaml
from torch import nn

from pada3dacb.exceptions import ConfigurationError
from pada3dacb.experiments import baselines as baseline_module
from pada3dacb.experiments.baselines import (
    load_baseline_config,
    plan_baseline_fold,
    summarize_baseline_cv_results,
    train_baseline_cv_fold,
)
from tests.phase14_helpers import make_baseline_environment


def test_config_loads_only_approved_baselines_and_resolves_paths(tmp_path: Path) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))

    assert config.baseline_names == ("aagn", "faster_snn")
    assert config.direction == "ADNI_to_OASIS"
    assert config.artifact_index.is_absolute()
    assert config.baseline_configs["aagn"]["n_classes"] == 3
    assert config.run_dir("aagn", fold=1, seed=42) == (
        tmp_path / "runs" / "baselines" / "aagn" / "ADNI_to_OASIS" / "seed_42" / "fold_1"
    )


def test_fold_plan_uses_source_only_and_target_evaluation_only(tmp_path: Path) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))

    plan = plan_baseline_fold(config, "aagn", fold=0, seed=42)

    assert plan.fold_seed == 42
    assert plan.source_train_count == 3
    assert plan.source_validation_count == 3
    assert plan.target_evaluation_count == 6
    assert plan.target_adaptation_loader_constructed is False
    assert set(plan.source_train["cohort"]) == {"ADNI"}
    assert set(plan.target_evaluation["cohort"]) == {"OASIS"}


def test_reverse_direction_swaps_roles_and_changes_identity(tmp_path: Path) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))
    reverse = config.with_direction("OASIS", "ADNI")

    plan = plan_baseline_fold(reverse, "faster_snn", fold=1, seed=42)

    assert set(plan.source_train["cohort"]) == {"OASIS"}
    assert set(plan.target_evaluation["cohort"]) == {"ADNI"}
    assert plan.fold_seed == 43
    assert reverse.sha256("faster_snn") != config.sha256("faster_snn")


def test_fold_plan_rejects_too_many_splits(tmp_path: Path) -> None:
    config = load_baseline_config(
        make_baseline_environment(tmp_path, n_splits=3, samples_per_class=2)
    )

    with pytest.raises(ConfigurationError, match="smallest source class"):
        plan_baseline_fold(config, "aagn", fold=0, seed=42)


def test_config_rejects_unknown_baseline_or_invalid_direction(tmp_path: Path) -> None:
    path = make_baseline_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["experiment"]["baseline_names"] = ["vit"]
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="unapproved baseline"):
        load_baseline_config(path)

    path = make_baseline_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["experiment"]["target_domain"] = "ADNI"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="different"):
        load_baseline_config(path)


class _TinyBaseline(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.classifier = nn.Linear(1, 3)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = x.mean(dim=(1, 2, 3, 4), keepdim=False).unsqueeze(1)
        return {"logits": self.classifier(features), "features": features}


def test_dry_run_and_validate_only_create_no_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))
    monkeypatch.setattr(baseline_module, "build_baseline", lambda *_args, **_kwargs: _TinyBaseline())

    dry = train_baseline_cv_fold(config, "faster_snn", 0, 42, dry_run=True)
    validated = train_baseline_cv_fold(config, "faster_snn", 0, 42, validate_only=True)

    assert dry.status == "PENDING"
    assert validated.status == "VALIDATED"
    assert validated.payload["parameter_count"] == 6
    assert not dry.run_dir.exists()
    assert dry.payload["target_adaptation_loader_constructed"] is False


def test_completed_fold_exports_predictions_and_reuses_exact_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))
    monkeypatch.setattr(baseline_module, "build_baseline", lambda *_args, **_kwargs: _TinyBaseline())

    completed = train_baseline_cv_fold(config, "faster_snn", 0, 42)
    reused = train_baseline_cv_fold(config, "faster_snn", 0, 42)
    predictions = pd.read_csv(completed.run_dir / "predictions.csv")

    assert completed.status == reused.status == "COMPLETED"
    assert reused.reused is True
    assert {"source_validation", "target_monitoring"} == set(predictions["split"])
    assert {"best_source_f1", "last"} == set(predictions["checkpoint"])
    assert set(predictions["method"]) == {"baseline"}
    assert "target_adaptation" not in predictions.to_csv(index=False)
    manifest = json.loads(
        (completed.run_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["trainable_parameter_count"] == 6
    assert manifest["baseline_configuration"]["base_ch"] == 16
    assert manifest["input_shape"] == [4, 4, 4]
    assert completed.payload["training_configuration"]["n_epochs"] == 1
    assert len(completed.payload["history"]) == 1
    assert completed.payload["final_source_metrics"]
    assert completed.payload["final_target_metrics"]
    _, grouped = summarize_baseline_cv_results([completed])
    assert "best_checkpoint_target_monitoring_macro_f1_mean" in grouped
    assert "last_checkpoint_target_monitoring_macro_f1_mean" in grouped

    (completed.run_dir / "predictions.csv").unlink()
    with pytest.raises(ConfigurationError, match="incomplete or incompatible"):
        train_baseline_cv_fold(config, "faster_snn", 0, 42)


def test_interruption_and_exact_resume_complete_same_fold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path, n_epochs=2))
    monkeypatch.setattr(baseline_module, "build_baseline", lambda *_args, **_kwargs: _TinyBaseline())

    interrupted = train_baseline_cv_fold(
        config, "faster_snn", 0, 42, interrupt_after_epoch=1
    )
    resumed = train_baseline_cv_fold(
        config,
        "faster_snn",
        0,
        42,
        resume_from=interrupted.run_dir / "last.pt",
    )

    assert interrupted.status == "INTERRUPTED"
    assert resumed.status == "COMPLETED"
    assert resumed.experiment_hash == interrupted.experiment_hash
    assert (resumed.run_dir / "weights.pt").is_file()


def test_all_folds_baselines_and_both_directions_dry_run(tmp_path: Path) -> None:
    from pada3dacb.experiments.baselines import run_baseline_both_directions

    config = load_baseline_config(make_baseline_environment(tmp_path))
    results = run_baseline_both_directions(config, dry_run=True)

    assert tuple(results) == ("ADNI_to_OASIS", "OASIS_to_ADNI")
    for direction in results.values():
        assert tuple(direction) == ("aagn", "faster_snn")
        assert all(result.status == "PENDING" for folds in direction.values() for result in folds)
        assert all(len(folds) == 2 for folds in direction.values())
    assert not config.output_root.exists()


def test_repository_config_accepts_explicit_runtime_path_overrides(tmp_path: Path) -> None:
    synthetic = load_baseline_config(make_baseline_environment(tmp_path))
    repository_config = Path(__file__).resolve().parents[1] / "configs" / "experiments" / "baselines.yaml"

    config = load_baseline_config(
        repository_config,
        overrides={
            "artifact_index": synthetic.artifact_index,
            "output_root": tmp_path / "runs-override",
            "device": "cpu",
        },
    )

    assert config.artifact_index == synthetic.artifact_index
    assert config.output_root == (tmp_path / "runs-override").resolve()
    assert config.baseline_configs["faster_snn"]["base_ch"] == 16


def test_completed_reuse_rejects_corrupt_checkpoint_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))
    monkeypatch.setattr(baseline_module, "build_baseline", lambda *_args, **_kwargs: _TinyBaseline())
    completed = train_baseline_cv_fold(config, "faster_snn", 0, 42)
    (completed.run_dir / "weights.pt").write_bytes(b"not-a-checkpoint")

    with pytest.raises(ConfigurationError, match="incomplete or incompatible"):
        train_baseline_cv_fold(config, "faster_snn", 0, 42)


@pytest.mark.parametrize("corruption", ["missing_target", "truncated_source"])
def test_completed_reuse_rejects_incomplete_prediction_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))
    monkeypatch.setattr(baseline_module, "build_baseline", lambda *_args, **_kwargs: _TinyBaseline())
    completed = train_baseline_cv_fold(config, "faster_snn", 0, 42)
    path = completed.run_dir / "predictions.csv"
    predictions = pd.read_csv(path)
    if corruption == "missing_target":
        predictions = predictions[predictions["split"] == "source_validation"]
    else:
        index = predictions[
            (predictions["split"] == "source_validation")
            & (predictions["checkpoint"] == "last")
        ].index[0]
        predictions = predictions.drop(index)
    predictions.to_csv(path, index=False)

    with pytest.raises(ConfigurationError, match="incomplete or incompatible"):
        train_baseline_cv_fold(config, "faster_snn", 0, 42)
