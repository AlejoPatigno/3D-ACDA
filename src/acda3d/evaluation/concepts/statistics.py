"""Statistical tests and bootstrap for concept evaluation."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence

import numpy as np
from scipy import stats

from acda3d.evaluation import bootstrap as phase15_bootstrap
from acda3d.evaluation.schemas import (
    CheckpointPolicy,
    Direction,
    McNemarResult,
    MethodId,
    ValueStatus,
)

from .schemas import (
    ConceptBootstrapInterval,
    ConceptHolmRow,
    ConceptPairedDifference,
    PairedMethodComparison,
)

CONCEPT_COMPARATOR_METHODS = (
    MethodId.SOURCE_ONLY,
    MethodId.CORAL,
    MethodId.MMD,
    MethodId.CDAN,
)
CONCEPT_COMPARISON_METRIC_ORDER = ("concept_mae", "anatomy_mae", "js_divergence")


# ============================================================================
# Bootstrap
# ============================================================================

def _diagnosis_strata(labels: np.ndarray, expected_size: int) -> tuple[np.ndarray, ...]:
    labels = np.asarray(labels)
    if labels.ndim != 1 or labels.size != expected_size:
        raise ValueError("diagnosis labels must align with per-subject values")
    if not np.issubdtype(labels.dtype, np.integer) or np.any((labels < 0) | (labels > 2)):
        raise ValueError("diagnosis labels must use fixed indices 0, 1, and 2")
    return tuple(np.flatnonzero(labels == label) for label in (0, 1, 2))


def bootstrap_metric(
    values: np.ndarray,
    *,
    labels: np.ndarray,
    metric: str = "accuracy",
    n_replicates: int = 10000,
    seed: int = 0,
    ci_level: float = 0.95,
    ci_method: str = "percentile",
) -> ConceptBootstrapInterval:
    """
    Compute bootstrap confidence interval for a per-subject metric.

    Args:
        values: Per-subject values [N]
        n_replicates: Number of bootstrap replicates
        seed: Random seed
        ci_level: Confidence level (e.g., 0.95)
        ci_method: "percentile" or "bca"

    Returns:
        ConceptBootstrapInterval with point estimate, CI bounds, and metadata
    """
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("bootstrap values must be a per-subject vector")
    if isinstance(n_replicates, bool) or not isinstance(n_replicates, int) or n_replicates <= 0:
        raise ValueError("bootstrap replicates must be a positive integer")
    if ci_level != 0.95 or ci_method != "percentile":
        raise ValueError("bootstrap interval must use percentile 95")
    if not np.isfinite(values).all():
        raise ValueError("bootstrap values must be finite")
    strata = _diagnosis_strata(labels, len(values))
    if len(values) < 2:
        return ConceptBootstrapInterval(
            metric=metric,
            point_estimate=None,
            ci_level=ci_level,
            ci_method=ci_method,
            ci_low=None,
            ci_high=None,
            bootstrap_seed=seed,
            requested=n_replicates,
            successful=0,
            invalid=n_replicates,
            status=ValueStatus.UNAVAILABLE,
            reason="insufficient_samples",
        )

    rng = np.random.Generator(np.random.PCG64(seed))
    point = float(np.mean(values))
    bootstrapped = []

    for _ in range(n_replicates):
        idx = phase15_bootstrap._draw_indices(rng, strata)
        bootstrapped.append(np.mean(values[idx]))

    bootstrapped = np.array(bootstrapped)
    successful = int(np.sum(np.isfinite(bootstrapped)))
    invalid = n_replicates - successful

    if successful < 2:
        return ConceptBootstrapInterval(
            metric=metric,
            point_estimate=point,
            ci_level=ci_level,
            ci_method=ci_method,
            ci_low=None,
            ci_high=None,
            bootstrap_seed=seed,
            requested=n_replicates,
            successful=successful,
            invalid=invalid,
            status=ValueStatus.UNAVAILABLE,
            reason="bootstrap_failed",
        )

    # Percentile CI
    alpha = (1 - ci_level) / 2
    ci_low = float(np.percentile(bootstrapped, alpha * 100, method="linear"))
    ci_high = float(np.percentile(bootstrapped, (1 - alpha) * 100, method="linear"))

    return ConceptBootstrapInterval(
        metric=metric,
        point_estimate=point,
        ci_level=ci_level,
        ci_method=ci_method,
        ci_low=ci_low,
        ci_high=ci_high,
        bootstrap_seed=seed,
        requested=n_replicates,
        successful=successful,
        invalid=invalid,
        status=ValueStatus.AVAILABLE,
        reason=None,
    )


def bootstrap_metrics_dict(
    metrics: dict[str, np.ndarray],
    *,
    labels: np.ndarray,
    n_replicates: int = 10000,
    seed: int = 0,
    ci_level: float = 0.95,
    ci_method: str = "percentile",
) -> dict[str, ConceptBootstrapInterval]:
    """Bootstrap multiple metrics at once."""
    results = {}
    for name, values in metrics.items():
        results[name] = bootstrap_metric(
            values,
            labels=labels,
            metric=name,
            n_replicates=n_replicates,
            seed=seed,
            ci_level=ci_level,
            ci_method=ci_method,
        )
    return results


# ============================================================================
# Exact McNemar
# ============================================================================

def exact_mcnemar(
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    y_true: np.ndarray,
    *,
    comparator_method: MethodId = MethodId.SOURCE_ONLY,
) -> McNemarResult:
    """Compute the protocol exact two-sided McNemar test on paired subjects."""
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    y_true = np.asarray(y_true)
    if pred_a.ndim != 1 or pred_a.shape != pred_b.shape or pred_a.shape != y_true.shape:
        raise ValueError("McNemar arrays must be aligned one-dimensional vectors")
    if pred_a.size == 0:
        raise ValueError("McNemar arrays must be non-empty")

    n11 = int(np.sum((pred_a == y_true) & (pred_b == y_true)))
    n00 = int(np.sum((pred_a != y_true) & (pred_b != y_true)))
    n01 = int(np.sum((pred_a == y_true) & (pred_b != y_true)))
    n10 = int(np.sum((pred_a != y_true) & (pred_b == y_true)))
    discordant = n01 + n10
    p_value = (
        1.0
        if discordant == 0
        else float(stats.binomtest(n01, discordant, 0.5, alternative="two-sided").pvalue)
    )

    return McNemarResult(
        comparator_method=comparator_method,
        n_subjects=int(pred_a.size),
        n00_both_wrong=n00,
        n01_reference_correct=n01,
        n10_comparator_correct=n10,
        n11_both_correct=n11,
        discordant_count=discordant,
        test="exact_two_sided_mcnemar",
        raw_p_value=p_value,
        status=ValueStatus.AVAILABLE,
        reason=None,
        note_code="no_discordant_pairs" if discordant == 0 else None,
    )


# ============================================================================
# Paired Bootstrap
# ============================================================================

def paired_bootstrap_diff(
    values_a: np.ndarray,
    values_b: np.ndarray,
    *,
    labels: np.ndarray,
    comparator_method: MethodId = MethodId.SOURCE_ONLY,
    metric: str = "accuracy",
    n_replicates: int = 10000,
    seed: int = 0,
    ci_level: float = 0.95,
    ci_method: str = "percentile",
) -> ConceptPairedDifference:
    """Bootstrap paired subject-level mean differences (A minus B)."""
    values_a = np.asarray(values_a, dtype=np.float64)
    values_b = np.asarray(values_b, dtype=np.float64)
    if values_a.ndim != 1 or values_a.shape != values_b.shape:
        raise ValueError("Paired arrays must be aligned per-subject vectors")
    if values_a.size < 2:
        raise ValueError("Paired bootstrap requires at least two subjects")
    if not np.isfinite(values_a).all() or not np.isfinite(values_b).all():
        raise ValueError("Paired arrays must contain only finite values")
    if isinstance(n_replicates, bool) or not isinstance(n_replicates, int) or n_replicates <= 0:
        raise ValueError("paired bootstrap replicates must be a positive integer")
    if ci_level != 0.95 or ci_method != "percentile":
        raise ValueError("paired bootstrap must use percentile 95")

    if comparator_method not in CONCEPT_COMPARATOR_METHODS:
        raise ValueError("concept comparator must be one of the four 3D-ACDA comparators")
    strata = _diagnosis_strata(labels, values_a.size)
    differences = values_a - values_b
    point = float(np.mean(differences))
    rng = np.random.Generator(np.random.PCG64(seed))
    bootstrapped = np.empty(n_replicates, dtype=np.float64)
    for index in range(n_replicates):
        indices = phase15_bootstrap._draw_indices(rng, strata)
        bootstrapped[index] = np.mean(differences[indices])

    ci_low, ci_high = np.percentile(
        bootstrapped, (2.5, 97.5), method="linear"
    )
    centered = bootstrapped - point
    raw_p_value = (1 + int(np.sum(np.abs(centered) >= abs(point)))) / (
        n_replicates + 1
    )
    return ConceptPairedDifference(
        comparator_method=comparator_method,
        metric=metric,
        orientation="prototype_pseudo-comparator",
        observed_difference=point,
        ci_level=ci_level,
        ci_method=ci_method,
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        p_value_method="centered_plus_one",
        raw_p_value=float(raw_p_value),
        bootstrap_seed=seed,
        requested=n_replicates,
        successful=n_replicates,
        invalid=0,
        status=ValueStatus.AVAILABLE,
        reason=None,
    )


# ============================================================================
# Holm Correction
# ============================================================================

def adjust_holm(
    p_values: list[float],
    *,
    metric: str = "accuracy",
) -> list[ConceptHolmRow]:
    """Adjust one fixed four-comparator concept-metric family."""
    if len(p_values) != len(CONCEPT_COMPARATOR_METHODS):
        raise ValueError("Holm requires the four 3D-ACDA comparators")
    if any(not np.isfinite(value) or not 0.0 <= value <= 1.0 for value in p_values):
        raise ValueError("Holm p-values must be finite and in [0, 1]")

    order = sorted(range(len(p_values)), key=lambda index: (p_values[index], index))
    ranks: dict[int, int] = {}
    adjusted: dict[int, float] = {}
    running_max = 0.0
    family_size = len(p_values)
    for rank, index in enumerate(order, start=1):
        running_max = max(running_max, (family_size - rank + 1) * p_values[index])
        ranks[index] = rank
        adjusted[index] = min(1.0, running_max)

    return [
        ConceptHolmRow(
            statistic_family="paired_bootstrap",
            metric=metric,
            family_size=family_size,
            available_count=family_size,
            comparator_method=comparator,
            raw_p_value=float(p_values[index]),
            holm_rank=ranks[index],
            adjusted_p_value=adjusted[index],
            status=ValueStatus.AVAILABLE,
            reason=None,
        )
        for index, comparator in enumerate(CONCEPT_COMPARATOR_METHODS)
    ]


def adjust_holm_families(
    families: dict[str, list[float]],
    alpha: float = 0.05,
) -> dict[str, list[ConceptHolmRow]]:
    """
    Apply Holm correction within each family.

    Args:
        families: Dict of family_name -> list of p-values
        alpha: FWER

    Returns:
        Dict of family_name -> list of ConceptHolmRow
    """
    results = {}
    for fam_name, p_vals in families.items():
        results[fam_name] = adjust_holm(p_vals, metric=fam_name)
    return results

def _subject_metric_vector(
    values: np.ndarray | Mapping[Hashable, float],
    *,
    metric: str,
    source: str,
    explicit_subject_ids: Sequence[Hashable] | None,
) -> tuple[tuple[Hashable, ...], np.ndarray]:
    """Return a metric vector and the subject identities that order it."""
    if isinstance(values, Mapping):
        subject_ids = tuple(values.keys())
        raw_values = tuple(values.values())
        if explicit_subject_ids is not None and tuple(explicit_subject_ids) != subject_ids:
            raise ValueError(
                f"{source} metric {metric} subject IDs must have identical ordering and set"
            )
    else:
        if explicit_subject_ids is None:
            raise ValueError(
                f"{source} metric {metric} requires explicit subject IDs or a keyed mapping"
            )
        subject_ids = tuple(explicit_subject_ids)
        raw_values = values

    try:
        if len(set(subject_ids)) != len(subject_ids):
            raise ValueError(f"{source} metric {metric} subject IDs must be unique")
    except TypeError as error:
        raise ValueError(f"{source} metric {metric} subject IDs must be hashable") from error

    vector = np.asarray(raw_values, dtype=np.float64)
    if vector.ndim != 1 or vector.size != len(subject_ids):
        raise ValueError(f"{source} metric {metric} must be a one-dimensional subject vector")
    return subject_ids, vector


def _comparator_subject_ids(
    subject_ids: Mapping[MethodId | str, Sequence[Hashable]] | None,
    comparator: MethodId,
) -> Sequence[Hashable] | None:
    if subject_ids is None:
        return None
    if comparator in subject_ids:
        return subject_ids[comparator]
    if comparator.value in subject_ids:
        return subject_ids[comparator.value]
    raise ValueError(f"missing explicit subject IDs for comparator {comparator.value}")


def compute_paired_method_comparisons(
    prototype_metrics: Mapping[str, np.ndarray | Mapping[Hashable, float]],
    comparator_metrics: Mapping[
        MethodId | str, Mapping[str, np.ndarray | Mapping[Hashable, float]]
    ],
    *,
    labels: np.ndarray | Mapping[Hashable, int],
    direction: Direction,
    checkpoint_policy: CheckpointPolicy,
    n_replicates: int = 10000,
    seed: int = 0,
    subject_ids: Sequence[Hashable] | None = None,
    comparator_subject_ids: Mapping[MethodId | str, Sequence[Hashable]] | None = None,
) -> list[PairedMethodComparison]:
    """Compare prototype-pseudo with each approved 3D-ACDA comparator.

    Every metric must carry subject identities either as a keyed mapping or
    through the explicit ``subject_ids``/``comparator_subject_ids`` arguments.
    The canonical subject order must be identical for every metric and method;
    otherwise the comparison fails before the approved paired-bootstrap
    equations are applied.
    """
    from .schemas import CONCEPT_COMPARISON_METRICS, PairedMethodComparison

    required_metrics = CONCEPT_COMPARISON_METRIC_ORDER
    if any(metric not in prototype_metrics for metric in required_metrics):
        raise ValueError("prototype metrics must contain concept_mae, anatomy_mae, and js_divergence")
    normalized = {
        method if isinstance(method, MethodId) else MethodId(method): metrics
        for method, metrics in comparator_metrics.items()
    }
    if set(normalized) != set(CONCEPT_COMPARATOR_METHODS):
        raise ValueError("paired comparisons require exactly the four 3D-ACDA comparators")
    if set(required_metrics) != set(CONCEPT_COMPARISON_METRICS):
        raise ValueError("concept comparison metric contract is inconsistent")
    if any(metric not in metrics for metrics in normalized.values() for metric in required_metrics):
        raise ValueError("each comparator must provide all concept comparison metrics")

    prototype_vectors: dict[str, np.ndarray] = {}
    canonical_ids: tuple[Hashable, ...] | None = None
    for metric in required_metrics:
        metric_ids, vector = _subject_metric_vector(
            prototype_metrics[metric],
            metric=metric,
            source="prototype",
            explicit_subject_ids=subject_ids,
        )
        if canonical_ids is None:
            canonical_ids = metric_ids
        elif metric_ids != canonical_ids:
            raise ValueError("prototype metric subject IDs must have identical ordering and set")
        prototype_vectors[metric] = vector
    assert canonical_ids is not None

    if not isinstance(labels, Mapping):
        raise ValueError("diagnosis labels must be a keyed subject mapping")
    label_ids = tuple(labels.keys())
    if label_ids != canonical_ids:
        raise ValueError("label subject IDs must have identical ordering and set")
    label_values = np.asarray(tuple(labels.values()))
    if label_values.ndim != 1 or label_values.size != len(canonical_ids):
        raise ValueError("diagnosis labels must align with paired subject identities")

    comparator_vectors: dict[MethodId, dict[str, np.ndarray]] = {}
    for comparator in CONCEPT_COMPARATOR_METHODS:
        comparator_ids: tuple[Hashable, ...] | None = None
        explicit_ids = _comparator_subject_ids(comparator_subject_ids, comparator)
        comparator_vectors[comparator] = {}
        for metric in required_metrics:
            metric_ids, vector = _subject_metric_vector(
                normalized[comparator][metric],
                metric=metric,
                source=comparator.value,
                explicit_subject_ids=explicit_ids,
            )
            if comparator_ids is None:
                comparator_ids = metric_ids
            elif metric_ids != comparator_ids:
                raise ValueError(
                    f"{comparator.value} metric subject IDs must have identical ordering and set"
                )
            comparator_vectors[comparator][metric] = vector
        assert comparator_ids is not None
        if comparator_ids != canonical_ids:
            if set(comparator_ids) != set(canonical_ids):
                raise ValueError("subject IDs must have identical ordering and set")
            raise ValueError("subject IDs must have identical ordering")

    by_metric: dict[str, dict[MethodId, ConceptPairedDifference]] = {
        metric: {} for metric in required_metrics
    }
    for metric in required_metrics:
        for comparator in CONCEPT_COMPARATOR_METHODS:
            by_metric[metric][comparator] = paired_bootstrap_diff(
                prototype_vectors[metric],
                comparator_vectors[comparator][metric],
                labels=label_values,
                comparator_method=comparator,
                metric=metric,
                n_replicates=n_replicates,
                seed=seed,
            )

    rows: list[PairedMethodComparison] = []
    for metric in required_metrics:
        raw = [by_metric[metric][method].raw_p_value for method in CONCEPT_COMPARATOR_METHODS]
        if any(value is None for value in raw):
            raise ValueError("Holm correction requires one available p-value per comparator")
        holm_rows = adjust_holm([float(value) for value in raw], metric=metric)
        holm_by_method = {row.comparator_method: row for row in holm_rows}
        for comparator in CONCEPT_COMPARATOR_METHODS:
            paired = by_metric[metric][comparator]
            holm = holm_by_method[comparator]
            rows.append(
                PairedMethodComparison(
                    comparator_method=comparator,
                    direction=direction,
                    checkpoint_policy=checkpoint_policy,
                    metric_family=metric,
                    mean_difference=paired.observed_difference,
                    ci_low=paired.ci_low,
                    ci_high=paired.ci_high,
                    p_value=paired.raw_p_value,
                    adjusted_p_value=holm.adjusted_p_value,
                    holm_rank=holm.holm_rank,
                    status=paired.status,
                    reason=paired.reason,
                )
            )
    return rows


# Descriptive alias used by report orchestration callers.
paired_subject_comparisons = compute_paired_method_comparisons
