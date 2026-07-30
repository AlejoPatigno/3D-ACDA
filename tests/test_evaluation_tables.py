from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    CheckpointPolicy,
    ConfusionResult,
    Direction,
    MethodId,
    MetricValue,
    SubjectPrediction,
)
from pada3dacb.evaluation.tables import (
    atomic_write,
    bind_subject_table_hash,
    computational_summary_bytes,
    confidence_intervals_bytes,
    confusion_artifacts,
    confusion_csv_rows,
    csv_bytes,
    evaluation_log_bytes,
    holm_adjusted_bytes,
    inclusion_report_bytes,
    json_bytes,
    mcnemar_results_bytes,
    method_status_bytes,
    paired_differences_bytes,
    per_class_metrics_bytes,
    predictive_metrics_bytes,
    provenance_report_bytes,
    publication_metrics_bytes,
    render_confusion_png,
    resolved_config_bytes,
    subject_predictions_bytes,
    yaml_bytes,
)

COLUMNS = (
    "true_class", "true_class_index", "row_status", "row_reason",
    "pred_cn", "pred_mci", "pred_ad",
)


def _confusion() -> ConfusionResult:
    return ConfusionResult(
        ((2, 0, 0), (0, 1, 1), (0, 0, 0)),
        ((1.0, 0.0, 0.0), (0.0, 0.5, 0.5), (None, None, None)),
        (
            MetricValue.available(2),
            MetricValue.available(2),
            MetricValue.unavailable("zero_true_support"),
        ),
    )


def _metadata() -> dict[str, str]:
    return {
        "direction": "adni_to_oasis",
        "checkpoint_policy": "primary_best_source_f1",
        "method_id": "mmd",
        "evaluation_identity": "e" * 64,
        "subject_table_sha256": "a" * 64,
    }


def test_csv_projection_preserves_exact_columns_order_and_null_encoding() -> None:
    rows = (
        {"metric": "accuracy", "value": 0.75, "status": "available", "reason": None},
        {"metric": "macro_f1", "value": None, "status": "unavailable", "reason": "missing_true_class"},
    )
    payload = csv_bytes(("metric", "value", "status", "reason"), rows)
    assert payload == (
        b"metric,value,status,reason\n"
        b"accuracy,0.75,available,\n"
        b"macro_f1,,unavailable,missing_true_class\n"
    )
    with pytest.raises(ValueError, match="columns"):
        csv_bytes(("metric", "value"), ({"metric": "accuracy"},))


def test_json_and_yaml_projections_are_canonical_and_newline_terminated() -> None:
    left = {"z": (2, 1), "a": {"status": "available", "reason": None}}
    right = {"a": {"reason": None, "status": "available"}, "z": (2, 1)}
    assert json_bytes(left) == json_bytes(right)
    assert json_bytes(left).endswith(b"\n")
    assert json.loads(json_bytes(left)) == json.loads(json_bytes(right))
    assert yaml_bytes(left) == yaml_bytes(right)
    assert yaml.safe_load(yaml_bytes(left)) == json.loads(json_bytes(left))


def test_root_status_provenance_and_subject_projectors_are_exact_and_private() -> None:
    identity = "e" * 64
    assert yaml.safe_load(resolved_config_bytes({"analysis_mode": "synthetic_test_only"})) == {
        "analysis_mode": "synthetic_test_only"
    }
    provenance = provenance_report_bytes(({
        "relative_path": "runs/input.csv", "sha256": "a" * 64, "status": "included",
    },))
    assert b"runs/input.csv" in provenance and b"private" not in provenance

    status_columns = (
        "schema_version", "evaluation_identity", "method_id", "public_model_name",
        "direction", "checkpoint_policy", "expected_folds", "completed_folds",
        "expected_seeds", "completed_seeds", "status", "reason_code", "reason_detail",
    )
    status_row = dict.fromkeys(status_columns)
    status_row.update(schema_version="phase15-output-v2", evaluation_identity=identity)
    assert method_status_bytes((status_row,)).splitlines()[0] == ",".join(status_columns).encode()

    inclusion_columns = (
        "schema_version", "evaluation_identity", "method_id", "public_model_name",
        "direction", "checkpoint_policy", "seed", "fold", "prediction_role", "expected",
        "present", "provenance_valid", "identity_valid", "probability_valid", "complete",
        "status", "reason_code", "reason_detail", "input_sha256s",
    )
    inclusion_row = dict.fromkeys(inclusion_columns)
    assert inclusion_report_bytes((inclusion_row,)).splitlines()[0] == ",".join(inclusion_columns).encode()

    computational_columns = (
        "schema_version", "evaluation_identity", "method_id", "direction",
        "checkpoint_policy", "field", "value", "unit", "status", "reason",
        "source_file_sha256",
    )
    computational_row = dict.fromkeys(computational_columns)
    computational_row.update(value=None, status="not_recorded", reason="not_recorded")
    assert b",,not_recorded,not_recorded," in computational_summary_bytes((computational_row,))

    row = SubjectPrediction(
        MethodId.MMD, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, "hash-a", 0, (0.8, 0.1, 0.1),
        5, 1, ("a" * 64,),
    )
    subject = subject_predictions_bytes(
        (row,), evaluation_identity=identity, analysis_mode=AnalysisMode.SYNTHETIC_TEST_ONLY
    )
    assert b"hash-a" in subject and b"private" not in subject
    log = evaluation_log_bytes(({
        "utc": "2026-01-01T00:00:00Z", "level": "INFO", "event_code": "complete",
        "evaluation_identity": identity, "message": "synthetic evaluation complete",
    },))
    assert b"synthetic evaluation complete" in log
    with pytest.raises(ValueError, match="raw identifier"):
        evaluation_log_bytes(({
            "utc": "x", "level": "INFO", "event_code": "bad",
            "evaluation_identity": identity, "message": "subject_id=private-a",
        },))


def test_metric_ci_confusion_and_publication_artifacts_are_exact() -> None:
    common = {
        "schema_version": "phase15-output-v2", "protocol_version": "phase15-statistical-v2",
        "evaluation_identity": "e" * 64, "analysis_mode": "synthetic_test_only",
        "direction": "adni_to_oasis", "checkpoint_policy": "primary_best_source_f1",
        "method_id": "mmd",
    }
    metric = {**common, "metric": "accuracy", "value": 0.75, "status": "available",
              "reason": None, "subject_count": 4}
    assert b"accuracy,0.75,available,,4" in predictive_metrics_bytes((metric,))
    per_class = {**common, "class_label": "CN", "class_index": 0, "support": 2,
                 "metric": "recall", "value": 1.0, "status": "available", "reason": None}
    assert b"CN,0,2,recall,1.0,available," in per_class_metrics_bytes((per_class,))
    interval = {**common, "metric": "accuracy", "point_estimate": 0.75, "ci_level": 0.95,
                "ci_method": "percentile", "ci_low": 0.5, "ci_high": 1.0,
                "bootstrap_seed": 17, "requested": 100, "successful": 100, "invalid": 0,
                "status": "available", "reason": None}
    assert b"percentile" in confidence_intervals_bytes((interval,))
    publication = {**interval, "subject_table_sha256": "a" * 64}
    assert b"a" * 64 in publication_metrics_bytes((publication,))
    artifacts = confusion_artifacts(_confusion(), metadata=_metadata())
    assert set(artifacts) == {
        "confusion_matrix_counts.csv", "confusion_matrix_normalized.csv",
        "confusion_matrix_counts.png", "confusion_matrix_normalized.png",
    }
    assert artifacts["confusion_matrix_counts.csv"].startswith(b"true_class,")
    assert artifacts["confusion_matrix_counts.png"].startswith(b"\x89PNG")


def test_paired_mcnemar_and_holm_projections_have_exact_fixed_slots() -> None:
    paired_columns = (
        "schema_version", "protocol_version", "evaluation_identity", "direction",
        "checkpoint_policy", "reference_method", "comparator_method", "metric",
        "orientation", "observed_difference", "ci_level", "ci_method", "ci_low", "ci_high",
        "p_value_method", "raw_p_value", "adjusted_p_value", "bootstrap_seed", "requested",
        "successful", "invalid", "status", "reason", "reference_subject_table_sha256",
        "comparator_subject_table_sha256",
    )
    paired = dict.fromkeys(paired_columns)
    paired.update(reference_method="prototype_pseudo", comparator_method="mmd",
                  orientation="prototype_pseudo-comparator", status="available")
    assert paired_differences_bytes((paired,)).splitlines()[0] == ",".join(paired_columns).encode()

    mcnemar_columns = (
        "schema_version", "protocol_version", "evaluation_identity", "direction",
        "checkpoint_policy", "reference_method", "comparator_method", "n_subjects",
        "n00_both_wrong", "n01_reference_correct", "n10_comparator_correct",
        "n11_both_correct", "discordant_count", "test", "raw_p_value",
        "adjusted_p_value", "status", "reason", "note_code",
    )
    mcnemar = dict.fromkeys(mcnemar_columns)
    mcnemar.update(reference_method="prototype_pseudo", comparator_method="mmd",
                   test="exact_two_sided_mcnemar", raw_p_value=1.0,
                   status="available", note_code="no_discordant_pairs")
    assert b"no_discordant_pairs" in mcnemar_results_bytes((mcnemar,))

    holm_columns = (
        "schema_version", "protocol_version", "evaluation_identity", "direction",
        "checkpoint_policy", "family_id", "statistic_family", "metric", "family_size",
        "available_count", "reference_method", "comparator_method", "raw_p_value",
        "holm_rank", "adjusted_p_value", "status", "reason",
    )
    rows = []
    for comparator in ("source_only", "coral", "mmd", "cdan", "aagn", "faster_snn"):
        row = dict.fromkeys(holm_columns)
        row.update(family_size=6, reference_method="prototype_pseudo",
                   comparator_method=comparator, status="available")
        rows.append(row)
    payload = holm_adjusted_bytes(rows)
    assert len(payload.splitlines()) == 7
    assert payload.splitlines()[0] == ",".join(holm_columns).encode()


def test_confusion_projection_has_fixed_rows_statuses_and_nullable_zero_support() -> None:
    counts = confusion_csv_rows(_confusion(), normalized=False)
    normalized = confusion_csv_rows(_confusion(), normalized=True)
    assert tuple(counts[0]) == COLUMNS
    assert counts[0] == {
        "true_class": "CN", "true_class_index": 0,
        "row_status": "available", "row_reason": None,
        "pred_cn": 2, "pred_mci": 0, "pred_ad": 0,
    }
    assert normalized[1]["pred_mci"] == normalized[1]["pred_ad"] == 0.5
    assert normalized[2] == {
        "true_class": "AD", "true_class_index": 2,
        "row_status": "unavailable", "row_reason": "zero_true_support",
        "pred_cn": None, "pred_mci": None, "pred_ad": None,
    }
    assert csv_bytes(COLUMNS, normalized).splitlines()[-1] == b"AD,2,unavailable,zero_true_support,,,"


def test_publication_rows_bind_the_exact_subject_table_hash() -> None:
    source_hash = "a" * 64
    rows = bind_subject_table_hash(
        ({"metric": "accuracy", "value": 0.75, "status": "available", "reason": None},),
        source_hash,
    )
    assert rows[0]["subject_table_sha256"] == source_hash
    with pytest.raises(ValueError, match="conflicts"):
        bind_subject_table_hash(
            ({"metric": "accuracy", "subject_table_sha256": "b" * 64},),
            source_hash,
        )
    with pytest.raises(ValueError, match="SHA-256"):
        bind_subject_table_hash((), "invalid")


def test_count_and_normalized_pngs_are_deterministic_and_identity_bound() -> None:
    metadata = _metadata()
    count_png = render_confusion_png(_confusion(), normalized=False, metadata=metadata)
    normalized_png = render_confusion_png(_confusion(), normalized=True, metadata=metadata)
    assert count_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert normalized_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert count_png == render_confusion_png(_confusion(), normalized=False, metadata=metadata)
    assert normalized_png == render_confusion_png(_confusion(), normalized=True, metadata=metadata)
    assert count_png != normalized_png
    for value in (*metadata.values(), "count", "row_normalized", "CN", "MCI", "AD"):
        assert value.encode("ascii") in count_png + normalized_png


def test_atomic_write_uses_same_filesystem_temporary_sibling(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "result.csv"
    observed: dict[str, Path] = {}

    def replace(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        observed.update(source=source_path, destination=destination_path)
        source_path.replace(destination_path)

    assert atomic_write(target, b"header\nvalue\n", replace=replace) == target
    assert target.read_bytes() == b"header\nvalue\n"
    assert observed["source"].parent == target.parent
    assert observed["destination"] == target
    assert not observed["source"].exists()


def test_atomic_write_cleans_temporary_file_and_preserves_target_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_bytes(b"original")
    before = set(tmp_path.iterdir())

    def fail_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("injected replace failure")

    with pytest.raises(OSError, match="injected"):
        atomic_write(target, b"replacement", replace=fail_replace)
    assert target.read_bytes() == b"original"
    assert set(tmp_path.iterdir()) == before
