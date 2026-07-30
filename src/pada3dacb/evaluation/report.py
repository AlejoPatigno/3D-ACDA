"""Deterministic Phase 15 report state machine and output orchestration seams."""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType

from .bootstrap import bootstrap_metrics
from .confusion_matrices import compute_confusion
from .metrics import compute_metrics
from .multiple_testing import adjust_holm
from .paired_statistics import exact_mcnemar, paired_bootstrap
from .schemas import (
    AGGREGATE_METRIC_NAMES,
    COMPARATOR_METHODS,
    PAIRED_METRIC_NAMES,
    PROTOCOL_VERSION,
    SCHEMA_VERSION,
    AnalysisMode,
    AuthorizationGateError,
    BootstrapInterval,
    CheckpointPolicy,
    ComputationalValue,
    ConfigurationError,
    ConfusionResult,
    Direction,
    EvaluationBundle,
    EvaluationPlan,
    EvaluationRequest,
    ExistingOutputError,
    HolmRow,
    McNemarResult,
    MethodId,
    MetricSet,
    OutputCommitError,
    PairedDifference,
    ReuseVerificationError,
    RunMode,
    SubjectPrediction,
    ValueStatus,
    canonical_json,
    canonical_sha256,
)
from .tables import (
    computational_summary_bytes,
    confidence_intervals_bytes,
    confusion_artifacts,
    evaluation_log_bytes,
    holm_adjusted_bytes,
    inclusion_report_bytes,
    mcnemar_results_bytes,
    method_status_bytes,
    paired_differences_bytes,
    per_class_metrics_bytes,
    predictive_metrics_bytes,
    provenance_report_bytes,
    publication_metrics_bytes,
    resolved_config_bytes,
    subject_predictions_bytes,
)

_COMPUTATIONAL_UNITS = (
    ("trainable_parameter_count", "count"),
    ("training_runtime_seconds", "seconds"),
    ("inference_runtime_seconds", "seconds"),
    ("peak_memory_bytes", "bytes"),
    ("checkpoint_epoch", "epoch"),
    ("completed_folds", "count"),
    ("completed_seeds", "count"),
)

ValidatedLoad = Callable[
    [],
    tuple[
        Mapping[str, tuple[SubjectPrediction, ...]],
        tuple[Mapping[str, object], ...],
    ],
]
StatisticsBuilder = Callable[
    [Mapping[str, tuple[SubjectPrediction, ...]]],
    Mapping[str, bytes],
]
BundleWriter = Callable[[EvaluationBundle], None]


class ReportState(str, Enum):
    PLANNED = "planned"
    VALIDATED = "validated"
    COMPLETED = "completed"
    REUSED = "reused"


@dataclass(frozen=True)
class ReportOutcome:
    state: ReportState
    plan: EvaluationPlan
    bundle: EvaluationBundle | None


@dataclass(frozen=True)
class ReportStatistics:
    metrics: Mapping[MethodId, MetricSet]
    confusions: Mapping[MethodId, ConfusionResult]
    bootstrap_intervals: Mapping[MethodId, tuple[BootstrapInterval, ...]]
    mcnemar_results: tuple[McNemarResult, ...]
    paired_differences: tuple[PairedDifference, ...]
    holm_rows: tuple[HolmRow, ...]


def _metric_functions(names: Sequence[str]):
    cache = []

    def metric(name: str):
        def evaluate(rows):
            current = tuple(rows)
            for index, (cached_rows, cached_metrics) in enumerate(cache):
                if current == cached_rows:
                    cache.append(cache.pop(index))
                    return cached_metrics.aggregate_metrics[name]
            computed = compute_metrics(current, allow_repeated_subjects=True)
            cache.append((current, computed))
            del cache[:-2]
            return computed.aggregate_metrics[name]
        return evaluate

    return {name: metric(name) for name in names}


def _unavailable_mcnemar(method: MethodId, reason: str) -> McNemarResult:
    return McNemarResult(
        method, 0, 0, 0, 0, 0, 0, "exact_two_sided_mcnemar", None,
        ValueStatus.UNAVAILABLE, reason, None,
    )


def _unavailable_paired(
    method: MethodId, metric: str, reason: str, replicates: int, seed: int
) -> PairedDifference:
    return PairedDifference(
        method, metric, "prototype_pseudo-comparator", None, 0.95, "percentile",
        None, None, "centered_plus_one", None, seed, replicates, 0, replicates,
        ValueStatus.UNAVAILABLE, reason,
    )


def build_report_statistics(
    tables: Mapping[str, tuple[SubjectPrediction, ...]],
    *,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> ReportStatistics:
    """Compose deterministic descriptive and fixed-family inferential statistics."""
    normalized = {}
    scope = None
    for method in MethodId:
        rows = tuple(tables.get(method.value, ()))
        if not rows:
            continue
        if any(row.method_id is not method for row in rows):
            raise ValueError("subject-table method is inconsistent")
        subjects = tuple(row.subject_hash for row in rows)
        if subjects != tuple(sorted(subjects)) or len(subjects) != len(set(subjects)):
            raise ValueError("subject tables must be sorted and unique")
        current_scope = (rows[0].direction, rows[0].checkpoint_policy)
        if any((row.direction, row.checkpoint_policy) != current_scope for row in rows):
            raise ValueError("subject table scope is inconsistent")
        if scope is not None and current_scope != scope:
            raise ValueError("all report tables must share direction and policy")
        scope = current_scope
        normalized[method] = rows
    if not normalized:
        raise ValueError("at least one canonical subject table is required")

    metrics = {method: compute_metrics(rows) for method, rows in normalized.items()}
    confusions = {method: compute_confusion(rows) for method, rows in normalized.items()}
    intervals = {
        method: bootstrap_metrics(
            rows, _metric_functions(AGGREGATE_METRIC_NAMES),
            replicates=bootstrap_replicates, seed=bootstrap_seed,
        )
        for method, rows in normalized.items()
    }

    reference = normalized.get(MethodId.PROTOTYPE_PSEUDO)
    mcnemar = []
    paired_by_comparator = {}
    for comparator in COMPARATOR_METHODS:
        compared = normalized.get(comparator)
        reason = (
            "reference_method_unavailable" if reference is None
            else "comparator_method_unavailable" if compared is None else None
        )
        if reason is not None:
            mcnemar.append(_unavailable_mcnemar(comparator, reason))
            paired_by_comparator[comparator] = tuple(
                _unavailable_paired(
                    comparator, name, reason, bootstrap_replicates, bootstrap_seed
                )
                for name in PAIRED_METRIC_NAMES
            )
        else:
            mcnemar.append(exact_mcnemar(reference, compared))
            paired_by_comparator[comparator] = paired_bootstrap(
                reference, compared, _metric_functions(PAIRED_METRIC_NAMES),
                replicates=bootstrap_replicates, seed=bootstrap_seed,
            )
    paired = tuple(
        next(row for row in paired_by_comparator[comparator] if row.metric == name)
        for name in PAIRED_METRIC_NAMES
        for comparator in COMPARATOR_METHODS
    )
    holm = list(adjust_holm(mcnemar))
    for name in PAIRED_METRIC_NAMES:
        holm.extend(adjust_holm(tuple(row for row in paired if row.metric == name)))
    return ReportStatistics(
        MappingProxyType(metrics), MappingProxyType(confusions), MappingProxyType(intervals),
        tuple(mcnemar), paired, tuple(holm),
    )


def _validate_source_hash(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("computational source_sha256 is invalid")
    return value


def extract_computational_values(
    records: Sequence[Mapping[str, object]],
) -> tuple[ComputationalValue, ...]:
    """Extract approved computational values with explicit missing/conflict states."""
    normalized = tuple(records)
    sources = tuple(_validate_source_hash(record.get("source_sha256")) for record in normalized)
    results = []
    for field, unit in _COMPUTATIONAL_UNITS:
        observed = [record[field] for record in normalized if field in record]
        if not observed:
            results.append(ComputationalValue(
                field, None, unit, ValueStatus.NOT_RECORDED, "not_recorded", None
            ))
            continue
        valid = all(
            not isinstance(value, bool)
            and isinstance(value, (float, int))
            and math.isfinite(value)
            for value in observed
        )
        if not valid:
            results.append(ComputationalValue(
                field, None, unit, ValueStatus.UNAVAILABLE,
                "invalid_computational_value", None,
            ))
            continue
        first = observed[0]
        if any(value != first for value in observed[1:]):
            results.append(ComputationalValue(
                field, None, unit, ValueStatus.UNAVAILABLE,
                "conflicting_values", canonical_sha256(tuple(sorted(set(sources)))),
            ))
            continue
        contributing = tuple(
            sources[index] for index, record in enumerate(normalized) if field in record
        )
        source_hash = contributing[0] if len(contributing) == 1 else canonical_sha256(tuple(sorted(set(contributing))))
        results.append(ComputationalValue(
            field, first, unit, ValueStatus.AVAILABLE, None, source_hash
        ))
    return tuple(results)


def _validate_plan(request: EvaluationRequest, plan: EvaluationPlan) -> None:
    if request.analysis_mode is not plan.analysis_mode:
        raise ConfigurationError("request and evaluation plan analysis modes differ")
    if (
        request.methods != plan.methods
        or request.directions != plan.directions
        or request.checkpoint_policies != plan.checkpoint_policies
    ):
        raise ConfigurationError("request and evaluation plan selectors differ")


def _validate_subject_tables(
    tables: Mapping[str, tuple[SubjectPrediction, ...]],
    plan: EvaluationPlan,
) -> dict[str, tuple[SubjectPrediction, ...]]:
    normalized = {method: tuple(rows) for method, rows in tables.items()}
    expected = tuple(method.value for method in plan.methods)
    if tuple(normalized) != expected:
        raise ValueError("subject-table methods must match the evaluation plan")
    for method, rows in normalized.items():
        if not rows or any(row.method_id is not MethodId(method) for row in rows):
            raise ValueError("subject-table method is inconsistent")
        subjects = tuple(row.subject_hash for row in rows)
        if subjects != tuple(sorted(subjects)) or len(subjects) != len(set(subjects)):
            raise ValueError("subject tables must be unique and canonically sorted")
    return normalized


def orchestrate_report(
    request: EvaluationRequest,
    plan: EvaluationPlan,
    *,
    gate_allowed: bool,
    load_validated: ValidatedLoad,
    build_statistics: StatisticsBuilder,
    write_bundle: BundleWriter,
) -> ReportOutcome:
    """Execute one explicit run-mode state machine using injected side-effect seams."""
    _validate_plan(request, plan)
    if request.run_mode is RunMode.DRY_RUN:
        return ReportOutcome(ReportState.PLANNED, plan, None)
    if request.run_mode is RunMode.REUSE:
        raise ConfigurationError("reuse requires the completed read-only verifier")
    if request.run_mode is RunMode.EVALUATE and request.analysis_mode is AnalysisMode.REAL and not gate_allowed:
        raise AuthorizationGateError("real evaluation gate is not authorized")

    raw_tables, computational_records = load_validated()
    tables = _validate_subject_tables(raw_tables, plan)
    if request.run_mode is RunMode.VALIDATE_ONLY:
        return ReportOutcome(ReportState.VALIDATED, plan, None)

    artifacts = dict(build_statistics(tables))
    if not artifacts or any(not path or not isinstance(payload, bytes) for path, payload in artifacts.items()):
        raise ValueError("statistics builder must return non-empty byte artifacts")
    result_hashes = {
        path: hashlib.sha256(payload).hexdigest()
        for path, payload in artifacts.items()
    }
    bundle = EvaluationBundle(
        plan.evaluation_identity,
        tables,
        result_hashes,
        extract_computational_values(computational_records),
    )
    write_bundle(bundle)
    return ReportOutcome(ReportState.COMPLETED, plan, bundle)


_ROOT_OUTPUTS = (
    "evaluation_config_resolved.yaml",
    "provenance_report.json",
    "method_status.csv",
    "computational_summary.csv",
    "evaluation_log.txt",
)
_POLICY_OUTPUTS = (
    "inclusion_report.csv",
    "metrics/predictive_metrics.csv",
    "metrics/per_class_metrics.csv",
    "confidence_intervals/predictive_metrics_with_ci.csv",
    "pairwise_comparisons/pairwise_metric_differences.csv",
    "pairwise_comparisons/mcnemar_results.csv",
    "pairwise_comparisons/holm_adjusted.csv",
    "tables/predictive_metrics_with_ci.csv",
)
_CONFUSION_OUTPUTS = (
    "confusion_matrix_counts.csv",
    "confusion_matrix_normalized.csv",
    "confusion_matrix_counts.png",
    "confusion_matrix_normalized.png",
)
OutputWriter = Callable[[Path, bytes], None]
ReplacePath = Callable[[str | Path, str | Path], None]


def build_output_plan(
    evaluation_identity: str,
    analysis_mode: AnalysisMode,
    methods: tuple[MethodId, ...],
    directions: tuple[Direction, ...],
    checkpoint_policies: tuple[CheckpointPolicy, ...],
    *,
    included_methods: tuple[MethodId, ...],
    include_artifact_index: bool = False,
) -> EvaluationPlan:
    """Build the exact manifest-last output allowlist without identity nesting."""
    if any(method not in methods for method in included_methods):
        raise ValueError("included methods must be selected methods")
    paths = list(_ROOT_OUTPUTS)
    for direction in directions:
        for policy in checkpoint_policies:
            base = f"predictive/{direction.value}/{policy.value}"
            paths.extend(f"{base}/{suffix}" for suffix in _POLICY_OUTPUTS)
            for method in included_methods:
                paths.append(f"{base}/subject_predictions/{method.value}.csv")
                matrix_root = f"{base}/confusion_matrices/{method.value}"
                paths.extend(f"{matrix_root}/{name}" for name in _CONFUSION_OUTPUTS)
    if include_artifact_index:
        paths.append("artifact_index.json")
    paths.append("evaluation_manifest.json")
    return EvaluationPlan(
        evaluation_identity, analysis_mode, methods, directions,
        checkpoint_policies, tuple(paths),
    )


def _common_row(plan, direction, policy, method):
    return {
        "schema_version": SCHEMA_VERSION, "protocol_version": PROTOCOL_VERSION,
        "evaluation_identity": plan.evaluation_identity,
        "analysis_mode": plan.analysis_mode.value, "direction": direction.value,
        "checkpoint_policy": policy.value, "method_id": method.value,
    }


def _statistics_artifacts(plan, direction, policy, tables, statistics):
    base = f"predictive/{direction.value}/{policy.value}"
    artifacts = {}
    metrics_rows, class_rows, ci_rows, publication_rows = [], [], [], []
    table_hashes = {}
    for method, rows in tables.items():
        path = f"{base}/subject_predictions/{method.value}.csv"
        payload = subject_predictions_bytes(
            rows, evaluation_identity=plan.evaluation_identity,
            analysis_mode=plan.analysis_mode,
        )
        artifacts[path] = payload
        table_hashes[method] = hashlib.sha256(payload).hexdigest()
        common = _common_row(plan, direction, policy, method)
        metric_set = statistics.metrics[method]
        for name, value in metric_set.aggregate_metrics.items():
            metrics_rows.append({
                **common, "metric": name, "value": value.value,
                "status": value.status.value, "reason": value.reason,
                "subject_count": metric_set.subject_count,
            })
        for row in metric_set.per_class_metrics:
            class_rows.append({
                **common, "class_label": row.class_label,
                "class_index": row.class_index, "support": row.support.value,
                "metric": row.metric, "value": row.value.value,
                "status": row.value.status.value, "reason": row.value.reason,
            })
        for row in statistics.bootstrap_intervals[method]:
            projected = {
                **common, "metric": row.metric,
                "point_estimate": row.point_estimate, "ci_level": row.ci_level,
                "ci_method": row.ci_method, "ci_low": row.ci_low,
                "ci_high": row.ci_high, "bootstrap_seed": row.bootstrap_seed,
                "requested": row.requested, "successful": row.successful,
                "invalid": row.invalid, "status": row.status.value,
                "reason": row.reason,
            }
            ci_rows.append(projected)
            publication_rows.append({
                **projected, "subject_table_sha256": table_hashes[method]
            })
        metadata = {
            "direction": direction.value, "checkpoint_policy": policy.value,
            "method_id": method.value,
            "evaluation_identity": plan.evaluation_identity,
            "subject_table_sha256": table_hashes[method],
        }
        for name, payload in confusion_artifacts(
            statistics.confusions[method], metadata=metadata
        ).items():
            artifacts[f"{base}/confusion_matrices/{method.value}/{name}"] = payload
    artifacts[f"{base}/metrics/predictive_metrics.csv"] = predictive_metrics_bytes(metrics_rows)
    artifacts[f"{base}/metrics/per_class_metrics.csv"] = per_class_metrics_bytes(class_rows)
    artifacts[f"{base}/confidence_intervals/predictive_metrics_with_ci.csv"] = confidence_intervals_bytes(ci_rows)
    artifacts[f"{base}/tables/predictive_metrics_with_ci.csv"] = publication_metrics_bytes(publication_rows)

    holm_lookup = {
        (row.statistic_family, row.metric, row.comparator_method): row
        for row in statistics.holm_rows
    }
    comparison_common = {
        "schema_version": SCHEMA_VERSION, "protocol_version": PROTOCOL_VERSION,
        "evaluation_identity": plan.evaluation_identity,
        "direction": direction.value, "checkpoint_policy": policy.value,
        "reference_method": MethodId.PROTOTYPE_PSEUDO.value,
    }
    paired_rows = []
    for row in statistics.paired_differences:
        adjusted = holm_lookup[("paired_bootstrap", row.metric, row.comparator_method)]
        paired_rows.append({
            **comparison_common, "comparator_method": row.comparator_method.value,
            "metric": row.metric, "orientation": row.orientation,
            "observed_difference": row.observed_difference, "ci_level": row.ci_level,
            "ci_method": row.ci_method, "ci_low": row.ci_low, "ci_high": row.ci_high,
            "p_value_method": row.p_value_method, "raw_p_value": row.raw_p_value,
            "adjusted_p_value": adjusted.adjusted_p_value,
            "bootstrap_seed": row.bootstrap_seed, "requested": row.requested,
            "successful": row.successful, "invalid": row.invalid,
            "status": row.status.value, "reason": row.reason,
            "reference_subject_table_sha256": table_hashes.get(MethodId.PROTOTYPE_PSEUDO),
            "comparator_subject_table_sha256": table_hashes.get(row.comparator_method),
        })
    mcnemar_rows = []
    for row in statistics.mcnemar_results:
        adjusted = holm_lookup[("mcnemar_accuracy", None, row.comparator_method)]
        mcnemar_rows.append({
            **comparison_common, "comparator_method": row.comparator_method.value,
            "n_subjects": row.n_subjects, "n00_both_wrong": row.n00_both_wrong,
            "n01_reference_correct": row.n01_reference_correct,
            "n10_comparator_correct": row.n10_comparator_correct,
            "n11_both_correct": row.n11_both_correct,
            "discordant_count": row.discordant_count, "test": row.test,
            "raw_p_value": row.raw_p_value,
            "adjusted_p_value": adjusted.adjusted_p_value,
            "status": row.status.value, "reason": row.reason,
            "note_code": row.note_code,
        })
    holm_rows = [{
        **comparison_common, "family_id": f"{row.statistic_family}:{row.metric or 'accuracy'}",
        "statistic_family": row.statistic_family, "metric": row.metric,
        "family_size": row.family_size, "available_count": row.available_count,
        "comparator_method": row.comparator_method.value,
        "raw_p_value": row.raw_p_value, "holm_rank": row.holm_rank,
        "adjusted_p_value": row.adjusted_p_value, "status": row.status.value,
        "reason": row.reason,
    } for row in statistics.holm_rows]
    artifacts[f"{base}/pairwise_comparisons/pairwise_metric_differences.csv"] = paired_differences_bytes(paired_rows)
    artifacts[f"{base}/pairwise_comparisons/mcnemar_results.csv"] = mcnemar_results_bytes(mcnemar_rows)
    artifacts[f"{base}/pairwise_comparisons/holm_adjusted.csv"] = holm_adjusted_bytes(holm_rows)
    return artifacts


def project_and_commit_output(
    output_root: str | Path,
    plan: EvaluationPlan,
    canonical_tables: Mapping[
        tuple[Direction, CheckpointPolicy],
        Mapping[MethodId, tuple[SubjectPrediction, ...]],
    ],
    report_statistics: Mapping[tuple[Direction, CheckpointPolicy], ReportStatistics],
    *,
    root_metadata: Mapping[str, object],
    policy_metadata: Mapping[tuple[Direction, CheckpointPolicy], Mapping[str, object]],
    identity_inputs: Mapping[str, object],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    ci_policy: str,
    gate_states: Mapping[str, bool],
    created_utc: str,
    completed_utc: str,
    disposition: str = "completed",
    overwrite: bool = False,
    writer: OutputWriter | None = None,
    replace: ReplacePath = os.replace,
) -> Path:
    """Project one exact completed tree, verify it, then publish atomically."""
    required_root = {
        "resolved_config", "provenance_records", "method_status_rows",
        "computational_rows", "log_events",
    }
    if set(root_metadata) != required_root:
        raise ValueError("root metadata fields must be exact")
    artifacts = {
        "evaluation_config_resolved.yaml": resolved_config_bytes(root_metadata["resolved_config"]),
        "provenance_report.json": provenance_report_bytes(root_metadata["provenance_records"]),
        "method_status.csv": method_status_bytes(root_metadata["method_status_rows"]),
        "computational_summary.csv": computational_summary_bytes(root_metadata["computational_rows"]),
        "evaluation_log.txt": evaluation_log_bytes(root_metadata["log_events"]),
    }
    expected_scopes = tuple(
        (direction, policy) for direction in plan.directions
        for policy in plan.checkpoint_policies
    )
    if set(canonical_tables) != set(expected_scopes) or set(policy_metadata) != set(expected_scopes):
        raise ValueError("report scope inputs must exactly match the plan")
    for direction, policy in expected_scopes:
        scope = (direction, policy)
        base = f"predictive/{direction.value}/{policy.value}"
        artifacts[f"{base}/inclusion_report.csv"] = inclusion_report_bytes(
            policy_metadata[scope]["inclusion_rows"]
        )
        tables = canonical_tables[scope]
        if tables:
            artifacts.update(_statistics_artifacts(
                plan, direction, policy, tables, report_statistics[scope]
            ))
        else:
            raise ValueError("included report scopes require canonical tables")
    ordinary_expected = set(plan.intended_relative_paths) - {
        "artifact_index.json", "evaluation_manifest.json"
    }
    if set(artifacts) != ordinary_expected:
        raise ValueError("projected artifacts do not exactly match the output plan")
    if "artifact_index.json" in plan.intended_relative_paths:
        artifacts["artifact_index.json"] = build_artifact_index(artifacts)
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, artifacts, identity_inputs=identity_inputs,
        library_versions=library_versions, bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed, ci_policy=ci_policy, gate_states=gate_states,
        created_utc=created_utc, completed_utc=completed_utc,
        disposition=disposition,
    )
    if set(artifacts) != set(plan.intended_relative_paths):
        raise ValueError("completed artifacts do not exactly match the output plan")
    options = {"overwrite": overwrite, "replace": replace}
    if writer is not None:
        options["writer"] = writer
    return commit_output(output_root, plan, artifacts, **options)


def _default_output_writer(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _relative_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def _replace_with_permission_retry(
    replace: ReplacePath,
    source: str | Path,
    destination: str | Path,
    *,
    attempts: int = 10,
    delay_seconds: float = 0.02,
) -> None:
    for attempt in range(attempts):
        try:
            replace(source, destination)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(delay_seconds)


def commit_output(
    output_root: str | Path,
    plan: EvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    overwrite: bool = False,
    writer: OutputWriter = _default_output_writer,
    replace: ReplacePath = os.replace,
) -> Path:
    """Stage a complete allowlisted tree and publish it with the manifest written last."""
    output = Path(output_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    expected = tuple(plan.intended_relative_paths)
    if set(artifacts) != set(expected) or any(not isinstance(artifacts[path], bytes) for path in expected):
        raise ValueError("output artifacts must exactly match the evaluation plan")
    if output.exists():
        if not output.is_dir() or not overwrite:
            raise ExistingOutputError("recognized output exists and overwrite is not authorized")
        unknown = _relative_files(output) - set(expected)
        if unknown:
            raise ExistingOutputError(f"unknown output paths block overwrite: {sorted(unknown)}")

    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage.", dir=output.parent))
    token = stage.name.rsplit(".", maxsplit=1)[-1]
    backup = output.parent / f".{output.name}.backup.{token}"
    moved_existing = False
    try:
        for relative_path in expected:
            writer(stage / relative_path, artifacts[relative_path])
        if output.exists():
            _replace_with_permission_retry(replace, output, backup)
            moved_existing = True
        _replace_with_permission_retry(replace, stage, output)
        if backup.exists():
            shutil.rmtree(backup)
        return output
    except Exception as error:
        restored = False
        if moved_existing and backup.exists() and not output.exists():
            try:
                _replace_with_permission_retry(replace, backup, output)
                restored = True
            except Exception as restore_error:
                raise OutputCommitError(
                    f"output commit and restoration failed; backup remains at {backup}"
                ) from restore_error
        message = "output commit failed; previous tree restored" if restored else "output commit failed"
        raise OutputCommitError(message) from error
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if backup.exists() and output.exists():
            shutil.rmtree(backup, ignore_errors=True)


def build_artifact_index(artifacts: Mapping[str, bytes]) -> bytes:
    """Build the optional self-excluding exact artifact hash inventory."""
    if "artifact_index.json" in artifacts:
        raise ValueError("artifact index input must exclude itself")
    if any(not path or not isinstance(payload, bytes) for path, payload in artifacts.items()):
        raise ValueError("artifact index inputs must be named byte payloads")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifacts": {
            path: hashlib.sha256(artifacts[path]).hexdigest()
            for path in sorted(artifacts)
        },
    }
    return (canonical_json(payload) + "\n").encode("utf-8")


def build_completion_manifest(
    plan: EvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    identity_inputs: Mapping[str, object],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 0,
    ci_policy: str = "percentile_95_linear",
    gate_states: Mapping[str, bool] | None = None,
    created_utc: str = "1970-01-01T00:00:00Z",
    completed_utc: str = "1970-01-01T00:00:00Z",
    disposition: str = "completed",
) -> bytes:
    """Build the identity-bound completion marker over every non-manifest artifact."""
    expected = tuple(path for path in plan.intended_relative_paths if path != "evaluation_manifest.json")
    if set(artifacts) != set(expected):
        raise ValueError("completion manifest artifacts must match every non-manifest output")
    required_gates = ("authorized_exports", "D-14-001", "D-14-002", "protocol_approval")
    gates = dict.fromkeys(required_gates, False) if gate_states is None else dict(gate_states)
    if tuple(gates) != required_gates or any(not isinstance(value, bool) for value in gates.values()):
        raise ValueError("all four ordered gate states are required")
    configuration_hash = identity_inputs.get("configuration_sha256", "0" * 64)
    authorization_hash = identity_inputs.get("authorization_sha256", "0" * 64)
    ordered_inputs = identity_inputs.get("ordered_input_sha256s", [])
    if not isinstance(configuration_hash, str) or not isinstance(authorization_hash, str):
        raise ValueError("configuration and authorization hashes are invalid")
    if not isinstance(ordered_inputs, list):
        raise ValueError("ordered input hashes are required")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "evaluation_identity": plan.evaluation_identity,
        "analysis_mode": plan.analysis_mode.value,
        "created_utc": created_utc,
        "completed_utc": completed_utc,
        "methods": [method.value for method in plan.methods],
        "directions": [direction.value for direction in plan.directions],
        "checkpoint_policies": [policy.value for policy in plan.checkpoint_policies],
        "class_order": {"CN": 0, "MCI": 1, "AD": 2},
        "bootstrap": {
            "replicates": bootstrap_replicates, "seed": bootstrap_seed,
            "ci_policy": ci_policy,
        },
        "configuration_sha256": configuration_hash,
        "authorization_sha256": authorization_hash,
        "gate_states": gates,
        "ordered_input_sha256s": ordered_inputs,
        "identity_inputs": dict(identity_inputs),
        "library_versions": dict(library_versions),
        "output_sha256s": {
            path: hashlib.sha256(artifacts[path]).hexdigest()
            for path in sorted(expected)
        },
        "disposition": disposition,
    }
    return (canonical_json(payload) + "\n").encode("utf-8")


def verify_reuse(
    output_root: str | Path,
    plan: EvaluationPlan,
    *,
    expected_identity_inputs: Mapping[str, object],
    expected_library_versions: Mapping[str, str],
    expected_bootstrap: Mapping[str, object] | None = None,
    expected_gate_states: Mapping[str, bool] | None = None,
    expected_disposition: str | None = None,
) -> ReportOutcome:
    """Verify one completed tree without creating, modifying, or deleting any path."""
    output = Path(output_root)
    manifest_path = output / "evaluation_manifest.json"
    if not output.is_dir() or not manifest_path.is_file():
        raise ReuseVerificationError("completed evaluation manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReuseVerificationError("completion manifest is unreadable") from error

    expected_manifest = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "evaluation_identity": plan.evaluation_identity,
        "analysis_mode": plan.analysis_mode.value,
        "methods": [method.value for method in plan.methods],
        "directions": [direction.value for direction in plan.directions],
        "checkpoint_policies": [policy.value for policy in plan.checkpoint_policies],
        "class_order": {"CN": 0, "MCI": 1, "AD": 2},
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            raise ReuseVerificationError(f"reuse identity mismatch for {field}")
    if manifest.get("identity_inputs") != dict(expected_identity_inputs):
        raise ReuseVerificationError("reuse identity inputs mismatch")
    if manifest.get("library_versions") != dict(expected_library_versions):
        raise ReuseVerificationError("reuse library versions mismatch")

    expected_completion = {
        field: expected_identity_inputs[field]
        for field in (
            "configuration_sha256", "authorization_sha256", "ordered_input_sha256s"
        )
        if field in expected_identity_inputs
    }
    if expected_bootstrap is not None:
        expected_completion["bootstrap"] = dict(expected_bootstrap)
    if expected_gate_states is not None:
        expected_completion["gate_states"] = dict(expected_gate_states)
    if expected_disposition is not None:
        expected_completion["disposition"] = expected_disposition
    for field, expected in expected_completion.items():
        if manifest.get(field) != expected:
            raise ReuseVerificationError(f"reuse identity mismatch for {field}")
    for field in ("created_utc", "completed_utc"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ReuseVerificationError(f"reuse identity mismatch for {field}")

    expected_files = set(plan.intended_relative_paths)
    actual_files = _relative_files(output)
    optional_index = "artifact_index.json"
    if actual_files - expected_files - {optional_index} or expected_files - actual_files:
        raise ReuseVerificationError("reuse required file set mismatch")
    output_hashes = manifest.get("output_sha256s")
    expected_hashed = expected_files - {"evaluation_manifest.json"}
    if not isinstance(output_hashes, dict) or set(output_hashes) != expected_hashed:
        raise ReuseVerificationError("reuse output hash inventory mismatch")
    actual_hashes = {}
    for relative_path in sorted(expected_hashed):
        digest = hashlib.sha256((output / relative_path).read_bytes()).hexdigest()
        actual_hashes[relative_path] = digest
        if output_hashes[relative_path] != digest:
            raise ReuseVerificationError(f"reuse output hash mismatch: {relative_path}")
    if optional_index in actual_files:
        try:
            index = json.loads((output / optional_index).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ReuseVerificationError("artifact index is unreadable") from error
        index_hashes = {
            path: digest for path, digest in actual_hashes.items()
            if path != optional_index
        }
        if index != {"schema_version": SCHEMA_VERSION, "artifacts": index_hashes}:
            raise ReuseVerificationError("artifact index hash inventory mismatch")
    return ReportOutcome(ReportState.REUSED, plan, None)
