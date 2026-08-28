"""Output-table tests for Phase 16 concept evaluation."""

from __future__ import annotations

import csv

from acda3d.evaluation.concepts.tables import holm_adjusted_rows, write_all_tables
from acda3d.evaluation.schemas import HolmRow, MethodId, ValueStatus


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


def test_write_required_tables_creates_complete_protocol_set(tmp_path) -> None:
    from acda3d.evaluation.concepts.tables import write_required_tables

    write_required_tables(tmp_path, {"method_status": [{"method": "aagn"}]})

    expected = {
        "concept_fidelity_global.csv",
        "concept_fidelity_per_subject.csv",
        "concept_fidelity_per_roi.csv",
        "anatomy_consistency_global.csv",
        "anatomy_consistency_per_subject.csv",
        "anatomy_consistency_per_roi.csv",
        "head_agreement.csv",
        "roi_stability.csv",
        "class_conditional_profiles.csv",
        "paired_method_comparisons.csv",
        "method_status.csv",
    }
    assert {path.name for path in (tmp_path / "tables").iterdir()} == expected
