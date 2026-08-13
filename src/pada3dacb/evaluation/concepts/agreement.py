"""Head agreement metrics implementation."""

from __future__ import annotations

import numpy as np

from pada3dacb.evaluation.metrics import compute_metrics
from pada3dacb.evaluation.schemas import (
    CheckpointPolicy,
    Direction,
    MethodId,
    SubjectPrediction,
)

from .schemas import (
    HeadAgreementMetrics,
    PerClassDisagreement,
    ValueStatus,
)


def _validate_probabilities(latent_probs: np.ndarray, concept_probs: np.ndarray) -> None:
    if latent_probs.shape != concept_probs.shape:
        raise ValueError("Head probability matrices must have the same shape")
    if latent_probs.ndim != 2 or latent_probs.shape[1] != 3:
        raise ValueError("Head probabilities must have shape [subjects, 3]")
    if latent_probs.shape[0] == 0:
        raise ValueError("Head probabilities require at least one subject")
    if not np.isfinite(latent_probs).all() or not np.isfinite(concept_probs).all():
        raise ValueError("Head probabilities must contain only finite values")
    for name, probabilities in (("latent", latent_probs), ("concept", concept_probs)):
        if np.any(probabilities < 0) or np.any(probabilities > 1):
            raise ValueError(f"{name} probabilities must be in [0, 1]")
        if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6):
            raise ValueError(f"{name} probabilities must sum to one")


def _probs_to_predictions(probs: np.ndarray, true_labels: np.ndarray) -> list[SubjectPrediction]:
    """Convert probability arrays to SubjectPrediction list for metrics computation."""
    return [
        SubjectPrediction(
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            subject_hash=f"subject_{i}",
            true_label=int(true_labels[i]),
            probabilities=tuple(probs[i]),
            fold_count=1,
            seed_count=1,
            source_file_sha256s=(f"{i:064x}",),
        )
        for i in range(len(true_labels))
    ]


def compute_head_predictive_metrics(
    latent_probs: np.ndarray,     # [N, 3]
    concept_probs: np.ndarray,    # [N, 3]
    true_labels: np.ndarray,      # [N]
) -> dict[str, float]:
    """
    Compute predictive metrics for latent and concept heads.

    Args:
        latent_probs: Latent head probabilities [N, 3]
        concept_probs: Concept head probabilities [N, 3]
        true_labels: True labels [N] (0=CN, 1=MCI, 2=AD)

    Returns:
        Dictionary with predictive metrics for both heads
    """
    _validate_probabilities(latent_probs, concept_probs)
    if true_labels.shape != (latent_probs.shape[0],):
        raise ValueError("true_labels must have one entry per subject")
    if not np.issubdtype(true_labels.dtype, np.integer) or np.any(
        ~np.isin(true_labels, np.array([0, 1, 2]))
    ):
        raise ValueError("true_labels must use the fixed class order indices 0, 1, and 2")
    latent_predictions = _probs_to_predictions(latent_probs, true_labels)
    concept_predictions = _probs_to_predictions(concept_probs, true_labels)

    # Use existing metrics infrastructure
    latent_metrics = compute_metrics(latent_predictions)
    concept_metrics = compute_metrics(concept_predictions)

    return {
        "latent_accuracy": latent_metrics.aggregate_metrics["accuracy"].value,
        "latent_balanced_accuracy": latent_metrics.aggregate_metrics["balanced_accuracy"].value,
        "latent_macro_f1": latent_metrics.aggregate_metrics["macro_f1"].value,
        "latent_macro_precision": latent_metrics.aggregate_metrics["macro_precision"].value,
        "latent_macro_recall": latent_metrics.aggregate_metrics["macro_recall"].value,
        "latent_mcc": latent_metrics.aggregate_metrics["multiclass_mcc"].value,
        "latent_kappa": latent_metrics.aggregate_metrics["cohen_kappa"].value,
        "concept_accuracy": concept_metrics.aggregate_metrics["accuracy"].value,
        "concept_balanced_accuracy": concept_metrics.aggregate_metrics["balanced_accuracy"].value,
        "concept_macro_f1": concept_metrics.aggregate_metrics["macro_f1"].value,
        "concept_macro_precision": concept_metrics.aggregate_metrics["macro_precision"].value,
        "concept_macro_recall": concept_metrics.aggregate_metrics["macro_recall"].value,
        "concept_mcc": concept_metrics.aggregate_metrics["multiclass_mcc"].value,
        "concept_kappa": concept_metrics.aggregate_metrics["cohen_kappa"].value,
    }


def compute_top1_agreement(
    latent_probs: np.ndarray,
    concept_probs: np.ndarray,
) -> tuple[float, float]:
    """
    Compute top-1 agreement and disagreement rates.

    Returns:
        (agreement_rate, disagreement_rate)
    """
    _validate_probabilities(latent_probs, concept_probs)
    latent_pred = np.argmax(latent_probs, axis=1)
    concept_pred = np.argmax(concept_probs, axis=1)

    agreement = float(np.mean(latent_pred == concept_pred))
    disagreement = 1.0 - agreement

    return agreement, disagreement


def compute_js_divergence(
    latent_probs: np.ndarray,
    concept_probs: np.ndarray,
) -> float:
    """
    Compute mean Jensen-Shannon divergence between head probability distributions.

    JS(P, Q) = 0.5 * KL(P || M) + 0.5 * KL(Q || M)
    where M = 0.5 * (P + Q)
    """
    _validate_probabilities(latent_probs, concept_probs)
    N = latent_probs.shape[0]
    js_values = np.zeros(N)

    for i in range(N):
        p = latent_probs[i]
        q = concept_probs[i]

        # Ensure valid probabilities
        p = np.clip(p, 1e-12, 1.0)
        q = np.clip(q, 1e-12, 1.0)
        p = p / np.sum(p)
        q = q / np.sum(q)

        m = 0.5 * (p + q)

        kl_pm = np.sum(p * np.log(p / m))
        kl_qm = np.sum(q * np.log(q / m))

        js_values[i] = 0.5 * (kl_pm + kl_qm)

    return float(np.mean(js_values))


def compute_consistency_direction(
    latent_probs: np.ndarray,
    concept_probs: np.ndarray,
    consistency_loss_type: str = "kl",
) -> str:
    """
    Determine canonical consistency direction from L_cons definition.

    Args:
        latent_probs: [N, 3]
        concept_probs: [N, 3]
        consistency_loss_type: "kl" or "js"

    Returns:
        "latent_supervises_concept" or "symmetric"
    """
    if consistency_loss_type == "kl":
        # L_cons = KL(latent || concept) -> latent supervises concept
        return "latent_supervises_concept"
    elif consistency_loss_type == "js":
        return "symmetric"
    else:
        raise ValueError(f"Unsupported consistency loss: {consistency_loss_type}")


def compute_per_class_disagreement(
    latent_pred: np.ndarray,
    concept_pred: np.ndarray,
    true_labels: np.ndarray,
) -> list[PerClassDisagreement]:
    """
    Compute per-class disagreement between heads.

    Args:
        latent_pred: Latent head predictions [N] (already argmax'd)
        concept_pred: Concept head predictions [N] (already argmax'd)
        true_labels: True labels [N] (0=CN, 1=MCI, 2=AD)

    Returns:
        List of PerClassDisagreement for classes CN, MCI, AD
    """
    if any(
        vector.ndim != 1
        for vector in (latent_pred, concept_pred, true_labels)
    ) or not (latent_pred.shape == concept_pred.shape == true_labels.shape):
        raise ValueError("prediction and label vectors must have the same length")
    if not np.issubdtype(true_labels.dtype, np.integer) or np.any(
        ~np.isin(true_labels, np.array([0, 1, 2]))
    ):
        raise ValueError("true_labels must use the fixed class order indices 0, 1, and 2")

    class_names = ["CN", "MCI", "AD"]
    results = []

    for c in range(3):
        mask = (true_labels == c)
        if not np.any(mask):
            results.append(PerClassDisagreement(
                class_label=class_names[c],
                class_index=c,
                disagree_count=0,
                total_count=0,
                disagree_rate=None,
                status=ValueStatus.UNAVAILABLE,
                reason="zero_support",
            ))
            continue

        latent_c = latent_pred[mask]
        concept_c = concept_pred[mask]
        disagree = np.sum(latent_c != concept_c)
        total = len(latent_c)
        rate = float(disagree / total)

        results.append(PerClassDisagreement(
            class_label=class_names[c],
            class_index=c,
            disagree_count=int(disagree),
            total_count=int(total),
            disagree_rate=rate,
            status=ValueStatus.AVAILABLE,
            reason=None,
        ))

    return results


def compute_all_agreement(
    latent_probs: np.ndarray,
    concept_probs: np.ndarray,
    true_labels: np.ndarray,
    *,
    consistency_loss_type: str,
) -> HeadAgreementMetrics:
    """Compute all head agreement metrics in one call."""
    predictive = compute_head_predictive_metrics(latent_probs, concept_probs, true_labels)
    agreement, disagreement = compute_top1_agreement(latent_probs, concept_probs)
    mean_js = compute_js_divergence(latent_probs, concept_probs)
    consistency_dir = compute_consistency_direction(latent_probs, concept_probs, consistency_loss_type)

    return HeadAgreementMetrics(
        latent_accuracy=predictive["latent_accuracy"],
        latent_balanced_accuracy=predictive["latent_balanced_accuracy"],
        latent_macro_f1=predictive["latent_macro_f1"],
        concept_accuracy=predictive["concept_accuracy"],
        concept_balanced_accuracy=predictive["concept_balanced_accuracy"],
        concept_macro_f1=predictive["concept_macro_f1"],
        top1_agreement_rate=agreement,
        top1_disagreement_rate=disagreement,
        mean_js_divergence=mean_js,
        consistency_direction=consistency_dir,
    )