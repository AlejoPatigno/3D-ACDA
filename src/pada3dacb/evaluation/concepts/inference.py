from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from pada3dacb.artifacts.concepts import ConceptNormalizer, ConceptTargetConfig
from pada3dacb.evaluation.schemas import canonical_sha256
from pada3dacb.exceptions import ConfigurationError
from pada3dacb.models.pada3dacb import PADA3DACB

from .schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptCandidate,
    ConceptNormalizerHash,
    ConceptSubjectRecord,
    Direction,
    MethodId,
    SubjectConceptRecord,
)


@dataclass(frozen=True)
class InferenceConfig:
    """Configuration for concept inference."""
    device: str
    batch_size: int
    num_workers: int


@dataclass(frozen=True)
class CheckpointBundle:
    """Loaded checkpoint with metadata."""
    model: PADA3DACB
    experiment_hash: str
    model_hash: str
    training_hash: str
    epoch: int
    logical_checkpoint: str
    config_dict: dict
    concept_normalizer: ConceptNormalizer | None


def load_checkpoint(
    checkpoint_path: Path,
    device: str,
    concept_normalizer: ConceptNormalizer | None = None,
) -> CheckpointBundle:
    """
    Load PADA-3DACB checkpoint for concept evaluation.

    Args:
        checkpoint_path: Path to .pt checkpoint file
        device: Device to load model on
        concept_normalizer: Pre-loaded concept normalizer (optional)

    Returns:
        CheckpointBundle with model and metadata
    """
    # Load checkpoint (use weights_only=False to allow loading config dict)
    try:
        ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except Exception as e:
        raise ConfigurationError(f"Failed to load checkpoint {checkpoint_path}: {e}") from e

    # Extract metadata
    model_state = ckpt.get("model_state_dict", ckpt.get("model", {}))
    experiment_hash = ckpt.get("experiment_hash", "")
    model_hash = ckpt.get("model_hash", "")
    training_hash = ckpt.get("training_hash", "")
    epoch = ckpt.get("epoch", 0)
    logical_checkpoint = ckpt.get("logical_checkpoint", "unknown")
    config_dict = ckpt.get("config", {})

    # Validate required metadata
    if not all([experiment_hash, model_hash]):
        raise ConfigurationError("Checkpoint missing required hashes")

    # Build model from config
    model = PADA3DACB(
        num_rois=config_dict.get("num_rois", 84),
        feature_dim=config_dict.get("feature_dim", 256),
        token_dim=config_dict.get("token_dim", 128),
        num_classes=config_dict.get("num_classes", 3),
        base_channels=config_dict.get("base_channels", 32),
        concept_hidden_dim=config_dict.get("concept_hidden_dim", 64),
        token_dropout=config_dict.get("token_dropout", 0.2),
        concept_dropout=config_dict.get("concept_dropout", 0.2),
        validate_inputs=config_dict.get("validate_inputs", True),
    )
    model.load_state_dict(model_state, strict=False)
    model.to(device)
    model.eval()

    return CheckpointBundle(
        model=model,
        experiment_hash=experiment_hash,
        model_hash=model_hash,
        training_hash=training_hash,
        epoch=epoch,
        logical_checkpoint=logical_checkpoint,
        config_dict=config_dict,
        concept_normalizer=concept_normalizer,
    )


def load_concept_normalizer_from_checkpoint(
    checkpoint_path: Path,
    artifacts_root: Path,
) -> ConceptNormalizer | None:
    """
    Load concept normalizer from checkpoint metadata or artifacts.

    Priority:
    1. Checkpoint metadata (concept_normalizer_hash + path)
    2. Artifacts root / concept_normalizer.json
    """
    # Try artifacts root first
    normalizer_path = artifacts_root / "concept_normalizer.json"
    if normalizer_path.exists():
        return ConceptNormalizer.load(normalizer_path)

    # Try checkpoint directory
    normalizer_path = checkpoint_path.parent.parent / "concept_normalizer.json"
    if normalizer_path.exists():
        return ConceptNormalizer.load(normalizer_path)

    return None


@torch.no_grad()
def run_subject_inference(
    model: PADA3DACB,
    dataloader: DataLoader,
    concept_normalizer: ConceptNormalizer,
    device: str,
    atlas_mgr,
    concept_config: ConceptTargetConfig | None = None,
    *,
    method_id: MethodId,
    model_name: str = "PADA-3DACB",
    direction: Direction,
    source_domain: str,
    target_domain: str,
    seed: int,
    fold: int,
    logical_checkpoint: str,
    checkpoint_epoch: int,
    checkpoint_policy: CheckpointPolicy,
    experiment_hash: str,
    roi_order_hash: AtlasROIOrderHash,
    normalizer_hash: ConceptNormalizerHash,
    concept_config_hash: str,
) -> list[SubjectConceptRecord]:
    """
    Run no-grad inference on subject batches to extract concept outputs.

    Args:
        model: PADA-3DACB model in eval mode
        dataloader: DataLoader yielding (x, subject_id, subject_hash, cohort, label, label_name, metadata)
        concept_normalizer: Fitted concept normalizer
        device: Device for computation
        atlas_mgr: AtlasROIManager for concept target extraction
        concept_config: Configuration for concept target extraction

    Returns:
        List of SubjectConceptRecord with all required tensors
    """
    model.eval()
    _ = concept_normalizer, atlas_mgr, concept_config
    records = []

    for batch in dataloader:
        if "concept_targets" not in batch or "anatomical_targets" not in batch:
            raise RuntimeError("batch must provide precomputed concept and anatomical targets")
        x = batch["x"].to(device, non_blocking=True)
        subject_ids = batch["subject_id"]
        subject_hashes = batch["subject_hash"]
        cohorts = batch["cohort"]
        labels = batch["label"].cpu().numpy()
        label_names = batch["label_name"]

        # Forward pass
        outputs = model(x)

        # Extract tensors
        concepts = outputs.get("concepts")  # [B, K]
        latent_logits = outputs.get("latent_logits")  # [B, 3]
        concept_logits = outputs.get("concept_logits")  # [B, 3]
        alpha = outputs.get("alpha")  # [B, K]

        if any(t is None for t in [concepts, latent_logits, concept_logits, alpha]):
            raise RuntimeError("Model output missing required keys: concepts, latent_logits, concept_logits, alpha")

        B = concepts.shape[0]
        K = concepts.shape[1]

        if atlas_mgr is not None and getattr(atlas_mgr, "K", None) is not None and atlas_mgr.K != K:
            raise RuntimeError("atlas K does not match model concepts")

        # Probabilities
        latent_probs = torch.softmax(latent_logits, dim=1).cpu().numpy()
        concept_probs = torch.softmax(concept_logits, dim=1).cpu().numpy()

        # Predictions
        latent_preds = latent_probs.argmax(axis=1)
        concept_preds = concept_probs.argmax(axis=1)

        concepts_np = concepts.cpu().numpy()
        alpha_np = alpha.cpu().numpy()
        concept_targets = batch["concept_targets"].detach().cpu().numpy()
        anatomical_targets = batch["anatomical_targets"].detach().cpu().numpy()
        if concept_targets.shape != concepts_np.shape:
            raise RuntimeError("precomputed concept target shape does not match model concepts")
        if anatomical_targets.shape != concepts_np.shape:
            raise RuntimeError("precomputed anatomical target shape does not match model concepts")

        for i in range(B):
            subject_hash = str(subject_hashes[i])
            record = SubjectConceptRecord(
                method_id=method_id,
                model=model_name,
                direction=direction,
                source_domain=source_domain,
                target_domain=target_domain,
                seed=seed,
                fold=fold,
                logical_checkpoint=logical_checkpoint,
                checkpoint_epoch=checkpoint_epoch,
                checkpoint_policy=checkpoint_policy,
                experiment_hash=experiment_hash,
                subject_id=str(subject_ids[i]),
                subject_hash=subject_hash,
                cohort=str(cohorts[i]),
                true_label=int(labels[i]),
                label_name=str(label_names[i]),
                predicted_concepts=tuple(float(v) for v in concepts_np[i]),
                concept_targets=tuple(float(v) for v in concept_targets[i]),
                anatomical_targets=tuple(float(v) for v in anatomical_targets[i]),
                attention_alpha=tuple(float(v) for v in alpha_np[i]),
                latent_probabilities=tuple(float(v) for v in latent_probs[i]),
                concept_probabilities=tuple(float(v) for v in concept_probs[i]),
                latent_prediction=int(latent_preds[i]),
                concept_prediction=int(concept_preds[i]),
                K=K,
                roi_order_hash=roi_order_hash,
                normalizer_hash=normalizer_hash,
                concept_config_hash=concept_config_hash,
            )
            records.append(record)

    return records


def run_inference_on_candidates(
    candidates: Sequence[ConceptCandidate],
    dataloader_factory,
    device: str,
    concept_normalizer: ConceptNormalizer,
    atlas_mgr,
    concept_config: ConceptTargetConfig | None = None,
) -> dict[tuple, list[ConceptSubjectRecord]]:
    """
    Run inference for all candidates and return records grouped by (method, direction, seed, fold, policy).

    Args:
        candidates: Validated concept candidates
        dataloader_factory: Function(config, subject_hashes) -> DataLoader
        device: Device string
        concept_normalizer: Fitted concept normalizer
        atlas_mgr: AtlasROIManager
        concept_config: Concept target extraction config

    Returns:
        Dict mapping (method, direction, seed, fold, policy) -> list of ConceptSubjectRecord
    """
    results = {}

    for candidate in candidates:
        if candidate.issues:
            raise ConfigurationError(
                "candidate has provenance validation issues: " + ", ".join(candidate.issues)
            )
        bundle = load_checkpoint(candidate.checkpoint_path, device, concept_normalizer)

        # Build dataloader for this candidate's subjects
        # In practice, would filter by candidate's seed/fold subjects
        dataloader = dataloader_factory(candidate)

        if candidate.concept_normalizer_hash is None:
            raise ConfigurationError("candidate is missing concept normalizer hash")
        source_domain, target_domain = candidate.direction.cohorts
        records = run_subject_inference(
            model=bundle.model,
            dataloader=dataloader,
            concept_normalizer=concept_normalizer,
            device=device,
            atlas_mgr=atlas_mgr,
            concept_config=concept_config,
            method_id=candidate.method_id,
            direction=candidate.direction,
            source_domain=source_domain,
            target_domain=target_domain,
            seed=candidate.seed,
            fold=candidate.fold,
            logical_checkpoint=candidate.logical_checkpoint,
            checkpoint_epoch=candidate.checkpoint_epoch,
            checkpoint_policy=candidate.checkpoint_policy,
            experiment_hash=candidate.experiment_hash,
            roi_order_hash=AtlasROIOrderHash(candidate.roi_order_hash),
            normalizer_hash=ConceptNormalizerHash(candidate.concept_normalizer_hash),
            concept_config_hash=canonical_sha256(
                bundle.config_dict.get("concept_target_config", {})
            ),
        )
        key = (
            candidate.method_id,
            candidate.direction,
            candidate.seed,
            candidate.fold,
            candidate.checkpoint_policy,
        )
        results[key] = records

    return results