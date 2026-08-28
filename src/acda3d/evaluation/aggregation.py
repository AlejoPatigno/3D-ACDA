"""Pure subject-level source OOF and target fold-then-seed aggregation."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .schemas import (
    CanonicalPrediction,
    CheckpointPolicy,
    Direction,
    IssueCode,
    MethodId,
    PredictionRole,
    SubjectPrediction,
)


class AggregationError(ValueError):
    def __init__(self, code: IssueCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True)
class SeedSubjectPrediction:
    method_id: MethodId
    direction: Direction
    checkpoint_policy: CheckpointPolicy
    seed: int
    subject_hash: str
    true_label: int
    probabilities: tuple[float, float, float]
    fold_count: int
    source_file_sha256s: tuple[str, ...]


@dataclass(frozen=True)
class AggregationResult:
    final_predictions: tuple[SubjectPrediction, ...]
    per_seed_predictions: tuple[SeedSubjectPrediction, ...]


def _policy(logical_checkpoint: str) -> CheckpointPolicy:
    if logical_checkpoint == "best_source_f1":
        return CheckpointPolicy.PRIMARY_BEST_SOURCE_F1
    if logical_checkpoint == "last":
        return CheckpointPolicy.SENSITIVITY_LAST
    raise AggregationError(IssueCode.UNSUPPORTED_CHECKPOINT_POLICY)


def _validate_expected(values: Sequence[int | str]) -> tuple[int | str, ...]:
    result = tuple(values)
    if not result or len(set(result)) != len(result):
        raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)
    return result


def _axes(
    rows: Sequence[CanonicalPrediction], role: PredictionRole
) -> tuple[MethodId, Direction, CheckpointPolicy]:
    if not rows:
        raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)
    first = rows[0]
    identity = (first.method_id, first.direction, first.logical_checkpoint, first.role)
    if first.role is not role:
        raise AggregationError(IssueCode.PROVENANCE_CONFLICT)
    if any(
        (row.method_id, row.direction, row.logical_checkpoint, row.role) != identity
        for row in rows[1:]
    ):
        raise AggregationError(IssueCode.PROVENANCE_CONFLICT)
    return first.method_id, first.direction, _policy(first.logical_checkpoint)


def _mean_probabilities(
    rows: Sequence[CanonicalPrediction] | Sequence[SeedSubjectPrediction],
) -> tuple[float, float, float]:
    count = len(rows)
    return tuple(math.fsum(row.probabilities[index] for row in rows) / count for index in range(3))  # type: ignore[return-value]


def _source_hashes(
    rows: Sequence[CanonicalPrediction],
    source_hashes_by_provenance: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    try:
        values = {
            digest
            for row in rows
            for digest in source_hashes_by_provenance[row.provenance_ref]
        }
    except KeyError as error:
        raise AggregationError(IssueCode.MISSING_REQUIRED_FIELD) from error
    if not values:
        raise AggregationError(IssueCode.MISSING_REQUIRED_FIELD)
    return tuple(sorted(values))


def _check_label(rows: Sequence[CanonicalPrediction]) -> int:
    labels = {row.true_label for row in rows}
    if len(labels) != 1:
        raise AggregationError(IssueCode.INCONSISTENT_TRUE_LABEL)
    return next(iter(labels))


def aggregate_target_ensemble(
    rows: Sequence[CanonicalPrediction],
    *,
    expected_subjects: Sequence[str],
    expected_folds: Sequence[int],
    expected_seeds: Sequence[int],
    source_hashes_by_provenance: Mapping[str, tuple[str, ...]],
) -> AggregationResult:
    method, direction, policy = _axes(rows, PredictionRole.TARGET_EVALUATION)
    subjects = tuple(str(value) for value in _validate_expected(expected_subjects))
    folds = tuple(int(value) for value in _validate_expected(expected_folds))
    seeds = tuple(int(value) for value in _validate_expected(expected_seeds))
    expected_keys = {(subject, seed, fold) for subject in subjects for seed in seeds for fold in folds}
    keyed: dict[tuple[str, int, int], CanonicalPrediction] = {}
    for row in rows:
        key = (row.subject_hash, row.seed, row.fold)
        if key in keyed:
            raise AggregationError(IssueCode.DUPLICATE_PREDICTION)
        keyed[key] = row
    if set(keyed) != expected_keys:
        raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)

    per_seed: list[SeedSubjectPrediction] = []
    final: list[SubjectPrediction] = []
    for subject in sorted(subjects):
        subject_rows = [keyed[(subject, seed, fold)] for seed in seeds for fold in folds]
        true_label = _check_label(subject_rows)
        for seed in seeds:
            seed_rows = [keyed[(subject, seed, fold)] for fold in folds]
            per_seed.append(SeedSubjectPrediction(
                method, direction, policy, seed, subject, true_label,
                _mean_probabilities(seed_rows), len(folds),
                _source_hashes(seed_rows, source_hashes_by_provenance),
            ))
        seed_rows = [row for row in per_seed if row.subject_hash == subject]
        final.append(SubjectPrediction(
            method, direction, policy, subject, true_label,
            _mean_probabilities(seed_rows), len(folds), len(seeds),
            _source_hashes(subject_rows, source_hashes_by_provenance),
        ))
    return AggregationResult(tuple(final), tuple(per_seed))


def aggregate_source_oof(
    rows: Sequence[CanonicalPrediction],
    *,
    expected_subjects: Sequence[str],
    expected_seeds: Sequence[int],
    source_hashes_by_provenance: Mapping[str, tuple[str, ...]],
) -> AggregationResult:
    method, direction, policy = _axes(rows, PredictionRole.SOURCE_OOF)
    subjects = tuple(str(value) for value in _validate_expected(expected_subjects))
    seeds = tuple(int(value) for value in _validate_expected(expected_seeds))
    expected_keys = {(subject, seed) for subject in subjects for seed in seeds}
    keyed: dict[tuple[str, int], CanonicalPrediction] = {}
    for row in rows:
        key = (row.subject_hash, row.seed)
        if key in keyed:
            raise AggregationError(IssueCode.DUPLICATE_PREDICTION)
        keyed[key] = row
    if set(keyed) != expected_keys:
        raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)

    per_seed: list[SeedSubjectPrediction] = []
    final: list[SubjectPrediction] = []
    for subject in sorted(subjects):
        subject_rows = [keyed[(subject, seed)] for seed in seeds]
        true_label = _check_label(subject_rows)
        for row in subject_rows:
            per_seed.append(SeedSubjectPrediction(
                method, direction, policy, row.seed, subject, true_label,
                row.probabilities, 1,
                _source_hashes((row,), source_hashes_by_provenance),
            ))
        final.append(SubjectPrediction(
            method, direction, policy, subject, true_label,
            _mean_probabilities(subject_rows), 1, len(seeds),
            _source_hashes(subject_rows, source_hashes_by_provenance),
        ))
    return AggregationResult(tuple(final), tuple(per_seed))


@dataclass(frozen=True)
class BinaryAggregationResult:
    final_predictions: tuple[Mapping[str, object], ...]
    per_seed_predictions: tuple[Mapping[str, object], ...]
    task: str = "cn_vs_impaired"
    task_hash: str | None = None


def _validate_binary_row(row: Mapping[str, object], expected_task_hash: str | None) -> tuple[str, int, int, tuple[float, float], int, str]:
    from acda3d.binary import BinaryLabelError, BinaryPrediction
    task = row.get("task", "cn_vs_impaired")
    if task != "cn_vs_impaired":
        raise AggregationError(IssueCode.PROVENANCE_CONFLICT)
    task_hash = row.get("task_hash")
    if expected_task_hash is not None and task_hash != expected_task_hash:
        raise AggregationError(IssueCode.INPUT_HASH_MISMATCH)
    subject = row.get("subject_hash")
    if not isinstance(subject, str) or not subject:
        raise AggregationError(IssueCode.MISSING_REQUIRED_FIELD)
    try:
        fold, seed = int(row["fold"]), int(row["seed"])
        label = int(row.get("true_label", row.get("true_label_index")))
        prediction = BinaryPrediction.from_mapping(row)
    except (KeyError, TypeError, ValueError, BinaryLabelError) as error:
        raise AggregationError(IssueCode.PROVENANCE_CONFLICT) from error
    if label not in (0, 1):
        raise AggregationError(IssueCode.UNSUPPORTED_CLASS_ORDER)
    return subject, fold, seed, (prediction.prob_cn, prediction.prob_impaired), label, str(row.get("cohort", ""))


def aggregate_binary_target_ensemble(
    rows: Sequence[Mapping[str, object]], *, expected_subjects: Sequence[str],
    expected_folds: Sequence[int], expected_seeds: Sequence[int], expected_task_hash: str | None = None,
) -> BinaryAggregationResult:
    """Aggregate target predictions fold-first, then seed, at subject level."""
    subjects = tuple(str(item) for item in expected_subjects)
    folds = tuple(int(item) for item in expected_folds)
    seeds = tuple(int(item) for item in expected_seeds)
    if not subjects or len(subjects) != len(set(subjects)) or not folds or not seeds:
        raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)
    keyed: dict[tuple[str, int, int], tuple[Mapping[str, object], tuple[float, float], int, str]] = {}
    task_hashes: set[object] = set()
    for row in rows:
        subject, fold, seed, probabilities, label, cohort = _validate_binary_row(row, expected_task_hash)
        key = (subject, fold, seed)
        if key in keyed:
            raise AggregationError(IssueCode.DUPLICATE_PREDICTION)
        if fold not in folds or seed not in seeds:
            raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)
        task_hashes.add(row.get("task_hash"))
        keyed[key] = (row, probabilities, label, cohort)
    expected_keys = {(subject, fold, seed) for subject in subjects for fold in folds for seed in seeds}
    if set(keyed) != expected_keys:
        raise AggregationError(IssueCode.INCOMPLETE_ENSEMBLE)
    if len(task_hashes - {None, expected_task_hash}) > 0 or len({value for value in task_hashes if value is not None}) > 1:
        raise AggregationError(IssueCode.INPUT_HASH_MISMATCH)
    task_hash = expected_task_hash or next((str(value) for value in task_hashes if value is not None), None)
    final: list[Mapping[str, object]] = []
    per_seed: list[Mapping[str, object]] = []
    for subject in sorted(subjects):
        subject_rows = [keyed[(subject, fold, seed)] for seed in seeds for fold in folds]
        labels = {item[2] for item in subject_rows}
        if len(labels) != 1:
            raise AggregationError(IssueCode.INCONSISTENT_TRUE_LABEL)
        cohort = subject_rows[0][3]
        seed_predictions = []
        for seed in seeds:
            seed_rows = [keyed[(subject, fold, seed)] for fold in folds]
            probabilities = tuple(math.fsum(item[1][index] for item in seed_rows) / len(seed_rows) for index in (0, 1))
            seed_prediction = {
                "task": "cn_vs_impaired", "task_hash": task_hash, "subject_hash": subject,
                "cohort": cohort, "true_label": next(iter(labels)), "prob_cn": probabilities[0],
                "prob_impaired": probabilities[1], "predicted_label": 0 if probabilities[0] >= probabilities[1] else 1,
                "seed": seed, "fold_count": len(folds),
            }
            seed_predictions.append(seed_prediction)
            per_seed.append(seed_prediction)
        probabilities = tuple(math.fsum(item["prob_cn"] if index == 0 else item["prob_impaired"] for item in seed_predictions) / len(seed_predictions) for index in (0, 1))
        final.append({
            "task": "cn_vs_impaired", "task_hash": task_hash, "subject_hash": subject,
            "cohort": cohort, "true_label": next(iter(labels)), "prob_cn": probabilities[0],
            "prob_impaired": probabilities[1], "predicted_label": 0 if probabilities[0] >= probabilities[1] else 1,
            "fold_count": len(folds), "seed_count": len(seeds),
        })
    return BinaryAggregationResult(tuple(final), tuple(per_seed), "cn_vs_impaired", task_hash)


aggregate_binary_predictions = aggregate_binary_target_ensemble
