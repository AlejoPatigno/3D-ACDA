"""Deterministic aggregation tests for Phase 16 concept evaluation."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from acda3d.evaluation.concepts.aggregation import (
    aggregate_source_oof,
    aggregate_target_evaluation,
)
from acda3d.evaluation.concepts.schemas import (
    CheckpointPolicy,
    ConceptSubjectRecord,
    Direction,
    MethodId,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record(
    subject: str,
    *,
    seed: int,
    fold: int,
    offset: float = 0.0,
    concept_targets: tuple[float, ...] = (0.25, 0.75),
) -> ConceptSubjectRecord:
    return ConceptSubjectRecord(
        method_id=MethodId.SOURCE_ONLY,
        model="3D-ACDA",
        direction=Direction.ADNI_TO_OASIS,
        source_domain="ADNI",
        target_domain="OASIS",
        seed=seed,
        fold=fold,
        logical_checkpoint="best_source_f1",
        checkpoint_epoch=10,
        checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        experiment_hash=_digest(f"experiment-{seed}-{fold}"),
        subject_id=subject,
        subject_hash=_digest(subject),
        cohort="OASIS",
        true_label=1,
        label_name="MCI",
        predicted_concepts=(0.2 + offset, 0.6 + offset),
        concept_targets=concept_targets,
        anatomical_targets=(0.3, 0.7),
        attention_alpha=(0.4 + offset, 0.6 - offset),
        latent_probabilities=(0.2, 0.6, 0.2),
        concept_probabilities=(0.3, 0.5, 0.2),
        latent_prediction=1,
        concept_prediction=1,
        K=2,
        roi_order_hash="a" * 64,
        normalizer_hash="b" * 64,
        concept_config_hash="c" * 64,
    )


def _source_record(subject: str, *, seed: int, fold: int) -> ConceptSubjectRecord:
    return replace(_record(subject, seed=seed, fold=fold), cohort="ADNI")


def test_source_oof_keeps_one_record_per_subject_and_seed() -> None:
    records = [
        _source_record("subject-a", seed=42, fold=0),
        _source_record("subject-b", seed=42, fold=1),
        _source_record("subject-a", seed=99, fold=1),
        _source_record("subject-b", seed=99, fold=0),
    ]

    aggregated = aggregate_source_oof(
        records,
        expected_folds=(0, 1),
        expected_subject_hashes=(_digest("subject-a"), _digest("subject-b")),
    )

    assert set(aggregated) == {
        (_digest("subject-a"), 42),
        (_digest("subject-b"), 42),
        (_digest("subject-a"), 99),
        (_digest("subject-b"), 99),
    }
    assert aggregated[(_digest("subject-a"), 42)].fold == 0
    assert aggregated[(_digest("subject-a"), 99)].fold == 1


def test_source_oof_rejects_duplicate_subject_seed() -> None:
    record = _source_record("subject-a", seed=42, fold=0)

    with pytest.raises(ValueError, match="duplicate source OOF record"):
        aggregate_source_oof(
            (record, record),
            expected_folds=(0,),
            expected_subject_hashes=(_digest("subject-a"),),
        )


def test_source_oof_rejects_missing_fold_for_seed() -> None:
    records = (
        _source_record("subject-a", seed=42, fold=0),
        _source_record("subject-b", seed=42, fold=1),
        _source_record("subject-a", seed=99, fold=0),
    )

    with pytest.raises(ValueError, match="seed 99 folds"):
        aggregate_source_oof(
            records,
            expected_folds=(0, 1),
            expected_subject_hashes=(_digest("subject-a"), _digest("subject-b")),
        )


def test_target_aggregation_is_fold_then_seed() -> None:
    records = [
        _record("subject-a", seed=42, fold=0, offset=0.0),
        _record("subject-a", seed=42, fold=1, offset=0.2),
        _record("subject-a", seed=99, fold=0, offset=0.1),
        _record("subject-a", seed=99, fold=1, offset=0.3),
    ]

    fold_ensembles, seed_ensembles = aggregate_target_evaluation(
        records,
        expected_folds=(0, 1),
        expected_seeds=(42, 99),
    )

    subject_hash = _digest("subject-a")
    assert set(fold_ensembles) == {(subject_hash, 42), (subject_hash, 99)}
    assert fold_ensembles[(subject_hash, 42)].predicted_concepts == pytest.approx((0.3, 0.7))
    assert fold_ensembles[(subject_hash, 99)].predicted_concepts == pytest.approx((0.4, 0.8))
    assert seed_ensembles is not None
    assert seed_ensembles[subject_hash].predicted_concepts == pytest.approx((0.35, 0.75))
    assert seed_ensembles[subject_hash].concept_targets == (0.25, 0.75)
    assert seed_ensembles[subject_hash].seed_count == 2


def test_target_aggregation_rejects_changed_immutable_targets() -> None:
    records = (
        _record("subject-a", seed=42, fold=0),
        _record("subject-a", seed=42, fold=1, concept_targets=(0.2, 0.8)),
    )

    with pytest.raises(ValueError, match="inconsistent concept_targets"):
        aggregate_target_evaluation(records, expected_folds=(0, 1))


def test_target_aggregation_rejects_changed_immutable_anatomy_targets() -> None:
    records = (
        _record("subject-a", seed=42, fold=0),
        replace(_record("subject-a", seed=42, fold=1), anatomical_targets=(0.2, 0.8)),
    )

    with pytest.raises(ValueError, match="inconsistent anatomical_targets"):
        aggregate_target_evaluation(records, expected_folds=(0, 1))


def test_target_aggregation_rejects_missing_seed() -> None:
    records = (
        _record("subject-a", seed=42, fold=0),
        _record("subject-a", seed=42, fold=1),
    )

    with pytest.raises(ValueError, match="seeds"):
        aggregate_target_evaluation(
            records,
            expected_folds=(0, 1),
            expected_seeds=(42, 99),
        )


def test_target_aggregation_rejects_unexpected_single_seed() -> None:
    records = (
        _record("subject-a", seed=99, fold=0),
        _record("subject-a", seed=99, fold=1),
    )

    with pytest.raises(ValueError, match="seeds"):
        aggregate_target_evaluation(
            records,
            expected_folds=(0, 1),
            expected_seeds=(42,),
        )


def test_target_aggregation_rejects_mixed_transfer_directions() -> None:
    adni_to_oasis = _record("subject-a", seed=42, fold=0)
    oasis_to_adni = replace(
        _record("subject-b", seed=42, fold=0),
        direction=Direction.OASIS_TO_ADNI,
        source_domain="OASIS",
        target_domain="ADNI",
        cohort="ADNI",
    )

    with pytest.raises(ValueError, match="direction"):
        aggregate_target_evaluation(
            (adni_to_oasis, oasis_to_adni),
            expected_folds=(0,),
        )


def test_source_oof_rejects_mixed_transfer_directions() -> None:
    adni_to_oasis = _source_record("subject-a", seed=42, fold=0)
    oasis_to_adni = replace(
        _record("subject-b", seed=42, fold=0),
        direction=Direction.OASIS_TO_ADNI,
        source_domain="OASIS",
        target_domain="ADNI",
        cohort="OASIS",
    )

    with pytest.raises(ValueError, match="direction"):
        aggregate_source_oof(
            (adni_to_oasis, oasis_to_adni),
            expected_folds=(0,),
            expected_subject_hashes=(
                _digest("subject-a"),
                _digest("subject-b"),
            ),
        )


def test_source_oof_rejects_target_cohort_record() -> None:
    target_record = _record("subject-a", seed=42, fold=0)

    with pytest.raises(ValueError, match="source OOF cohort"):
        aggregate_source_oof(
            (target_record,),
            expected_folds=(0,),
            expected_subject_hashes=(_digest("subject-a"),),
        )


def test_target_aggregation_rejects_source_cohort_record() -> None:
    source_record = _source_record("subject-a", seed=42, fold=0)

    with pytest.raises(ValueError, match="target evaluation cohort"):
        aggregate_target_evaluation((source_record,), expected_folds=(0,))
