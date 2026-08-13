from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

from pada3dacb.artifacts.concepts import ConceptNormalizer, ConceptTargetConfig
from pada3dacb.evaluation.schemas import AnalysisMode, AuthorizationGateError, canonical_sha256
from pada3dacb.exceptions import ConfigurationError
from pada3dacb.models.pada3dacb import PADA3DACB
from pada3dacb.models.roi_mask_preparation import prepare_feature_grid_roi_masks

from .provenance import VerifiedEvaluationInputs
from .schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptCandidate,
    ConceptNormalizerHash,
    ConceptSubjectRecord,
    Direction,
    FileIdentity,
    MethodId,
    RealEvaluationCapability,
    SubjectConceptRecord,
    VerifiedFixtureManifest,
    _is_issued_real_evaluation_capability,
    _is_verified_fixture_manifest,
    compute_sha256_file,
    validate_sha256,
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


def _canonical_roi_order_hash(
    atlas_mgr: object,
    concept_normalizer: ConceptNormalizer | None,
) -> AtlasROIOrderHash | None:
    """Hash canonical atlas labels with the established provenance algorithm."""
    for owner in (atlas_mgr, concept_normalizer):
        labels = getattr(owner, "label_values", None)
        if labels is None:
            labels = getattr(owner, "roi_labels", None)
        if isinstance(labels, Sequence) and not isinstance(labels, (str, bytes)):
            labels = list(labels)
            if labels:
                encoded = json.dumps(labels).encode()
                return AtlasROIOrderHash(hashlib.sha256(encoded).hexdigest())
    return None


def _is_primitive_metadata(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _is_primitive_metadata(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_primitive_metadata(item) for item in value)
    return False


def _safe_load_checkpoint_payload(checkpoint_path: Path) -> Mapping[str, Any]:
    """Load only tensor state and primitive metadata after identity is available."""
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    except Exception as error:
        raise ConfigurationError(
            f"Failed to load checkpoint {checkpoint_path}: unsupported or unsafe checkpoint format"
        ) from error
    if not isinstance(payload, Mapping):
        raise ConfigurationError(f"checkpoint must contain a top-level mapping: {checkpoint_path}")
    model_state = payload.get("model_state_dict", payload.get("model"))
    if not isinstance(model_state, Mapping) or not all(torch.is_tensor(value) for value in model_state.values()):
        raise ConfigurationError(f"checkpoint state dict is unsupported: {checkpoint_path}")
    config = payload.get("config", {})
    if not isinstance(config, Mapping) or not _is_primitive_metadata(config):
        raise ConfigurationError(f"checkpoint metadata format is unsupported: {checkpoint_path}")
    for name in ("experiment_hash", "model_hash", "training_hash"):
        if not isinstance(payload.get(name), str) or not payload[name]:
            raise ConfigurationError("Checkpoint missing required hashes")
    if isinstance(payload.get("epoch", 0), bool) or not isinstance(payload.get("epoch", 0), int):
        raise ConfigurationError(f"checkpoint epoch is unsupported: {checkpoint_path}")
    if not isinstance(payload.get("logical_checkpoint", "unknown"), str):
        raise ConfigurationError(f"checkpoint logical checkpoint is unsupported: {checkpoint_path}")
    return payload


def _build_checkpoint_bundle(
    payload: Mapping[str, Any],
    device: str,
    concept_normalizer: ConceptNormalizer | None,
    event_hook: Callable[[str], None] | None = None,
) -> CheckpointBundle:
    model_state = payload.get("model_state_dict", payload.get("model"))
    config_dict = dict(payload.get("config", {}))
    if event_hook is not None:
        event_hook("model_ctor")
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
    try:
        model.load_state_dict(model_state, strict=True)
    except (RuntimeError, TypeError, ValueError) as error:
        raise ConfigurationError(
            f"Checkpoint has incompatible model state for PADA-3DACB: {error}"
        ) from error
    model.to(device)
    model.eval()
    return CheckpointBundle(
        model=model,
        experiment_hash=payload["experiment_hash"],
        model_hash=payload["model_hash"],
        training_hash=payload["training_hash"],
        epoch=payload.get("epoch", 0),
        logical_checkpoint=payload.get("logical_checkpoint", "unknown"),
        config_dict=config_dict,
        concept_normalizer=concept_normalizer,
    )


def load_checkpoint(
    checkpoint_path: Path,
    device: str,
    concept_normalizer: ConceptNormalizer | None = None,
) -> CheckpointBundle:
    """Establish checkpoint identity, then use the safe tensor-only loader."""
    try:
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.is_file():
            raise OSError(f"checkpoint file is missing: {checkpoint_path}")
        _ = FileIdentity(checkpoint_path, compute_sha256_file(checkpoint_path), checkpoint_path.stat().st_size)
        payload = _safe_load_checkpoint_payload(checkpoint_path)
    except ConfigurationError:
        raise
    except Exception as error:
        raise ConfigurationError(f"Failed to load checkpoint {checkpoint_path}: {error}") from error
    return _build_checkpoint_bundle(payload, device, concept_normalizer)


def load_concept_normalizer_from_checkpoint(
    checkpoint_path: Path,
    artifacts_root: Path,
) -> ConceptNormalizer | None:
    """Load the concept normalizer from the artifact root first.

    The authoritative location is ``artifacts_root / concept_normalizer.json``.
    If that file is absent, fall back to the checkpoint directory's
    ``concept_normalizer.json``.
    """
    # The artifact root is authoritative when it contains the normalizer.
    normalizer_path = artifacts_root / "concept_normalizer.json"
    if normalizer_path.exists():
        return ConceptNormalizer.load(normalizer_path)

    # Fall back to the checkpoint directory when the artifact-root file is absent.
    normalizer_path = checkpoint_path.parent.parent / "concept_normalizer.json"
    if normalizer_path.exists():
        return ConceptNormalizer.load(normalizer_path)

    return None


@torch.no_grad()
def _canonical_roi_masks(
    atlas_mgr: object,
    observed_masks: torch.Tensor,
) -> torch.Tensor:
    """Return the canonical feature-grid masks from the atlas artifact."""
    get_binary_masks = getattr(atlas_mgr, "get_binary_masks", None)
    if callable(get_binary_masks):
        try:
            source_masks = get_binary_masks()
        except TypeError as error:
            raise RuntimeError(
                "atlas_mgr must expose canonical ROI masks without a target-shape override"
            ) from error
    else:
        source_masks = getattr(atlas_mgr, "atlas_tensor", None)
    if not torch.is_tensor(source_masks) or source_masks.ndim != 4:
        raise RuntimeError(
            "atlas_mgr must provide canonical ROI masks as a four-dimensional tensor"
        )
    if source_masks.shape[0] != observed_masks.shape[0]:
        raise RuntimeError(
            "canonical atlas ROI masks must have the same K as the batch roi_masks"
        )
    if tuple(source_masks.shape[1:]) == tuple(observed_masks.shape[1:]):
        return source_masks.to(dtype=torch.float32, device="cpu")
    try:
        return prepare_feature_grid_roi_masks(
            source_masks,
            tuple(int(value) for value in observed_masks.shape[1:]),
            device="cpu",
            dtype=torch.float32,
        )
    except (RuntimeError, ValueError) as error:
        raise RuntimeError(
            "canonical atlas ROI masks cannot be prepared for the model feature grid"
        ) from error


@torch.no_grad()
def run_subject_inference(
    model: PADA3DACB,
    dataloader: DataLoader,
    concept_normalizer: ConceptNormalizer,
    device: str,
    atlas_mgr,
    concept_config: ConceptTargetConfig | None = None,
    *,
    _event_hook: Callable[[str], None] | None = None,
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
    canonical_roi_order_hash = _canonical_roi_order_hash(atlas_mgr, concept_normalizer)
    if (
        canonical_roi_order_hash is not None
        and roi_order_hash != canonical_roi_order_hash
    ):
        raise RuntimeError(
            "declared ROI order hash does not match the canonical atlas label/order hash"
        )
    _ = concept_config
    records = []

    for batch in dataloader:
        if "concept_targets" not in batch or "anatomical_targets" not in batch:
            raise RuntimeError("batch must provide precomputed concept and anatomical targets")
        x = batch["x"].to(device, non_blocking=True)
        if "roi_masks" not in batch:
            raise RuntimeError(
                "batch must provide canonical roi_masks with shape (K,h,w,d) "
                "for PADA3DACB.forward"
            )
        roi_masks = batch["roi_masks"]
        if not torch.is_tensor(roi_masks):
            raise RuntimeError("batch roi_masks must be a torch.Tensor")
        if roi_masks.ndim == 4:
            canonical_roi_masks = roi_masks
        elif roi_masks.ndim == 5:
            if roi_masks.shape[0] != x.shape[0]:
                raise RuntimeError(
                    "batched roi_masks B dimension must match x; "
                    f"got {roi_masks.shape[0]} and {x.shape[0]}"
                )
            if not torch.isfinite(roi_masks).all():
                raise RuntimeError("batch roi_masks must contain only finite values")
            if not torch.allclose(
                roi_masks,
                roi_masks[0].unsqueeze(0),
                rtol=0.0,
                atol=0.0,
            ):
                raise RuntimeError("batched roi_masks must be identical across subjects")
            canonical_roi_masks = roi_masks[0]
        else:
            raise RuntimeError(
                "batch roi_masks must have shape (B,K,h,w,d) or (K,h,w,d); "
                f"got {tuple(roi_masks.shape)}"
            )
        expected_k = getattr(model, "num_rois", None)
        if isinstance(expected_k, int) and canonical_roi_masks.shape[0] != expected_k:
            raise RuntimeError(
                f"batch roi_masks K={canonical_roi_masks.shape[0]} does not match model K={expected_k}"
            )
        if not torch.is_floating_point(canonical_roi_masks):
            canonical_roi_masks = canonical_roi_masks.float()
        if not torch.isfinite(canonical_roi_masks).all():
            raise RuntimeError("batch roi_masks must contain only finite values")
        if (canonical_roi_masks.flatten(1).abs().sum(dim=1) == 0).any():
            raise RuntimeError("batch roi_masks must contain at least one voxel per ROI")
        expected_roi_masks = _canonical_roi_masks(atlas_mgr, canonical_roi_masks)
        observed_roi_masks = canonical_roi_masks.detach().to(device="cpu", dtype=torch.float32)
        if not torch.equal(observed_roi_masks, expected_roi_masks):
            raise RuntimeError(
                "batch roi_masks do not match the canonical atlas ROI masks "
                "and their declared ROI order"
            )
        roi_masks = canonical_roi_masks.to(device=device, non_blocking=True)
        subject_ids = batch["subject_id"]
        subject_hashes = batch["subject_hash"]
        cohorts = batch["cohort"]
        labels = batch["label"].cpu().numpy()
        label_names = batch["label_name"]

        # Forward pass
        if _event_hook is not None:
            _event_hook("forward")
        outputs = model(x, roi_masks)

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


def _candidate_key(candidate: ConceptCandidate) -> tuple:
    return tuple(
        value.value if hasattr(value, "value") else value
        for value in candidate.candidate_key
    )


def _validate_capability_contract(
    capability: object,
    authorization_evidence: Mapping[str, Any],
) -> None:
    if not _is_issued_real_evaluation_capability(capability):
        raise AuthorizationGateError("real evaluation requires an issued capability")
    try:
        validate_sha256(capability.manifest_sha256, "capability manifest sha256")
        validate_sha256(capability.authorization_sha256, "capability authorization sha256")
    except ValueError as error:
        raise AuthorizationGateError("real evaluation capability is malformed") from error
    if canonical_sha256(authorization_evidence) != capability.authorization_sha256:
        raise AuthorizationGateError("real evaluation capability authorization evidence is stale")


def _authorize_real_evaluation(
    capability: object,
    verified_inputs: object,
    authorization_evidence: Mapping[str, Any],
) -> None:
    _validate_capability_contract(capability, authorization_evidence)
    if not isinstance(verified_inputs, VerifiedEvaluationInputs):
        raise AuthorizationGateError("real evaluation requires verified Slice A inputs")
    if capability.manifest_sha256 != verified_inputs.manifest_sha256:
        raise AuthorizationGateError("real evaluation capability is stale for the manifest")


def _verify_real_artifact_identities(
    candidates: Sequence[ConceptCandidate],
    verified_inputs: VerifiedEvaluationInputs,
    event_hook: Callable[[str], None] | None,
) -> dict[tuple, Mapping[str, Any]]:
    candidate_keys = [_candidate_key(candidate) for candidate in candidates]
    if len(set(candidate_keys)) != len(candidate_keys):
        raise ConfigurationError("real evaluation candidates must have unique keys")
    if set(candidate_keys) != set(verified_inputs.checkpoints):
        raise ConfigurationError("all real candidates must have exact verified checkpoint assignments")
    if not verified_inputs.atlas.path.is_file() or compute_sha256_file(verified_inputs.atlas.path) != verified_inputs.atlas.sha256:
        raise ConfigurationError("verified atlas identity is stale")
    for candidate, key in zip(candidates, candidate_keys, strict=True):
        identity = verified_inputs.normalizers.get(key)
        if identity is None or not identity.path.is_file():
            raise ConfigurationError(f"verified normalizer assignment is missing for {key}")
        candidate_hash = candidate.concept_normalizer_hash
        if candidate_hash is None:
            raise ConfigurationError(f"candidate is missing concept normalizer hash for {key}")
        if candidate_hash != identity.sha256:
            raise ConfigurationError(
                f"candidate concept normalizer hash conflicts with verified identity for {key}"
            )
        if compute_sha256_file(identity.path) != identity.sha256:
            raise ConfigurationError(f"verified normalizer identity is stale for {key}")
    if event_hook is not None:
        event_hook("artifact_hash")

    checkpoint_payloads: dict[tuple, Mapping[str, Any]] = {}
    for _candidate, key in zip(candidates, candidate_keys, strict=True):
        identity = verified_inputs.checkpoints[key]
        if not identity.path.is_file() or compute_sha256_file(identity.path) != identity.sha256:
            raise ConfigurationError(f"verified checkpoint identity is stale for {key}")
    if event_hook is not None:
        event_hook("checkpoint_hash")
    for candidate, key in zip(candidates, candidate_keys, strict=True):
        identity = verified_inputs.checkpoints[key]
        payload = _safe_load_checkpoint_payload(identity.path)
        expected = {
            "experiment_hash": candidate.experiment_hash,
            "model_hash": candidate.model_hash,
            "training_hash": candidate.training_hash,
            "atlas_hash": verified_inputs.atlas.sha256,
            "concept_normalizer_hash": verified_inputs.normalizers[key].sha256,
            "roi_order_hash": str(verified_inputs.roi_order_hash),
            "logical_checkpoint": candidate.logical_checkpoint,
            "epoch": candidate.checkpoint_epoch,
        }
        for name, value in expected.items():
            if payload.get(name) != value:
                raise ConfigurationError(f"checkpoint metadata {name} conflicts for {key}")
        checkpoint_payloads[key] = payload
    if event_hook is not None:
        event_hook("safe_load")
    return checkpoint_payloads


def run_real_evaluation(
    candidates: Sequence[ConceptCandidate],
    dataloader_factory,
    device: str,
    concept_normalizer: ConceptNormalizer,
    atlas_mgr,
    concept_config: ConceptTargetConfig | None = None,
    *,
    capability: RealEvaluationCapability | object,
    verified_inputs: VerifiedEvaluationInputs | object,
    authorization_evidence: Mapping[str, Any],
    statistics_callback: Callable[[dict[tuple, list[ConceptSubjectRecord]]], Any] | None,
    publish_callback: Callable[[Any, dict[tuple, list[ConceptSubjectRecord]]], Any] | None,
    event_hook: Callable[[str], None] | None = None,
) -> Any:
    """Authorize and execute real evaluation without inventing a data source."""
    # Validate the capability before returning the intentional closed-seam error.
    _validate_capability_contract(capability, authorization_evidence)
    if not callable(dataloader_factory) or not callable(statistics_callback) or not callable(publish_callback):
        raise ConfigurationError(
            "real evaluation is closed: no approved local data, statistics, and publication callbacks are configured"
        )
    _authorize_real_evaluation(capability, verified_inputs, authorization_evidence)
    if event_hook is not None:
        event_hook("authorize")
    if not candidates:
        raise ConfigurationError("real evaluation requires at least one verified candidate")
    for candidate in candidates:
        if candidate.issues:
            raise ConfigurationError("real candidate has provenance validation issues")
    payloads = _verify_real_artifact_identities(candidates, verified_inputs, event_hook)

    bundles: dict[tuple, CheckpointBundle] = {}
    for candidate in candidates:
        key = _candidate_key(candidate)
        bundles[key] = _build_checkpoint_bundle(
            payloads[key], device, concept_normalizer, event_hook
        )

    results: dict[tuple, list[ConceptSubjectRecord]] = {}
    for candidate in candidates:
        key = _candidate_key(candidate)
        bundle = bundles[key]
        dataloader = dataloader_factory(candidate)
        if candidate.concept_normalizer_hash is None:
            raise ConfigurationError("candidate is missing concept normalizer hash")
        source_domain, target_domain = candidate.direction.cohorts
        results[key] = run_subject_inference(
            model=bundle.model,
            dataloader=dataloader,
            concept_normalizer=concept_normalizer,
            device=device,
            atlas_mgr=atlas_mgr,
            concept_config=concept_config,
            _event_hook=event_hook,
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
            concept_config_hash=canonical_sha256(bundle.config_dict.get("concept_target_config", {})),
        )

    statistics = statistics_callback(results)
    if event_hook is not None:
        event_hook("statistics")
    publication = publish_callback(statistics, results)
    if event_hook is not None:
        event_hook("publish")
    return publication


def _verify_fixture_execution_inputs(
    candidates: Sequence[ConceptCandidate],
    fixture_manifest: object,
) -> VerifiedFixtureManifest:
    if not _is_verified_fixture_manifest(fixture_manifest):
        raise AuthorizationGateError(
            "fixture execution requires a verified fixture manifest"
        )
    assert isinstance(fixture_manifest, VerifiedFixtureManifest)
    for candidate in candidates:
        if candidate.issues:
            raise ConfigurationError(
                "candidate has provenance validation issues: " + ", ".join(candidate.issues)
            )
        if candidate.concept_normalizer_hash is None:
            raise ConfigurationError("candidate is missing concept normalizer hash")
        try:
            validate_sha256(
                candidate.concept_normalizer_hash,
                "candidate concept normalizer hash",
            )
        except ValueError as error:
            raise ConfigurationError("candidate concept normalizer hash is invalid") from error
    for candidate in candidates:
        identity = fixture_manifest.file_identity(candidate.checkpoint_path)
        if identity is None:
            raise ConfigurationError(
                "fixture checkpoint is not listed in the verified fixture manifest"
            )
        if (
            not identity.path.is_file()
            or compute_sha256_file(identity.path) != identity.sha256
        ):
            raise ConfigurationError("fixture checkpoint identity is stale")
    return fixture_manifest


def run_inference_on_candidates(
    candidates: Sequence[ConceptCandidate],
    dataloader_factory,
    device: str,
    concept_normalizer: ConceptNormalizer,
    atlas_mgr,
    concept_config: ConceptTargetConfig | None = None,
    *,
    analysis_mode: AnalysisMode | None = None,
    capability: RealEvaluationCapability | object = None,
    verified_inputs: VerifiedEvaluationInputs | object = None,
    fixture_only: bool = False,
    fixture_manifest: VerifiedFixtureManifest | object = None,
) -> dict[tuple, list[ConceptSubjectRecord]]:
    """
    Run inference for all candidates and return records grouped by (method, direction, seed, fold, policy).

    This lower-level helper is fixture-only. Real callers must use
    :func:`run_real_evaluation`, which performs the capability and verified-input
    preflight before any checkpoint load.

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
    if analysis_mode is AnalysisMode.REAL:
        if fixture_only or not _is_issued_real_evaluation_capability(capability):
            raise AuthorizationGateError(
                "direct real candidate inference requires an issued capability"
            )
        if not isinstance(verified_inputs, VerifiedEvaluationInputs):
            raise AuthorizationGateError(
                "direct real candidate inference requires verified Slice A inputs"
            )
        raise ConfigurationError(
            "direct real candidate inference is closed; use run_real_evaluation"
        )
    if not fixture_only:
        raise AuthorizationGateError(
            "candidate inference requires explicit fixture_only=True"
        )
    _verify_fixture_execution_inputs(candidates, fixture_manifest)
    results = {}

    for candidate in candidates:
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