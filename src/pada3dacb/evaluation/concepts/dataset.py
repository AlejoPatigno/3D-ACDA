"""Read-only concept-evaluation dataset."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import Dataset

from .schemas import (
    AtlasROIOrderHash,
    ConceptNormalizerHash,
    ConfigurationError,
    SubjectConceptRecord,
)


@dataclass(frozen=True)
class ConceptEvaluationSample:
    """One subject's concept evaluation tensors."""

    subject_id: str
    subject_hash: str
    cohort: str
    true_label: int
    label_name: str
    predicted_concepts: torch.Tensor       # [K]
    concept_targets: torch.Tensor          # [K]
    anatomical_targets: torch.Tensor       # [K]
    attention_alpha: torch.Tensor          # [K]
    latent_probabilities: torch.Tensor     # [3]
    concept_probabilities: torch.Tensor    # [3]
    latent_prediction: int
    concept_prediction: int
    experiment_hash: str
    direction: str
    checkpoint_policy: str
    seed: int
    fold: int
    logical_checkpoint: str
    checkpoint_epoch: int

    def __post_init__(self) -> None:
        # Validate alpha sums to 1
        alpha = self.attention_alpha.numpy()
        sums = np.array([alpha.sum()]) if alpha.ndim == 1 else alpha.sum(axis=1)
        if not np.allclose(sums, 1.0, atol=1e-4):
            raise ValueError(f"attention alpha sums to {sums}, expected ~1.0")

        # Validate finite values
        for name, tensor in [
            ("predicted_concepts", self.predicted_concepts),
            ("concept_targets", self.concept_targets),
            ("anatomical_targets", self.anatomical_targets),
            ("attention_alpha", self.attention_alpha),
            ("latent_probabilities", self.latent_probabilities),
            ("concept_probabilities", self.concept_probabilities),
        ]:
            if not torch.isfinite(tensor).all():
                raise ValueError(f"{name} contains non-finite values")

        # Validate shapes
        if self.latent_probabilities.shape != (3,):
            raise ValueError("latent_probabilities must have 3 entries")
        if self.concept_probabilities.shape != (3,):
            raise ValueError("concept_probabilities must have 3 entries")
        if not (0 <= self.latent_prediction <= 2):
            raise ValueError("latent_prediction must be 0, 1, or 2")
        if not (0 <= self.concept_prediction <= 2):
            raise ValueError("concept_prediction must be 0, 1, or 2")


class ConceptEvaluationDataset(Dataset[ConceptEvaluationSample]):
    """
    Read-only dataset for concept evaluation.

    Loads precomputed subject-level tensors from checkpoint inference outputs.
    Never computes gradients, never modifies inputs, never invokes training.
    """

    def __init__(
        self,
        samples: Sequence[ConceptEvaluationSample],
        roi_order_hash: AtlasROIOrderHash,
        concept_normalizer_hash: ConceptNormalizerHash,
    ):
        self._samples = tuple(samples)
        self._roi_order_hash = roi_order_hash
        self._concept_normalizer_hash = concept_normalizer_hash

        if not self._samples:
            raise ConfigurationError("ConceptEvaluationDataset requires at least one sample")

        # Validate shape consistency across samples (all must have same K)
        k = self._samples[0].predicted_concepts.shape[0]
        for i, s in enumerate(self._samples):
            if s.predicted_concepts.shape != (k,):
                raise ConfigurationError(f"Sample {i} predicted_concepts shape mismatch: {s.predicted_concepts.shape} != ({k},)")
            if s.concept_targets.shape != (k,):
                raise ConfigurationError(f"Sample {i} concept_targets shape mismatch")
            if s.anatomical_targets.shape != (k,):
                raise ConfigurationError(f"Sample {i} anatomical_targets shape mismatch")
            if s.attention_alpha.shape != (k,):
                raise ConfigurationError(f"Sample {i} attention_alpha shape mismatch")
            if s.latent_probabilities.shape != (3,):
                raise ConfigurationError(f"Sample {i} latent_probabilities shape mismatch")
            if s.concept_probabilities.shape != (3,):
                raise ConfigurationError(f"Sample {i} concept_probabilities shape mismatch")

        self._k = k

    @property
    def k(self) -> int:
        return self._k

    @property
    def roi_order_hash(self) -> AtlasROIOrderHash:
        return self._roi_order_hash

    @property
    def concept_normalizer_hash(self) -> ConceptNormalizerHash:
        return self._concept_normalizer_hash

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> ConceptEvaluationSample:
        return self._samples[idx]

    def get_subject_hashes(self) -> tuple[str, ...]:
        return tuple(s.subject_hash for s in self._samples)

    def get_labels(self) -> tuple[int, ...]:
        return tuple(s.true_label for s in self._samples)

    def get_cohorts(self) -> tuple[str, ...]:
        return tuple(s.cohort for s in self._samples)

    def filter_by_label(self, label: int) -> ConceptEvaluationDataset:
        """Return dataset containing only subjects with given label."""
        filtered = [s for s in self._samples if s.true_label == label]
        return ConceptEvaluationDataset(filtered, self._roi_order_hash, self._concept_normalizer_hash)

    def filter_by_cohort(self, cohort: str) -> ConceptEvaluationDataset:
        filtered = [s for s in self._samples if s.cohort == cohort]
        return ConceptEvaluationDataset(filtered, self._roi_order_hash, self._concept_normalizer_hash)

    def to_arrays(self) -> dict[str, np.ndarray]:
        """Convert all samples to stacked numpy arrays for metrics computation."""
        return {
            "predicted_concepts": np.stack([s.predicted_concepts.numpy() for s in self._samples]),
            "concept_targets": np.stack([s.concept_targets.numpy() for s in self._samples]),
            "anatomical_targets": np.stack([s.anatomical_targets.numpy() for s in self._samples]),
            "attention_alpha": np.stack([s.attention_alpha.numpy() for s in self._samples]),
            "latent_probabilities": np.stack([s.latent_probabilities.numpy() for s in self._samples]),
            "concept_probabilities": np.stack([s.concept_probabilities.numpy() for s in self._samples]),
            "latent_predictions": np.array([s.latent_prediction for s in self._samples], dtype=np.int64),
            "concept_predictions": np.array([s.concept_prediction for s in self._samples], dtype=np.int64),
            "true_labels": np.array([s.true_label for s in self._samples], dtype=np.int64),
            "subject_hashes": np.array([s.subject_hash for s in self._samples]),
        }


def build_concept_evaluation_dataset(
    subject_records: Sequence[SubjectConceptRecord],
    roi_order_hash: AtlasROIOrderHash,
    concept_normalizer_hash: ConceptNormalizerHash,
) -> ConceptEvaluationDataset:
    """
    Build ConceptEvaluationDataset from subject records produced by inference.

    Args:
        subject_records: Output from inference pipeline
        roi_order_hash: Validated ROI order hash
        concept_normalizer_hash: Validated normalizer hash

    Returns:
        ConceptEvaluationDataset ready for metrics computation
    """
    samples = []
    for rec in subject_records:
        sample = ConceptEvaluationSample(
            subject_id=rec.subject_id,
            subject_hash=rec.subject_hash,
            cohort=rec.cohort,
            true_label=rec.true_label,
            label_name=rec.label_name,
            predicted_concepts=torch.tensor(rec.predicted_concepts, dtype=torch.float32),
            concept_targets=torch.tensor(rec.concept_targets, dtype=torch.float32),
            anatomical_targets=torch.tensor(rec.anatomical_targets, dtype=torch.float32),
            attention_alpha=torch.tensor(rec.attention_alpha, dtype=torch.float32),
            latent_probabilities=torch.tensor(rec.latent_probabilities, dtype=torch.float32),
            concept_probabilities=torch.tensor(rec.concept_probabilities, dtype=torch.float32),
            latent_prediction=rec.latent_prediction,
            concept_prediction=rec.concept_prediction,
            experiment_hash=rec.experiment_hash,
            direction=rec.direction.value,
            checkpoint_policy=rec.checkpoint_policy.value,
            seed=rec.seed,
            fold=rec.fold,
            logical_checkpoint=rec.logical_checkpoint,
            checkpoint_epoch=rec.checkpoint_epoch,
        )
        samples.append(sample)

    return ConceptEvaluationDataset(samples, roi_order_hash, concept_normalizer_hash)


@dataclass(frozen=True)
class FoldEnsemble:
    """Aggregated target subject record across folds for one seed."""

    subject_id: str
    subject_hash: str
    cohort: str
    true_label: int
    label_name: str
    predicted_concepts: np.ndarray      # [K] mean across folds
    concept_targets: np.ndarray         # [K] (immutable)
    anatomical_targets: np.ndarray      # [K] (immutable)
    attention_alpha: np.ndarray         # [K] mean across folds
    latent_probabilities: np.ndarray    # [3] mean across folds
    concept_probabilities: np.ndarray   # [3] mean across folds
    latent_prediction: int
    concept_prediction: int
    fold_count: int
    experiment_hash: str
    direction: str
    checkpoint_policy: str
    seed: int
    fold_hashes: tuple[str, ...]        # source fold hashes for provenance


def aggregate_folds(
    fold_records: Sequence[SubjectConceptRecord],
    expected_folds: Sequence[int],
) -> FoldEnsemble:
    """
    Aggregate subject records across folds within one seed.

    Args:
        fold_records: Records for same subject/seed across folds
        expected_folds: Expected fold indices

    Returns:
        FoldEnsemble with averaged predictions
    """
    if not fold_records:
        raise ValueError("No fold records to aggregate")

    # Verify all same subject
    subject_hash = fold_records[0].subject_hash
    if any(r.subject_hash != subject_hash for r in fold_records):
        raise ValueError("Fold records have inconsistent subject hashes")

    # Verify folds match
    observed_folds = tuple(sorted(r.fold for r in fold_records))
    if observed_folds != tuple(expected_folds):
        raise ValueError(f"Missing or extra folds: got {observed_folds}, expected {tuple(expected_folds)}")

    # Average predicted concepts, probabilities, alpha across folds
    pred_concepts = np.mean(np.stack([r.predicted_concepts for r in fold_records]), axis=0)
    pred_alpha = np.mean(np.stack([r.attention_alpha for r in fold_records]), axis=0)
    pred_latent_probs = np.mean(np.stack([r.latent_probabilities for r in fold_records]), axis=0)
    pred_concept_probs = np.mean(np.stack([r.concept_probabilities for r in fold_records]), axis=0)

    # Predictions from averaged probabilities
    latent_pred = int(np.argmax(pred_latent_probs))
    concept_pred = int(np.argmax(pred_concept_probs))

    return FoldEnsemble(
        subject_id=fold_records[0].subject_id,
        subject_hash=subject_hash,
        cohort=fold_records[0].cohort,
        true_label=fold_records[0].true_label,
        label_name=fold_records[0].label_name,
        predicted_concepts=pred_concepts,
        concept_targets=fold_records[0].concept_targets,      # immutable
        anatomical_targets=fold_records[0].anatomical_targets,  # immutable
        attention_alpha=pred_alpha,
        latent_probabilities=pred_latent_probs,
        concept_probabilities=pred_concept_probs,
        latent_prediction=latent_pred,
        concept_prediction=concept_pred,
        fold_count=len(fold_records),
        experiment_hash=fold_records[0].experiment_hash,
        direction=fold_records[0].direction,
        checkpoint_policy=fold_records[0].checkpoint_policy,
        seed=fold_records[0].seed,
        fold_hashes=tuple(r.experiment_hash for r in fold_records),
    )


def aggregate_seeds(
    seed_ensembles: Sequence[FoldEnsemble],
) -> tuple[np.ndarray, ...]:
    """
    Aggregate fold ensembles across seeds.

    Returns:
        Tuple of (mean_concepts, mean_alpha, mean_latent_probs, mean_concept_probs)
        all averaged across seeds.
    """
    if not seed_ensembles:
        raise ValueError("No seed ensembles to aggregate")

    mean_concepts = np.mean(np.stack([e.predicted_concepts for e in seed_ensembles]), axis=0)
    mean_alpha = np.mean(np.stack([e.attention_alpha for e in seed_ensembles]), axis=0)
    mean_latent = np.mean(np.stack([e.latent_probabilities for e in seed_ensembles]), axis=0)
    mean_concept = np.mean(np.stack([e.concept_probabilities for e in seed_ensembles]), axis=0)

    return mean_concepts, mean_alpha, mean_latent, mean_concept