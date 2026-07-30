"""Fold and seed aggregation for concept evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from .schemas import (
    ConceptSubjectRecord,
    FoldEnsembleRecord,
    SeedEnsembleRecord,
)


@dataclass(frozen=True)
class AggregationPolicy:
    """Configuration for aggregation behavior."""
    fold_then_seed: bool = True  # Always true for target evaluation
    preserve_immutable_artifacts: bool = True  # c_target, g_bar never aggregated


_IMMUTABLE_FIELDS = (
    "method_id", "direction", "subject_id", "subject_hash", "cohort",
    "true_label", "label_name", "concept_targets", "anatomical_targets",
    "K", "roi_order_hash", "normalizer_hash",
)


def _require_consistent(records: Sequence[ConceptSubjectRecord | FoldEnsembleRecord]) -> None:
    base = records[0]
    for record in records[1:]:
        for field_name in _IMMUTABLE_FIELDS:
            if getattr(record, field_name) != getattr(base, field_name):
                raise ValueError(f"inconsistent {field_name} across folds/seeds")


def _mean_tuple(
    records: Sequence[ConceptSubjectRecord | FoldEnsembleRecord],
    field_name: str,
) -> tuple[float, ...]:
    values = np.stack([getattr(record, field_name) for record in records])
    return tuple(float(value) for value in np.mean(values, axis=0))


def aggregate_source_oof(
    records: Sequence[ConceptSubjectRecord],
    expected_folds: Sequence[int],
    *,
    expected_subject_hashes: Sequence[str],
) -> dict[tuple[str, int], ConceptSubjectRecord]:
    """Validate true OOF membership and retain one row per subject and seed."""
    expected = set(expected_folds)
    expected_subjects = set(expected_subject_hashes)
    if not expected or not expected_subjects:
        raise ValueError("source OOF expected folds and subjects must be non-empty")
    observed_by_seed: dict[int, set[int]] = defaultdict(set)
    subjects_by_seed: dict[int, set[str]] = defaultdict(set)
    aggregated: dict[tuple[str, int], ConceptSubjectRecord] = {}

    for record in records:
        key = (record.subject_hash, record.seed)
        if key in aggregated:
            raise ValueError(
                f"duplicate source OOF record for subject {record.subject_hash} "
                f"seed {record.seed}"
            )
        aggregated[key] = record
        observed_by_seed[record.seed].add(record.fold)
        subjects_by_seed[record.seed].add(record.subject_hash)

    for seed, observed in observed_by_seed.items():
        if observed != expected:
            raise ValueError(f"seed {seed} folds {observed} != expected {expected}")
        if subjects_by_seed[seed] != expected_subjects:
            raise ValueError(
                f"seed {seed} source OOF population does not match expected subjects"
            )

    return aggregated


def aggregate_target_evaluation(
    records: Sequence[ConceptSubjectRecord],
    expected_folds: Sequence[int],
    expected_seeds: Sequence[int] | None = None,
) -> tuple[
    dict[tuple[str, int], FoldEnsembleRecord],
    dict[str, SeedEnsembleRecord] | None,
]:
    """Aggregate target rows across folds first and seeds second."""
    expected_fold_tuple = tuple(sorted(expected_folds))
    grouped: dict[tuple[str, int], list[ConceptSubjectRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.subject_hash, record.seed)].append(record)

    fold_ensembles: dict[tuple[str, int], FoldEnsembleRecord] = {}
    for key, subject_records in grouped.items():
        subject_hash, seed = key
        observed = tuple(sorted(record.fold for record in subject_records))
        if observed != expected_fold_tuple:
            raise ValueError(
                f"Subject {subject_hash} seed {seed} folds {observed} "
                f"!= expected {expected_fold_tuple}"
            )
        _require_consistent(subject_records)
        base = subject_records[0]
        fold_ensembles[key] = FoldEnsembleRecord(
            method_id=base.method_id,
            direction=base.direction,
            seed=seed,
            subject_id=base.subject_id,
            subject_hash=subject_hash,
            cohort=base.cohort,
            true_label=base.true_label,
            label_name=base.label_name,
            predicted_concepts=_mean_tuple(subject_records, "predicted_concepts"),
            latent_probabilities=_mean_tuple(subject_records, "latent_probabilities"),
            concept_probabilities=_mean_tuple(subject_records, "concept_probabilities"),
            attention_alpha=_mean_tuple(subject_records, "attention_alpha"),
            concept_targets=base.concept_targets,
            anatomical_targets=base.anatomical_targets,
            K=base.K,
            fold_count=len(subject_records),
            roi_order_hash=base.roi_order_hash,
            normalizer_hash=base.normalizer_hash,
        )

    if expected_seeds is None or len(expected_seeds) <= 1:
        return fold_ensembles, None

    expected_seed_set = set(expected_seeds)
    by_subject: dict[str, list[FoldEnsembleRecord]] = defaultdict(list)
    for record in fold_ensembles.values():
        by_subject[record.subject_hash].append(record)

    seed_ensembles: dict[str, SeedEnsembleRecord] = {}
    for subject_hash, seed_records in by_subject.items():
        observed_seeds = {record.seed for record in seed_records}
        if observed_seeds != expected_seed_set:
            raise ValueError(
                f"Subject {subject_hash} seeds {observed_seeds} "
                f"!= expected {expected_seed_set}"
            )
        _require_consistent(seed_records)
        base = seed_records[0]
        seed_ensembles[subject_hash] = SeedEnsembleRecord(
            method_id=base.method_id,
            direction=base.direction,
            subject_id=base.subject_id,
            subject_hash=subject_hash,
            cohort=base.cohort,
            true_label=base.true_label,
            label_name=base.label_name,
            predicted_concepts=_mean_tuple(seed_records, "predicted_concepts"),
            latent_probabilities=_mean_tuple(seed_records, "latent_probabilities"),
            concept_probabilities=_mean_tuple(seed_records, "concept_probabilities"),
            attention_alpha=_mean_tuple(seed_records, "attention_alpha"),
            concept_targets=base.concept_targets,
            anatomical_targets=base.anatomical_targets,
            K=base.K,
            seed_count=len(seed_records),
            roi_order_hash=base.roi_order_hash,
            normalizer_hash=base.normalizer_hash,
        )

    return fold_ensembles, seed_ensembles


def validate_aggregation(
    fold_ensembles: Mapping[tuple[str, int], FoldEnsembleRecord],
    expected_folds: Sequence[int],
    expected_seeds: Sequence[int] | None = None,
) -> list[str]:
    """Validate aggregated record counts without changing their output."""
    issues: list[str] = []
    seeds_by_subject: dict[str, set[int]] = defaultdict(set)
    for (subject_hash, seed), record in fold_ensembles.items():
        if record.fold_count != len(expected_folds):
            issues.append(
                f"subject_{subject_hash}: fold_count {record.fold_count} "
                f"!= expected {len(expected_folds)}"
            )
        seeds_by_subject[subject_hash].add(seed)

    if expected_seeds is not None:
        expected_seed_set = set(expected_seeds)
        for subject_hash, observed in seeds_by_subject.items():
            if observed != expected_seed_set:
                issues.append(
                    f"subject_{subject_hash}: seeds {observed} "
                    f"!= expected {expected_seed_set}"
                )
    return issues


