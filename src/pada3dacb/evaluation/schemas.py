"""Pure, versioned contracts for Phase 15 predictive evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Generic, TypeVar

SCHEMA_VERSION = "phase15-output-v2"
PROTOCOL_VERSION = "phase15-statistical-v2"
ANALYSIS_CLASS_LABELS = ("CN", "MCI", "AD")
ANALYSIS_CLASS_INDICES = (0, 1, 2)
AGGREGATE_METRIC_NAMES = (
    "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1",
    "macro_precision", "macro_recall", "multiclass_mcc", "cohen_kappa",
    "multiclass_log_loss", "multiclass_brier_score",
    "macro_ovr_roc_auc", "macro_ovr_average_precision",
)
PER_CLASS_METRIC_NAMES = (
    "support", "precision", "recall", "sensitivity",
    "specificity", "f1", "ovr_roc_auc", "ovr_average_precision",
)
PAIRED_METRIC_NAMES = (
    "accuracy", "balanced_accuracy", "macro_f1", "multiclass_mcc",
    "macro_ovr_roc_auc",
)
REQUIRED_PROVENANCE_FIELDS = (
    "method_id", "public_model_name", "direction", "source_cohort", "target_cohort",
    "seed", "fold", "logical_checkpoint", "checkpoint_epoch", "experiment_hash",
    "model_configuration_hash", "training_configuration_hash", "source_subject_assignment_hash",
    "source_train_assignment_hash", "source_validation_assignment_hash",
    "target_subject_assignment_hash", "target_adaptation_assignment_hash",
    "target_evaluation_assignment_hash", "split_assignment_hash", "atlas_hash",
    "roi_order_hash", "class_order",
)
T = TypeVar("T")


class MethodId(str, Enum):
    SOURCE_ONLY = "source_only"
    CORAL = "coral"
    MMD = "mmd"
    CDAN = "cdan"
    PROTOTYPE_PSEUDO = "prototype_pseudo"
    AAGN = "aagn"
    FASTER_SNN = "faster_snn"


COMPARATOR_METHODS = (
    MethodId.SOURCE_ONLY, MethodId.CORAL, MethodId.MMD,
    MethodId.CDAN, MethodId.AAGN, MethodId.FASTER_SNN,
)


class Direction(str, Enum):
    ADNI_TO_OASIS = "adni_to_oasis"
    OASIS_TO_ADNI = "oasis_to_adni"

    @property
    def cohorts(self) -> tuple[str, str]:
        return ("ADNI", "OASIS") if self is self.ADNI_TO_OASIS else ("OASIS", "ADNI")


class CheckpointPolicy(str, Enum):
    PRIMARY_BEST_SOURCE_F1 = "primary_best_source_f1"
    SENSITIVITY_LAST = "sensitivity_last"

    @property
    def logical_checkpoint(self) -> str:
        return "best_source_f1" if self is self.PRIMARY_BEST_SOURCE_F1 else "last"


class PredictionRole(str, Enum):
    SOURCE_OOF = "source_oof"
    TARGET_EVALUATION = "target_evaluation"


class AnalysisMode(str, Enum):
    REAL = "real"
    SYNTHETIC_TEST_ONLY = "synthetic_test_only"


class RunMode(str, Enum):
    DRY_RUN = "dry_run"
    VALIDATE_ONLY = "validate_only"
    EVALUATE = "evaluate"
    REUSE = "reuse"


class ValueStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_RECORDED = "not_recorded"


class CandidateStatus(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    INCOMPLETE = "incomplete"


class IssueCode(str, Enum):
    UNSUPPORTED_METHOD = "unsupported_method"
    UNSUPPORTED_DIRECTION = "unsupported_direction"
    UNSUPPORTED_CHECKPOINT_POLICY = "unsupported_checkpoint_policy"
    UNSUPPORTED_CLASS_ORDER = "unsupported_class_order"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNAPPROVED_IDENTITY_MAPPING = "unapproved_identity_mapping"
    PROVENANCE_CONFLICT = "provenance_conflict"
    INPUT_HASH_MISMATCH = "input_hash_mismatch"
    TARGET_EVALUATION_MEMBERSHIP_UNPROVABLE = "target_evaluation_membership_unprovable"
    UNSTABLE_SUBJECT_IDENTITY = "unstable_subject_identity"
    RAW_IDENTIFIER_PERSISTENCE_ATTEMPT = "raw_identifier_persistence_attempt"
    DUPLICATE_PREDICTION = "duplicate_prediction"
    INCONSISTENT_TRUE_LABEL = "inconsistent_true_label"
    NON_FINITE_PROBABILITY = "non_finite_probability"
    PROBABILITY_OUT_OF_RANGE = "probability_out_of_range"
    PROBABILITY_SUM_INVALID = "probability_sum_invalid"
    INCOMPLETE_ENSEMBLE = "incomplete_ensemble"
    CHECKPOINT_POLICY_MISMATCH = "checkpoint_policy_mismatch"
    INCOMPATIBLE_SUBJECTS = "incompatible_subjects"


@dataclass(frozen=True)
class MetricValue:
    value: float | int | None
    status: ValueStatus
    reason: str | None

    def __post_init__(self) -> None:
        available = self.status is ValueStatus.AVAILABLE
        finite_number = (
            not isinstance(self.value, bool)
            and isinstance(self.value, (float, int))
            and math.isfinite(self.value)
        )
        if available and (not finite_number or self.reason is not None):
            raise ValueError("available values must be finite and have no reason")
        if not available and (self.value is not None or not self.reason):
            raise ValueError("unavailable values must be null and include a reason")

    @classmethod
    def available(cls, value: float | int) -> MetricValue:
        return cls(value=value, status=ValueStatus.AVAILABLE, reason=None)

    @classmethod
    def unavailable(cls, reason: str) -> MetricValue:
        return cls(value=None, status=ValueStatus.UNAVAILABLE, reason=reason)


@dataclass(frozen=True)
class PerClassMetric:
    class_label: str
    class_index: int
    support: MetricValue
    metric: str
    value: MetricValue

    def __post_init__(self) -> None:
        if self.class_index not in ANALYSIS_CLASS_INDICES:
            raise ValueError("class index is invalid")
        if self.class_label != ANALYSIS_CLASS_LABELS[self.class_index]:
            raise ValueError("class label and index must match")
        if self.metric not in PER_CLASS_METRIC_NAMES:
            raise ValueError("per-class metric name is invalid")
        if self.support.status is ValueStatus.AVAILABLE and (
            not isinstance(self.support.value, int) or isinstance(self.support.value, bool)
        ):
            raise ValueError("available support must be an integer")
        if self.metric == "support" and self.value != self.support:
            raise ValueError("support row value must equal support")


@dataclass(frozen=True)
class MetricSet:
    subject_count: int
    aggregate_metrics: Mapping[str, MetricValue]
    per_class_metrics: tuple[PerClassMetric, ...]

    def __post_init__(self) -> None:
        if self.subject_count < 0 or tuple(self.aggregate_metrics) != AGGREGATE_METRIC_NAMES:
            raise ValueError("aggregate metrics must be complete and ordered")
        expected = tuple(
            (index, metric)
            for index in ANALYSIS_CLASS_INDICES
            for metric in PER_CLASS_METRIC_NAMES
        )
        actual = tuple((row.class_index, row.metric) for row in self.per_class_metrics)
        if actual != expected:
            raise ValueError("per-class metrics must be complete and ordered")
        for index in ANALYSIS_CLASS_INDICES:
            recall = self.per_class_metrics[index * 8 + 2].value
            sensitivity = self.per_class_metrics[index * 8 + 3].value
            if recall != sensitivity:
                raise ValueError("recall and sensitivity must match")
        object.__setattr__(self, "aggregate_metrics", MappingProxyType(dict(self.aggregate_metrics)))
        object.__setattr__(self, "per_class_metrics", tuple(self.per_class_metrics))


@dataclass(frozen=True)
class ConfusionResult:
    counts: tuple[tuple[int, int, int], ...]
    normalized: tuple[tuple[float | None, float | None, float | None], ...]
    normalized_row_statuses: tuple[MetricValue, ...]

    def __post_init__(self) -> None:
        counts = tuple(tuple(row) for row in self.counts)
        normalized = tuple(tuple(row) for row in self.normalized)
        statuses = tuple(self.normalized_row_statuses)
        if len(counts) != 3 or any(len(row) != 3 for row in counts):
            raise ValueError("confusion counts must have fixed 3x3 shape")
        if len(normalized) != 3 or any(len(row) != 3 for row in normalized) or len(statuses) != 3:
            raise ValueError("normalized confusion data must have fixed 3x3 shape")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for row in counts for value in row):
            raise ValueError("confusion counts must be non-negative integers")
        for count_row, normalized_row, status in zip(counts, normalized, statuses, strict=True):
            support = sum(count_row)
            if support == 0:
                if any(value is not None for value in normalized_row) or status.reason != "zero_true_support":
                    raise ValueError("zero-support rows must be null and unavailable")
            else:
                values = tuple(value for value in normalized_row if value is not None)
                if len(values) != 3 or status != MetricValue.available(support):
                    raise ValueError("supported normalized row status is invalid")
                if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
                    raise ValueError("normalized confusion values are invalid")
                if abs(math.fsum(values) - 1.0) > 1e-12:
                    raise ValueError("normalized confusion row must sum to one")
        object.__setattr__(self, "counts", counts)
        object.__setattr__(self, "normalized", normalized)
        object.__setattr__(self, "normalized_row_statuses", statuses)

    @property
    def subject_count(self) -> int:
        return sum(value for row in self.counts for value in row)


def _valid_finite(value: float | None) -> bool:
    return value is not None and not isinstance(value, bool) and math.isfinite(value)


def _validate_bootstrap_counts(requested: int, successful: int, invalid: int) -> None:
    values = (requested, successful, invalid)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("bootstrap counts must be integers")
    if requested <= 0 or successful < 0 or invalid < 0 or successful + invalid != requested:
        raise ValueError("bootstrap counts are inconsistent")


@dataclass(frozen=True)
class BootstrapInterval:
    metric: str
    point_estimate: float | None
    ci_level: float
    ci_method: str
    ci_low: float | None
    ci_high: float | None
    bootstrap_seed: int
    requested: int
    successful: int
    invalid: int
    status: ValueStatus
    reason: str | None

    def __post_init__(self) -> None:
        if self.metric not in AGGREGATE_METRIC_NAMES:
            raise ValueError("bootstrap metric is invalid")
        if self.ci_level != 0.95 or self.ci_method != "percentile":
            raise ValueError("bootstrap interval definition is invalid")
        _validate_bootstrap_counts(self.requested, self.successful, self.invalid)
        available = self.status is ValueStatus.AVAILABLE
        if available:
            values = (self.point_estimate, self.ci_low, self.ci_high)
            if not all(_valid_finite(value) for value in values) or self.reason is not None:
                raise ValueError("available bootstrap intervals require finite values and no reason")
            if self.ci_low > self.ci_high or self.successful < math.ceil(0.95 * self.requested):  # type: ignore[operator]
                raise ValueError("available bootstrap interval is inconsistent")
        elif self.status is not ValueStatus.UNAVAILABLE or self.ci_low is not None or self.ci_high is not None or not self.reason:
            raise ValueError("unavailable bootstrap intervals require null limits and a reason")
        if self.point_estimate is not None and not _valid_finite(self.point_estimate):
            raise ValueError("point estimate must be finite when present")


@dataclass(frozen=True)
class PairedDifference:
    comparator_method: MethodId
    metric: str
    orientation: str
    observed_difference: float | None
    ci_level: float
    ci_method: str
    ci_low: float | None
    ci_high: float | None
    p_value_method: str
    raw_p_value: float | None
    bootstrap_seed: int
    requested: int
    successful: int
    invalid: int
    status: ValueStatus
    reason: str | None

    def __post_init__(self) -> None:
        if self.comparator_method not in COMPARATOR_METHODS or self.metric not in PAIRED_METRIC_NAMES:
            raise ValueError("paired comparator or metric is invalid")
        if self.orientation != "prototype_pseudo-comparator" or self.ci_level != 0.95:
            raise ValueError("paired orientation or interval level is invalid")
        if self.ci_method != "percentile" or self.p_value_method != "centered_plus_one":
            raise ValueError("paired inference method is invalid")
        _validate_bootstrap_counts(self.requested, self.successful, self.invalid)
        available = self.status is ValueStatus.AVAILABLE
        values = (self.observed_difference, self.ci_low, self.ci_high, self.raw_p_value)
        if available:
            if not all(_valid_finite(value) for value in values) or self.reason is not None:
                raise ValueError("available paired differences require finite values and no reason")
            if self.ci_low > self.ci_high or not 0.0 <= self.raw_p_value <= 1.0:  # type: ignore[operator]
                raise ValueError("paired interval or p-value is invalid")
            if self.successful < math.ceil(0.95 * self.requested):
                raise ValueError("available paired difference has insufficient replicates")
        elif self.status is not ValueStatus.UNAVAILABLE or any(value is not None for value in (self.ci_low, self.ci_high, self.raw_p_value)) or not self.reason:
            raise ValueError("unavailable paired differences require null inference and a reason")
        if self.observed_difference is not None and not _valid_finite(self.observed_difference):
            raise ValueError("observed difference must be finite when present")


@dataclass(frozen=True)
class McNemarResult:
    comparator_method: MethodId
    n_subjects: int
    n00_both_wrong: int
    n01_reference_correct: int
    n10_comparator_correct: int
    n11_both_correct: int
    discordant_count: int
    test: str
    raw_p_value: float | None
    status: ValueStatus
    reason: str | None
    note_code: str | None = None

    def __post_init__(self) -> None:
        counts = (
            self.n_subjects, self.n00_both_wrong, self.n01_reference_correct,
            self.n10_comparator_correct, self.n11_both_correct, self.discordant_count,
        )
        if self.comparator_method not in COMPARATOR_METHODS:
            raise ValueError("McNemar comparator is invalid")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("McNemar contingency counts are invalid")
        cells = counts[1:5]
        if sum(cells) != self.n_subjects or self.n01_reference_correct + self.n10_comparator_correct != self.discordant_count:
            raise ValueError("McNemar contingency counts are inconsistent")
        if self.test != "exact_two_sided_mcnemar":
            raise ValueError("McNemar test identifier is invalid")
        if self.status is ValueStatus.AVAILABLE:
            if not _valid_finite(self.raw_p_value) or not 0.0 <= self.raw_p_value <= 1.0 or self.reason is not None:  # type: ignore[operator]
                raise ValueError("available McNemar results require a valid p-value and no reason")
            expected_note = "no_discordant_pairs" if self.discordant_count == 0 else None
            if self.note_code != expected_note or (self.discordant_count == 0 and self.raw_p_value != 1.0):
                raise ValueError("McNemar informational note is inconsistent")
        elif self.status is not ValueStatus.UNAVAILABLE or self.raw_p_value is not None or not self.reason or self.note_code is not None:
            raise ValueError("unavailable McNemar results require null inference and a reason")


@dataclass(frozen=True)
class HolmRow:
    statistic_family: str
    metric: str | None
    family_size: int
    available_count: int
    comparator_method: MethodId
    raw_p_value: float | None
    holm_rank: int | None
    adjusted_p_value: float | None
    status: ValueStatus
    reason: str | None

    def __post_init__(self) -> None:
        paired = self.statistic_family == "paired_bootstrap"
        if self.statistic_family not in {"mcnemar_accuracy", "paired_bootstrap"}:
            raise ValueError("Holm statistic family is invalid")
        if (paired and self.metric not in PAIRED_METRIC_NAMES) or (not paired and self.metric not in {None, "accuracy"}):
            raise ValueError("Holm metric is invalid")
        if self.family_size != 6 or not 0 <= self.available_count <= self.family_size:
            raise ValueError("Holm family counts are invalid")
        if self.comparator_method not in COMPARATOR_METHODS:
            raise ValueError("Holm comparator is invalid")
        if self.status is ValueStatus.AVAILABLE:
            p_values = (self.raw_p_value, self.adjusted_p_value)
            if not all(_valid_finite(value) and 0.0 <= value <= 1.0 for value in p_values):  # type: ignore[operator]
                raise ValueError("Holm p-values are invalid")
            if self.holm_rank is None or not 1 <= self.holm_rank <= self.available_count or self.reason is not None:
                raise ValueError("available Holm rank or reason is invalid")
        elif self.status is not ValueStatus.UNAVAILABLE or any(
            value is not None for value in (self.raw_p_value, self.holm_rank, self.adjusted_p_value)
        ) or not self.reason:
            raise ValueError("unavailable Holm rows require null inference and a reason")


@dataclass(frozen=True)
class CandidateIssue:
    code: IssueCode
    status: CandidateStatus
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.status is CandidateStatus.INCLUDED:
            raise ValueError("included candidates cannot carry issues")


@dataclass(frozen=True)
class EvaluationRequest:
    methods: tuple[MethodId, ...]
    directions: tuple[Direction, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    analysis_mode: AnalysisMode
    run_mode: RunMode
    bootstrap_replicates: int
    bootstrap_seed: int

    def __post_init__(self) -> None:
        selections = (self.methods, self.directions, self.checkpoint_policies)
        if any(not items or len(set(items)) != len(items) for items in selections):
            raise ValueError("selectors must be non-empty and contain no duplicates")
        if isinstance(self.bootstrap_replicates, bool) or self.bootstrap_replicates <= 0:
            raise ValueError("bootstrap_replicates must be a positive integer")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _is_safe_relative_path(value: str) -> bool:
    parts = value.split("/")
    return bool(value) and not value.startswith("/") and "\\" not in value and ".." not in parts


@dataclass(frozen=True)
class IdentityMapping:
    relative_path: str
    sha256: str
    raw_identifier_field: str
    subject_hash_field: str
    approved: bool

    def __post_init__(self) -> None:
        if not _is_safe_relative_path(self.relative_path) or not _is_sha256(self.sha256):
            raise ValueError("identity mapping path and hash must be approved immutable inputs")
        if self.approved is not True:
            raise ValueError("identity mapping must be explicitly approved")
        if (
            not self.raw_identifier_field
            or not self.raw_identifier_field.isidentifier()
            or self.raw_identifier_field in {"subject_hash", "true_label", "probabilities"}
        ):
            raise ValueError("raw identifier field must be transient and distinct")
        if self.subject_hash_field != "subject_hash":
            raise ValueError("identity mapping must supply the canonical subject_hash field")


@dataclass(frozen=True)
class ExpectedPopulation:
    direction: Direction
    role: PredictionRole
    relative_path: str
    sha256: str
    subject_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.direction, Direction) or not isinstance(self.role, PredictionRole):
            raise ValueError("expected population direction and role are invalid")
        if not _is_safe_relative_path(self.relative_path) or not _is_sha256(self.sha256):
            raise ValueError("expected population path and hash must be immutable inputs")
        hashes = tuple(self.subject_hashes)
        if (
            not hashes
            or any(not isinstance(value, str) or not value for value in hashes)
            or len(hashes) != len(set(hashes))
            or hashes != tuple(sorted(hashes))
        ):
            raise ValueError("expected population hashes must be non-empty, unique, and canonical")
        object.__setattr__(self, "subject_hashes", hashes)


@dataclass(frozen=True)
class ComputationalValue:
    field: str
    value: float | int | None
    unit: str
    status: ValueStatus
    reason: str | None
    source_sha256: str | None

    def __post_init__(self) -> None:
        if not self.field or not self.unit:
            raise ValueError("computational field and unit are required")
        if self.status is ValueStatus.AVAILABLE:
            valid = (
                not isinstance(self.value, bool)
                and isinstance(self.value, (float, int))
                and math.isfinite(self.value)
            )
            if not valid or self.reason is not None or self.source_sha256 is None:
                raise ValueError("available computational values require finite value, source, and no reason")
        elif self.value is not None or not self.reason:
            raise ValueError("non-available computational values require a null value and reason")
        if self.source_sha256 is not None and not _is_sha256(self.source_sha256):
            raise ValueError("computational source must be a SHA-256")


@dataclass(frozen=True)
class EvaluationPlan:
    evaluation_identity: str
    analysis_mode: AnalysisMode
    methods: tuple[MethodId, ...]
    directions: tuple[Direction, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    intended_relative_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _is_sha256(self.evaluation_identity):
            raise ValueError("evaluation identity must be a SHA-256")
        selections = (self.methods, self.directions, self.checkpoint_policies)
        if any(not values or len(values) != len(set(values)) for values in selections):
            raise ValueError("evaluation plan selections must be non-empty and unique")
        paths = tuple(self.intended_relative_paths)
        if not paths or len(paths) != len(set(paths)):
            raise ValueError("intended paths must be non-empty and unique")
        for path in paths:
            parts = path.split("/")
            if not path or path.startswith("/") or "\\" in path or ".." in parts:
                raise ValueError("intended outputs must use safe relative POSIX paths")
        if paths[-1] != "evaluation_manifest.json":
            raise ValueError("evaluation manifest must be the final intended output")
        for name in ("methods", "directions", "checkpoint_policies", "intended_relative_paths"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


@dataclass(frozen=True)
class InputFile:
    relative_path: str
    sha256: str
    size_bytes: int
    schema_family: str
    schema_version: str

    def __post_init__(self) -> None:
        if not _is_safe_relative_path(self.relative_path):
            raise ValueError("relative_path must be a sanitized root-relative POSIX path")
        if not _is_sha256(self.sha256) or self.size_bytes < 0:
            raise ValueError("input hash and size are invalid")
        if not self.schema_family or not self.schema_version:
            raise ValueError("schema family and version are required")


@dataclass(frozen=True)
class ProvenanceValue(Generic[T]):
    field_name: str
    value: T
    source_kind: str
    source_file_sha256: str
    derivation_rule: str | None = None

    def __post_init__(self) -> None:
        if self.field_name == "subject_hash":
            raise ValueError("subject_hash is identity and cannot be a derived provenance value")
        if not self.field_name or not self.source_kind or not _is_sha256(self.source_file_sha256):
            raise ValueError("provenance source identity is invalid")
        if self.derivation_rule is not None and not self.derivation_rule:
            raise ValueError("derivation_rule must be non-empty when supplied")


@dataclass(frozen=True)
class ProvenanceRecord:
    values: Mapping[str, ProvenanceValue[Any]]
    input_sha256s: tuple[str, ...]
    equality_checks: tuple[str, ...]

    def __post_init__(self) -> None:
        if tuple(self.values) != REQUIRED_PROVENANCE_FIELDS:
            raise ValueError("required provenance fields must be complete and ordered")
        if any(value.field_name != name for name, value in self.values.items()):
            raise ValueError("provenance field names must match their keys")
        if not self.input_sha256s or any(not _is_sha256(value) for value in self.input_sha256s):
            raise ValueError("ordered input hashes are required")
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))
        object.__setattr__(self, "input_sha256s", tuple(self.input_sha256s))
        object.__setattr__(self, "equality_checks", tuple(self.equality_checks))


@dataclass(frozen=True)
class CanonicalPrediction:
    method_id: MethodId
    direction: Direction
    seed: int
    fold: int
    logical_checkpoint: str
    role: PredictionRole
    subject_hash: str
    true_label: int
    probabilities: tuple[float, float, float]
    provenance_ref: str

    def __post_init__(self) -> None:
        probabilities = tuple(self.probabilities)
        if self.seed < 0 or self.fold < 0 or self.logical_checkpoint not in {"best_source_f1", "last"}:
            raise ValueError("seed, fold, or logical checkpoint is invalid")
        if not self.subject_hash or self.true_label not in ANALYSIS_CLASS_INDICES:
            raise ValueError("subject identity or true label is invalid")
        if len(probabilities) != 3 or any(not math.isfinite(value) for value in probabilities):
            raise ValueError("probabilities must contain three finite values")
        if any(value < 0.0 or value > 1.0 for value in probabilities) or abs(math.fsum(probabilities) - 1.0) > 1e-6:
            raise ValueError("probabilities must be in [0,1] and sum to one")
        if not _is_sha256(self.provenance_ref):
            raise ValueError("provenance_ref must be a SHA-256")
        object.__setattr__(self, "probabilities", probabilities)

    @property
    def predicted_label(self) -> int:
        return max(ANALYSIS_CLASS_INDICES, key=self.probabilities.__getitem__)


@dataclass(frozen=True)
class SubjectPrediction:
    method_id: MethodId
    direction: Direction
    checkpoint_policy: CheckpointPolicy
    subject_hash: str
    true_label: int
    probabilities: tuple[float, float, float]
    fold_count: int
    seed_count: int
    source_file_sha256s: tuple[str, ...]
    status: ValueStatus = ValueStatus.AVAILABLE
    reason: str | None = None

    def __post_init__(self) -> None:
        probabilities = tuple(self.probabilities)
        hashes = tuple(self.source_file_sha256s)
        if not self.subject_hash or self.true_label not in ANALYSIS_CLASS_INDICES:
            raise ValueError("subject identity or true label is invalid")
        if len(probabilities) != 3 or any(not math.isfinite(value) for value in probabilities):
            raise ValueError("probabilities must contain three finite values")
        if any(value < 0.0 or value > 1.0 for value in probabilities) or abs(math.fsum(probabilities) - 1.0) > 1e-6:
            raise ValueError("probabilities must be in [0,1] and sum to one")
        if self.fold_count <= 0 or self.seed_count <= 0:
            raise ValueError("complete positive fold and seed counts are required")
        if not hashes or len(set(hashes)) != len(hashes) or any(not _is_sha256(value) for value in hashes):
            raise ValueError("ordered unique source hashes are required")
        if self.status is not ValueStatus.AVAILABLE or self.reason is not None:
            raise ValueError("final subject predictions must be available with no reason")
        object.__setattr__(self, "probabilities", probabilities)
        object.__setattr__(self, "source_file_sha256s", hashes)

    @property
    def predicted_label(self) -> int:
        return max(ANALYSIS_CLASS_INDICES, key=self.probabilities.__getitem__)


@dataclass(frozen=True)
class EvaluationBundle:
    evaluation_identity: str
    subject_tables: Mapping[str, tuple[SubjectPrediction, ...]]
    result_sha256s: Mapping[str, str]
    computational_values: tuple[ComputationalValue, ...]

    def __post_init__(self) -> None:
        if not _is_sha256(self.evaluation_identity):
            raise ValueError("bundle identity must be a SHA-256")
        subject_tables = {
            method: tuple(rows) for method, rows in self.subject_tables.items()
        }
        if not subject_tables:
            raise ValueError("bundle subject tables are required")
        for method, rows in subject_tables.items():
            if method not in {item.value for item in MethodId} or not rows:
                raise ValueError("bundle method and subject table are invalid")
            if any(row.method_id.value != method for row in rows):
                raise ValueError("bundle subject-table method is inconsistent")
        result_sha256s = dict(self.result_sha256s)
        if not result_sha256s or any(not _is_sha256(value) for value in result_sha256s.values()):
            raise ValueError("bundle result hashes are required and must be SHA-256")
        object.__setattr__(self, "subject_tables", MappingProxyType(subject_tables))
        object.__setattr__(self, "result_sha256s", MappingProxyType(result_sha256s))
        object.__setattr__(self, "computational_values", tuple(self.computational_values))


@dataclass(frozen=True)
class NormalizedBatch:
    adapter_id: str
    schema_family: str
    input_files: tuple[InputFile, ...]
    provenance_records: tuple[ProvenanceRecord, ...]
    predictions: tuple[CanonicalPrediction, ...]
    computational_records: tuple[Mapping[str, Any], ...]
    issues: tuple[CandidateIssue, ...]

    def __post_init__(self) -> None:
        if not self.adapter_id or not self.schema_family:
            raise ValueError("adapter and schema family are required")
        if any(item.schema_family != self.schema_family for item in self.input_files):
            raise ValueError("input schema family must match normalized batch")
        for name in ("input_files", "provenance_records", "predictions", "issues"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        records = tuple(MappingProxyType(dict(record)) for record in self.computational_records)
        object.__setattr__(self, "computational_records", records)


class EvaluationError(RuntimeError):
    """Base class for sanitized request-level failures."""


_ERROR_TYPE_NAMES = (  # noqa: SIM905
    "ConfigurationError SelectorConflictError UnsafePathError ExistingOutputError "
    "ReuseVerificationError AuthorizationGateError SchemaVersionError "
    "OutputCommitError InternalInvariantError"
).split()
for _error_name in _ERROR_TYPE_NAMES:
    globals()[_error_name] = type(_error_name, (EvaluationError,), {})
del _error_name


def _canonicalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonicalize({field.name: getattr(value, field.name) for field in fields(value)})
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("canonical values must be finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
