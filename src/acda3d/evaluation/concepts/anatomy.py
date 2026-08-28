"""Anatomical consistency metrics implementation."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from .schemas import (
    AnatomyConsistencyGlobal,
    AnatomyConsistencyPerROI,
    AnatomyConsistencyPerSubject,
    ValueStatus,
    WeightedAnatomyScore,
)

# ============================================================================
# Global metrics
# ============================================================================

def _validate_matrices(c_hat: np.ndarray, g_bar: np.ndarray) -> None:
    if c_hat.shape != g_bar.shape:
        raise ValueError(f"Shape mismatch: c_hat {c_hat.shape} vs g_bar {g_bar.shape}")
    if c_hat.ndim != 2:
        raise ValueError("Anatomy matrices must be two-dimensional [subjects, ROIs]")
    if c_hat.shape[0] == 0 or c_hat.shape[1] == 0:
        raise ValueError("Anatomy matrices require at least one subject and one ROI")
    if not np.isfinite(c_hat).all() or not np.isfinite(g_bar).all():
        raise ValueError("Anatomy matrices must contain only finite values")


def compute_global_anatomy(
    c_hat: np.ndarray,    # [N, K]
    g_bar: np.ndarray,    # [N, K]
) -> AnatomyConsistencyGlobal:
    """Compute global anatomical consistency metrics."""
    _validate_matrices(c_hat, g_bar)

    diff = c_hat - g_bar
    abs_diff = np.abs(diff)

    mae = float(np.mean(abs_diff))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    bias = float(np.mean(diff))

    return AnatomyConsistencyGlobal(
        mae=mae,
        rmse=rmse,
        bias=bias,
    )


def compute_per_subject_anatomy(
    c_hat: np.ndarray,
    g_bar: np.ndarray,
) -> list[AnatomyConsistencyPerSubject]:
    """Compute per-subject MAE and RMSE across ROIs."""
    _validate_matrices(c_hat, g_bar)

    N = c_hat.shape[0]
    results = []

    for i in range(N):
        diff = c_hat[i] - g_bar[i]
        abs_diff = np.abs(diff)
        mae = float(np.mean(abs_diff))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        results.append(AnatomyConsistencyPerSubject(
            subject_hash="",  # Filled by caller
            mae=mae,
            rmse=rmse,
        ))

    return results


def compute_per_roi_anatomy(
    c_hat: np.ndarray,
    g_bar: np.ndarray,
) -> list[AnatomyConsistencyPerROI]:
    """Compute per-ROI anatomical consistency metrics."""
    _validate_matrices(c_hat, g_bar)

    N, K = c_hat.shape
    results = []

    for k in range(K):
        x = c_hat[:, k]
        y = g_bar[:, k]

        diff = x - y
        abs_diff = np.abs(diff)

        mae = float(np.mean(abs_diff))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        bias = float(np.mean(diff))

        # Correlations with unavailable handling
        pearson, spearman, status, reason = _compute_correlations(x, y)

        results.append(AnatomyConsistencyPerROI(
            roi_index=k,
            mae=mae,
            rmse=rmse,
            bias=bias,
            pearson=pearson,
            spearman=spearman,
            status=status,
            reason=reason,
        ))

    return results


def _compute_correlations(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[float | None, float | None, ValueStatus, str | None]:
    """Compute Pearson and Spearman with unavailable handling."""
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        return None, None, ValueStatus.UNAVAILABLE, "numerical_error"

    if len(x) < 3:
        return None, None, ValueStatus.UNAVAILABLE, "insufficient_samples"

    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return None, None, ValueStatus.UNAVAILABLE, "constant_roi"

    try:
        pearson_r, _ = stats.pearsonr(x, y)
        spearman_r, _ = stats.spearmanr(x, y)

        if not np.isfinite(pearson_r) or not np.isfinite(spearman_r):
            return None, None, ValueStatus.UNAVAILABLE, "numerical_error"

        return float(pearson_r), float(spearman_r), ValueStatus.AVAILABLE, None

    except Exception:
        return None, None, ValueStatus.UNAVAILABLE, "numerical_error"


# ============================================================================
# Canonical weighted anatomy score
# ============================================================================

def compute_weighted_anatomy_score(
    c_hat: np.ndarray,
    g_bar: np.ndarray,
    roi_weights: np.ndarray | None,
) -> WeightedAnatomyScore:
    """
    Compute canonical weighted anatomy score.

    Args:
        c_hat: Predicted concepts [N, K]
        g_bar: Anatomical targets [N, K]
        roi_weights: Canonical ROI weights from anatomical loss [K]. Sums to 1.

    Returns:
        WeightedAnatomyScore with weighted MAE, RMSE, Bias
    """
    _validate_matrices(c_hat, g_bar)

    if roi_weights is None:
        return WeightedAnatomyScore(
            weighted_mae=None,
            weighted_rmse=None,
            weighted_bias=None,
            status=ValueStatus.UNAVAILABLE,
            reason="weights_unavailable",
        )

    weights = np.asarray(roi_weights, dtype=np.float64)
    if weights.shape != (c_hat.shape[1],):
        raise ValueError(f"ROI weights shape {weights.shape} != K={c_hat.shape[1]}")
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("ROI weights must be finite and non-negative")
    if not np.isclose(np.sum(weights), 1.0):
        raise ValueError(f"ROI weights must sum to 1, got {np.sum(weights)}")

    diff = c_hat - g_bar
    abs_diff = np.abs(diff)

    # Weighted global metrics
    weighted_mae = float(np.sum(weights * np.mean(abs_diff, axis=0)))
    weighted_rmse = float(np.sqrt(np.sum(weights * np.mean(diff ** 2, axis=0))))
    weighted_bias = float(np.sum(weights * np.mean(diff, axis=0)))

    return WeightedAnatomyScore(
        weighted_mae=weighted_mae,
        weighted_rmse=weighted_rmse,
        weighted_bias=weighted_bias,
        status=ValueStatus.AVAILABLE,
        reason=None,
    )


def compute_all_anatomy(
    c_hat: np.ndarray,
    g_bar: np.ndarray,
    roi_weights: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute all anatomical consistency metrics."""
    global_metrics = compute_global_anatomy(c_hat, g_bar)
    per_subject = compute_per_subject_anatomy(c_hat, g_bar)
    per_roi = compute_per_roi_anatomy(c_hat, g_bar)
    weighted = compute_weighted_anatomy_score(c_hat, g_bar, roi_weights)

    return {
        "global": global_metrics,
        "per_subject": per_subject,
        "per_roi": per_roi,
        "weighted": weighted,
    }