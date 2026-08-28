import json
from types import SimpleNamespace

import pandas as pd
import pytest

from acda3d.exceptions import ExperimentValidationError
from acda3d.experiments.cdan import CDAN_DISPLAY_NAME, CDANExperimentRunner, load_cdan_config
from acda3d.experiments.prediction_export import PREDICTION_COLUMNS, validate_prediction_frame
from tests.phase12_helpers import make_cdan_environment


def test_cdan_reuses_subject_level_prediction_schema_with_phase12_identity():
    assert "method" in PREDICTION_COLUMNS and "model" in PREDICTION_COLUMNS
    assert "domain_label" not in PREDICTION_COLUMNS
    assert "target_adaptation" not in PREDICTION_COLUMNS

    frame = pd.DataFrame(
        [
            {
                "subject_hash": "subject-001",
                "cohort": "OASIS",
                "true_label": "CN",
                "true_label_index": 0,
                "predicted_label": "CN",
                "predicted_label_index": 0,
                "probability_CN": 0.7,
                "probability_MCI": 0.2,
                "probability_AD": 0.1,
                "direction": "ADNI_to_OASIS",
                "method": "cdan",
                "model": CDAN_DISPLAY_NAME,
                "fold": 0,
                "seed": 42,
                "checkpoint_name": "best_source_f1",
                "checkpoint_epoch": 3,
                "split": "target_monitoring",
                "experiment_hash": "phase12-cdan-hash",
            }
        ],
        columns=PREDICTION_COLUMNS,
    )

    validate_prediction_frame(frame)
    assert frame.loc[0, "method"] == "cdan"
    assert frame.loc[0, "model"] == "3D-ACDA + CDAN"
    assert frame.loc[0, "split"] != "target_adaptation"


def _prepared_reuse_stub():
    return SimpleNamespace(
        base=SimpleNamespace(source_assignment_hash="source-split-hash"),
        target_adaptation_assignment_hash="target-adaptation-hash",
        target_evaluation_assignment_hash="target-evaluation-hash",
    )


def _write_completed_cdan_run(run_dir, experiment_hash: str, *, method: str = "cdan") -> None:
    run_dir.mkdir(parents=True)
    manifest = {
        "status": "COMPLETED",
        "direction": "ADNI_to_OASIS",
        "seed": 42,
        "fold": 0,
        "experiment_hash": experiment_hash,
        "method": method,
        "adaptation_method": "cdan",
        "adaptation_weight": 1.0,
        "source_split_assignment_hash": "source-split-hash",
        "target_adaptation_assignment_hash": "target-adaptation-hash",
        "target_evaluation_assignment_hash": "target-evaluation-hash",
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "fold_metrics.json").write_text(json.dumps({"source/val_macro_f1": 0.75}), encoding="utf-8")
    (run_dir / "training_history.csv").write_text("epoch,stage\n1,full\n", encoding="utf-8")
    (run_dir / "checkpoint_last.pt").write_bytes(b"test-only")
    (run_dir / "checkpoint_best_source_f1.pt").write_bytes(b"test-only")


def test_cdan_reuses_completed_fold_with_matching_phase12_manifest(tmp_path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    runner = CDANExperimentRunner(config)
    run_dir = tmp_path / "completed"
    _write_completed_cdan_run(run_dir, config.sha256())

    reused = runner._completed_reuse(run_dir, config.sha256(), _prepared_reuse_stub())

    assert reused is not None
    assert reused.reused is True
    assert reused.status == "COMPLETED"
    assert reused.experiment_hash == config.sha256()


def test_cdan_rejects_completed_run_with_incompatible_method_identity(tmp_path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    runner = CDANExperimentRunner(config)
    run_dir = tmp_path / "completed"
    _write_completed_cdan_run(run_dir, config.sha256(), method="coral")

    with pytest.raises(ExperimentValidationError, match="CDAN fold has incompatible fields"):
        runner._completed_reuse(run_dir, config.sha256(), _prepared_reuse_stub())
