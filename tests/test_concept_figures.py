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


def test_generate_all_figures_writes_fixed_protocol_names(tmp_path) -> None:
    import numpy as np

    from pada3dacb.evaluation.concepts.figures import generate_all_figures
    from pada3dacb.evaluation.concepts.stability import compute_all_stability

    profiles = np.array([[0.1, 0.3], [0.2, 0.4]], dtype=float)
    stability = compute_all_stability(profiles, profiles, profiles, profiles, k_values=[1])
    data = {
        "fidelity_per_roi": [
            {"method": "prototype_pseudo", "roi_index": 0, "mae": 0.1},
            {"method": "prototype_pseudo", "roi_index": 1, "mae": 0.2},
        ],
        "anatomy_per_roi": [
            {"method": "prototype_pseudo", "roi_index": 0, "mae": 0.2},
            {"method": "prototype_pseudo", "roi_index": 1, "mae": 0.3},
        ],
        "agreement": {
            "prototype_pseudo": {
                "comparator_method": "prototype_pseudo",
                "confusion_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            }
        },
        "stability": stability,
        "class_profiles": [
            {"class_label": label, "roi_index": roi, "mean": 0.1 + roi,
             "ci_low": 0.05 + roi, "ci_high": 0.15 + roi}
            for label in ("CN", "MCI", "AD") for roi in (0, 1)
        ],
    }

    generate_all_figures(tmp_path, data, roi_labels=["ROI 0", "ROI 1"], top_k=[1])

    assert {
        path.name for path in tmp_path.iterdir() if path.is_file()
    } == {
        "concept_fidelity_roi_heatmap.png",
        "anatomy_consistency_roi_heatmap.png",
        "head_agreement_matrix.png",
        "roi_stability_heatmap.png",
        "class_conditional_concept_profiles.png",
    }
