"""Class-conditional descriptive profiles."""

from __future__ import annotations

import numpy as np

from .schemas import (
    ClassConditionalProfile,
    FoldEnsembleRecord,
    SeedEnsembleRecord,
    ValueStatus,
)


def _validate_records(records: list[FoldEnsembleRecord | SeedEnsembleRecord]) -> int | None:
    """Validate subject-level profile inputs before class aggregation."""
    if not records:
        return None

    widths: set[int] = set()
    for record in records:
        if record.true_label not in {0, 1, 2}:
            raise ValueError("true_label must use the fixed class order indices 0, 1, and 2")
        vectors = (
            record.predicted_concepts,
            record.concept_targets,
            record.anatomical_targets,
        )
        lengths = {len(vector) for vector in vectors}
        if len(lengths) != 1:
            raise ValueError("profile vectors must have the same ROI width")
        widths.update(lengths)
        if any(not np.isfinite(np.asarray(vector, dtype=np.float64)).all() for vector in vectors):
            raise ValueError("class profile vectors must contain only finite values")

    if len(widths) != 1:
        raise ValueError("all records must have the same ROI width")
    return widths.pop()


def _bootstrap_mean_ci(
    values: np.ndarray,
    *,
    replicates: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap ROI means by resampling subjects with fixed PCG64 draws."""
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("bootstrap_replicates must be a positive integer")
    if values.ndim != 2 or values.shape[0] == 0 or not np.isfinite(values).all():
        raise ValueError("bootstrap values must be a non-empty finite matrix")
    rng = np.random.Generator(np.random.PCG64(seed))
    draws = np.empty((replicates, values.shape[1]), dtype=np.float64)
    for index in range(replicates):
        subject_indices = rng.integers(0, values.shape[0], size=values.shape[0])
        draws[index] = np.mean(values[subject_indices], axis=0)
    return (
        np.percentile(draws, 2.5, axis=0, method="linear"),
        np.percentile(draws, 97.5, axis=0, method="linear"),
    )


def compute_class_profiles(
    records: list[FoldEnsembleRecord | SeedEnsembleRecord],
    class_labels: list[str] | None = None,
    bootstrap_replicates: int = 10000,
    bootstrap_seed: int = 12345,
) -> list[ClassConditionalProfile]:
    """
    Generate class-conditional descriptive profiles.

    Args:
        records: Fold-ensemble or seed-ensemble records
        class_labels: Class names in order CN=0, MCI=1, AD=2
        bootstrap_replicates: Number of bootstrap replicates
        bootstrap_seed: Bootstrap seed

    Returns:
        List of ClassConditionalProfile for each class
    """
    _validate_records(records)
    if class_labels is None:
        class_labels = ["CN", "MCI", "AD"]
    if class_labels != ["CN", "MCI", "AD"]:
        raise ValueError("class_labels must preserve the fixed CN, MCI, AD order")

    profiles = []

    for c in range(3):
        class_records = [r for r in records if r.true_label == c]

        if not class_records:
            profiles.append(ClassConditionalProfile(
                class_label=class_labels[c],
                class_index=c,
                support=0,
                mean_predicted_concepts=(),
                mean_concept_targets=(),
                mean_anatomical_targets=(),
                bootstrap_ci_low=(),
                bootstrap_ci_high=(),
                status=ValueStatus.UNAVAILABLE,
                reason="zero_support",
            ))
            continue

        N = len(class_records)

        # Stack arrays
        pred_concepts = np.stack([np.array(r.predicted_concepts) for r in class_records])  # [N, K]
        c_targets = np.stack([np.array(r.concept_targets) for r in class_records])        # [N, K]
        g_bar = np.stack([np.array(r.anatomical_targets) for r in class_records])         # [N, K]

        # Mean per ROI
        mean_pred = np.mean(pred_concepts, axis=0)
        mean_c_target = np.mean(c_targets, axis=0)
        mean_g_bar = np.mean(g_bar, axis=0)

        # Bootstrap CIs for mean predicted concepts
        ci_low, ci_high = _bootstrap_mean_ci(
            pred_concepts,
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        )

        profile = ClassConditionalProfile(
            class_label=class_labels[c],
            class_index=c,
            support=N,
            mean_predicted_concepts=tuple(float(v) for v in mean_pred),
            mean_concept_targets=tuple(float(v) for v in mean_c_target),
            mean_anatomical_targets=tuple(float(v) for v in mean_g_bar),
            bootstrap_ci_low=tuple(float(v) for v in ci_low),
            bootstrap_ci_high=tuple(float(v) for v in ci_high),
            status=ValueStatus.AVAILABLE,
            reason=None,
        )
        profiles.append(profile)

    return profiles


def compute_global_class_support(records: list) -> dict[str, int]:
    """Compute global class support across all records."""
    from collections import Counter

    labels = [r.true_label for r in records]
    counts = Counter(labels)

    return {
        "CN": counts.get(0, 0),
        "MCI": counts.get(1, 0),
        "AD": counts.get(2, 0),
    }


def compute_per_roi_class_means(
    records: list,
    class_labels: list[str] | None = None,
) -> dict[str, np.ndarray]:
    """Compute per-ROI mean predicted concepts per class."""
    _validate_records(records)
    if class_labels is None:
        class_labels = ["CN", "MCI", "AD"]
    if class_labels != ["CN", "MCI", "AD"]:
        raise ValueError("class_labels must preserve the fixed CN, MCI, AD order")
    results = {}

    for c in range(3):
        class_records = [r for r in records if r.true_label == c]

        if not class_records:
            results[class_labels[c]] = np.array([])
            continue

        pred_concepts = np.stack([np.array(r.predicted_concepts) for r in class_records])
        results[class_labels[c]] = np.mean(pred_concepts, axis=0)

    return results