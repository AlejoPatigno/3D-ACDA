"""Deterministic true-class-stratified subject bootstrap."""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence

import numpy as np

from .schemas import (
    AGGREGATE_METRIC_NAMES,
    ANALYSIS_CLASS_INDICES,
    BootstrapInterval,
    MetricValue,
    SubjectPrediction,
    ValueStatus,
)

MetricFunction = Callable[[tuple[SubjectPrediction, ...]], MetricValue | float | int | None]


def _validate_table(table: tuple[SubjectPrediction, ...]) -> None:
    if not table:
        raise ValueError("bootstrap table must be non-empty")
    first = table[0]
    identity = (first.method_id, first.direction, first.checkpoint_policy)
    if any((row.method_id, row.direction, row.checkpoint_policy) != identity for row in table[1:]):
        raise ValueError("bootstrap table must be homogeneous")
    subjects = tuple(row.subject_hash for row in table)
    if len(subjects) != len(set(subjects)):
        raise ValueError("bootstrap table must contain unique subjects")


def _metric_value(value: MetricValue | float | int | None) -> MetricValue:
    if isinstance(value, MetricValue):
        return value
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
    ):
        return MetricValue.unavailable("non_finite_metric")
    return MetricValue.available(float(value))


def _strata(table: tuple[SubjectPrediction, ...]) -> tuple[np.ndarray, ...]:
    labels = np.asarray([row.true_label for row in table], dtype=np.int64)
    return tuple(np.flatnonzero(labels == label) for label in ANALYSIS_CLASS_INDICES)


def _draw_indices(
    rng: np.random.Generator,
    strata: tuple[np.ndarray, ...],
) -> np.ndarray:
    draws = tuple(
        rng.choice(stratum, size=len(stratum), replace=True)
        for stratum in strata
        if len(stratum) > 0
    )
    return np.concatenate(draws).astype(np.int64, copy=False)


def bootstrap_metrics(
    table: Sequence[SubjectPrediction],
    metric_fns: Mapping[str, MetricFunction],
    *,
    replicates: int,
    seed: int,
) -> tuple[BootstrapInterval, ...]:
    """Compute fixed-order percentile intervals without redrawing invalid replicates."""
    rows = tuple(table)
    _validate_table(rows)
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("bootstrap replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("bootstrap seed must be an integer")
    if not metric_fns or any(name not in AGGREGATE_METRIC_NAMES for name in metric_fns):
        raise ValueError("bootstrap metrics must be a non-empty ordered aggregate subset")

    observed = {
        name: _metric_value(metric_fn(rows))
        for name, metric_fn in metric_fns.items()
    }
    successful_values: dict[str, list[float]] = {name: [] for name in metric_fns}
    rng = np.random.Generator(np.random.PCG64(seed))
    strata = _strata(rows)

    for _ in range(replicates):
        indices = _draw_indices(rng, strata)
        sampled = tuple(rows[int(index)] for index in indices)
        for name, metric_fn in metric_fns.items():
            value = _metric_value(metric_fn(sampled))
            if value.status is ValueStatus.AVAILABLE:
                successful_values[name].append(float(value.value))

    threshold = math.ceil(0.95 * replicates)
    intervals: list[BootstrapInterval] = []
    for name in metric_fns:
        point = observed[name]
        values = successful_values[name]
        successful = len(values)
        common = (name, float(point.value) if point.status is ValueStatus.AVAILABLE else None,
                  0.95, "percentile")
        counts = (seed, replicates, successful, replicates - successful)
        if point.status is ValueStatus.AVAILABLE and successful >= threshold:
            low, high = np.quantile(np.asarray(values, dtype=np.float64), (0.025, 0.975), method="linear")
            intervals.append(BootstrapInterval(
                *common, float(low), float(high), *counts, ValueStatus.AVAILABLE, None
            ))
        else:
            reason = point.reason if point.status is ValueStatus.UNAVAILABLE else "insufficient_valid_bootstrap_replicates"
            intervals.append(BootstrapInterval(
                *common, None, None, *counts, ValueStatus.UNAVAILABLE, reason
            ))
    return tuple(intervals)
