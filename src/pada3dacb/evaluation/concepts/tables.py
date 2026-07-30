"""Table generation for concept evaluation."""

from __future__ import annotations

import csv
from pathlib import Path

from .schemas import (
    ConceptFidelityGlobal,
)


def write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    """Write list of dicts to CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ============================================================================
# Concept Fidelity Tables
# ============================================================================

def concept_fidelity_global_rows(
    metrics: ConceptFidelityGlobal,
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    """Generate rows for concept_fidelity_global.csv."""
    return [
        {
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "metric": "MAE_global",
            "value": metrics.mae,
        },
        {
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "metric": "RMSE_global",
            "value": metrics.rmse,
        },
        {
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "metric": "Bias_global",
            "value": metrics.bias,
        },
    ]


def concept_fidelity_per_subject_rows(
    per_subject: list[dict],  # List of {subject_hash, mae, rmse}
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    """Generate rows for concept_fidelity_per_subject.csv."""
    rows = []
    for p in per_subject:
        rows.append({
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "subject_hash": p["subject_hash"],
            "MAE": p["mae"],
            "RMSE": p["rmse"],
        })
    return rows


def concept_fidelity_per_roi_rows(
    per_roi: list[dict],  # List of {roi_index, mae, rmse, bias, pearson, spearman, status, reason}
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    """Generate rows for concept_fidelity_per_roi.csv."""
    rows = []
    for p in per_roi:
        rows.append({
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "roi_index": p["roi_index"],
            "MAE": p["mae"],
            "RMSE": p["rmse"],
            "Bias": p["bias"],
            "Pearson": p["pearson"] if p["pearson"] is not None else "",
            "Pearson_status": p["status"],
            "Pearson_reason": p["reason"] if p["reason"] else "",
            "Spearman": p["spearman"] if p["spearman"] is not None else "",
            "Spearman_status": p["status"],
            "Spearman_reason": p["reason"] if p["reason"] else "",
        })
    return rows


# ============================================================================
# Anatomy Consistency Tables
# ============================================================================

def anatomy_consistency_global_rows(
    metrics: dict,  # {mae, rmse, bias}
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    return [
        {"method": method, "direction": direction, "checkpoint_policy": checkpoint_policy,
         "metric": "MAE_global", "value": metrics["mae"]},
        {"method": method, "direction": direction, "checkpoint_policy": checkpoint_policy,
         "metric": "RMSE_global", "value": metrics["rmse"]},
        {"method": method, "direction": direction, "checkpoint_policy": checkpoint_policy,
         "metric": "Bias_global", "value": metrics["bias"]},
    ]


def anatomy_consistency_per_roi_rows(
    per_roi: list[dict],
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    rows = []
    for p in per_roi:
        rows.append({
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "roi_index": p["roi_index"],
            "MAE": p["mae"],
            "RMSE": p["rmse"],
            "Bias": p["bias"],
            "Pearson": p["pearson"] if p["pearson"] is not None else "",
            "Pearson_status": p["status"],
            "Pearson_reason": p["reason"] if p["reason"] else "",
            "Spearman": p["spearman"] if p["spearman"] is not None else "",
            "Spearman_status": p["status"],
            "Spearman_reason": p["reason"] if p["reason"] else "",
        })
    return rows


def weighted_anatomy_score_rows(
    weighted: dict,  # {weighted_mae, weighted_rmse, weighted_bias, status, reason}
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    return [
        {"method": method, "direction": direction, "checkpoint_policy": checkpoint_policy,
         "metric": "weighted_MAE", "value": weighted["weighted_mae"] if weighted["weighted_mae"] is not None else "",
         "status": weighted["status"], "reason": weighted["reason"]},
        {"method": method, "direction": direction, "checkpoint_policy": checkpoint_policy,
         "metric": "weighted_RMSE", "value": weighted["weighted_rmse"] if weighted["weighted_rmse"] is not None else "",
         "status": weighted["status"], "reason": weighted["reason"]},
        {"method": method, "direction": direction, "checkpoint_policy": checkpoint_policy,
         "metric": "weighted_Bias", "value": weighted["weighted_bias"] if weighted["weighted_bias"] is not None else "",
         "status": weighted["status"], "reason": weighted["reason"]},
    ]


# ============================================================================
# Head Agreement Tables
# ============================================================================

def head_agreement_rows(
    metrics: dict,  # All agreement metrics
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    rows = []
    for metric_name, value in metrics.items():
        if isinstance(value, (int, float)):
            rows.append({
                "method": method,
                "direction": direction,
                "checkpoint_policy": checkpoint_policy,
                "metric": metric_name,
                "value": value,
            })
    return rows


def per_class_disagreement_rows(
    per_class: list[dict],  # List of {class_label, class_index, disagree_count, total_count, disagree_rate}
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    rows = []
    for p in per_class:
        rows.append({
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "class_label": p["class_label"],
            "class_index": p["class_index"],
            "disagree_count": p["disagree_count"],
            "total_count": p["total_count"],
            "disagree_rate": p["disagree_rate"] if p["disagree_rate"] is not None else "",
        })
    return rows


# ============================================================================
# ROI Stability Tables
# ============================================================================

def roi_stability_rows(
    stability: dict,  # ROIStabilityMetrics
    method: str,
    direction: str,
    checkpoint_policy: str,
) -> list[dict]:
    rows = []

    # Pairwise rho
    rows.append({
        "method": method,
        "direction": direction,
        "checkpoint_policy": checkpoint_policy,
        "metric": "mean_pairwise_rho_fidelity",
        "value": stability["mean_pairwise_rho_fidelity"],
    })
    rows.append({
        "method": method,
        "direction": direction,
        "checkpoint_policy": checkpoint_policy,
        "metric": "mean_pairwise_rho_anatomy",
        "value": stability["mean_pairwise_rho_anatomy"],
    })
    rows.append({
        "method": method,
        "direction": direction,
        "checkpoint_policy": checkpoint_policy,
        "metric": "mean_pairwise_rho_concept",
        "value": stability["mean_pairwise_rho_concept"],
    })
    rows.append({
        "method": method,
        "direction": direction,
        "checkpoint_policy": checkpoint_policy,
        "metric": "mean_pairwise_rho_alpha",
        "value": stability["mean_pairwise_rho_alpha"],
    })

    # Instance std (per ROI)
    for k, std in enumerate(stability["instance_std_fidelity"]):
        rows.append({
            "method": method,
            "direction": direction,
            "checkpoint_policy": checkpoint_policy,
            "metric": "instance_std_fidelity",
            "roi_index": k,
            "value": std,
        })

    # Jaccard remains profile-specific; averaging unlike profiles is prohibited.
    for profile in ("fidelity", "anatomy", "concept", "alpha"):
        for k, jaccard in stability[f"jaccard_{profile}"].items():
            rows.append({
                "method": method,
                "direction": direction,
                "checkpoint_policy": checkpoint_policy,
                "metric": f"jaccard_{profile}",
                "k": k,
                "value": jaccard,
            })

    for statistic in ("std", "range"):
        for roi_index, dispersion in enumerate(stability[f"rank_dispersion_{statistic}"]):
            rows.append({
                "method": method,
                "direction": direction,
                "checkpoint_policy": checkpoint_policy,
                "metric": f"rank_dispersion_{statistic}",
                "roi_index": roi_index,
                "value": dispersion,
            })

    return rows


# ============================================================================
# Class Conditional Profiles
# ============================================================================

def class_conditional_rows(
    profiles: dict,  # {class_label: {mean_concepts, mean_c_targets, mean_g_bar, ci_low, ci_high, support}}
) -> list[dict]:
    rows = []
    for class_label, data in profiles.items():
        for k in range(len(data["mean_concepts"])):
            rows.append({
                "class_label": class_label,
                "roi_index": k,
                "mean_predicted_concept": data["mean_concepts"][k],
                "ci_low": data["ci_low"][k],
                "ci_high": data["ci_high"][k],
                "mean_c_target": data["mean_c_targets"][k],
                "mean_g_bar": data["mean_g_bar"][k],
                "support": data["support"],
            })
    return rows


# ============================================================================
# Paired Method Comparisons
# ============================================================================

def paired_comparison_rows(
    comparisons: list[dict],  # List of {comparator_method, direction, checkpoint_policy, metric_family, mean_diff, ci_low, ci_high, p_value, adj_p_value, holm_rank, status, reason}
) -> list[dict]:
    rows = []
    for c in comparisons:
        rows.append({
            "comparator_method": c["comparator_method"],
            "direction": c["direction"],
            "checkpoint_policy": c["checkpoint_policy"],
            "metric_family": c["metric_family"],
            "mean_difference": c["mean_difference"],
            "ci_low": c["ci_low"] if c["ci_low"] is not None else "",
            "ci_high": c["ci_high"] if c["ci_high"] is not None else "",
            "raw_p_value": c["p_value"] if c["p_value"] is not None else "",
            "adjusted_p_value": c["adj_p_value"] if c["adj_p_value"] is not None else "",
            "holm_rank": c["holm_rank"] if c["holm_rank"] is not None else "",
            "significant": c["adj_p_value"] <= 0.05 if c["adj_p_value"] is not None else False,
            "status": c["status"],
            "reason": c["reason"] if c["reason"] else "",
        })
    return rows


def holm_adjusted_rows(
    holm_results: dict,  # {family_name: list of HolmRow}
) -> list[dict]:
    output_rows = []
    for family, family_rows in holm_results.items():
        for r in family_rows:
            output_rows.append({
                "family": family,
                "metric": r.metric,
                "comparator_method": r.comparator_method,
                "family_size": r.family_size,
                "available_count": r.available_count,
                "raw_p_value": r.raw_p_value,
                "adjusted_p_value": r.adjusted_p_value,
                "holm_rank": r.holm_rank,
                "significant": (
                    r.adjusted_p_value is not None and r.adjusted_p_value <= 0.05
                ),
                "status": r.status,
                "reason": r.reason if r.reason else "",
            })
    return output_rows


# ============================================================================
# Method Status
# ============================================================================

def method_status_rows(
    methods: list[dict],  # List of {method, direction, checkpoint_policy, status, reason}
) -> list[dict]:
    rows = []
    for m in methods:
        rows.append({
            "method": m["method"],
            "direction": m["direction"],
            "checkpoint_policy": m["checkpoint_policy"],
            "status": m["status"],
            "reason_code": m.get("reason", ""),
        })
    return rows


# ============================================================================
# Main table writer
# ============================================================================

def write_all_tables(
    output_root: str,
    tables: dict[str, list[dict]],
) -> None:
    """
    Write all tables to output directory.

    Args:
        output_root: Root directory for concept evaluation output
        tables: Dict of table_name -> list of row dicts
    """
    for name, rows in tables.items():
        if not rows:
            continue
        # Get fieldnames from first row
        fieldnames = list(rows[0].keys())
        path = Path(output_root) / "tables" / f"{name}.csv"
        write_csv(path, rows, fieldnames)