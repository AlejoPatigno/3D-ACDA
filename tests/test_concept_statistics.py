"""Deterministic statistical reference tests for Phase 16."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.statistics import (
    CONCEPT_COMPARATOR_METHODS,
    adjust_holm,
    bootstrap_metric,
    compute_paired_method_comparisons,
    exact_mcnemar,
    paired_bootstrap_diff,
)
from pada3dacb.evaluation.schemas import CheckpointPolicy, Direction, MethodId, ValueStatus


def test_subject_bootstrap_is_deterministic() -> None:
    values = np.array([0.1, 0.2, 0.3, 0.4])

    labels = np.array([0, 0, 1, 1])
    first = bootstrap_metric(values, labels=labels, metric="concept_mae", n_replicates=100, seed=7)
    second = bootstrap_metric(values, labels=labels, metric="concept_mae", n_replicates=100, seed=7)

    assert first == second
    assert first.status is ValueStatus.AVAILABLE
    assert first.point_estimate == pytest.approx(0.25)
    assert first.requested == first.successful == 100
    assert first.invalid == 0
    assert first.ci_low <= first.point_estimate <= first.ci_high


def test_subject_bootstrap_rejects_roi_matrix() -> None:
    with pytest.raises(ValueError, match="per-subject vector"):
        bootstrap_metric(
            np.ones((2, 3)), labels=np.array([0, 1]), metric="concept_mae", n_replicates=10
        )


def test_exact_mcnemar_matches_known_discordant_counts() -> None:
    result = exact_mcnemar(
        pred_a=np.array([0, 0, 1, 2]),
        pred_b=np.array([0, 1, 0, 2]),
        y_true=np.array([0, 0, 0, 2]),
        comparator_method=MethodId.SOURCE_ONLY,
    )

    assert result.n01_reference_correct == 1
    assert result.n10_comparator_correct == 1
    assert result.discordant_count == 2
    assert result.raw_p_value == pytest.approx(1.0)


def test_paired_bootstrap_uses_subject_pairs_and_centered_p_value() -> None:
    result = paired_bootstrap_diff(
        np.array([0.1, 0.2, 0.3, 0.4]),
        np.array([0.2, 0.2, 0.2, 0.2]),
        labels=np.array([0, 0, 1, 1]),
        comparator_method=MethodId.CORAL,
        metric="concept_mae",
        n_replicates=100,
        seed=11,
    )

    assert result.status is ValueStatus.AVAILABLE
    assert result.observed_difference == pytest.approx(0.05)
    assert result.p_value_method == "centered_plus_one"
    assert 0.0 <= result.raw_p_value <= 1.0
    assert result.requested == result.successful == 100


def test_paired_bootstrap_rejects_non_concept_baseline() -> None:
    with pytest.raises(ValueError, match="four PADA-3DACB comparators"):
        paired_bootstrap_diff(
            np.array([0.1, 0.2]),
            np.array([0.2, 0.1]),
            labels=np.array([0, 1]),
            comparator_method=MethodId.AAGN,
            metric="concept_mae",
            n_replicates=10,
            seed=3,
        )


def test_stratified_bootstrap_preserves_diagnosis_support() -> None:
    result = bootstrap_metric(
        np.array([0.0, 0.0, 10.0, 10.0]),
        labels=np.array([0, 0, 1, 1]),
        metric="concept_mae",
        n_replicates=100,
        seed=19,
    )

    assert result.ci_low == result.ci_high == 5.0


def test_holm_uses_only_the_four_pada_comparators() -> None:
    raw = [0.01, 0.04, 0.03, 0.2]

    rows = adjust_holm(raw, metric="concept_mae")

    assert tuple(row.comparator_method for row in rows) == CONCEPT_COMPARATOR_METHODS
    assert len(rows) == 4
    assert all(row.family_size == 4 for row in rows)
    assert all(row.status is ValueStatus.AVAILABLE for row in rows)
    adjusted = [row.adjusted_p_value for row in rows]
    assert all(value is not None and 0.0 <= value <= 1.0 for value in adjusted)


def test_concept_bootstrap_reuses_phase15_subject_sampler(monkeypatch) -> None:
    import pada3dacb.evaluation.bootstrap as phase15_bootstrap

    calls = []
    sampler = phase15_bootstrap._draw_indices

    def recording_sampler(rng, strata):
        calls.append(tuple(len(group) for group in strata))
        return sampler(rng, strata)

    monkeypatch.setattr(phase15_bootstrap, "_draw_indices", recording_sampler)
    result = bootstrap_metric(
        np.array([0.1, 0.2, 0.3, 0.4]),
        labels=np.array([0, 0, 1, 1]),
        metric="concept_mae",
        n_replicates=8,
        seed=23,
    )

    assert result.requested == result.successful == 8
    assert len(calls) == 8
    assert all(item == (2, 2, 0) for item in calls)


def test_paired_method_comparisons_use_four_slots_per_metric() -> None:
    from pada3dacb.evaluation.concepts.statistics import compute_paired_method_comparisons
    from pada3dacb.evaluation.schemas import CheckpointPolicy, Direction

    subject_ids = ("subject-0", "subject-1", "subject-2", "subject-3", "subject-4", "subject-5")
    labels = dict(zip(subject_ids, [0, 0, 1, 1, 2, 2], strict=True))
    prototype_values = {
        "concept_mae": np.array([0.1, 0.2, 0.3, 0.4, 0.2, 0.1]),
        "anatomy_mae": np.array([0.2, 0.2, 0.4, 0.3, 0.2, 0.3]),
        "js_divergence": np.array([0.1, 0.1, 0.2, 0.2, 0.3, 0.2]),
    }
    prototype = {
        metric: dict(zip(subject_ids, values, strict=True))
        for metric, values in prototype_values.items()
    }
    comparators = {
        method: {
            metric: dict(zip(subject_ids, values + 0.05, strict=True))
            for metric, values in prototype_values.items()
        }
        for method in CONCEPT_COMPARATOR_METHODS
    }

    rows = compute_paired_method_comparisons(
        prototype,
        comparators,
        labels=labels,
        direction=Direction.ADNI_TO_OASIS,
        checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        n_replicates=20,
        seed=31,
    )

    assert len(rows) == 12
    assert {row.metric_family for row in rows} == {
        "concept_mae", "anatomy_mae", "js_divergence"
    }
    for metric in ("concept_mae", "anatomy_mae", "js_divergence"):
        family = [row for row in rows if row.metric_family == metric]
        assert {row.comparator_method for row in family} == set(CONCEPT_COMPARATOR_METHODS)
        assert all(row.adjusted_p_value is not None for row in family)


def test_paired_method_comparisons_rejects_unkeyed_metric_arrays() -> None:
    prototype = {metric: np.ones(6) for metric in ("concept_mae", "anatomy_mae", "js_divergence")}
    comparators = {
        method: {metric: np.ones(6) for metric in prototype}
        for method in CONCEPT_COMPARATOR_METHODS
    }

    with pytest.raises(ValueError, match="requires explicit subject IDs or a keyed mapping"):
        compute_paired_method_comparisons(
            prototype,
            comparators,
            labels=np.array([0, 0, 1, 1, 2, 2]),
            direction=Direction.ADNI_TO_OASIS,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            n_replicates=10,
            seed=31,
        )


def test_paired_method_comparisons_rejects_unkeyed_labels_even_with_keyed_metrics() -> None:
    subject_ids = ("subject-0", "subject-1", "subject-2", "subject-3", "subject-4", "subject-5")
    prototype = {
        metric: dict(zip(subject_ids, np.ones(6), strict=True))
        for metric in ("concept_mae", "anatomy_mae", "js_divergence")
    }
    comparators = {
        method: {
            metric: dict(zip(subject_ids, np.ones(6), strict=True))
            for metric in prototype
        }
        for method in CONCEPT_COMPARATOR_METHODS
    }

    with pytest.raises(ValueError, match="diagnosis labels must be a keyed subject mapping"):
        compute_paired_method_comparisons(
            prototype,
            comparators,
            labels=np.array([0, 0, 1, 1, 2, 2]),
            direction=Direction.ADNI_TO_OASIS,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            n_replicates=10,
            seed=31,
        )


def test_paired_method_comparisons_rejects_permuted_and_stale_labels() -> None:
    subject_ids = ("subject-0", "subject-1", "subject-2", "subject-3", "subject-4", "subject-5")
    prototype = {
        metric: dict(zip(subject_ids, np.ones(6), strict=True))
        for metric in ("concept_mae", "anatomy_mae", "js_divergence")
    }
    comparators = {
        method: {
            metric: dict(zip(subject_ids, np.ones(6), strict=True))
            for metric in prototype
        }
        for method in CONCEPT_COMPARATOR_METHODS
    }

    for labels in (
        {subject_id: index % 3 for index, subject_id in enumerate(reversed(subject_ids))},
        {**{subject_id: index % 3 for index, subject_id in enumerate(subject_ids[:5])}, "stale": 2},
    ):
        with pytest.raises(ValueError, match="label subject IDs must have identical ordering and set"):
            compute_paired_method_comparisons(
                prototype,
                comparators,
                labels=labels,
                direction=Direction.ADNI_TO_OASIS,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                n_replicates=10,
                seed=31,
            )


def test_paired_method_comparisons_rejects_subject_order_mismatch() -> None:
    subject_ids = ("subject-0", "subject-1", "subject-2", "subject-3", "subject-4", "subject-5")
    prototype = {
        metric: dict(zip(subject_ids, values, strict=True))
        for metric, values in {
            "concept_mae": np.linspace(0.1, 0.6, 6),
            "anatomy_mae": np.linspace(0.2, 0.7, 6),
            "js_divergence": np.linspace(0.3, 0.8, 6),
        }.items()
    }
    comparator_ids = (subject_ids[1], *subject_ids[2:], subject_ids[0])
    comparators = {
        method: {
            metric: dict(zip(comparator_ids, values, strict=True))
            for metric, values in {
                "concept_mae": np.linspace(0.2, 0.7, 6),
                "anatomy_mae": np.linspace(0.3, 0.8, 6),
                "js_divergence": np.linspace(0.4, 0.9, 6),
            }.items()
        }
        for method in CONCEPT_COMPARATOR_METHODS
    }

    with pytest.raises(ValueError, match="subject IDs must have identical ordering"):
        compute_paired_method_comparisons(
            prototype,
            comparators,
            labels={subject_id: index % 3 for index, subject_id in enumerate(subject_ids)},
            direction=Direction.ADNI_TO_OASIS,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            n_replicates=10,
            seed=31,
        )


def test_paired_method_comparisons_rejects_subject_set_mismatch() -> None:
    subject_ids = ("subject-0", "subject-1", "subject-2", "subject-3", "subject-4", "subject-5")
    prototype = {
        metric: dict(zip(subject_ids, np.ones(6), strict=True))
        for metric in ("concept_mae", "anatomy_mae", "js_divergence")
    }
    mismatched_ids = (*subject_ids[:5], "subject-other")
    comparators = {
        method: {
            metric: dict(zip(mismatched_ids, np.ones(6), strict=True))
            for metric in ("concept_mae", "anatomy_mae", "js_divergence")
        }
        for method in CONCEPT_COMPARATOR_METHODS
    }

    with pytest.raises(ValueError, match="subject IDs must have identical ordering and set"):
        compute_paired_method_comparisons(
            prototype,
            comparators,
            labels={subject_id: index % 3 for index, subject_id in enumerate(subject_ids)},
            direction=Direction.ADNI_TO_OASIS,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            n_replicates=10,
            seed=31,
        )
