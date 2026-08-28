"""Engineering fold summaries without publication-level inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from acda3d.experiments.run_manifest import atomic_json


def write_ablation_fold_summary(
    rows: list[dict[str, Any]],
    direction_dir: str | Path,
) -> pd.DataFrame:
    """Write engineering-only ablation rows without publication metrics or inference."""
    root = Path(direction_dir)
    root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty and "method" in frame and set(frame["method"]) != {"ablation"}:
        raise ValueError("ablation summaries may contain only method='ablation' rows")
    frame.to_csv(root / "fold_summary.csv", index=False)
    aggregate: dict[str, dict[str, float]] = {}
    completed = frame[frame["status"] == "COMPLETED"] if "status" in frame else frame.iloc[0:0]
    for column in ("resolved_objective", "source_validation_macro_f1"):
        if column in completed:
            aggregate[column] = {
                "mean": float(completed[column].mean()),
                "std": float(completed[column].std(ddof=0)),
            }
    atomic_json(
        root / "fold_summary.json",
        {
            "schema_version": "phase17.fold-summary.v1",
            "phase": 17,
            "method": "ablation",
            "real_data_run": False,
            "publication_metrics_present": False,
            "folds": json.loads(frame.to_json(orient="records")),
            "completed_aggregate": aggregate,
        },
    )
    return frame


def write_fold_summary(rows: list[dict[str, Any]], direction_dir: str | Path) -> pd.DataFrame:
    root = Path(direction_dir)
    root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "fold_summary.csv", index=False)
    completed = frame[frame["status"] == "COMPLETED"] if not frame.empty else frame
    numeric = [
        column for column in (
            "best_source_macro_f1", "best_source_validation_accuracy",
            "last_source_macro_f1", "last_source_validation_accuracy",
            "best_target_monitoring_macro_f1", "last_target_monitoring_macro_f1",
            "final_train_coral_loss", "final_weighted_coral_loss",
            "mean_train_coral_loss_full_stage", "target_batch_cycles",
            "best_source_target_monitoring_macro_f1",
            "final_train_mmd_loss", "final_weighted_mmd_loss",
            "mean_train_mmd_loss_full_stage", "final_source_kernel_mean",
            "final_target_kernel_mean", "final_cross_kernel_mean",
                "final_train_prototype_pseudo_loss", "final_weighted_prototype_pseudo_loss",
                "final_train_prototype_raw", "final_train_pseudo_label_raw",
                "mean_train_prototype_pseudo_loss_full_stage",
        ) if column in completed
    ]
    aggregate = {
        column: {
            "mean": float(completed[column].mean()),
            "std": float(completed[column].std(ddof=0)),
        }
        for column in numeric
    }
    atomic_json(
        root / "fold_summary.json",
        {"folds": json.loads(frame.to_json(orient="records")), "completed_aggregate": aggregate},
    )
    return frame
