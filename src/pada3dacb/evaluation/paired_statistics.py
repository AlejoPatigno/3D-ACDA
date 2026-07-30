"""Exact paired predictive inference on aligned canonical subject tables."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
from scipy.stats import binomtest

from .bootstrap import MetricFunction, _draw_indices, _metric_value, _strata
from .schemas import (
    COMPARATOR_METHODS,
    PAIRED_METRIC_NAMES,
    McNemarResult,
    MethodId,
    PairedDifference,
    SubjectPrediction,
    ValueStatus,
)


def _validate_pair(
    reference: tuple[SubjectPrediction, ...],
    comparator: tuple[SubjectPrediction, ...],
) -> bool:
    if not reference or not comparator:
        raise ValueError("paired tables must be non-empty")
    if any(row.method_id is not MethodId.PROTOTYPE_PSEUDO for row in reference):
        raise ValueError("reference method must be prototype_pseudo")
    comparator_method = comparator[0].method_id
    if comparator_method not in COMPARATOR_METHODS or any(
        row.method_id is not comparator_method for row in comparator
    ):
        raise ValueError("comparator table must contain one approved comparator")
    reference_identity = (reference[0].direction, reference[0].checkpoint_policy)
    if any((row.direction, row.checkpoint_policy) != reference_identity for row in reference):
        raise ValueError("reference table must be homogeneous")
    if any((row.direction, row.checkpoint_policy) != reference_identity for row in comparator):
        raise ValueError("paired direction and checkpoint policy must match")
    reference_keys = tuple((row.subject_hash, row.true_label) for row in reference)
    comparator_keys = tuple((row.subject_hash, row.true_label) for row in comparator)
    return reference_keys == comparator_keys


def exact_mcnemar(
    reference: Sequence[SubjectPrediction],
    comparator: Sequence[SubjectPrediction],
) -> McNemarResult:
    """Compute the protocol two-sided exact McNemar result."""
    reference_rows = tuple(reference)
    comparator_rows = tuple(comparator)
    compatible = _validate_pair(reference_rows, comparator_rows)
    if not compatible:
        return McNemarResult(
            comparator_rows[0].method_id,
            0, 0, 0, 0, 0, 0,
            "exact_two_sided_mcnemar", None,
            ValueStatus.UNAVAILABLE, "incompatible_subjects", None,
        )
    outcomes = tuple(
        (ref.predicted_label == ref.true_label, comp.predicted_label == comp.true_label)
        for ref, comp in zip(reference_rows, comparator_rows, strict=True)
    )
    n00 = sum(not ref_correct and not comp_correct for ref_correct, comp_correct in outcomes)
    n01 = sum(ref_correct and not comp_correct for ref_correct, comp_correct in outcomes)
    n10 = sum(not ref_correct and comp_correct for ref_correct, comp_correct in outcomes)
    n11 = sum(ref_correct and comp_correct for ref_correct, comp_correct in outcomes)
    discordant = n01 + n10
    raw_p_value = (
        1.0
        if discordant == 0
        else float(binomtest(k=n01, n=discordant, p=0.5, alternative="two-sided").pvalue)
    )
    return McNemarResult(
        comparator_rows[0].method_id,
        len(reference_rows), n00, n01, n10, n11, discordant,
        "exact_two_sided_mcnemar", raw_p_value,
        ValueStatus.AVAILABLE, None,
        "no_discordant_pairs" if discordant == 0 else None,
    )


def paired_bootstrap(
    reference: Sequence[SubjectPrediction],
    comparator: Sequence[SubjectPrediction],
    metric_fns: Mapping[str, MetricFunction],
    *,
    replicates: int,
    seed: int,
) -> tuple[PairedDifference, ...]:
    """Compute paired stratified differences using one shared index vector per replicate."""
    reference_rows = tuple(reference)
    comparator_rows = tuple(comparator)
    compatible = _validate_pair(reference_rows, comparator_rows)
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("paired bootstrap replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("paired bootstrap seed must be an integer")
    if not metric_fns or any(name not in PAIRED_METRIC_NAMES for name in metric_fns):
        raise ValueError("paired metrics must be a non-empty ordered protocol subset")
    if not compatible:
        return tuple(
            PairedDifference(
                comparator_rows[0].method_id, name, "prototype_pseudo-comparator",
                None, 0.95, "percentile", None, None, "centered_plus_one", None,
                seed, replicates, 0, replicates,
                ValueStatus.UNAVAILABLE, "incompatible_subjects",
            )
            for name in metric_fns
        )

    observed: dict[str, float | None] = {}
    for name, metric_fn in metric_fns.items():
        reference_value = _metric_value(metric_fn(reference_rows))
        comparator_value = _metric_value(metric_fn(comparator_rows))
        observed[name] = (
            float(reference_value.value) - float(comparator_value.value)
            if reference_value.status is ValueStatus.AVAILABLE
            and comparator_value.status is ValueStatus.AVAILABLE
            else None
        )

    differences: dict[str, list[float]] = {name: [] for name in metric_fns}
    rng = np.random.Generator(np.random.PCG64(seed))
    strata = _strata(reference_rows)
    for _ in range(replicates):
        indices = _draw_indices(rng, strata)
        reference_sample = tuple(reference_rows[int(index)] for index in indices)
        comparator_sample = tuple(comparator_rows[int(index)] for index in indices)
        for name, metric_fn in metric_fns.items():
            reference_value = _metric_value(metric_fn(reference_sample))
            comparator_value = _metric_value(metric_fn(comparator_sample))
            if (
                reference_value.status is ValueStatus.AVAILABLE
                and comparator_value.status is ValueStatus.AVAILABLE
            ):
                difference = float(reference_value.value) - float(comparator_value.value)
                if math.isfinite(difference):
                    differences[name].append(difference)

    threshold = math.ceil(0.95 * replicates)
    results: list[PairedDifference] = []
    for name in metric_fns:
        values = differences[name]
        successful = len(values)
        common = (
            comparator_rows[0].method_id, name, "prototype_pseudo-comparator",
            observed[name], 0.95, "percentile",
        )
        tail = ("centered_plus_one", seed, replicates, successful, replicates - successful)
        if observed[name] is not None and successful >= threshold:
            array = np.asarray(values, dtype=np.float64)
            low, high = np.quantile(array, (0.025, 0.975), method="linear")
            centered = array - observed[name]
            raw_p_value = (1 + int(np.sum(np.abs(centered) >= abs(observed[name])))) / (successful + 1)
            results.append(PairedDifference(
                *common, float(low), float(high), tail[0], raw_p_value,
                *tail[1:], ValueStatus.AVAILABLE, None,
            ))
        else:
            reason = (
                "observed_metric_unavailable"
                if observed[name] is None
                else "insufficient_valid_bootstrap_replicates"
            )
            results.append(PairedDifference(
                *common, None, None, tail[0], None,
                *tail[1:], ValueStatus.UNAVAILABLE, reason,
            ))
    return tuple(results)
