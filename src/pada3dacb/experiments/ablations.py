"""Synthetic-only Phase 17 ablation orchestration and CLI contracts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import pickle
import platform
import stat
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import yaml
from torch.utils.data import DataLoader

from pada3dacb.ablations import (
    AblationResolutionError,
    Disposition,
    resolve_ablation_config,
    validate_target_adaptation_batch,
)
from pada3dacb.ablations.registry import (
    alias_target,
    get_ablation_spec,
    is_unresolved_name,
    list_ablations,
)
from pada3dacb.ablations.schemas import sha256_payload
from pada3dacb.adaptation import MMDAdaptationMethod
from pada3dacb.binary import binary_ablation_plan
from pada3dacb.exceptions import ExperimentValidationError
from pada3dacb.experiments.run_manifest import ablation_output_path, atomic_json, sha256_file
from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.models import build_pada3dacb, prepare_feature_grid_roi_masks
from pada3dacb.models.ablations import build_mean_pool_model
from pada3dacb.training.reproducibility import seed_everything
from pada3dacb.training.uda_trainer import ComposedCoreLoss

APPROVED_ABLATIONS = ("no_proto", "no_pl", "no_cons", "no_concept", "no_anat", "mean_pool", "no_da")
SUPPORTED_DOMAINS = ("ADNI", "OASIS")
DEFAULT_DIRECTIONS = ("ADNI_to_OASIS", "OASIS_to_ADNI")
MONITORING_LABEL = "MONITORING ONLY — NOT A TRAINING LOSS"
MMD_BASELINE_ADAPTATION = {
    "name": "mmd",
    "feature": "z",
    "active_during_warmup": False,
    "kernel": {
        "name": "gaussian_rbf_mixture",
        "bandwidths": [0.5, 1.0, 2.0],
        "aggregation": "mean",
    },
    "estimator": "biased",
    "include_diagonal": True,
    "compute_dtype": "float32",
}


class AblationCLIError(ValueError):
    """Structured command error that leaves the workspace unchanged."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


class SyntheticLifecycleError(AblationCLIError):
    """Fail-closed error for the synthetic lifecycle boundary."""


class SyntheticLifecycleInterrupted(SyntheticLifecycleError):
    """Optional exception type for callers that prefer exception interruption."""


@dataclass(frozen=True)
class SyntheticLifecycleResult:
    """Small typed result returned by synthetic run and resume entry points."""

    status: str
    output_dir: Path
    candidate_id: str
    direction: str
    seed: int
    fold: int
    completed_epochs: int
    total_epochs: int
    reused: bool = False
    interrupted: bool = False

    @property
    def complete(self) -> bool:
        return self.status == "COMPLETED"

    def __getitem__(self, key: str) -> Any:
        return {
            "status": self.status,
            "output_dir": str(self.output_dir),
            "candidate_id": self.candidate_id,
            "direction": self.direction,
            "seed": self.seed,
            "fold": self.fold,
            "completed_epochs": self.completed_epochs,
            "total_epochs": self.total_epochs,
            "reused": self.reused,
            "interrupted": self.interrupted,
        }[key]


@dataclass(frozen=True)
class ResumeIdentityResult:
    """Read-only identity validation result used by resume callers."""

    valid: bool
    mismatches: tuple[str, ...] = ()
    identity: dict[str, Any] | None = None

    def __bool__(self) -> bool:
        return self.valid


@dataclass(frozen=True)
class AblationExperimentConfig:
    path: Path
    payload: dict[str, Any]
    base: dict[str, Any]
    source_domain: str
    target_domain: str
    directions: tuple[str, ...]
    folds: tuple[int, ...]
    seeds: tuple[int, ...]
    output_root: Path
    target_monitoring: bool
    synthetic_only: bool
    real_data_authorized: bool
    publication_metrics: bool

    @property
    def model(self) -> dict[str, Any]:
        value = self.payload.get("synthetic_model", self.payload.get("model", {}))
        if not isinstance(value, dict):
            raise AblationCLIError("invalid_config", "model must be a mapping")
        return value

    @property
    def configured_hashes(self) -> dict[str, str]:
        value = self.payload.get("hashes", {})
        if not isinstance(value, dict):
            raise AblationCLIError("invalid_config", "hashes must be a mapping")
        hashes = {str(key): str(item) for key, item in value.items() if item is not None}
        for key, digest in hashes.items():
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise AblationCLIError("invalid_hash", f"configured hash {key!r} is not SHA-256")
        return hashes

    def direction_for(self, source: str | None, target: str | None) -> tuple[str, ...]:
        source_name = (source or self.source_domain).upper()
        target_name = (target or self.target_domain).upper()
        if source_name not in SUPPORTED_DOMAINS or target_name not in SUPPORTED_DOMAINS:
            raise AblationCLIError("invalid_direction", "source and target domains must be ADNI or OASIS")
        if source_name == target_name:
            raise AblationCLIError("invalid_direction", "source and target domains must differ")
        requested = f"{source_name}_to_{target_name}"
        if requested not in self.directions:
            raise AblationCLIError(
                "incomplete_matrix",
                f"direction {requested!r} is not present in the predeclared complete matrix",
            )
        return (requested,)

    def base_for_direction(self, direction: str) -> dict[str, Any]:
        source, target = direction.split("_to_", 1)
        value = copy.deepcopy(self.base)
        value["assignments"] = copy.deepcopy(self.base["assignments"])
        value["direction"] = direction
        value["source_domain"] = source
        value["target_domain"] = target
        return value


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise AblationCLIError("config_unreadable", f"cannot read config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AblationCLIError("invalid_config", "ablation config must contain a mapping")
    return payload


def _as_tuple(values: object, field: str, *, integers: bool = False) -> tuple[Any, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        raise AblationCLIError("incomplete_matrix", f"{field} must be a non-empty sequence")
    result = tuple(values)
    if integers and any(isinstance(value, bool) or not isinstance(value, int) for value in result):
        raise AblationCLIError("invalid_config", f"{field} must contain integers")
    if len(set(result)) != len(result):
        raise AblationCLIError("invalid_config", f"{field} must not contain duplicates")
    return result


def load_ablation_config(path: str | Path, *, output_root: str | Path | None = None) -> AblationExperimentConfig:
    """Load an explicit Phase 17 config without discovering scientific defaults."""
    config_path = Path(path).resolve()
    payload = _read_payload(config_path)
    experiment = payload.get("experiment", {})
    if not isinstance(experiment, dict):
        raise AblationCLIError("invalid_config", "experiment must be a mapping")
    if experiment.get("method", "ablation") != "ablation":
        raise AblationCLIError("invalid_config", "config method must be 'ablation'")
    base = copy.deepcopy(payload)
    base.pop("experiment", None)
    base.pop("synthetic_model", None)
    base.pop("hashes", None)
    base.update({key: value for key, value in experiment.items() if key not in {"method", "name"}})
    base.setdefault("base_method", "PADA-3DACB")
    if "losses" not in base or "approval" not in base or "epochs" not in base:
        raise AblationCLIError("invalid_config", "losses, approval, and explicit epochs are required")
    source = str(experiment.get("source_domain", "")).upper()
    target = str(experiment.get("target_domain", "")).upper()
    directions = tuple(str(value) for value in experiment.get("directions", DEFAULT_DIRECTIONS))
    folds = _as_tuple(experiment.get("folds"), "experiment.folds", integers=True)
    seeds = _as_tuple(experiment.get("seeds"), "experiment.seeds", integers=True)
    output = output_root if output_root is not None else payload.get("paths", {}).get("output_root")
    if output is None or str(output).strip() == "":
        output = "runs/phase17"
    synthetic_only = bool(experiment.get("synthetic_only", payload.get("synthetic_only", False)))
    real_authorized = bool(
        experiment.get("real_data_authorized", payload.get("real_data_authorized", False))
    )
    publication = bool(experiment.get("publication_metrics", payload.get("publication_metrics", False)))
    config = AblationExperimentConfig(
        path=config_path,
        payload=payload,
        base=base,
        source_domain=source,
        target_domain=target,
        directions=directions,
        folds=folds,
        seeds=seeds,
        output_root=Path(output).resolve(),
        target_monitoring=bool((payload.get("evaluation") or {}).get("target_monitoring", True)),
        synthetic_only=synthetic_only,
        real_data_authorized=real_authorized,
        publication_metrics=publication,
    )
    if source not in SUPPORTED_DOMAINS or target not in SUPPORTED_DOMAINS or source == target:
        raise AblationCLIError("invalid_direction", "config must explicitly declare opposite ADNI/OASIS domains")
    if set(config.directions) != set(DEFAULT_DIRECTIONS):
        raise AblationCLIError("incomplete_matrix", "the complete matrix must declare both transfer directions")
    if set(config.folds) != set(range(5)):
        raise AblationCLIError("incomplete_matrix", "the complete matrix must declare folds 0 through 4")
    if not config.seeds:
        raise AblationCLIError("incomplete_matrix", "the complete matrix must declare at least one seed")
    _ = config.configured_hashes
    return config


def _requested_candidates(name: str | None, all_approved: bool) -> tuple[str, ...]:
    if name and all_approved:
        raise AblationCLIError("ambiguous_selection", "use either --ablation or --all-approved-ablations")
    if all_approved:
        return APPROVED_ABLATIONS
    if not name:
        raise AblationCLIError("missing_selection", "--ablation or --all-approved-ablations is required")
    return (name,)


def _blocked_ids() -> tuple[str, ...]:
    return tuple(name for name in list_ablations() if name not in APPROVED_ABLATIONS)


def build_equivalence_reference(requested_name: str) -> dict[str, Any]:
    """Serialize a visible candidate disposition without silently resolving it."""
    alias = alias_target(requested_name)
    if alias is not None:
        payload = {
            "requested_name": requested_name,
            "canonical_id": None,
            "alias_mapping": {"candidate": alias, "approved": False},
            "classification": "unsupported",
            "disposition": Disposition.UNSUPPORTED_ALIAS.value,
            "blocked_reason": "alias is not explicitly approved; use the exact registry ID",
            "source": None,
        }
    elif is_unresolved_name(requested_name):
        payload = {
            "requested_name": requested_name,
            "canonical_id": None,
            "alias_mapping": None,
            "classification": "unsupported",
            "disposition": Disposition.UNRESOLVED_CONFIGURATION.value,
            "blocked_reason": "lambda_proto=0.2 remains unresolved against canonical primary lambda_proto=1.0",
            "source": None,
        }
    else:
        try:
            spec = get_ablation_spec(requested_name)
        except KeyError:
            payload = {
                "requested_name": requested_name,
                "canonical_id": None,
                "alias_mapping": None,
                "classification": "unknown",
                "disposition": Disposition.BLOCKED_NOT_PROVEN.value,
                "blocked_reason": "candidate is not present in the immutable registry",
                "source": None,
            }
        else:
            payload = {
                "requested_name": requested_name,
                "canonical_id": spec.id if spec.is_runnable else None,
                "alias_mapping": None,
                "classification": spec.classification.value,
                "disposition": spec.disposition.value,
                "blocked_reason": spec.blocked_reasons[0] if spec.blocked_reasons else None,
                "source": spec.provenance.to_dict(),
                "intervention": None if spec.intervention is None else spec.intervention.to_dict(),
                "changed_components": spec.changed_components,
                "preserved_components": spec.preserved_components,
                "equivalent_method": spec.equivalent_method,
            }
    payload.update(
        {
            "method": "ablation",
            "base_method": "prototype_pseudo",
            "real_data_run": False,
            "publication_metrics_present": False,
            "read_only": not bool(payload.get("canonical_id")),
                "adaptation_method": "mmd" if requested_name in APPROVED_ABLATIONS else "prototype_pseudo",
                "adaptation_weight": 0.0 if requested_name == "no_da" else 1.0,
                "adaptation_configuration": {
                    **copy.deepcopy(MMD_BASELINE_ADAPTATION),
                    "weight": 0.0 if requested_name == "no_da" else 1.0,
                } if requested_name in APPROVED_ABLATIONS else None,
                "adaptation_configuration_hash": sha256_payload({
                    **MMD_BASELINE_ADAPTATION,
                    "weight": 0.0 if requested_name == "no_da" else 1.0,
                }) if requested_name in APPROVED_ABLATIONS else None,
        }
    )
    payload["equivalence_manifest_hash"] = sha256_payload(payload)
    return payload


def planned_run_path(
    config: AblationExperimentConfig,
    ablation_id: str,
    direction: str,
    seed: int,
    fold: int,
) -> Path:
    return ablation_output_path(config.output_root, ablation_id, direction, seed, fold)


def _plan(
    config: AblationExperimentConfig,
    requested_name: str,
    direction: str,
    seed: int,
    fold: int,
) -> dict[str, Any]:
    source, target = direction.split("_to_", 1)
    direction_assignments = {
        "source": [f"{source}:source_fold_{fold}"],
        "target_adaptation": [f"{target}:target_adaptation_fold_{fold}"],
        "target_evaluation": [f"{target}:target_evaluation_fold_{fold}"],
    }
    materialized_base = config.base_for_direction(direction)
    materialized_base["assignments"] = copy.deepcopy(direction_assignments)
    resolved = resolve_ablation_config(materialized_base, requested_name)
    reference = build_equivalence_reference(requested_name)
    assignment_hashes = {
        "source_split_assignment_hash": sha256_payload(direction_assignments["source"]),
        "target_adaptation_assignment_hash": sha256_payload(direction_assignments["target_adaptation"]),
        "target_evaluation_assignment_hash": sha256_payload(direction_assignments["target_evaluation"]),
    }
    config_hash = sha256_payload(materialized_base)
    identity = {
        "method": "ablation",
        "ablation_id": resolved.candidate_id,
        "base_method": "prototype_pseudo",
        "adaptation_method": resolved.adaptation_method,
        "adaptation_weight": resolved.adaptation_weight,
        "adaptation_configuration": copy.deepcopy(resolved.adaptation_configuration),
        "adaptation_configuration_hash": resolved.adaptation_configuration_hash,
        "requested_name": requested_name,
        "direction": direction,
        "seed": seed,
        "fold": fold,
        "registry_hash": resolved.registry_hash,
        "candidate_hash": resolved.candidate_hash,
        "configuration_hash": config_hash,
        "base_configuration_hash": config_hash,
        "resolved_config_hash": resolved.resolved_config_hash,
        "model_variant_hash": resolved.model_variant_hash,
        "split_assignment_hash": sha256_payload(direction_assignments),
        **assignment_hashes,
        "assignments": copy.deepcopy(direction_assignments),
        "precomputed_artifacts_hash": resolved.precomputed_artifacts_hash,
        "artifact_index_hash": sha256_payload(config.configured_hashes.get("artifact_index", "synthetic-artifact-index")),
        "atlas_hash": config.configured_hashes.get("atlas", sha256_payload("synthetic-atlas")),
        "loader_requirements": {
            "target_adaptation": "unlabeled_only",
            "target_evaluation": "monitoring_only",
            "target_adaptation_batch_keys": ["x", "subject_id", "subject_hash", "cohort"],
        },
        "target_label_firewall": {
            "target_adaptation_batch_keys": ["x", "subject_id", "subject_hash", "cohort"],
            "target_labels_in_adaptation": False,
        },
        "approval_boundary": {
            "approval_id": resolved.approval.approval_id,
            "scope": resolved.approval.scope,
            "approved_by": resolved.approval.approved_by,
            "real_execution_authorized": False,
        },
        "configured_hashes": config.configured_hashes,
        "synthetic": True,
        "real_data_run": False,
        "publication_metrics_present": False,
    }
    return {
        **identity,
        "output_dir": str(planned_run_path(config, resolved.candidate_id, direction, seed, fold)),
        "equivalence_reference": reference,
        "equivalence_manifest_hash": reference["equivalence_manifest_hash"],
        "changed_components": get_ablation_spec(resolved.candidate_id).changed_components,
        "preserved_components": get_ablation_spec(resolved.candidate_id).preserved_components,
        "model_variant": resolved.model_variant.to_dict(),
        "target_loader_use": "unlabeled_target_adaptation",
        "target_monitoring_enabled": config.target_monitoring,
        "forward_executed": False,
        "target_forward_executed": False,
        "adaptation_method": resolved.adaptation_method,
        "adaptation_weight": resolved.adaptation_weight,
        "adaptation_configuration_hash": resolved.adaptation_configuration_hash,
        "validated": False,
    }


_LIFECYCLE_IDENTITY_FIELDS = (
    "phase",
    "method",
    "base_method",
    "adaptation_method",
    "adaptation_weight",
    "adaptation_configuration",
    "adaptation_configuration_hash",
    "ablation_id",
    "requested_name",
    "direction",
    "seed",
    "fold",
    "registry_hash",
    "candidate_hash",
    "configuration_hash",
    "base_configuration_hash",
    "resolved_config_hash",
    "model_variant_hash",
    "split_assignment_hash",
    "source_split_assignment_hash",
    "target_adaptation_assignment_hash",
    "target_evaluation_assignment_hash",
    "precomputed_artifacts_hash",
    "artifact_index_hash",
    "atlas_hash",
    "configured_hashes",
    "matrix",
    "assignments",
    "loader_requirements",
    "target_label_firewall",
    "approval_boundary",
    "synthetic",
    "real_data_run",
    "publication_metrics_present",
)
_LIFECYCLE_FILES = {
    "identity.json": "identity",
    "config_resolved.json": "resolved_configuration",
    "checkpoint_last.pt": "checkpoint_last",
    "checkpoint_best_source_f1.pt": "checkpoint_best_source_validation_macro_f1",
    "training_history.json": "history",
    "predictions.jsonl": "predictions",
    "source_validation_predictions.jsonl": "source_validation_predictions",
    "target_monitoring_predictions.jsonl": "target_monitoring_predictions",
    "reproducibility_metadata.json": "reproducibility_metadata",
    "equivalence_manifest.json": "equivalence_manifest_read_only",
}


def _lifecycle_config(
    config: AblationExperimentConfig | str | Path,
    output_root: str | Path | None = None,
) -> AblationExperimentConfig:
    if isinstance(config, AblationExperimentConfig):
        result = copy.copy(config)
        if output_root is not None:
            object.__setattr__(result, "output_root", Path(output_root).resolve())
    else:
        result = load_ablation_config(config, output_root=output_root)
    if result.real_data_authorized or result.publication_metrics or not result.synthetic_only:
        raise SyntheticLifecycleError(
            "real_run_not_authorized",
            "synthetic lifecycle requires synthetic_only=true, real_data_authorized=false, and publication_metrics=false",
        )
    return result


def _lifecycle_selection(
    config: AblationExperimentConfig,
    requested_name: str | None,
    direction: str | None,
    source_domain: str | None,
    target_domain: str | None,
    seed: int | None,
    fold: int | None,
) -> tuple[str, str, int, int, dict[str, Any]]:
    name = requested_name or config.payload.get("ablation_id")
    if not isinstance(name, str) or not name:
        raise SyntheticLifecycleError("missing_selection", "one exact approved candidate is required")
    if direction is not None:
        if "_to_" not in direction:
            raise SyntheticLifecycleError("invalid_direction", "direction must be SOURCE_to_TARGET")
        selected_direction = config.direction_for(*direction.split("_to_", 1)) [0]
    else:
        selected_direction = config.direction_for(source_domain, target_domain)[0]
    selected_seed = config.seeds[0] if seed is None else seed
    selected_fold = config.folds[0] if fold is None else fold
    if selected_seed not in config.seeds or selected_fold not in config.folds:
        raise SyntheticLifecycleError("incomplete_matrix", "seed and fold must be present in the complete matrix")
    plan = _plan(config, name, selected_direction, selected_seed, selected_fold)
    return name, selected_direction, selected_seed, selected_fold, plan


def _lifecycle_identity(plan: dict[str, Any], config: AblationExperimentConfig) -> dict[str, Any]:
    identity = {key: copy.deepcopy(plan[key]) for key in _LIFECYCLE_IDENTITY_FIELDS if key in plan}
    identity.update(
        {
            "schema_version": "phase17.identity.v1",
                "phase": 17,
            "candidate_classification": get_ablation_spec(plan["ablation_id"]).classification.value,
            "candidate_approval_id": plan["approval_boundary"]["approval_id"],
            "alias_mapping": None,
            "requested_name": plan["requested_name"],
            "matrix": {
                "directions": list(config.directions),
                "folds": list(config.folds),
                "seeds": list(config.seeds),
            },
            "assignments": copy.deepcopy(plan["assignments"]),
            "hash_algorithm": "sha256",
            "canonicalization_version": "phase17.canonical-json.v1",
            "target_monitoring_label": MONITORING_LABEL,
        }
    )
    return identity


def _artifact_envelope(identity: dict[str, Any], role: str, schema: str) -> dict[str, Any]:
    return {
        "schema_version": schema,
        "phase": 17,
        "artifact_role": role,
        "identity": copy.deepcopy(identity),
        "real_data_run": False,
        "publication_metrics_present": False,
    }


def _atomic_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            "".join(json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for record in records),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _checkpoint_bytes(payload: dict[str, Any]) -> bytes:
    stream = io.BytesIO()
    torch.save(payload, stream, _use_new_zipfile_serialization=False)
    return stream.getvalue()


def _atomic_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(_checkpoint_bytes(payload))
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_checkpoint(path: Path) -> dict[str, Any]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, EOFError, pickle.UnpicklingError) as exc:
        raise SyntheticLifecycleError("hash_mismatch", f"checkpoint cannot be read: {path}") from exc
    if not isinstance(value, dict):
        raise SyntheticLifecycleError("hash_mismatch", "checkpoint payload must be a mapping")
    return value


def _history_value(identity: dict[str, Any], epoch: int, name: str) -> float:
    digest = hashlib.sha256(f"{sha256_payload(identity)}:{epoch}:{name}".encode()).digest()
    return round(int.from_bytes(digest[:8], "big") / 2**64, 8)


def _history_row(identity: dict[str, Any], resolved: Any, epoch: int, stage: str, target_monitoring: bool) -> dict[str, Any]:
    source_f1 = round(0.45 + 0.5 * _history_value(identity, epoch, "source_validation_macro_f1"), 6)
    source_accuracy = round(0.5 + 0.45 * _history_value(identity, epoch, "source_validation_accuracy"), 6)
    target_f1 = round(0.4 + 0.5 * _history_value(identity, epoch, "target_monitoring_macro_f1"), 6)
    disabled = {
        "no_cons": "L_cons",
        "no_concept": "L_concept",
        "no_anat": "L_anat",
        "no_proto": "L_proto",
        "no_pl": "L_pl",
    }.get(identity["ablation_id"])
    coefficients = resolved.losses.to_dict()
    names = ("L_cls_z", "L_cls_c", "L_cons", "L_concept", "L_anat", "L_proto", "L_pl")
    components: dict[str, dict[str, Any]] = {}
    for name in names:
        raw = round(0.1 + _history_value(identity, epoch, name), 8)
        active = not (stage == "warm" and name in {"L_proto", "L_pl"}) and name != disabled
        weighted = round(raw * (coefficients.get({
            "L_cls_z": "lambda_z", "L_cls_c": "lambda_c", "L_cons": "lambda_cons",
            "L_concept": "lambda_cbm", "L_anat": "lambda_anat", "L_proto": "lambda_proto",
            "L_pl": "lambda_pl",
        }[name], 0.0) if active else 0.0), 8)
        components[name] = {"active": active, "raw": raw if active else 0.0, "weighted": weighted}
    total = round(sum(item["weighted"] for item in components.values()), 8)
    target = {
        "enabled": target_monitoring,
        "label": MONITORING_LABEL,
        "metrics_present": target_monitoring,
        "metrics": {"macro_f1": target_f1} if target_monitoring else {},
    }
    return {
        "stage": stage,
        "epoch": epoch,
        "global_step": epoch,
        "learning_rate": 0.001,
        "loss": {"total": total, "components": components},
        "source_metrics": {"macro_f1": source_f1, "accuracy": source_accuracy},
        "target_monitoring": target,
        "gradient_norm": round(_history_value(identity, epoch, "gradient_norm"), 8),
        "duration_seconds": 0.0,
        "real_data_run": False,
        "publication_metrics_present": False,
    }


def _history_payload(identity: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **_artifact_envelope(identity, "history", "phase17.history.v1"),
        "rows": rows,
        "history_hash": sha256_payload(rows),
    }


def _checkpoint_payload(identity: dict[str, Any], *, kind: str, epoch: int, best: float, history_position: int) -> dict[str, Any]:
    stage = "warm" if epoch <= identity["epochs"]["warm"] else "full"
    return {
        **_artifact_envelope(identity, "checkpoint_last" if kind == "last" else "checkpoint_best_source_validation_macro_f1", "phase17.checkpoint.v1"),
        "checkpoint_kind": kind,
        "epoch": epoch,
        "global_step": epoch,
        "stage": stage,
        "best_source_validation_macro_f1": best,
        "history_append_position": history_position,
        "model_state_dict": {},
        "optimizer_state_dict": {},
        "scheduler_state_dict": None,
        "amp_scaler_state_dict": None,
        "rng_state": {"seed": identity["seed"], "epoch": epoch},
        "loader_generator_state": {"source": identity["seed"], "target_adaptation": identity["seed"]},
        "target_checkpoint_selection_state": {},
        "contains_mri_data": False,
    }


def _refresh_artifact_index(run_dir: Path, identity: dict[str, Any], status: str) -> None:
    entries = []
    for name, role in _LIFECYCLE_FILES.items():
        path = run_dir / name
        if not path.exists():
            continue
        entries.append({
            "path": name,
            "role": role,
            "byte_size": path.stat().st_size,
            "content_hash": sha256_file(path),
            "schema_version": "phase17.artifact.v1",
        })
    payload = {
        **_artifact_envelope(identity, "artifact_index", "phase17.artifact-index.v1"),
        "status": status,
        "entries": entries,
        "target_adaptation_loader_role": "unlabeled_only",
        "target_evaluation_loader_role": "monitoring_only",
        "target_labels_in_adaptation": False,
    }
    atomic_json(run_dir / "artifact_index.json", payload)


def _write_initial_artifacts(run_dir: Path, identity: dict[str, Any], resolved: Any) -> None:
    config_payload = {
        **_artifact_envelope(identity, "resolved_configuration", "phase17.config.v1"),
        "method": {"base_method": "PADA-3DACB", "model_variant": resolved.model_variant.to_dict()},
        "resolved": resolved.to_dict(),
        "epochs": {"warm": resolved.epochs_warm, "full": resolved.epochs_full, "early_stopping": False, "checkpoint_metric": "source_validation_macro_f1"},
        "target_contract": {"target_adaptation_batch_keys": ["x", "subject_id", "subject_hash", "cohort"], "target_evaluation": "monitoring_only", "assignments_disjoint": True},
    }
    atomic_json(run_dir / "identity.json", _artifact_envelope(identity, "identity", "phase17.identity.v1"))
    atomic_json(run_dir / "config_resolved.json", config_payload)
    equivalence = {
        **build_equivalence_reference(identity["requested_name"]),
        "schema_version": "phase17.equivalence.v1",
        "phase": 17,
        "identity": copy.deepcopy(identity),
        "artifact_role": "equivalence_manifest_read_only",
        "immutable": True,
        "real_data_run": False,
        "publication_metrics_present": False,
    }
    atomic_json(run_dir / "equivalence_manifest.json", equivalence)
    with suppress(OSError):
        (run_dir / "equivalence_manifest.json").chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    atomic_json(
        run_dir / "reproducibility_metadata.json",
        {**_artifact_envelope(identity, "reproducibility_metadata", "phase17.reproducibility.v1"), "python": platform.python_version(), "platform": platform.platform(), "torch": torch.__version__, "device": "cpu"},
    )
    _refresh_artifact_index(run_dir, identity, "RUNNING")


def _advance_synthetic_lifecycle(
    run_dir: Path,
    identity: dict[str, Any],
    resolved: Any,
    *,
    interrupt_after: int | None,
    target_monitoring: bool,
) -> SyntheticLifecycleResult:
    total = resolved.epochs_warm + resolved.epochs_full
    history_path = run_dir / "training_history.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else _history_payload(identity, [])
    rows = list(history.get("rows", []))
    if len(rows) > total:
        raise SyntheticLifecycleError("hash_mismatch", "history contains more epochs than the resolved lifecycle")
    if interrupt_after is not None and (interrupt_after <= len(rows) or interrupt_after > total):
        raise SyntheticLifecycleError("invalid_interrupt", "interrupt_after must be in the remaining fixed epoch range")
    best_checkpoint = run_dir / "checkpoint_best_source_f1.pt"
    best = -1.0
    if best_checkpoint.exists():
        best = float(_read_checkpoint(best_checkpoint).get("best_source_validation_macro_f1", -1.0))
    stop = interrupt_after if interrupt_after is not None else total
    for epoch in range(len(rows) + 1, stop + 1):
        stage = "warm" if epoch <= resolved.epochs_warm else "full"
        row = _history_row(identity, resolved, epoch, stage, target_monitoring)
        rows.append(row)
        source_f1 = float(row["source_metrics"]["macro_f1"])
        if source_f1 > best:
            best = source_f1
            _atomic_checkpoint(best_checkpoint, _checkpoint_payload(identity, kind="best_source_validation_macro_f1", epoch=epoch, best=best, history_position=len(rows)))
        atomic_json(history_path, _history_payload(identity, rows))
        _atomic_checkpoint(run_dir / "checkpoint_last.pt", _checkpoint_payload(identity, kind="last", epoch=epoch, best=best, history_position=len(rows)))
        _refresh_artifact_index(run_dir, identity, "INTERRUPTED" if epoch < total else "COMPLETED")
    if len(rows) < total:
        return SyntheticLifecycleResult("INTERRUPTED", run_dir, identity["ablation_id"], identity["direction"], identity["seed"], identity["fold"], len(rows), total, interrupted=True)
    best_hash = sha256_file(best_checkpoint)
    source_records = []
    for index in range(2):
        source_records.append({
            **_artifact_envelope(identity, "source_validation_prediction", "phase17.prediction.v1"),
            "schema_version": "phase17.prediction.v1", "subject_id": f"synthetic-source-validation-{index}", "subject_hash": f"synthetic-source-validation-hash-{index}", "cohort": identity["direction"].split("_to_", 1)[0], "dataset_role": "source_validation", "target_labels_present": False, "target_label_usage": "not_applicable", "target_monitoring_label": None, "split_assignment_hash": identity["source_split_assignment_hash"], "checkpoint_hash": best_hash, "direction": identity["direction"], "method": "ablation", "model": identity["ablation_id"], "fold": identity["fold"], "seed": identity["seed"], "checkpoint_name": "checkpoint_best_source_f1.pt", "checkpoint_epoch": _read_checkpoint(best_checkpoint)["epoch"], "split": "source_validation", "experiment_hash": identity["resolved_config_hash"], "predicted_class_z": index % 3, "predicted_class_c": (index + 1) % 3,
        })
    target_records = []
    if target_monitoring:
        for index in range(2):
            target_records.append({
                **_artifact_envelope(identity, "target_monitoring_prediction", "phase17.prediction.v1"),
                "schema_version": "phase17.prediction.v1", "subject_id": f"synthetic-target-monitoring-{index}", "subject_hash": f"synthetic-target-monitoring-hash-{index}", "cohort": identity["direction"].split("_to_", 1)[1], "dataset_role": "target_evaluation", "target_labels_present": True, "target_label_usage": "monitoring_only", "target_monitoring_label": MONITORING_LABEL, "split_assignment_hash": identity["target_evaluation_assignment_hash"], "checkpoint_hash": best_hash, "direction": identity["direction"], "method": "ablation", "model": identity["ablation_id"], "fold": identity["fold"], "seed": identity["seed"], "checkpoint_name": "checkpoint_best_source_f1.pt", "checkpoint_epoch": _read_checkpoint(best_checkpoint)["epoch"], "split": "target_monitoring", "experiment_hash": identity["resolved_config_hash"], "predicted_class_z": (index + 2) % 3, "predicted_class_c": index % 3,
            })
    _atomic_jsonl(run_dir / "source_validation_predictions.jsonl", source_records)
    _atomic_jsonl(run_dir / "target_monitoring_predictions.jsonl", target_records)
    _atomic_jsonl(run_dir / "predictions.jsonl", [*source_records, *target_records])
    _refresh_artifact_index(run_dir, identity, "COMPLETED")
    return SyntheticLifecycleResult("COMPLETED", run_dir, identity["ablation_id"], identity["direction"], identity["seed"], identity["fold"], len(rows), total)


def _expected_lifecycle(
    config: AblationExperimentConfig,
    requested_name: str | None,
    direction: str | None,
    source_domain: str | None,
    target_domain: str | None,
    seed: int | None,
    fold: int | None,
) -> tuple[dict[str, Any], Any, Path]:
    name, selected_direction, selected_seed, selected_fold, plan = _lifecycle_selection(config, requested_name, direction, source_domain, target_domain, seed, fold)
    identity = _lifecycle_identity(plan, config)
    materialized_base = config.base_for_direction(selected_direction)
    materialized_base["assignments"] = copy.deepcopy(plan["assignments"])
    resolved = resolve_ablation_config(materialized_base, name)
    identity["epochs"] = {"warm": resolved.epochs_warm, "full": resolved.epochs_full}
    return identity, resolved, planned_run_path(config, plan["ablation_id"], selected_direction, selected_seed, selected_fold)


def validate_resume_identity(
    config: AblationExperimentConfig | str | Path | Mapping[str, Any],
    run_dir: str | Path | Mapping[str, Any] | None = None,
    *,
    requested_name: str | None = None,
    direction: str | None = None,
    source_domain: str | None = None,
    target_domain: str | None = None,
    seed: int | None = None,
    fold: int | None = None,
) -> ResumeIdentityResult:
    """Validate resume identity and file hashes without repairing or rewriting output."""
    mismatches: list[str] = []
    if isinstance(config, Mapping):
        expected = dict(config)
        actual = dict(run_dir) if isinstance(run_dir, Mapping) else expected
        for key in _LIFECYCLE_IDENTITY_FIELDS + ("hash_algorithm", "canonicalization_version", "loader_requirements"):
            if key in expected and actual.get(key) != expected[key]:
                mismatches.append(key)
        return ResumeIdentityResult(not mismatches, tuple(mismatches), actual)
    try:
        resolved_config = _lifecycle_config(config)
        expected, _, expected_dir = _expected_lifecycle(resolved_config, requested_name, direction, source_domain, target_domain, seed, fold)
        root = Path(run_dir) if run_dir is not None and not isinstance(run_dir, Mapping) else expected_dir
        identity_path = root / "identity.json"
        if not identity_path.exists():
            mismatches.append("identity.json")
            return ResumeIdentityResult(False, tuple(mismatches), None)
        identity_payload = json.loads(identity_path.read_text(encoding="utf-8"))
        actual = identity_payload.get("identity", {})
        for key, value in expected.items():
            if key in {"epochs"}:
                continue
            if actual.get(key) != value:
                mismatches.append(key)
        if actual.get("loader_requirements", {}).get("target_adaptation_batch_keys") != ["x", "subject_id", "subject_hash", "cohort"]:
            mismatches.append("loader_requirements")
        index_path = root / "artifact_index.json"
        if not index_path.exists():
            mismatches.append("artifact_index.json")
        else:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if index.get("target_labels_in_adaptation") is not False or index.get("real_data_run") is not False or index.get("publication_metrics_present") is not False:
                mismatches.append("artifact_index_contract")
            for entry in index.get("entries", []):
                artifact = root / str(entry.get("path", ""))
                if not artifact.exists() or sha256_file(artifact) != entry.get("content_hash"):
                    mismatches.append(f"artifact:{entry.get('path')}")
        equivalence = root / "equivalence_manifest.json"
        if not equivalence.exists():
            mismatches.append("equivalence_manifest.json")
        else:
            manifest = json.loads(equivalence.read_text(encoding="utf-8"))
            manifest_hash = manifest.get("equivalence_manifest_hash")
            unsigned = {
                key: value for key, value in manifest.items()
                if key not in {"equivalence_manifest_hash", "schema_version", "phase", "artifact_role", "immutable", "identity"}
            }
            if manifest_hash != sha256_payload(unsigned):
                mismatches.append("equivalence_manifest_hash")
        if (root / "target_adaptation_predictions.jsonl").exists() or (root / "predictions_target_adaptation.jsonl").exists():
            mismatches.append("target_adaptation_predictions")
        if (root / "checkpoint_last.pt").exists():
            checkpoint = _read_checkpoint(root / "checkpoint_last.pt")
            if checkpoint.get("identity") != actual or checkpoint.get("contains_mri_data") is not False or checkpoint.get("target_checkpoint_selection_state") != {}:
                mismatches.append("checkpoint_identity")
    except (AblationCLIError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        mismatches.append(getattr(exc, "reason", "resume_identity_mismatch"))
        actual = None
    return ResumeIdentityResult(not mismatches, tuple(dict.fromkeys(mismatches)), actual if isinstance(actual, dict) else None)


def run_synthetic_lifecycle(
    config: AblationExperimentConfig | str | Path,
    requested_name: str | None = None,
    *,
    candidate_id: str | None = None,
    ablation_id: str | None = None,
    output_root: str | Path | None = None,
    direction: str | None = None,
    source_domain: str | None = None,
    target_domain: str | None = None,
    seed: int | None = None,
    fold: int | None = None,
    interrupt_after: int | None = None,
    overwrite: bool = False,
    raise_on_interrupt: bool = False,
) -> SyntheticLifecycleResult:
    """Run one deterministic CPU-only synthetic fold; never loads MRI or trains a model."""
    lifecycle_config = _lifecycle_config(config)
    identity, resolved, run_dir = _expected_lifecycle(lifecycle_config, requested_name, direction, source_domain, target_domain, seed, fold)
    validate_target_adaptation_batch({"x": "synthetic", "subject_id": "synthetic-target", "subject_hash": "synthetic-target-hash", "cohort": identity["direction"].split("_to_", 1)[1]})
    if run_dir.exists():
        validation = validate_resume_identity(lifecycle_config, run_dir, requested_name=identity["requested_name"], direction=identity["direction"], seed=identity["seed"], fold=identity["fold"])
        if not validation.valid:
            raise SyntheticLifecycleError("resume_identity_mismatch", f"existing output identity mismatch: {', '.join(validation.mismatches)}")
        status = "COMPLETED" if (run_dir / "predictions.jsonl").exists() else "INTERRUPTED"
        if not overwrite:
            if status == "COMPLETED":
                total = resolved.epochs_warm + resolved.epochs_full
                return SyntheticLifecycleResult(status, run_dir, identity["ablation_id"], identity["direction"], identity["seed"], identity["fold"], total, total, reused=True)
            raise SyntheticLifecycleError("resume_required", "matching interrupted output must use resume_synthetic_lifecycle")
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_initial_artifacts(run_dir, identity, resolved)
    result = _advance_synthetic_lifecycle(
        run_dir,
        identity,
        resolved,
        interrupt_after=interrupt_after,
        target_monitoring=lifecycle_config.target_monitoring,
    )
    if result.interrupted and raise_on_interrupt:
        raise SyntheticLifecycleInterrupted("interrupted", f"synthetic lifecycle interrupted after {result.completed_epochs} epochs")
    return result


def resume_synthetic_lifecycle(
    config: AblationExperimentConfig | str | Path,
    run_dir: str | Path | None = None,
    requested_name: str | None = None,
    *,
    candidate_id: str | None = None,
    ablation_id: str | None = None,
    direction: str | None = None,
    source_domain: str | None = None,
    target_domain: str | None = None,
    seed: int | None = None,
    fold: int | None = None,
    interrupt_after: int | None = None,
) -> SyntheticLifecycleResult:
    """Resume one matching interrupted synthetic fold without rewriting immutable identity."""
    lifecycle_config = _lifecycle_config(config)
    identity, resolved, expected_dir = _expected_lifecycle(lifecycle_config, requested_name, direction, source_domain, target_domain, seed, fold)
    root = Path(run_dir) if run_dir is not None else expected_dir
    validation = validate_resume_identity(lifecycle_config, root, requested_name=identity["requested_name"], direction=identity["direction"], seed=identity["seed"], fold=identity["fold"])
    if not validation.valid:
        raise SyntheticLifecycleError("resume_identity_mismatch", f"resume identity mismatch: {', '.join(validation.mismatches)}")
    if (root / "predictions.jsonl").exists():
        total = resolved.epochs_warm + resolved.epochs_full
        return SyntheticLifecycleResult("COMPLETED", root, identity["ablation_id"], identity["direction"], identity["seed"], identity["fold"], total, total, reused=True)
    return _advance_synthetic_lifecycle(
        root,
        identity,
        resolved,
        interrupt_after=interrupt_after,
        target_monitoring=lifecycle_config.target_monitoring,
    )


def _model_kwargs(config: AblationExperimentConfig) -> dict[str, Any]:
    model = config.model
    encoder = dict(model.get("encoder") or {})
    tokenizer = dict(model.get("tokenizer") or {})
    token_processing = dict(model.get("token_processing") or {})
    concept = dict(model.get("concept_bottleneck") or {})
    return {
        "num_rois": int(model.get("num_rois", 3)),
        "feature_dim": int(tokenizer.get("feature_dim", encoder.get("output_channels", 8))),
        "token_dim": int(tokenizer.get("token_dim", 6)),
        "num_classes": int(model.get("num_classes", 3)),
        "base_channels": int(encoder.get("base_channels", 2)),
        "concept_hidden_dim": int(concept.get("hidden_dim", 4)),
        "token_dropout": float(token_processing.get("dropout", 0.0)),
        "concept_dropout": float(concept.get("dropout", 0.0)),
    }


def _synthetic_loaders(config: AblationExperimentConfig, seed: int) -> tuple[DataLoader, DataLoader]:
    generator = torch.Generator().manual_seed(seed)
    kwargs = _model_kwargs(config)
    shape = (2, 1, 16, 16, 16)
    source_x = torch.randn(shape, generator=generator)
    target_x = torch.randn(shape, generator=generator)
    num_rois = kwargs["num_rois"]
    source = [
        {
            "x": source_x[index],
            "y": torch.tensor(index % kwargs["num_classes"], dtype=torch.long),
            "c_target": torch.full((num_rois,), 0.5, dtype=torch.float32),
            "g_bar": torch.full((num_rois,), 0.25, dtype=torch.float32),
        }
        for index in range(2)
    ]
    target = [
        {
            "x": target_x[index],
            "subject_id": f"synthetic-target-{index}",
            "subject_hash": f"synthetic-target-hash-{index}",
            "cohort": "OASIS",
        }
        for index in range(2)
    ]
    return DataLoader(source, batch_size=2, shuffle=False), DataLoader(target, batch_size=2, shuffle=False)


def _validate_synthetic(
    config: AblationExperimentConfig,
    requested_name: str,
    direction: str,
    seed: int,
    fold: int,
) -> dict[str, Any]:
    seed_everything(seed)
    resolved = resolve_ablation_config(config.base_for_direction(direction), requested_name)
    kwargs = _model_kwargs(config)
    task_id = config.payload.get("task_id", config.base.get("task_id"))
    binary_task = isinstance(task_id, str) and task_id.strip().lower() == "cn_vs_impaired"
    binary_plan = binary_ablation_plan(resolved.candidate_id) if binary_task else None
    if resolved.candidate_id == "mean_pool":
        model = build_mean_pool_model(**kwargs)
    else:
        model = build_pada3dacb({**config.model, "contextual_encoder": False})
    model.eval()
    input_shape = (16, 16, 16)
    num_rois = int(kwargs["num_rois"])
    masks = torch.zeros((num_rois, 2, 2, 2), dtype=torch.float32)
    for index in range(num_rois):
        masks[index].flatten()[index % masks[index].numel()] = 1.0
    feature_shape = model.encoder.infer_output_shape((1, 1, *input_shape))[2:]
    feature_masks = prepare_feature_grid_roi_masks(masks, feature_shape)
    source_loader, target_loader = _synthetic_loaders(config, seed)
    source_batch = next(iter(source_loader))
    target_batch = next(iter(target_loader))
    validate_target_adaptation_batch(target_batch)
    before = {name: value.detach().clone() for name, value in model.state_dict().items()}
    with torch.no_grad():
        source_output = model(source_batch["x"], feature_masks)
        target_output = model(target_batch["x"], feature_masks)
        base_core = CorePADA3DACBLoss(
            num_rois, label_smoothing=resolved.losses.label_smoothing
        )
        core = (
            base_core
            if resolved.candidate_id in {"mean_pool", "no_da"}
            else ComposedCoreLoss(base_core, resolved, binary_plan=binary_plan)
        )
        core_output = core(
            source_output,
            source_batch["y"],
            source_batch["c_target"],
            source_batch["g_bar"],
            stage="full",
        )
        adaptation_configuration = resolved.adaptation_configuration
        kernel = adaptation_configuration["kernel"]
        assert isinstance(kernel, dict)
        adaptation_method = MMDAdaptationMethod(kernel["bandwidths"])
        adaptation = adaptation_method.compute(source_output, target_output, "full")
        weighted_adaptation = resolved.adaptation_weight * adaptation.total
        objective = core_output.total + weighted_adaptation
    if not torch.isfinite(objective):
        raise AblationCLIError("validation_failed", "resolved synthetic objective is non-finite")
    if any(not torch.equal(before[name], value) for name, value in model.state_dict().items()):
        raise AblationCLIError("validation_failed", "validate-only changed model state")
    disabled = {
        "no_cons": "L_cons",
        "no_concept": "L_concept",
        "no_anat": "L_anat",
    }
    if resolved.candidate_id in disabled:
        term = disabled[resolved.candidate_id]
        if core_output.component_diagnostics[f"{term}_active"] is not False:
            raise AblationCLIError("validation_failed", f"disabled component {term} remained active")
    return {
        "validated": True,
        "forward_executed": True,
        "backward_executed": False,
        "optimizer_step_executed": False,
        "target_batch_keys": sorted(target_batch),
        "target_labels_in_adaptation": False,
        "resolved_objective": float(objective.detach().cpu()),
        "adaptation_method": adaptation_method.name,
        "adaptation_weight": resolved.adaptation_weight,
        "mmd_loss": float(adaptation.total.detach().cpu()),
        "raw_mmd_loss": float(adaptation.total.detach().cpu()),
        "weighted_mmd_loss": float(weighted_adaptation.detach().cpu()),
        "weighted_raw_mmd_loss": float(weighted_adaptation.detach().cpu()),
        "target_forward_executed": True,
        "mmd_diagnostics": adaptation.detached(),
        "model_variant": resolved.model_variant.name,
        "feature_shape": list(feature_shape),
        "target_monitoring_enabled": config.target_monitoring,
        "target_monitoring_label": MONITORING_LABEL,
    }


def execute(
    config: AblationExperimentConfig,
    *,
    requested_names: tuple[str, ...],
    source_domain: str | None = None,
    target_domain: str | None = None,
    fold: int | None = None,
    all_folds: bool = False,
    seed: int | None = None,
    all_seeds: bool = False,
    both_directions: bool = False,
    dry_run: bool = False,
    validate_only: bool = False,
    target_monitoring: bool | None = None,
) -> dict[str, Any]:
    if dry_run and validate_only:
        raise AblationCLIError("ambiguous_mode", "use either --dry-run or --validate-only")
    if target_monitoring is not None:
        config = copy.copy(config)
        object.__setattr__(config, "target_monitoring", target_monitoring)
    if both_directions:
        directions = tuple(config.directions)
    else:
        directions = config.direction_for(source_domain, target_domain)
    if fold is not None and all_folds:
        raise AblationCLIError("ambiguous_selection", "use either --fold or --all-folds")
    folds = config.folds if all_folds else ((fold,) if fold is not None else config.folds[:1])
    if any(value not in config.folds for value in folds):
        raise AblationCLIError("incomplete_matrix", "requested fold is absent from the complete matrix")
    seeds = config.seeds if all_seeds else ((seed,) if seed is not None else config.seeds[:1])
    if any(value not in config.seeds for value in seeds):
        raise AblationCLIError("incomplete_matrix", "requested seed is absent from the complete matrix")
    plans: list[dict[str, Any]] = []
    for name in requested_names:
        for direction in directions:
            for selected_seed in seeds:
                for selected_fold in folds:
                    plan = _plan(config, name, direction, selected_seed, selected_fold)
                    if validate_only:
                        plan.update(_validate_synthetic(config, name, direction, selected_seed, selected_fold))
                    plans.append(plan)
    mode = "dry-run" if dry_run else "validate-only" if validate_only else "real"
    if not dry_run and not validate_only:
        raise AblationCLIError(
            "real_run_not_authorized",
            "Phase 17 permits synthetic dry-run and validate-only only; real ADNI/OASIS execution requires separate authorization",
        )
    return {
        "phase": 17,
        "mode": mode,
        "method": "ablation",
        "base_method": "prototype_pseudo",
        "approved_ids": list(requested_names),
        "blocked_ids": list(_blocked_ids()),
        "plans": plans,
        "real_data_run": False,
        "publication_metrics_present": False,
        "target_monitoring_label": MONITORING_LABEL,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--ablation")
    selection.add_argument("--all-approved-ablations", action="store_true")
    parser.add_argument("--source-domain", choices=SUPPORTED_DOMAINS)
    parser.add_argument("--target-domain", choices=SUPPORTED_DOMAINS)
    parser.add_argument("--fold", type=int)
    parser.add_argument("--all-folds", action="store_true")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--all-seeds", action="store_true")
    parser.add_argument("--both-directions", action="store_true")
    for name in ("artifact-index", "artifact-root", "split-root", "roi-masks", "atlas-metadata", "output-root", "resume-from"):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    monitoring = parser.add_mutually_exclusive_group()
    monitoring.add_argument("--target-monitoring", action="store_true", dest="target_monitoring")
    monitoring.add_argument("--no-target-monitoring", action="store_false", dest="target_monitoring")
    parser.set_defaults(target_monitoring=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_ablation_config(args.config, output_root=args.output_root)
        if args.source_domain is not None and args.target_domain is None:
            raise AblationCLIError("invalid_direction", "--source-domain and --target-domain must be supplied together")
        if args.target_domain is not None and args.source_domain is None:
            raise AblationCLIError("invalid_direction", "--source-domain and --target-domain must be supplied together")
        names = _requested_candidates(args.ablation, args.all_approved_ablations)
        configured_id = config.payload.get("ablation_id")
        if configured_id is None:
            configured_id = (config.payload.get("experiment") or {}).get("ablation_id")
        if configured_id and len(names) == 1 and names[0] != configured_id:
            raise AblationCLIError("config_candidate_mismatch", f"config is bound to ablation {configured_id!r}")
        payload = execute(
            config,
            requested_names=names,
            source_domain=args.source_domain,
            target_domain=args.target_domain,
            fold=args.fold,
            all_folds=args.all_folds,
            seed=args.seed,
            all_seeds=args.all_seeds,
            both_directions=args.both_directions,
            dry_run=args.dry_run,
            validate_only=args.validate_only,
            target_monitoring=args.target_monitoring,
        )
    except (AblationCLIError, AblationResolutionError, ExperimentValidationError, ValueError) as exc:
        reason = getattr(exc, "reason", "invalid_request")
        print(json.dumps({"status": "blocked", "reason": reason, "message": str(exc)}), file=__import__("sys").stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def validate_task_scoped_binary_ablation(
    candidate: str, config_path: str | Path = "configs/publication/phase18b_binary.yaml"
) -> dict[str, Any]:
    """Validate one approved binary ablation without entering the Phase 17 lifecycle."""
    from pada3dacb.publication.binary_runtime import BinaryPublicationRuntime

    return BinaryPublicationRuntime.from_path(config_path).validate_ablation(candidate)


def validate_task_scoped_binary_ablations(
    config_path: str | Path = "configs/publication/phase18b_binary.yaml",
) -> dict[str, dict[str, Any]]:
    """Validate all six approved binary ablations on synthetic CPU tensors only."""
    from pada3dacb.publication.binary_runtime import BinaryPublicationRuntime

    return BinaryPublicationRuntime.from_path(config_path).validate_all_ablations()
