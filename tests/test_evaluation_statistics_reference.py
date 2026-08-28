from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import binomtest
from statsmodels.stats.multitest import multipletests

from acda3d.evaluation.bootstrap import bootstrap_metrics
from acda3d.evaluation.multiple_testing import adjust_holm
from acda3d.evaluation.paired_statistics import exact_mcnemar, paired_bootstrap
from acda3d.evaluation.schemas import (
    COMPARATOR_METHODS,
    CheckpointPolicy,
    Direction,
    MethodId,
    MetricValue,
    PairedDifference,
    SubjectPrediction,
    ValueStatus,
)


def _row(method: MethodId, index: int, truth: int, prediction: int) -> SubjectPrediction:
    probability = [0.05, 0.05, 0.05]
    probability[prediction] = 0.9
    return SubjectPrediction(
        method,
        Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        f"subject-{index}",
        truth,
        tuple(probability),
        5,
        2,
        (f"{index + 1 + list(MethodId).index(method):064x}",),
    )


def _table(method: MethodId, predictions: tuple[int, ...]) -> tuple[SubjectPrediction, ...]:
    truths = (0, 0, 1, 1, 2, 2)
    return tuple(
        _row(method, index, truth, prediction)
        for index, (truth, prediction) in enumerate(zip(truths, predictions, strict=True))
    )


def _accuracy(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
    return MetricValue.available(sum(row.true_label == row.predicted_label for row in rows) / len(rows))


def _manual_stratified_draws(
    truth: np.ndarray,
    *,
    replicates: int,
    seed: int,
) -> tuple[np.ndarray, ...]:
    strata = tuple(np.flatnonzero(truth == label) for label in (0, 1, 2))
    rng = np.random.Generator(np.random.PCG64(seed))
    return tuple(
        np.concatenate([
            rng.choice(stratum, size=len(stratum), replace=True)
            for stratum in strata
        ])
        for _ in range(replicates)
    )


def test_bootstrap_matches_independent_pcg64_draws_counts_and_linear_quantiles() -> None:
    table = _table(MethodId.MMD, (0, 1, 1, 2, 2, 0))
    replicates = 25
    result = bootstrap_metrics(
        table, {"accuracy": _accuracy}, replicates=replicates, seed=41
    )[0]
    truth = np.asarray([row.true_label for row in table], dtype=np.int64)
    draws = _manual_stratified_draws(truth, replicates=replicates, seed=41)
    values = np.asarray([
        sum(table[index].true_label == table[index].predicted_label for index in draw) / len(draw)
        for draw in draws
    ])
    assert (result.requested, result.successful, result.invalid) == (25, 25, 0)
    assert result.point_estimate == pytest.approx(0.5)
    assert result.ci_low == pytest.approx(np.quantile(values, 0.025, method="linear"))
    assert result.ci_high == pytest.approx(np.quantile(values, 0.975, method="linear"))


def test_mcnemar_matches_exact_scipy_binomial_reference() -> None:
    reference = _table(MethodId.PROTOTYPE_PSEUDO, (0, 1, 1, 2, 2, 0))
    comparator = _table(MethodId.CORAL, (1, 0, 1, 1, 0, 2))
    result = exact_mcnemar(reference, comparator)
    assert (result.n00_both_wrong, result.n01_reference_correct) == (0, 2)
    assert (result.n10_comparator_correct, result.n11_both_correct) == (3, 1)
    assert result.raw_p_value == pytest.approx(
        binomtest(2, n=5, p=0.5, alternative="two-sided").pvalue
    )


def test_paired_bootstrap_matches_independent_shared_draws_and_centered_p_value() -> None:
    reference = _table(MethodId.PROTOTYPE_PSEUDO, (0, 1, 1, 2, 2, 0))
    comparator = _table(MethodId.CORAL, (1, 0, 1, 1, 0, 2))
    replicates = 30
    result = paired_bootstrap(
        reference, comparator, {"accuracy": _accuracy}, replicates=replicates, seed=7
    )[0]
    truth = np.asarray([row.true_label for row in reference], dtype=np.int64)
    draws = _manual_stratified_draws(truth, replicates=replicates, seed=7)
    differences = np.asarray([
        (
            sum(reference[index].true_label == reference[index].predicted_label for index in draw)
            - sum(comparator[index].true_label == comparator[index].predicted_label for index in draw)
        ) / len(draw)
        for draw in draws
    ])
    observed = 3 / 6 - 4 / 6
    centered = differences - observed
    expected_p = (1 + int(np.sum(np.abs(centered) >= abs(observed)))) / (replicates + 1)
    assert result.observed_difference == pytest.approx(observed)
    assert result.ci_low == pytest.approx(np.quantile(differences, 0.025, method="linear"))
    assert result.ci_high == pytest.approx(np.quantile(differences, 0.975, method="linear"))
    assert result.raw_p_value == pytest.approx(expected_p)


def test_holm_matches_statsmodels_for_complete_six_hypothesis_family() -> None:
    raw = (0.01, 0.04, 0.03, 0.20, 0.50, 0.01)
    rows = tuple(
        PairedDifference(
            method, "accuracy", "prototype_pseudo-comparator", 0.1,
            0.95, "percentile", 0.0, 0.2, "centered_plus_one", p_value,
            17, 100, 100, 0, ValueStatus.AVAILABLE, None,
        )
        for method, p_value in zip(COMPARATOR_METHODS, raw, strict=True)
    )
    result = adjust_holm(rows)
    expected = multipletests(np.asarray(raw), method="holm")[1]
    assert tuple(row.comparator_method for row in result) == COMPARATOR_METHODS
    assert np.asarray([row.adjusted_p_value for row in result]) == pytest.approx(expected)
