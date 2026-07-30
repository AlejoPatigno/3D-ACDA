"""ROI-level stability metrics implementation."""

from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

from .schemas import ROIStabilityMetrics

# ============================================================================
# Rank correlation stability
# ============================================================================

def _validate_profiles(profiles: np.ndarray) -> None:
    if profiles.ndim != 2:
        raise ValueError("ROI profiles must be two-dimensional [instances, ROIs]")
    if profiles.shape[0] == 0 or profiles.shape[1] == 0:
        raise ValueError("ROI profiles require at least one instance and one ROI")
    if not np.isfinite(profiles).all():
        raise ValueError("ROI profiles must contain only finite values")


def _serializable_matrix(matrix: np.ndarray) -> tuple[tuple[float | None, ...], ...]:
    return tuple(
        tuple(None if not np.isfinite(value) else float(value) for value in row)
        for row in matrix
    )


def compute_pairwise_spearman(
    profiles: np.ndarray,     # [M, K] M instances, K ROIs
) -> np.ndarray:
    """
    Compute pairwise Spearman rank correlation between all instance profiles.

    Args:
        profiles: [M, K] where M is number of model instances (folds/seeds), K is ROIs

    Returns:
        [M, M] matrix of Spearman rho values (diagonal = 1.0)
    """
    _validate_profiles(profiles)
    M, K = profiles.shape
    if M < 2:
        return np.eye(M)

    rho_matrix = np.eye(M, dtype=np.float32)

    for i in range(M):
        for j in range(i + 1, M):
            if np.allclose(profiles[i], profiles[i, 0]) or np.allclose(
                profiles[j], profiles[j, 0]
            ):
                rho = np.nan
            else:
                rho, _ = spearmanr(profiles[i], profiles[j])
            rho_matrix[i, j] = rho
            rho_matrix[j, i] = rho

    return rho_matrix


def compute_mean_pairwise_rho(rho_matrix: np.ndarray) -> float | None:
    """Compute the mean finite upper-triangular Spearman correlation."""
    if rho_matrix.ndim != 2 or rho_matrix.shape[0] != rho_matrix.shape[1]:
        raise ValueError("rho_matrix must be square")
    if rho_matrix.shape[0] < 2:
        return 1.0

    upper_tri = rho_matrix[np.triu_indices_from(rho_matrix, k=1)]
    finite = upper_tri[np.isfinite(upper_tri)]
    return None if finite.size == 0 else float(np.mean(finite))


def compute_instance_std(profiles: np.ndarray) -> np.ndarray:
    """
    Compute standard deviation across model instances for each ROI.

    Args:
        profiles: [M, K]

    Returns:
        [K] array of standard deviations per ROI
    """
    _validate_profiles(profiles)
    if profiles.shape[0] < 2:
        return np.zeros(profiles.shape[1], dtype=np.float64)
    return np.std(profiles, axis=0, ddof=1)  # Sample std


# ============================================================================
# Top-k Jaccard overlap
# ============================================================================

def compute_top_k_indices(
    profiles: np.ndarray,     # [M, K]
    k: int,
    ascending: bool = False,
) -> list[np.ndarray]:
    """
    Get top-k ROI indices for each model instance.

    Args:
        profiles: [M, K] profiles (e.g., concept fidelity MAE per ROI)
        k: Number of top ROIs to select
        ascending: If True, select smallest values (e.g., for MAE). If False, largest.

    Returns:
        List of M arrays, each containing k ROI indices
    """
    _validate_profiles(profiles)
    M, K = profiles.shape
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("top-k values must be positive integers")
    if k > K:
        raise ValueError(f"top-k value {k} exceeds ROI count {K}")

    if ascending:
        # For MAE/fidelity: smaller is better -> top-k = smallest values
        top_indices = np.argsort(profiles, axis=1)[:, :k]
    else:
        # For stability/agreement: larger is better -> top-k = largest values
        top_indices = np.argsort(profiles, axis=1)[:, -k:]

    return [top_indices[i] for i in range(profiles.shape[0])]


def compute_jaccard_overlap(
    top_k_indices_a: np.ndarray,
    top_k_indices_b: np.ndarray,
) -> float:
    """Compute Jaccard overlap between two top-k index sets."""
    set_a = set(top_k_indices_a)
    set_b = set(top_k_indices_b)

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    if union == 0:
        return 0.0

    return float(intersection / union)


def compute_mean_jaccard(
    profiles: np.ndarray,     # [M, K]
    k_values: list[int],
    ascending: bool = False,
) -> dict[int, float]:
    """
    Compute mean pairwise Jaccard overlap for multiple k values.

    Args:
        profiles: [M, K]
        k_values: List of k values to compute
        ascending: Whether to select smallest (True) or largest (False) values

    Returns:
        Dict mapping k -> mean Jaccard overlap
    """
    results = {}

    for k in k_values:
        top_indices = compute_top_k_indices(profiles, k, ascending)

        M = profiles.shape[0]
        if M < 2:
            results[k] = 1.0
            continue

        jaccards = []
        for i in range(M):
            for j in range(i + 1, M):
                jacc = compute_jaccard_overlap(top_indices[i], top_indices[j])
                jaccards.append(jacc)

        results[k] = float(np.mean(jaccards))

    return results


# ============================================================================
# ROI rank dispersion
# ============================================================================

def compute_roi_rank_dispersion(profiles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute rank dispersion across model instances for each ROI.

    Args:
        profiles: [M, K] - higher values = higher rank (or use ascending=True for lower=better)

    Returns:
        (rank_std, rank_range) both [K]
        - rank_std: standard deviation of ranks across instances
        - rank_range: max rank - min rank for each ROI
    """
    M, K = profiles.shape
    if M < 2:
        return np.zeros(K), np.zeros(K)

    # Rank each instance's profile (1 = highest value)
    ranks = np.argsort(np.argsort(-profiles, axis=1), axis=1) + 1  # 1-indexed ranks

    rank_std = np.std(ranks, axis=0, ddof=1)
    rank_range = np.max(ranks, axis=0) - np.min(ranks, axis=0)

    return rank_std, rank_range


# ============================================================================
# Complete stability computation
# ============================================================================

def compute_all_stability(
    fidelity_profiles: np.ndarray,      # [M, K] per-ROI concept fidelity (e.g., MAE)
    anatomy_profiles: np.ndarray,       # [M, K] per-ROI anatomy consistency (e.g., MAE)
    concept_profiles: np.ndarray,       # [M, K] mean predicted concepts per ROI
    alpha_profiles: np.ndarray,         # [M, K] mean attention alpha per ROI
    k_values: list[int],
) -> ROIStabilityMetrics:
    """
    Compute all ROI stability metrics.

    Args:
        fidelity_profiles: Per-instance per-ROI concept fidelity (lower=better)
        anatomy_profiles: Per-instance per-ROI anatomy consistency (lower=better)
        concept_profiles: Per-instance mean predicted concepts per ROI
        alpha_profiles: Per-instance mean attention alpha per ROI
        k_values: List of k values for top-k Jaccard (default: [5, 10, 20])

    Returns:
        ROIStabilityMetrics with all stability measures
    """
    profile_shapes = {
        fidelity_profiles.shape,
        anatomy_profiles.shape,
        concept_profiles.shape,
        alpha_profiles.shape,
    }
    if len(profile_shapes) != 1:
        raise ValueError("All ROI profile matrices must have the same shape")
    for profiles in (
        fidelity_profiles, anatomy_profiles, concept_profiles, alpha_profiles,
    ):
        _validate_profiles(profiles)
    # Pairwise Spearman
    rho_fidelity = compute_pairwise_spearman(fidelity_profiles)
    rho_anatomy = compute_pairwise_spearman(anatomy_profiles)
    rho_concept = compute_pairwise_spearman(concept_profiles)
    rho_alpha = compute_pairwise_spearman(alpha_profiles)

    mean_rho_fidelity = compute_mean_pairwise_rho(rho_fidelity)
    mean_rho_anatomy = compute_mean_pairwise_rho(rho_anatomy)
    mean_rho_concept = compute_mean_pairwise_rho(rho_concept)
    mean_rho_alpha = compute_mean_pairwise_rho(rho_alpha)

    # Instance std
    std_fidelity = compute_instance_std(fidelity_profiles)
    std_anatomy = compute_instance_std(anatomy_profiles)
    std_concept = compute_instance_std(concept_profiles)
    std_alpha = compute_instance_std(alpha_profiles)

    # Jaccard (for fidelity/anatomy: ascending=True since lower is better)
    jaccard_fidelity = compute_mean_jaccard(fidelity_profiles, k_values, ascending=True)
    jaccard_anatomy = compute_mean_jaccard(anatomy_profiles, k_values, ascending=True)
    jaccard_concept = compute_mean_jaccard(concept_profiles, k_values, ascending=False)
    jaccard_alpha = compute_mean_jaccard(alpha_profiles, k_values, ascending=False)

    # Rank dispersion (using concept profiles)
    rank_std, rank_range = compute_roi_rank_dispersion(concept_profiles)

    return ROIStabilityMetrics(
        pairwise_rho_fidelity=_serializable_matrix(rho_fidelity),
        pairwise_rho_anatomy=_serializable_matrix(rho_anatomy),
        pairwise_rho_concept=_serializable_matrix(rho_concept),
        pairwise_rho_alpha=_serializable_matrix(rho_alpha),
        mean_pairwise_rho_fidelity=mean_rho_fidelity,
        mean_pairwise_rho_anatomy=mean_rho_anatomy,
        mean_pairwise_rho_concept=mean_rho_concept,
        mean_pairwise_rho_alpha=mean_rho_alpha,
        instance_std_fidelity=tuple(float(value) for value in std_fidelity),
        instance_std_anatomy=tuple(float(value) for value in std_anatomy),
        instance_std_concept=tuple(float(value) for value in std_concept),
        instance_std_alpha=tuple(float(value) for value in std_alpha),
        jaccard_fidelity=jaccard_fidelity,
        jaccard_anatomy=jaccard_anatomy,
        jaccard_concept=jaccard_concept,
        jaccard_alpha=jaccard_alpha,
        rank_dispersion_std=tuple(float(value) for value in rank_std),
        rank_dispersion_range=tuple(float(value) for value in rank_range),
    )