"""Direct deterministic Holm correction for fixed six-comparator families."""
from __future__ import annotations

from collections.abc import Sequence

from .schemas import (
    COMPARATOR_METHODS,
    HolmRow,
    McNemarResult,
    PairedDifference,
    ValueStatus,
)

RawInference = McNemarResult | PairedDifference


def adjust_holm(
    rows: Sequence[RawInference],
    *,
    family_size: int = 6,
    comparator_order: tuple = COMPARATOR_METHODS,
) -> tuple[HolmRow, ...]:
    """Adjust one predeclared family while retaining unavailable hypothesis slots."""
    items = tuple(rows)
    if family_size != 6 or len(comparator_order) != 6:
        raise ValueError("Holm family size must remain six")
    if len(items) != 6:
        raise ValueError("Holm requires exactly six hypothesis rows")
    if tuple(comparator_order) != COMPARATOR_METHODS:
        raise ValueError("Holm comparator order must be canonical")
    by_comparator = {row.comparator_method: row for row in items}
    if len(by_comparator) != 6 or set(by_comparator) != set(COMPARATOR_METHODS):
        raise ValueError("Holm comparators must be complete and unique")

    paired_family = all(isinstance(row, PairedDifference) for row in items)
    mcnemar_family = all(isinstance(row, McNemarResult) for row in items)
    if not paired_family and not mcnemar_family:
        raise ValueError("Holm rows must belong to the same family")
    metric = items[0].metric if paired_family else None  # type: ignore[union-attr]
    if paired_family and any(row.metric != metric for row in items):  # type: ignore[union-attr]
        raise ValueError("paired Holm rows must use the same metric")
    statistic_family = "paired_bootstrap" if paired_family else "mcnemar_accuracy"

    order_index = {method: index for index, method in enumerate(COMPARATOR_METHODS)}
    available = [
        row for row in items
        if row.status is ValueStatus.AVAILABLE and row.raw_p_value is not None
    ]
    ranked = sorted(
        available,
        key=lambda row: (float(row.raw_p_value), order_index[row.comparator_method]),
    )
    ranks: dict = {}
    adjusted: dict = {}
    running_max = 0.0
    for rank, row in enumerate(ranked, start=1):
        candidate = (family_size - rank + 1) * float(row.raw_p_value)
        running_max = max(running_max, candidate)
        ranks[row.comparator_method] = rank
        adjusted[row.comparator_method] = min(1.0, running_max)

    results = []
    for comparator in COMPARATOR_METHODS:
        source = by_comparator[comparator]
        if source.status is ValueStatus.AVAILABLE and source.raw_p_value is not None:
            results.append(HolmRow(
                statistic_family, metric, family_size, len(available), comparator,
                float(source.raw_p_value), ranks[comparator], adjusted[comparator],
                ValueStatus.AVAILABLE, None,
            ))
        else:
            results.append(HolmRow(
                statistic_family, metric, family_size, len(available), comparator,
                None, None, None, ValueStatus.UNAVAILABLE,
                source.reason or "p_value_unavailable",
            ))
    return tuple(results)
