from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import binomtest

from acda3d.evaluation.paired_statistics import exact_mcnemar, paired_bootstrap
from acda3d.evaluation.schemas import (
    CheckpointPolicy,
    Direction,
    McNemarResult,
    MethodId,
    MetricValue,
    SubjectPrediction,
    ValueStatus,
)


def _row(method: MethodId, subject: str, truth: int, prediction: int) -> SubjectPrediction:
    probabilities = [0.05, 0.05, 0.05]
    probabilities[prediction] = 0.9
    return SubjectPrediction(
        method, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, subject, truth,
        tuple(probabilities), 5, 2, (f"{len(subject) + list(MethodId).index(method):064x}",),
    )


def _accuracy(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
    return MetricValue.available(sum(row.predicted_label == row.true_label for row in rows) / len(rows))


def _pair(
    reference_predictions: tuple[int, ...], comparator_predictions: tuple[int, ...]
) -> tuple[tuple[SubjectPrediction, ...], tuple[SubjectPrediction, ...]]:
    truths = (0, 0, 1, 1, 2, 2)
    subjects = tuple(f"subject-{index}" for index in range(len(truths)))
    reference = tuple(
        _row(MethodId.PROTOTYPE_PSEUDO, subject, truth, prediction)
        for subject, truth, prediction in zip(subjects, truths, reference_predictions, strict=True)
    )
    comparator = tuple(
        _row(MethodId.CORAL, subject, truth, prediction)
        for subject, truth, prediction in zip(subjects, truths, comparator_predictions, strict=True)
    )
    return reference, comparator


def test_exact_mcnemar_uses_protocol_contingency_and_scipy_binomtest() -> None:
    reference, comparator = _pair((0, 1, 1, 2, 2, 0), (1, 0, 1, 1, 0, 2))
    result = exact_mcnemar(reference, comparator)
    assert result == McNemarResult(
        MethodId.CORAL, 6, 0, 2, 3, 1, 5, "exact_two_sided_mcnemar",
        float(binomtest(k=2, n=5, p=0.5, alternative="two-sided").pvalue),
        ValueStatus.AVAILABLE, None, None,
    )


def test_exact_mcnemar_zero_discordance_is_available_with_note() -> None:
    reference, comparator = _pair((0, 0, 1, 1, 2, 2), (0, 0, 1, 1, 2, 2))
    result = exact_mcnemar(reference, comparator)
    assert result.raw_p_value == 1.0
    assert result.note_code == "no_discordant_pairs"
    assert result.reason is None


def test_pairing_marks_ordered_subject_or_label_mismatch_unavailable() -> None:
    reference, comparator = _pair((0, 0, 1, 1, 2, 2), (0, 0, 1, 1, 2, 2))
    reversed_result = exact_mcnemar(reference, tuple(reversed(comparator)))
    assert reversed_result.status is ValueStatus.UNAVAILABLE
    assert reversed_result.reason == "incompatible_subjects"
    changed = list(comparator)
    changed[0] = _row(MethodId.CORAL, changed[0].subject_hash, 1, 0)
    changed_result = exact_mcnemar(reference, tuple(changed))
    assert changed_result.status is ValueStatus.UNAVAILABLE
    assert changed_result.n_subjects == 0

    wrong_reference = tuple(
        _row(MethodId.MMD, row.subject_hash, row.true_label, row.predicted_label)
        for row in reference
    )
    with pytest.raises(ValueError, match="prototype_pseudo"):
        exact_mcnemar(wrong_reference, comparator)


def test_paired_bootstrap_uses_shared_pcg64_indices_and_reference_orientation() -> None:
    reference, comparator = _pair((0, 1, 1, 2, 2, 0), (1, 0, 1, 1, 0, 2))
    result = paired_bootstrap(
        reference, comparator, {"accuracy": _accuracy}, replicates=20, seed=9
    )[0]
    observed = float(_accuracy(reference).value) - float(_accuracy(comparator).value)

    labels = np.asarray([row.true_label for row in reference])
    strata = tuple(np.flatnonzero(labels == label) for label in (0, 1, 2))
    rng = np.random.Generator(np.random.PCG64(9))
    differences = []
    for _ in range(20):
        indices = np.concatenate([rng.choice(stratum, size=len(stratum), replace=True) for stratum in strata])
        ref_sample = tuple(reference[index] for index in indices)
        cmp_sample = tuple(comparator[index] for index in indices)
        differences.append(float(_accuracy(ref_sample).value) - float(_accuracy(cmp_sample).value))
    centered = np.asarray(differences) - observed
    expected_p = (1 + int(np.sum(np.abs(centered) >= abs(observed)))) / 21

    assert result.observed_difference == observed
    assert result.orientation == "prototype_pseudo-comparator"
    assert result.ci_low == float(np.quantile(differences, 0.025, method="linear"))
    assert result.ci_high == float(np.quantile(differences, 0.975, method="linear"))
    assert result.raw_p_value == expected_p
    assert result == paired_bootstrap(
        reference, comparator, {"accuracy": _accuracy}, replicates=20, seed=9
    )[0]


def test_paired_bootstrap_counts_invalid_pairs_once_without_redraw() -> None:
    reference, comparator = _pair((0, 0, 1, 1, 2, 2), (0, 0, 1, 1, 2, 2))
    calls = 0

    def intermittent(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
        nonlocal calls
        calls += 1
        return MetricValue.unavailable("undefined") if calls > 2 and calls % 4 == 0 else _accuracy(rows)

    result = paired_bootstrap(
        reference, comparator, {"accuracy": intermittent}, replicates=10, seed=2
    )[0]
    assert calls == 22
    assert (result.successful, result.invalid) == (5, 5)
    assert result.status is ValueStatus.UNAVAILABLE
    assert result.reason == "insufficient_valid_bootstrap_replicates"


def test_paired_bootstrap_observed_unavailable_has_no_inference() -> None:
    reference, comparator = _pair((0, 0, 1, 1, 2, 2), (0, 0, 1, 1, 2, 2))
    result = paired_bootstrap(
        reference, comparator,
        {"macro_ovr_roc_auc": lambda rows: MetricValue.unavailable("missing_negative_class")},
        replicates=2, seed=1,
    )[0]
    assert result.observed_difference is None
    assert result.raw_p_value is None
    assert result.reason == "observed_metric_unavailable"
