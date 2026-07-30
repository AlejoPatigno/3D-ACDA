from __future__ import annotations

import pytest

from pada3dacb.evaluation.multiple_testing import adjust_holm
from pada3dacb.evaluation.schemas import (
    COMPARATOR_METHODS,
    McNemarResult,
    MethodId,
    PairedDifference,
    ValueStatus,
)


def _paired(
    comparator: MethodId,
    raw_p_value: float | None,
    reason: str | None = None,
) -> PairedDifference:
    available = raw_p_value is not None
    return PairedDifference(
        comparator, "accuracy", "prototype_pseudo-comparator",
        0.1 if available else None, 0.95, "percentile",
        0.0 if available else None, 0.2 if available else None,
        "centered_plus_one", raw_p_value, 17, 100,
        100 if available else 0, 0 if available else 100,
        ValueStatus.AVAILABLE if available else ValueStatus.UNAVAILABLE,
        None if available else reason,
    )


def test_holm_uses_six_hypotheses_canonical_ties_and_unavailable_slots() -> None:
    raw = {
        MethodId.SOURCE_ONLY: 0.01,
        MethodId.CORAL: 0.04,
        MethodId.MMD: 0.03,
        MethodId.CDAN: None,
        MethodId.AAGN: 0.20,
        MethodId.FASTER_SNN: 0.01,
    }
    rows = tuple(
        _paired(method, raw[method], "observed_metric_unavailable")
        for method in reversed(COMPARATOR_METHODS)
    )
    adjusted = adjust_holm(rows)
    assert tuple(row.comparator_method for row in adjusted) == COMPARATOR_METHODS
    assert all(row.family_size == 6 and row.available_count == 5 for row in adjusted)

    by_method = {row.comparator_method: row for row in adjusted}
    assert (by_method[MethodId.SOURCE_ONLY].holm_rank, by_method[MethodId.SOURCE_ONLY].adjusted_p_value) == (1, 0.06)
    assert (by_method[MethodId.FASTER_SNN].holm_rank, by_method[MethodId.FASTER_SNN].adjusted_p_value) == (2, 0.06)
    assert (by_method[MethodId.MMD].holm_rank, by_method[MethodId.MMD].adjusted_p_value) == (3, 0.12)
    assert (by_method[MethodId.CORAL].holm_rank, by_method[MethodId.CORAL].adjusted_p_value) == (4, 0.12)
    assert (by_method[MethodId.AAGN].holm_rank, by_method[MethodId.AAGN].adjusted_p_value) == (5, 0.4)
    unavailable = by_method[MethodId.CDAN]
    assert unavailable.raw_p_value is unavailable.adjusted_p_value is unavailable.holm_rank is None
    assert unavailable.reason == "observed_metric_unavailable"


def test_holm_builds_separate_mcnemar_family() -> None:
    rows = tuple(
        McNemarResult(
            method, 3, 1, 0, 0, 2, 0, "exact_two_sided_mcnemar",
            1.0, ValueStatus.AVAILABLE, None, "no_discordant_pairs",
        )
        for method in COMPARATOR_METHODS
    )
    adjusted = adjust_holm(rows)
    assert all(row.statistic_family == "mcnemar_accuracy" for row in adjusted)
    assert all(row.metric is None for row in adjusted)
    assert all(row.adjusted_p_value == 1.0 for row in adjusted)


def test_holm_rejects_missing_duplicate_mixed_or_non_six_families() -> None:
    paired = tuple(_paired(method, 0.5) for method in COMPARATOR_METHODS)
    with pytest.raises(ValueError, match="exactly six"):
        adjust_holm(paired[:-1])
    with pytest.raises(ValueError, match="comparators"):
        adjust_holm(paired[:-1] + (paired[0],))
    mcnemar = McNemarResult(
        MethodId.SOURCE_ONLY, 3, 1, 0, 0, 2, 0,
        "exact_two_sided_mcnemar", 1.0, ValueStatus.AVAILABLE,
        None, "no_discordant_pairs",
    )
    with pytest.raises(ValueError, match="same family"):
        adjust_holm((mcnemar,) + paired[1:])
    with pytest.raises(ValueError, match="six"):
        adjust_holm(paired, family_size=5)  # type: ignore[arg-type]


def test_holm_rejects_mixed_paired_metrics() -> None:
    rows = [_paired(method, 0.5) for method in COMPARATOR_METHODS]
    rows[-1] = PairedDifference(
        MethodId.FASTER_SNN, "macro_f1", "prototype_pseudo-comparator",
        0.1, 0.95, "percentile", 0.0, 0.2, "centered_plus_one",
        0.5, 17, 100, 100, 0, ValueStatus.AVAILABLE, None,
    )
    with pytest.raises(ValueError, match="same metric"):
        adjust_holm(rows)
