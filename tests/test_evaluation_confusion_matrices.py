from __future__ import annotations

import pytest

from pada3dacb.evaluation.confusion_matrices import compute_confusion
from pada3dacb.evaluation.schemas import (
    CheckpointPolicy,
    Direction,
    MethodId,
    SubjectPrediction,
    ValueStatus,
)


def _subject(name: str, truth: int, prediction: int, *, direction: Direction = Direction.ADNI_TO_OASIS) -> SubjectPrediction:
    probabilities = tuple(1.0 if index == prediction else 0.0 for index in range(3))
    return SubjectPrediction(
        MethodId.MMD, direction, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        name, truth, probabilities, 5, 2, ("a" * 64,),
    )


def test_confusion_counts_and_rows_use_fixed_cn_mci_ad_order() -> None:
    table = (
        _subject("a", 0, 0), _subject("b", 0, 1),
        _subject("c", 1, 1), _subject("d", 1, 1),
        _subject("e", 2, 2), _subject("f", 2, 0),
    )
    result = compute_confusion(table)
    assert result.counts == ((1, 1, 0), (0, 2, 0), (1, 0, 1))
    assert result.normalized[0] == pytest.approx((0.5, 0.5, 0.0))
    assert result.normalized[1] == pytest.approx((0.0, 1.0, 0.0))
    assert result.normalized[2] == pytest.approx((0.5, 0.0, 0.5))
    assert result.subject_count == 6
    assert [status.value for status in result.normalized_row_statuses] == [2, 2, 2]


def test_zero_support_normalized_row_is_null_not_zero() -> None:
    result = compute_confusion((_subject("a", 0, 0), _subject("b", 1, 1)))
    assert result.counts[2] == (0, 0, 0)
    assert result.normalized[2] == (None, None, None)
    assert result.normalized_row_statuses[2].status is ValueStatus.UNAVAILABLE
    assert result.normalized_row_statuses[2].reason == "zero_true_support"


def test_empty_confusion_retains_integer_counts_and_null_rows() -> None:
    result = compute_confusion(())
    assert result.counts == ((0, 0, 0),) * 3
    assert result.normalized == ((None, None, None),) * 3
    assert result.subject_count == 0
    assert all(status.reason == "zero_true_support" for status in result.normalized_row_statuses)


def test_confusion_rejects_mixed_identity_and_duplicate_subjects() -> None:
    mixed = (_subject("a", 0, 0), _subject("b", 1, 1, direction=Direction.OASIS_TO_ADNI))
    with pytest.raises(ValueError, match="homogeneous"):
        compute_confusion(mixed)
    with pytest.raises(ValueError, match="one row"):
        compute_confusion((_subject("a", 0, 0), _subject("a", 0, 0)))


def test_confusion_uses_fixed_order_argmax_for_ties() -> None:
    tied = SubjectPrediction(
        MethodId.CORAL, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.SENSITIVITY_LAST, "subject", 0,
        (0.5, 0.5, 0.0), 5, 1, ("a" * 64,),
    )
    result = compute_confusion((tied,))
    assert result.counts[0] == (1, 0, 0)
