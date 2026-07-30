"""CPU-only figure smoke tests for Phase 16."""

from __future__ import annotations

from pada3dacb.evaluation.concepts.figures import (
    plot_concept_fidelity_roi_heatmap,
    plot_head_agreement_matrix,
)


def test_fidelity_heatmap_creates_nested_output(tmp_path) -> None:
    output = tmp_path / "figures" / "fidelity.png"

    plot_concept_fidelity_roi_heatmap(
        [
            {"method": "source_only", "roi_index": 0, "mae": 0.1},
            {"method": "source_only", "roi_index": 1, "mae": 0.2},
            {"method": "coral", "roi_index": 0, "mae": 0.2},
            {"method": "coral", "roi_index": 1, "mae": 0.3},
        ],
        output,
        roi_labels=["ROI A", "ROI B"],
    )

    assert output.is_file()
    assert output.stat().st_size > 0


def test_head_agreement_handles_zero_support_rows(tmp_path) -> None:
    output = tmp_path / "figures" / "agreement.png"

    plot_head_agreement_matrix(
        {
            "source_only": {
                "comparator_method": "source_only",
                "confusion_matrix": [[2, 0, 0], [0, 0, 0], [0, 1, 1]],
            }
        },
        output,
    )

    assert output.is_file()
    assert output.stat().st_size > 0
