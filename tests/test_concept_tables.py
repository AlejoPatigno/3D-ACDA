"""Output-table tests for Phase 16 concept evaluation."""

from __future__ import annotations

import csv

from pada3dacb.evaluation.concepts.tables import holm_adjusted_rows, write_all_tables
from pada3dacb.evaluation.schemas import HolmRow, MethodId, ValueStatus


def test_holm_rows_do_not_mutate_the_input_collection() -> None:
    source = HolmRow(
        statistic_family="paired_bootstrap",
        metric="accuracy",
        family_size=6,
        available_count=1,
        comparator_method=MethodId.SOURCE_ONLY,
        raw_p_value=0.01,
        holm_rank=1,
        adjusted_p_value=0.06,
        status=ValueStatus.AVAILABLE,
        reason=None,
    )
    family = [source]

    rows = holm_adjusted_rows({"accuracy": family})

    assert family == [source]
    assert len(rows) == 1
    assert rows[0]["comparator_method"] is MethodId.SOURCE_ONLY
    assert rows[0]["adjusted_p_value"] == 0.06


def test_write_all_tables_preserves_first_row_column_order(tmp_path) -> None:
    rows = [{"method": "source_only", "value": 0.25}]

    write_all_tables(tmp_path, {"summary": rows})

    output = tmp_path / "tables" / "summary.csv"
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["method", "value"]
        assert list(reader) == [{"method": "source_only", "value": "0.25"}]
