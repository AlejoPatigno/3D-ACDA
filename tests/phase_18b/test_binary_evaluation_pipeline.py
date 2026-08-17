import json
import subprocess
import sys

import pytest

from pada3dacb.binary import (
    BinaryLabelError,
    BinaryPrediction,
    evaluate_binary_predictions,
    select_best_checkpoint_by_source_validation_macro_f1,
)
from pada3dacb.evaluation.aggregation import aggregate_binary_target_ensemble
from pada3dacb.evaluation.confusion_matrices import compute_binary_confusion
from pada3dacb.evaluation.discovery import BinaryDiscoveryConfig, discover_binary_candidates
from pada3dacb.evaluation.report import build_binary_report, load_binary_report
from pada3dacb.exceptions import ExperimentValidationError
from pada3dacb.experiments.prediction_export import validate_task_scoped_binary_prediction_records


def rows():
    return [
        {"subject_hash": "a", "cohort": "ADNI", "true_label": 0, "prob_cn": 0.9, "prob_impaired": 0.1},
        {"subject_hash": "b", "cohort": "ADNI", "true_label": 0, "prob_cn": 0.4, "prob_impaired": 0.6},
        {"subject_hash": "c", "cohort": "OASIS", "true_label": 1, "prob_cn": 0.2, "prob_impaired": 0.8},
        {"subject_hash": "d", "cohort": "OASIS", "true_label": 1, "prob_cn": 0.7, "prob_impaired": 0.3},
    ]


def test_binary_schema_rejects_historical_fields_and_ties_cn():
    with pytest.raises(BinaryLabelError):
        BinaryPrediction.from_mapping({"prob_cn": 0.5, "prob_impaired": 0.5, "prob_mci": 0.0})
    with pytest.raises(BinaryLabelError):
        BinaryPrediction.from_mapping({"prob_cn": 0.5, "prob_impaired": 0.5, "probability_MCI": 0.0})
    assert BinaryPrediction.from_mapping({"prob_cn": 0.5, "prob_impaired": 0.5}).predicted_label == 0


def test_all_required_metrics_and_fixed_confusion():
    result = evaluate_binary_predictions(rows())
    assert set(result.metrics) >= {
        "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "sensitivity", "specificity",
        "mcc", "cohen_kappa", "roc_auc", "pr_auc", "log_loss", "brier_score",
    }
    assert result.confusion_matrix == ((1, 1), (1, 1))
    assert compute_binary_confusion(rows()) == ((1, 1), (1, 1))
    assert all(item["value"] is not None for item in result.metrics.values())


def test_undefined_support_is_null_with_reason():
    result = evaluate_binary_predictions([{"true_label": 0, "prob_cn": 1.0, "prob_impaired": 0.0}])
    for name in ("balanced_accuracy", "macro_f1", "sensitivity", "roc_auc", "pr_auc"):
        assert result.metrics[name]["value"] is None
        assert result.metrics[name]["reason"]


def test_task_scoped_export_rejects_legacy_fields():
    with pytest.raises(ExperimentValidationError):
        validate_task_scoped_binary_prediction_records([
            {"subject_hash": "a", "cohort": "ADNI", "prob_cn": 0.5, "prob_impaired": 0.5,
             "predicted_label": 0, "prob_ad": 0.0}
        ])


def test_discovery_aggregation_report_roundtrip_and_hash_collision(tmp_path):
    payload = {"task": "cn_vs_impaired", "task_hash": "binary-hash", "fold": 0, "seed": 1, "rows": rows()}
    path = tmp_path / "predictions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    config = BinaryDiscoveryConfig(runs_root=tmp_path, task="cn_vs_impaired", expected_task_hash="binary-hash")
    candidates = discover_binary_candidates(config)
    assert len(candidates) == 1
    expanded = []
    for fold in (0, 1):
        for seed in (1, 2):
            for row in rows():
                expanded.append({**row, "fold": fold, "seed": seed, "task": "cn_vs_impaired", "task_hash": "binary-hash"})
    aggregate = aggregate_binary_target_ensemble(
        expanded, expected_subjects=[r["subject_hash"] for r in rows()], expected_folds=[0, 1], expected_seeds=[1, 2],
        expected_task_hash="binary-hash",
    )
    report = build_binary_report(aggregate.final_predictions, task_hash="binary-hash")
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert load_binary_report(report_path)["task"] == "cn_vs_impaired"
    bad = dict(payload, task="cn_vs_mci_vs_ad")
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert discover_binary_candidates(config) == ()


def test_checkpoint_selection_uses_only_source_validation_macro_f1():
    candidates = [
        {"metrics": {"source_validation_macro_f1": 0.6, "roc_auc": 0.1, "target_macro_f1": 0.1}},
        {"metrics": {"source_validation_macro_f1": 0.5, "roc_auc": 0.99, "target_macro_f1": 0.99}},
    ]
    assert select_best_checkpoint_by_source_validation_macro_f1(candidates) is candidates[0]
    with pytest.raises(BinaryLabelError):
        select_best_checkpoint_by_source_validation_macro_f1([{"metrics": {"roc_auc": 0.99}}])


def test_cli_validate_only_is_not_a_real_run():
    completed = subprocess.run(
        [sys.executable, "scripts/evaluate_binary.py", "--validate-only"],
        check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "validate_only" in completed.stdout
    assert "real_run" in completed.stdout
    assert "true" not in completed.stdout.lower().split("real_run", 1)[-1][:20]


def test_empty_evaluation_kappa_is_undefined_with_reason():
    result = evaluate_binary_predictions([])
    assert result.metrics["cohen_kappa"]["value"] is None
    assert result.metrics["cohen_kappa"]["reason"] == "zero_support"
