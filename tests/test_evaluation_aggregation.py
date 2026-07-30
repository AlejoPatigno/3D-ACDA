from __future__ import annotations

import pytest

from pada3dacb.evaluation.aggregation import (
    AggregationError,
    aggregate_source_oof,
    aggregate_target_ensemble,
)
from pada3dacb.evaluation.schemas import (
    CanonicalPrediction,
    CheckpointPolicy,
    Direction,
    IssueCode,
    MethodId,
    PredictionRole,
)


def _prediction(
    subject: str,
    label: int,
    probabilities: tuple[float, float, float],
    *,
    seed: int,
    fold: int,
    role: PredictionRole = PredictionRole.TARGET_EVALUATION,
    direction: Direction = Direction.ADNI_TO_OASIS,
    checkpoint: str = "best_source_f1",
    provenance: str = "a" * 64,
) -> CanonicalPrediction:
    return CanonicalPrediction(
        MethodId.MMD, direction, seed, fold, checkpoint, role,
        subject, label, probabilities, provenance,
    )


def _hashes(*refs: str) -> dict[str, tuple[str, ...]]:
    return {ref: (ref,) for ref in refs}


def test_target_averages_folds_within_seed_then_all_seeds() -> None:
    rows = (
        _prediction("subject-a", 1, (1.0, 0.0, 0.0), seed=1, fold=0, provenance="a" * 64),
        _prediction("subject-a", 1, (0.0, 1.0, 0.0), seed=1, fold=1, provenance="b" * 64),
        _prediction("subject-a", 1, (0.0, 0.0, 1.0), seed=2, fold=0, provenance="c" * 64),
        _prediction("subject-a", 1, (0.0, 1.0, 0.0), seed=2, fold=1, provenance="d" * 64),
    )
    result = aggregate_target_ensemble(
        rows, expected_subjects=("subject-a",), expected_folds=(0, 1),
        expected_seeds=(1, 2), source_hashes_by_provenance=_hashes("a" * 64, "b" * 64, "c" * 64, "d" * 64),
    )
    assert result.final_predictions[0].probabilities == pytest.approx((0.25, 0.5, 0.25))
    assert result.final_predictions[0].predicted_label == 1
    assert result.final_predictions[0].fold_count == 2
    assert result.final_predictions[0].seed_count == 2
    assert [item.probabilities for item in result.per_seed_predictions] == pytest.approx(
        [(0.5, 0.5, 0.0), (0.0, 0.5, 0.5)]
    )


def test_source_oof_is_not_fold_averaged_but_seeds_are_averaged() -> None:
    rows = (
        _prediction("subject-a", 0, (0.8, 0.1, 0.1), seed=1, fold=3, role=PredictionRole.SOURCE_OOF),
        _prediction("subject-a", 0, (0.6, 0.2, 0.2), seed=2, fold=3, role=PredictionRole.SOURCE_OOF),
    )
    result = aggregate_source_oof(
        rows, expected_subjects=("subject-a",), expected_seeds=(1, 2),
        source_hashes_by_provenance=_hashes("a" * 64),
    )
    assert result.final_predictions[0].probabilities == pytest.approx((0.7, 0.15, 0.15))
    assert result.final_predictions[0].fold_count == 1
    assert result.final_predictions[0].seed_count == 2


def test_target_missing_fold_or_seed_fails_without_partial_table() -> None:
    complete_minus_one = (
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=0),
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=1),
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=2, fold=0),
    )
    with pytest.raises(AggregationError) as error:
        aggregate_target_ensemble(
            complete_minus_one, expected_subjects=("subject-a",), expected_folds=(0, 1),
            expected_seeds=(1, 2), source_hashes_by_provenance=_hashes("a" * 64),
        )
    assert error.value.code is IssueCode.INCOMPLETE_ENSEMBLE


def test_source_oof_missing_or_duplicate_subject_seed_fails() -> None:
    row = _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=0, role=PredictionRole.SOURCE_OOF)
    with pytest.raises(AggregationError) as duplicate:
        aggregate_source_oof(
            (row, row), expected_subjects=("subject-a",), expected_seeds=(1,),
            source_hashes_by_provenance=_hashes("a" * 64),
        )
    assert duplicate.value.code is IssueCode.DUPLICATE_PREDICTION

    with pytest.raises(AggregationError) as missing:
        aggregate_source_oof(
            (row,), expected_subjects=("subject-a", "subject-b"), expected_seeds=(1,),
            source_hashes_by_provenance=_hashes("a" * 64),
        )
    assert missing.value.code is IssueCode.INCOMPLETE_ENSEMBLE


def test_true_labels_must_agree_across_folds_and_seeds() -> None:
    rows = (
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=0),
        _prediction("subject-a", 1, (0.0, 1.0, 0.0), seed=1, fold=1),
    )
    with pytest.raises(AggregationError) as error:
        aggregate_target_ensemble(
            rows, expected_subjects=("subject-a",), expected_folds=(0, 1),
            expected_seeds=(1,), source_hashes_by_provenance=_hashes("a" * 64),
        )
    assert error.value.code is IssueCode.INCONSISTENT_TRUE_LABEL


def test_directions_checkpoints_methods_and_roles_cannot_mix() -> None:
    base = _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=0)
    variants = (
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=1, direction=Direction.OASIS_TO_ADNI),
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=1, checkpoint="last"),
        _prediction("subject-a", 0, (1.0, 0.0, 0.0), seed=1, fold=1, role=PredictionRole.SOURCE_OOF),
    )
    for variant in variants:
        with pytest.raises(AggregationError) as error:
            aggregate_target_ensemble(
                (base, variant), expected_subjects=("subject-a",), expected_folds=(0, 1),
                expected_seeds=(1,), source_hashes_by_provenance=_hashes("a" * 64),
            )
        assert error.value.code is IssueCode.PROVENANCE_CONFLICT


def test_final_rows_are_sorted_and_keep_policy_identity() -> None:
    rows = (
        _prediction("subject-b", 2, (0.1, 0.1, 0.8), seed=1, fold=0),
        _prediction("subject-a", 0, (0.5, 0.5, 0.0), seed=1, fold=0),
    )
    result = aggregate_target_ensemble(
        rows, expected_subjects=("subject-b", "subject-a"), expected_folds=(0,),
        expected_seeds=(1,), source_hashes_by_provenance=_hashes("a" * 64),
    )
    assert [item.subject_hash for item in result.final_predictions] == ["subject-a", "subject-b"]
    assert result.final_predictions[0].predicted_label == 0
    assert all(item.checkpoint_policy is CheckpointPolicy.PRIMARY_BEST_SOURCE_F1 for item in result.final_predictions)
