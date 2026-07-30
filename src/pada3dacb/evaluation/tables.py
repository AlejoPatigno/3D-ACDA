"""Pure schema-v2 projections and atomic single-artifact writers."""
from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .schemas import (
    ANALYSIS_CLASS_INDICES,
    ANALYSIS_CLASS_LABELS,
    PROTOCOL_VERSION,
    SCHEMA_VERSION,
    AnalysisMode,
    ConfusionResult,
    SubjectPrediction,
    ValueStatus,
    canonical_json,
)

CONFUSION_COLUMNS = (
    "true_class", "true_class_index", "row_status", "row_reason",
    "pred_cn", "pred_mci", "pred_ad",
)
_REQUIRED_PNG_METADATA = (
    "direction", "checkpoint_policy", "method_id",
    "evaluation_identity", "subject_table_sha256",
)
ReplaceFunction = Callable[[str | Path, str | Path], None]
_METHOD_STATUS_COLUMNS = (
    "schema_version", "evaluation_identity", "method_id", "public_model_name",
    "direction", "checkpoint_policy", "expected_folds", "completed_folds",
    "expected_seeds", "completed_seeds", "status", "reason_code", "reason_detail",
)
_INCLUSION_COLUMNS = (
    "schema_version", "evaluation_identity", "method_id", "public_model_name",
    "direction", "checkpoint_policy", "seed", "fold", "prediction_role", "expected",
    "present", "provenance_valid", "identity_valid", "probability_valid", "complete",
    "status", "reason_code", "reason_detail", "input_sha256s",
)
_COMPUTATIONAL_COLUMNS = (
    "schema_version", "evaluation_identity", "method_id", "direction",
    "checkpoint_policy", "field", "value", "unit", "status", "reason",
    "source_file_sha256",
)
_SUBJECT_COLUMNS = (
    "schema_version", "protocol_version", "evaluation_identity", "analysis_mode",
    "direction", "checkpoint_policy", "method_id", "public_model_name", "subject_hash",
    "true_label", "prob_cn", "prob_mci", "prob_ad", "predicted_label", "fold_count",
    "seed_count", "source_file_sha256s", "status", "reason",
)
_COMMON_COLUMNS = (
    "schema_version", "protocol_version", "evaluation_identity", "analysis_mode",
    "direction", "checkpoint_policy", "method_id",
)
_METRIC_COLUMNS = _COMMON_COLUMNS + ("metric", "value", "status", "reason", "subject_count")
_PER_CLASS_COLUMNS = _COMMON_COLUMNS + (
    "class_label", "class_index", "support", "metric", "value", "status", "reason",
)
_CI_COLUMNS = _COMMON_COLUMNS + (
    "metric", "point_estimate", "ci_level", "ci_method", "ci_low", "ci_high",
    "bootstrap_seed", "requested", "successful", "invalid", "status", "reason",
)
_PUBLICATION_COLUMNS = _CI_COLUMNS + ("subject_table_sha256",)
_PAIRED_COLUMNS = (
    "schema_version", "protocol_version", "evaluation_identity", "direction",
    "checkpoint_policy", "reference_method", "comparator_method", "metric",
    "orientation", "observed_difference", "ci_level", "ci_method", "ci_low", "ci_high",
    "p_value_method", "raw_p_value", "adjusted_p_value", "bootstrap_seed", "requested",
    "successful", "invalid", "status", "reason", "reference_subject_table_sha256",
    "comparator_subject_table_sha256",
)
_MCNEMAR_COLUMNS = (
    "schema_version", "protocol_version", "evaluation_identity", "direction",
    "checkpoint_policy", "reference_method", "comparator_method", "n_subjects",
    "n00_both_wrong", "n01_reference_correct", "n10_comparator_correct",
    "n11_both_correct", "discordant_count", "test", "raw_p_value",
    "adjusted_p_value", "status", "reason", "note_code",
)
_HOLM_COLUMNS = (
    "schema_version", "protocol_version", "evaluation_identity", "direction",
    "checkpoint_policy", "family_id", "statistic_family", "metric", "family_size",
    "available_count", "reference_method", "comparator_method", "raw_p_value",
    "holm_rank", "adjusted_p_value", "status", "reason",
)
_PUBLIC_NAMES = {
    "source_only": "PADA-3DACB Source-Only", "coral": "PADA-3DACB + CORAL",
    "mmd": "PADA-3DACB + MMD", "cdan": "PADA-3DACB + CDAN",
    "prototype_pseudo": "PADA-3DACB", "aagn": "AAGN", "faster_snn": "FasterSNN",
}


def _assert_private_safe(value: Any) -> None:
    if isinstance(value, Mapping):
        if any(str(key).lower() == "subject_id" for key in value):
            raise ValueError("raw identifier persistence is forbidden")
        for nested in value.values():
            _assert_private_safe(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_private_safe(nested)
    elif isinstance(value, str) and ("subject_id=" in value.lower() or "private-" in value):
        raise ValueError("raw identifier persistence is forbidden")


def resolved_config_bytes(config: Mapping[str, Any]) -> bytes:
    _assert_private_safe(config)
    return yaml_bytes(config)


def provenance_report_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(records)
    return json_bytes({"schema_version": SCHEMA_VERSION, "candidates": tuple(records)})


def method_status_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_METHOD_STATUS_COLUMNS, rows)


def inclusion_report_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_INCLUSION_COLUMNS, rows)


def computational_summary_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_COMPUTATIONAL_COLUMNS, rows)


def predictive_metrics_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_METRIC_COLUMNS, rows)


def per_class_metrics_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_PER_CLASS_COLUMNS, rows)


def confidence_intervals_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_CI_COLUMNS, rows)


def publication_metrics_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_PUBLICATION_COLUMNS, rows)


def paired_differences_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_PAIRED_COLUMNS, rows)


def mcnemar_results_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    return csv_bytes(_MCNEMAR_COLUMNS, rows)


def holm_adjusted_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    _assert_private_safe(rows)
    if rows and any(row.get("family_size") != 6 for row in rows):
        raise ValueError("Holm rows must retain six hypothesis slots")
    return csv_bytes(_HOLM_COLUMNS, rows)


def evaluation_log_bytes(events: Sequence[Mapping[str, Any]]) -> bytes:
    columns = ("utc", "level", "event_code", "evaluation_identity", "message")
    _assert_private_safe(events)
    lines = []
    for event in events:
        if tuple(event) != columns or any("\n" in str(event[field]) for field in columns):
            raise ValueError("evaluation log event fields are invalid")
        lines.append(" | ".join(str(event[field]) for field in columns))
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")


def subject_predictions_bytes(
    rows: Sequence[SubjectPrediction],
    *,
    evaluation_identity: str,
    analysis_mode: AnalysisMode,
) -> bytes:
    projected = []
    for row in sorted(rows, key=lambda item: item.subject_hash):
        projected.append({
            "schema_version": SCHEMA_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "evaluation_identity": evaluation_identity,
            "analysis_mode": analysis_mode.value,
            "direction": row.direction.value,
            "checkpoint_policy": row.checkpoint_policy.value,
            "method_id": row.method_id.value,
            "public_model_name": _PUBLIC_NAMES[row.method_id.value],
            "subject_hash": row.subject_hash,
            "true_label": row.true_label,
            "prob_cn": row.probabilities[0],
            "prob_mci": row.probabilities[1],
            "prob_ad": row.probabilities[2],
            "predicted_label": row.predicted_label,
            "fold_count": row.fold_count,
            "seed_count": row.seed_count,
            "source_file_sha256s": ";".join(row.source_file_sha256s),
            "status": row.status.value,
            "reason": row.reason,
        })
    _assert_private_safe(projected)
    return csv_bytes(_SUBJECT_COLUMNS, projected)


def csv_bytes(
    columns: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> bytes:
    """Project exact ordered columns using an empty field for null values."""
    ordered_columns = tuple(columns)
    if not ordered_columns or len(set(ordered_columns)) != len(ordered_columns):
        raise ValueError("CSV columns must be non-empty and unique")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(ordered_columns)
    expected = set(ordered_columns)
    for row in rows:
        if set(row) != expected or len(row) != len(ordered_columns):
            raise ValueError("CSV row columns must match exactly")
        writer.writerow([row[column] for column in ordered_columns])
    return stream.getvalue().encode("utf-8")


def json_bytes(value: Any) -> bytes:
    """Project canonical compact JSON with one terminal newline."""
    return (canonical_json(value) + "\n").encode("utf-8")


def yaml_bytes(value: Any) -> bytes:
    """Project deterministic YAML from the canonical JSON-compatible value."""
    plain = json.loads(canonical_json(value))
    text = yaml.safe_dump(
        plain,
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=True,
    )
    return text.encode("utf-8")


def confusion_csv_rows(
    result: ConfusionResult,
    *,
    normalized: bool,
) -> tuple[dict[str, Any], ...]:
    """Project fixed CN/MCI/AD confusion rows without performing I/O."""
    matrix = result.normalized if normalized else result.counts
    rows = []
    for index in ANALYSIS_CLASS_INDICES:
        status = result.normalized_row_statuses[index]
        row_status = status.status
        row_reason = status.reason
        if not normalized:
            row_status = ValueStatus.AVAILABLE
            row_reason = None
        values = matrix[index]
        rows.append({
            "true_class": ANALYSIS_CLASS_LABELS[index],
            "true_class_index": index,
            "row_status": row_status.value,
            "row_reason": row_reason,
            "pred_cn": values[0],
            "pred_mci": values[1],
            "pred_ad": values[2],
        })
    return tuple(rows)


def bind_subject_table_hash(
    rows: Sequence[Mapping[str, Any]],
    subject_table_sha256: str,
) -> tuple[dict[str, Any], ...]:
    """Bind publication rows to the exact canonical subject-table bytes."""
    if len(subject_table_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in subject_table_sha256
    ):
        raise ValueError("subject table hash must be a lowercase SHA-256")
    bound = []
    for row in rows:
        existing = row.get("subject_table_sha256")
        if existing is not None and existing != subject_table_sha256:
            raise ValueError("subject table hash conflicts with the projected row")
        bound.append({**row, "subject_table_sha256": subject_table_sha256})
    return tuple(bound)


def _validate_png_metadata(metadata: Mapping[str, str]) -> dict[str, str]:
    if tuple(metadata) != _REQUIRED_PNG_METADATA:
        raise ValueError("PNG metadata fields must be complete and ordered")
    values = dict(metadata)
    if any(not value or not value.isascii() for value in values.values()):
        raise ValueError("PNG metadata values must be non-empty ASCII")
    for field in ("evaluation_identity", "subject_table_sha256"):
        value = values[field]
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"{field} must be a lowercase SHA-256")
    return values


def render_confusion_png(
    result: ConfusionResult,
    *,
    normalized: bool,
    metadata: Mapping[str, str],
) -> bytes:
    """Render deterministic confusion PNG bytes bound to canonical table identity."""
    identity = _validate_png_metadata(metadata)
    kind = "row_normalized" if normalized else "count"
    raw = result.normalized if normalized else result.counts
    matrix = np.asarray(
        [[np.nan if value is None else float(value) for value in row] for row in raw],
        dtype=np.float64,
    )
    figure = Figure(figsize=(4.8, 4.2), dpi=100, layout="tight")
    canvas = FigureCanvasAgg(figure)
    axes = figure.subplots()
    image = axes.imshow(matrix, cmap="Blues", vmin=0.0, vmax=1.0 if normalized else None)
    axes.set_xticks(ANALYSIS_CLASS_INDICES, ANALYSIS_CLASS_LABELS)
    axes.set_yticks(ANALYSIS_CLASS_INDICES, ANALYSIS_CLASS_LABELS)
    axes.set_xlabel("Predicted class")
    axes.set_ylabel("True class")
    axes.set_title(f"{identity['method_id']} | {kind}")
    for row in ANALYSIS_CLASS_INDICES:
        for column in ANALYSIS_CLASS_INDICES:
            value = raw[row][column]
            text = "NA" if value is None else (f"{value:.3f}" if normalized else str(value))
            axes.text(column, row, text, ha="center", va="center", color="black")
    figure.colorbar(image, ax=axes)
    png_metadata = {
        "Software": "pada3dacb",
        "Title": canonical_json({**identity, "content": kind, "labels": ANALYSIS_CLASS_LABELS}),
    }
    stream = io.BytesIO()
    canvas.print_png(stream, metadata=png_metadata)
    figure.clear()
    return stream.getvalue()


def confusion_artifacts(
    result: ConfusionResult, *, metadata: Mapping[str, str]
) -> dict[str, bytes]:
    return {
        "confusion_matrix_counts.csv": csv_bytes(
            CONFUSION_COLUMNS, confusion_csv_rows(result, normalized=False)
        ),
        "confusion_matrix_normalized.csv": csv_bytes(
            CONFUSION_COLUMNS, confusion_csv_rows(result, normalized=True)
        ),
        "confusion_matrix_counts.png": render_confusion_png(
            result, normalized=False, metadata=metadata
        ),
        "confusion_matrix_normalized.png": render_confusion_png(
            result, normalized=True, metadata=metadata
        ),
    }


def atomic_write(
    path: str | Path,
    payload: bytes,
    *,
    replace: ReplaceFunction = os.replace,
) -> Path:
    """Flush a temporary sibling and atomically replace one target artifact."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return target
