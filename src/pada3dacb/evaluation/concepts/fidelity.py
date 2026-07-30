"""Concept fidelity metrics implementation."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from .schemas import (
    ConceptFidelityGlobal,
    ConceptFidelityPerROI,
    ConceptFidelityPerSubject,
    ValueStatus,
)

# ============================================================================
# Global metrics
# ============================================================================

def _validate_matrices(c_hat: np.ndarray, c_target: np.ndarray) -> None:
    if c_hat.shape != c_target.shape:
        raise ValueError(f"Shape mismatch: c_hat {c_hat.shape} vs c_target {c_target.shape}")
    if c_hat.ndim != 2:
        raise ValueError("Concept matrices must be two-dimensional [subjects, ROIs]")
    if c_hat.shape[0] == 0 or c_hat.shape[1] == 0:
        raise ValueError("Concept matrices require at least one subject and one ROI")
    if not np.isfinite(c_hat).all() or not np.isfinite(c_target).all():
        raise ValueError("Concept matrices must contain only finite values")


def compute_global_fidelity(
    c_hat: np.ndarray,      # [N, K]
    c_target: np.ndarray,   # [N, K]
) -> ConceptFidelityGlobal:
    """
    Compute global concept fidelity metrics.

    Args:
        c_hat: Predicted concepts [N_subjects, K_ROIs]
        c_target: Concept targets [N_subjects, K_ROIs]

    Returns:
        ConceptFidelityGlobal with MAE, RMSE, and mean signed bias
    """
    _validate_matrices(c_hat, c_target)

    diff = c_hat - c_target
    abs_diff = np.abs(diff)

    mae = float(np.mean(abs_diff))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    bias = float(np.mean(diff))

    return ConceptFidelityGlobal(
        mae=mae,
        rmse=rmse,
        bias=bias,
    )


def compute_per_subject_fidelity(
    c_hat: np.ndarray,      # [N, K]
    c_target: np.ndarray,   # [N, K]
) -> list[ConceptFidelityPerSubject]:
    """Compute per-subject MAE and RMSE across ROIs."""
    _validate_matrices(c_hat, c_target)

    N = c_hat.shape[0]
    results = []

    for i in range(N):
        diff = c_hat[i] - c_target[i]
        abs_diff = np.abs(diff)
        mae = float(np.mean(abs_diff))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        results.append(ConceptFidelityPerSubject(
            subject_hash="",  # Filled by caller
            mae=mae,
            rmse=rmse,
        ))

    return results


def compute_per_roi_fidelity(
    c_hat: np.ndarray,      # [N, K]
    c_target: np.ndarray,   # [N, K]
) -> list[ConceptFidelityPerROI]:
    """
    Compute per-ROI concept fidelity metrics.

    Args:
        c_hat: Predicted concepts [N_subjects, K_ROIs]
        c_target: Concept targets [N_subjects, K_ROIs]

    Returns:
        List of ConceptFidelityPerROI for each ROI
    """
    _validate_matrices(c_hat, c_target)

    N, K = c_hat.shape
    results = []

    for k in range(K):
        x = c_hat[:, k]
        y = c_target[:, k]

        diff = x - y
        abs_diff = np.abs(diff)

        mae = float(np.mean(abs_diff))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        bias = float(np.mean(diff))

        # Correlations with unavailable handling
        pearson, spearman, status, reason = _compute_correlations(x, y)

        results.append(ConceptFidelityPerROI(
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
    """
    Compute Pearson and Spearman correlations with unavailable handling.

    Returns:
        (pearson, spearman, status, reason)
    """
    # Check for constant arrays
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return None, None, ValueStatus.UNAVAILABLE, "constant_roi"

    # Check sample count
    if len(x) < 3:
        return None, None, ValueStatus.UNAVAILABLE, "insufficient_samples"

    # Check for NaN/inf
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        return None, None, ValueStatus.UNAVAILABLE, "numerical_error"

    try:
        pearson_r, _ = stats.pearsonr(x, y)
        spearman_r, _ = stats.spearmanr(x, y)

        if not np.isfinite(pearson_r) or not np.isfinite(spearman_r):
            return None, None, ValueStatus.UNAVAILABLE, "numerical_error"

        return float(pearson_r), float(spearman_r), ValueStatus.AVAILABLE, None

    except Exception:
        return None, None, ValueStatus.UNAVAILABLE, "numerical_error"


def compute_all_fidelity(
    c_hat: np.ndarray,
    c_target: np.ndarray,
) -> dict[str, Any]:
    """
    Compute all concept fidelity metrics in one call.

    Returns:
        Dict with keys: global, per_subject, per_roi
    """
    global_metrics = compute_global_fidelity(c_hat, c_target)
    per_subject = compute_per_subject_fidelity(c_hat, c_target)
    per_roi = compute_per_roi_fidelity(c_hat, c_target)

    return {
        "global": global_metrics,
        "per_subject": per_subject,
        "per_roi": per_roi,
    }