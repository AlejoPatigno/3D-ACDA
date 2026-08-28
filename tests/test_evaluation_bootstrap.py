from __future__ import annotations

import math

import numpy as np
import pytest

from acda3d.evaluation.bootstrap import bootstrap_metrics
from acda3d.evaluation.schemas import (
    BootstrapInterval,
    CheckpointPolicy,
    Direction,
    MethodId,
    MetricValue,
    SubjectPrediction,
    ValueStatus,
)


def _row(subject: str, true_label: int, predicted_label: int) -> SubjectPrediction:
    probabilities = [0.05, 0.05, 0.05]
    probabilities[predicted_label] = 0.9
    return SubjectPrediction(
        MethodId.MMD,
        Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        subject,
        true_label,
        tuple(probabilities),
        5,
        2,
        (f"{len(subject):064x}",),
    )


def _accuracy(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
    return MetricValue.available(
        sum(row.predicted_label == row.true_label for row in rows) / len(rows)
    )


def test_stratified_bootstrap_is_pcg64_deterministic_and_linear() -> None:
    table = (
        _row("cn-a", 0, 0), _row("cn-b", 0, 1),
        _row("mci-a", 1, 1), _row("mci-b", 1, 2),
        _row("ad-a", 2, 2), _row("ad-b", 2, 0),
    )
    result = bootstrap_metrics(table, {"accuracy": _accuracy}, replicates=20, seed=17)
    assert result == bootstrap_metrics(table, {"accuracy": _accuracy}, replicates=20, seed=17)

    rng = np.random.Generator(np.random.PCG64(17))
    strata = tuple(np.flatnonzero(np.asarray([row.true_label for row in table]) == label) for label in (0, 1, 2))
    expected = []
    for _ in range(20):
        indices = np.concatenate([rng.choice(stratum, size=len(stratum), replace=True) for stratum in strata])
        expected.append(float(_accuracy(tuple(table[index] for index in indices)).value))
    interval = result[0]
    assert interval == BootstrapInterval(
        "accuracy", 0.5, 0.95, "percentile",
        float(np.quantile(expected, 0.025, method="linear")),
        float(np.quantile(expected, 0.975, method="linear")),
        17, 20, 20, 0, ValueStatus.AVAILABLE, None,
    )


def test_bootstrap_never_redraws_invalid_metric_replicates() -> None:
    table = (_row("cn", 0, 0), _row("mci", 1, 1), _row("ad", 2, 2))
    calls = 0

    def alternating(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
        nonlocal calls
        calls += 1
        if calls > 1 and calls % 2 == 0:
            return MetricValue.unavailable("missing_true_class")
        return MetricValue.available(1.0)

    result = bootstrap_metrics(table, {"accuracy": alternating}, replicates=10, seed=3)[0]
    assert calls == 11
    assert (result.requested, result.successful, result.invalid) == (10, 5, 5)
    assert result.status is ValueStatus.UNAVAILABLE
    assert result.reason == "insufficient_valid_bootstrap_replicates"
    assert result.ci_low is result.ci_high is None


def test_bootstrap_threshold_is_exact_ceiling_of_ninety_five_percent() -> None:
    table = (_row("cn", 0, 0), _row("mci", 1, 1), _row("ad", 2, 2))
    calls = 0

    def one_invalid(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
        nonlocal calls
        calls += 1
        return MetricValue.unavailable("undefined") if calls == 2 else MetricValue.available(1.0)

    interval = bootstrap_metrics(table, {"accuracy": one_invalid}, replicates=20, seed=5)[0]
    assert (interval.successful, interval.invalid) == (19, 1)
    assert interval.status is ValueStatus.AVAILABLE
    assert interval.ci_low == interval.ci_high == 1.0


def test_bootstrap_preserves_metric_order_and_observed_unavailability() -> None:
    table = (_row("cn", 0, 0), _row("mci", 1, 1), _row("ad", 2, 2))
    results = bootstrap_metrics(
        table,
        {
            "accuracy": _accuracy,
            "macro_ovr_roc_auc": lambda rows: MetricValue.unavailable("missing_negative_class"),
        },
        replicates=3,
        seed=0,
    )
    assert tuple(result.metric for result in results) == ("accuracy", "macro_ovr_roc_auc")
    unavailable = results[1]
    assert unavailable.point_estimate is None
    assert unavailable.reason == "missing_negative_class"
    assert unavailable.status is ValueStatus.UNAVAILABLE


@pytest.mark.parametrize("replicates", [0, -1, True])
def test_bootstrap_rejects_nonpositive_replicates(replicates: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        bootstrap_metrics((_row("cn", 0, 0),), {"accuracy": _accuracy}, replicates=replicates, seed=1)


def test_bootstrap_rejects_empty_tables_and_nonfinite_metric_values() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        bootstrap_metrics((), {"accuracy": _accuracy}, replicates=1, seed=1)

    table = (_row("cn", 0, 0),)
    result = bootstrap_metrics(
        table, {"accuracy": lambda rows: math.nan}, replicates=2, seed=1
    )[0]
    assert result.successful == 0
    assert result.status is ValueStatus.UNAVAILABLE
