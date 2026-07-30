"""Figure generation for concept evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np


def set_publication_style():
    """Set publication-ready matplotlib style."""
    plt.rcParams.update({
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.figsize": (8, 6),
        "font.family": "DejaVu Sans",
    })


def _save_figure(output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def plot_concept_fidelity_roi_heatmap(
    fidelity_per_roi: list[dict],     # List of {method, roi_index, mae, rmse, bias}
    output_path: str | Path,
    roi_labels: list[str] | None = None,
) -> None:
    """
    Plot concept fidelity ROI heatmap.

    Args:
        fidelity_per_roi: List of dicts with per-ROI metrics per method
        output_path: Output path for PNG
        roi_labels: Optional ROI names
    """
    set_publication_style()

    # Prepare data matrix [methods x ROIs]
    methods = sorted({d["method"] for d in fidelity_per_roi})
    max_roi = max(d["roi_index"] for d in fidelity_per_roi)
    K = max_roi + 1

    matrix = np.full((len(methods), K), np.nan)
    for d in fidelity_per_roi:
        m_idx = methods.index(d["method"])
        matrix[m_idx, d["roi_index"]] = d["mae"]

    fig, ax = plt.subplots(figsize=(max(8, K * 0.3), max(4, len(methods) * 0.4)))

    im = ax.imshow(matrix, aspect="auto", cmap="Reds", vmin=0, vmax=np.nanmax(matrix))

    ax.set_xticks(range(K))
    ax.set_xticklabels(roi_labels or [f"ROI {i}" for i in range(K)], rotation=45, ha="right")
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods)
    ax.set_xlabel("ROI")
    ax.set_ylabel("Method")
    ax.set_title("Concept Fidelity MAE per ROI")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("MAE")

    _save_figure(output_path)


def plot_anatomy_consistency_roi_heatmap(
    anatomy_per_roi: list[dict],
    output_path: str | Path,
    roi_labels: list[str] | None = None,
) -> None:
    """Plot anatomical consistency ROI heatmap."""
    set_publication_style()

    methods = sorted({d["method"] for d in anatomy_per_roi})
    max_roi = max(d["roi_index"] for d in anatomy_per_roi)
    K = max_roi + 1

    matrix = np.full((len(methods), K), np.nan)
    for d in anatomy_per_roi:
        m_idx = methods.index(d["method"])
        matrix[m_idx, d["roi_index"]] = d["mae"]

    fig, ax = plt.subplots(figsize=(max(8, K * 0.3), max(4, len(methods) * 0.4)))

    im = ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=np.nanmax(matrix))

    ax.set_xticks(range(K))
    ax.set_xticklabels(roi_labels or [f"ROI {i}" for i in range(K)], rotation=45, ha="right")
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods)
    ax.set_xlabel("ROI")
    ax.set_ylabel("Method")
    ax.set_title("Anatomical Consistency MAE per ROI")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("MAE")

    _save_figure(output_path)


def plot_head_agreement_matrix(
    agreement_data: dict,  # {method_pair: agreement_metrics}
    output_path: str | Path,
) -> None:
    """Plot head agreement matrix (latent vs concept predictions)."""
    set_publication_style()

    methods = sorted({d["comparator_method"] for d in agreement_data.values()})

    fig, axes = plt.subplots(2, len(methods), figsize=(4 * len(methods), 8))
    if len(methods) == 1:
        axes = axes.reshape(2, 1)

    for m_idx, method in enumerate(methods):
        data = agreement_data[method]
        # Confusion matrix: latent pred vs concept pred
        cm = np.array(data["confusion_matrix"])

        # Top row: count
        ax = axes[0, m_idx]
        ax.imshow(cm, cmap="Oranges", aspect="auto")
        ax.set_title(f"{method}: Count")
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["CN", "MCI", "AD"])
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(["CN", "MCI", "AD"])
        ax.set_ylabel("Latent")
        ax.set_xlabel("Concept")

        for i in range(3):
            for j in range(3):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center")

        # Bottom row: normalized
        ax = axes[1, m_idx]
        row_sums = cm.sum(axis=1, keepdims=True)
        cm_norm = np.divide(
            cm,
            row_sums,
            out=np.zeros_like(cm, dtype=np.float64),
            where=row_sums != 0,
        )
        ax.imshow(cm_norm, cmap="Oranges", aspect="auto", vmin=0, vmax=1)
        ax.set_title(f"{method}: Normalized")
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["CN", "MCI", "AD"])
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(["CN", "MCI", "AD"])
        ax.set_ylabel("Latent")
        ax.set_xlabel("Concept")

        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{cm_norm[i, j]:.2f}", ha="center", va="center")

    _save_figure(output_path)


def plot_roi_stability_heatmap(
    stability: Any,  # ROIStabilityMetrics
    output_path: str | Path,
    roi_labels: list[str] | None = None,
) -> None:
    """Plot ROI stability heatmap."""
    set_publication_style()

    metrics = ["fidelity", "anatomy", "concept", "alpha"]

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axes = axes.flatten()

    for i, metric in enumerate(metrics):
        ax = axes[i]
        if metric == "fidelity":
            std = stability.instance_std_fidelity
        elif metric == "anatomy":
            std = stability.instance_std_anatomy
        elif metric == "concept":
            std = stability.instance_std_concept
        else:
            std = stability.instance_std_alpha

        ax.bar(range(len(std)), std)
        ax.set_xticks(range(len(std)))
        ax.set_xticklabels(roi_labels or [f"ROI {i}" for i in range(len(std))], rotation=45)
        ax.set_ylabel("Std across instances")
        ax.set_title(f"{metric.capitalize()} Std")

    _save_figure(output_path)


def plot_class_conditional_profiles(
    class_profiles: list[dict],  # List of {class_label, roi_index, mean, ci_low, ci_high}
    output_path: str | Path,
    roi_labels: list[str] | None = None,
) -> None:
    """Plot class-conditional concept profiles with bootstrap CIs."""
    set_publication_style()

    classes = ["CN", "MCI", "AD"]
    K = max(p["roi_index"] for p in class_profiles) + 1

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for c_idx, class_name in enumerate(classes):
        ax = axes[c_idx]
        class_data = [p for p in class_profiles if p["class_label"] == class_name]
        class_data.sort(key=lambda x: x["roi_index"])

        x = [p["roi_index"] for p in class_data]
        y = [p["mean"] for p in class_data]
        ci_low = [p["ci_low"] for p in class_data]
        ci_high = [p["ci_high"] for p in class_data]

        ax.plot(x, y, "o-", label=class_name)
        ax.fill_between(x, ci_low, ci_high, alpha=0.2)

        ax.set_xticks(range(K))
        ax.set_xticklabels(roi_labels or [f"ROI {i}" for i in range(K)], rotation=45)
        ax.set_xlabel("ROI")
        ax.set_ylabel("Mean Predicted Concept")
        ax.set_title(class_name)
        ax.legend()
        ax.grid(True, alpha=0.3)

    _save_figure(output_path)