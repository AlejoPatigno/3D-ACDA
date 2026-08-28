"""Deterministic tests for Phase 16 class-conditional profiles."""

from __future__ import annotations

import pytest

from acda3d.evaluation.concepts.class_profiles import compute_class_profiles
from acda3d.evaluation.concepts.schemas import (
    Direction,
    FoldEnsembleRecord,
    MethodId,
)
from acda3d.evaluation.schemas import ValueStatus


def _record(subject: str, concepts: tuple[float, float]) -> FoldEnsembleRecord:
    return FoldEnsembleRecord(
        method_id=MethodId.SOURCE_ONLY,
        direction=Direction.ADNI_TO_OASIS,
        seed=42,
        subject_id=subject,
        subject_hash=f"hash-{subject}",
        cohort="OASIS",
        true_label=0,
        label_name="CN",
        predicted_concepts=concepts,
        latent_probabilities=(0.8, 0.1, 0.1),
        concept_probabilities=(0.7, 0.2, 0.1),
        attention_alpha=(0.4, 0.6),
        concept_targets=(0.25, 0.75),
        anatomical_targets=(0.3, 0.7),
        K=2,
        fold_count=5,
        roi_order_hash="roi-hash",
        normalizer_hash="normalizer-hash",
    )


def test_class_profiles_are_subject_bootstrapped_and_deterministic() -> None:
    records = [_record("a", (0.2, 0.6)), _record("b", (0.4, 0.8))]

    first = compute_class_profiles(records, bootstrap_replicates=50, bootstrap_seed=7)
    second = compute_class_profiles(records, bootstrap_replicates=50, bootstrap_seed=7)

    assert first == second
    assert first[0].support == 2
    assert first[0].mean_predicted_concepts == pytest.approx((0.3, 0.7))
    assert first[0].mean_concept_targets == (0.25, 0.75)
    assert first[0].status is ValueStatus.AVAILABLE
    assert first[0].bootstrap_ci_low[0] <= 0.3 <= first[0].bootstrap_ci_high[0]


def test_class_profiles_keep_zero_support_unavailable() -> None:
    profiles = compute_class_profiles([_record("a", (0.2, 0.6))], bootstrap_replicates=10)

    assert profiles[1].class_label == "MCI"
    assert profiles[1].support == 0
    assert profiles[1].status is ValueStatus.UNAVAILABLE
    assert profiles[1].reason == "zero_support"
    assert profiles[2].class_label == "AD"


def test_class_profiles_reject_mixed_roi_widths() -> None:
    with pytest.raises(ValueError, match="same ROI width"):
        compute_class_profiles(
            [_record("a", (0.2, 0.6)), _record("b", (0.2, 0.6, 0.8))],
            bootstrap_replicates=10,
        )


def test_class_profiles_reject_non_finite_concepts() -> None:
    record = _record("a", (0.2, 0.6))
    record = record.__class__(
        **{**record.__dict__, "predicted_concepts": (float("nan"), 0.6)}
    )

    with pytest.raises(ValueError, match="finite"):
        compute_class_profiles([record], bootstrap_replicates=10)
