"""Typed output contracts for future Phase 17 lifecycle artifacts.

This module validates metadata only. It does not train, checkpoint, or write data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from .schemas import IdentityEnvelope, validate_sha256

OutputIdentity = IdentityEnvelope


class CheckpointKind(str, Enum):
    LAST = "last"
    BEST_SOURCE_VALIDATION_MACRO_F1 = "best_source_validation_macro_f1"
    EPOCH = "epoch"


class TrainingStage(str, Enum):
    WARM = "warm"
    FULL = "full"


class DatasetRole(str, Enum):
    SOURCE_TRAIN = "source_train"
    SOURCE_VALIDATION = "source_validation"
    TARGET_ADAPTATION = "target_adaptation"
    TARGET_EVALUATION = "target_evaluation"


@dataclass(frozen=True)
class CheckpointManifest:
    identity: OutputIdentity
    checkpoint_kind: CheckpointKind
    epoch: int
    global_step: int
    stage: TrainingStage
    best_source_validation_macro_f1: float
    history_append_position: int
    contains_mri_data: bool = False
    target_checkpoint_selection_state_empty: bool = True
    model_state_present: bool = True
    optimizer_state_present: bool = True
    scheduler_state_present: bool = False
    amp_scaler_state_present: bool = False
    rng_state_present: bool = True
    loader_generator_state_present: bool = True
    schema_version: ClassVar[str] = "phase17.checkpoint.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint_kind, CheckpointKind):
            raise ValueError("checkpoint_kind must be a typed CheckpointKind")
        if not isinstance(self.stage, TrainingStage):
            raise ValueError("checkpoint.stage must be a typed TrainingStage")
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("checkpoint epoch must be non-negative")
        if not isinstance(self.global_step, int) or isinstance(self.global_step, bool) or self.global_step < 0:
            raise ValueError("checkpoint global_step must be non-negative")
        if (
            not isinstance(self.history_append_position, int)
            or isinstance(self.history_append_position, bool)
            or self.history_append_position < 0
        ):
            raise ValueError("history_append_position must be non-negative")
        if self.contains_mri_data:
            raise ValueError("checkpoints must not contain MRI data")
        if not self.target_checkpoint_selection_state_empty:
            raise ValueError("target metrics cannot participate in checkpoint selection")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "checkpoint_kind": self.checkpoint_kind.value,
            "epoch": self.epoch,
            "global_step": self.global_step,
            "stage": self.stage.value,
            "best_source_validation_macro_f1": self.best_source_validation_macro_f1,
            "history_append_position": self.history_append_position,
            "contains_mri_data": self.contains_mri_data,
            "target_checkpoint_selection_state": {},
            "model_state_present": self.model_state_present,
            "optimizer_state_present": self.optimizer_state_present,
            "scheduler_state_present": self.scheduler_state_present,
            "amp_scaler_state_present": self.amp_scaler_state_present,
            "rng_state_present": self.rng_state_present,
            "loader_generator_state_present": self.loader_generator_state_present,
        }


@dataclass(frozen=True)
class LossComponentRecord:
    name: str
    active: bool
    raw: float
    weighted: float

    def __post_init__(self) -> None:
        if self.name not in {"L_cls_z", "L_cls_c", "L_cons", "L_concept", "L_anat", "L_proto", "L_pl"}:
            raise ValueError(f"unknown loss component: {self.name}")
        if not isinstance(self.active, bool):
            raise ValueError("loss component active must be boolean")

    def to_dict(self) -> dict[str, object]:
        return {"active": self.active, "raw": self.raw, "weighted": self.weighted}


@dataclass(frozen=True)
class TargetMonitoring:
    enabled: bool
    metrics_present: bool = False
    label: str = "MONITORING ONLY — NOT A TRAINING LOSS"

    def __post_init__(self) -> None:
        if self.label != "MONITORING ONLY — NOT A TRAINING LOSS":
            raise ValueError("target monitoring must carry the exact monitoring-only label")
        if not self.enabled and self.metrics_present:
            raise ValueError("disabled target monitoring cannot contain metrics")

    def to_dict(self) -> dict[str, object]:
        return {"enabled": self.enabled, "label": self.label, "metrics_present": self.metrics_present}


@dataclass(frozen=True)
class HistoryRow:
    stage: TrainingStage
    epoch: int
    global_step: int
    learning_rate: float
    total_loss: float
    components: tuple[LossComponentRecord, ...]
    source_macro_f1: float
    source_accuracy: float
    target_monitoring: TargetMonitoring
    gradient_norm: float
    duration_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.stage, TrainingStage):
            raise ValueError("history.stage must be typed")
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("history.epoch must be non-negative")
        if not isinstance(self.global_step, int) or isinstance(self.global_step, bool) or self.global_step < 0:
            raise ValueError("history.global_step must be non-negative")
        names = tuple(item.name for item in self.components)
        expected = ("L_cls_z", "L_cls_c", "L_cons", "L_concept", "L_anat", "L_proto", "L_pl")
        if names != expected:
            raise ValueError("history rows must contain every canonical loss component in order")
        for value_name in ("learning_rate", "total_loss", "source_macro_f1", "source_accuracy", "gradient_norm", "duration_seconds"):
            value = getattr(self, value_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"history.{value_name} must be numeric")

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "epoch": self.epoch,
            "global_step": self.global_step,
            "learning_rate": self.learning_rate,
            "loss": {
                "total": self.total_loss,
                "components": {item.name: item.to_dict() for item in self.components},
            },
            "source_metrics": {"macro_f1": self.source_macro_f1, "accuracy": self.source_accuracy},
            "target_monitoring": self.target_monitoring.to_dict(),
            "gradient_norm": self.gradient_norm,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class HistoryManifest:
    identity: OutputIdentity
    rows: tuple[HistoryRow, ...]
    history_hash: str
    schema_version: ClassVar[str] = "phase17.history.v1"

    def __post_init__(self) -> None:
        validate_sha256(self.history_hash, "history_hash")

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "identity": self.identity.to_dict(), "rows": tuple(row.to_dict() for row in self.rows), "history_hash": self.history_hash}


@dataclass(frozen=True)
class PredictionRecord:
    identity: OutputIdentity
    subject_id: str
    dataset_role: DatasetRole
    target_labels_present: bool
    target_label_usage: str
    split_assignment_hash: str
    checkpoint_hash: str
    predicted_class_z: int
    predicted_class_c: int
    logits_z: tuple[float, ...]
    logits_c: tuple[float, ...]
    target_monitoring_label: str | None = None
    schema_version: ClassVar[str] = "phase17.prediction.v1"

    def __post_init__(self) -> None:
        if not self.subject_id.strip():
            raise ValueError("prediction.subject_id must be non-empty")
        if not isinstance(self.dataset_role, DatasetRole):
            raise ValueError("prediction.dataset_role must be typed")
        validate_sha256(self.split_assignment_hash, "prediction.split_assignment_hash")
        validate_sha256(self.checkpoint_hash, "prediction.checkpoint_hash")
        if self.dataset_role is DatasetRole.TARGET_ADAPTATION and (
            self.target_labels_present
            or self.target_label_usage != "forbidden"
            or self.target_monitoring_label is not None
        ):
            raise ValueError("target adaptation predictions must not contain target labels")
        if self.dataset_role is DatasetRole.TARGET_EVALUATION and (
            not self.target_labels_present or self.target_label_usage != "monitoring_only"
        ):
            raise ValueError("target evaluation labels must be monitoring_only")
        if self.target_label_usage not in {"forbidden", "monitoring_only", "not_applicable"}:
            raise ValueError("prediction.target_label_usage is not a supported role")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "subject_id": self.subject_id,
            "dataset_role": self.dataset_role.value,
            "target_labels_present": self.target_labels_present,
            "target_label_usage": self.target_label_usage,
            "split_assignment_hash": self.split_assignment_hash,
            "checkpoint_hash": self.checkpoint_hash,
            "logits_z": self.logits_z,
            "logits_c": self.logits_c,
            "predicted_class_z": self.predicted_class_z,
            "predicted_class_c": self.predicted_class_c,
            "target_monitoring_label": self.target_monitoring_label,
        }


@dataclass(frozen=True)
class SourceOnlyProof:
    target_loader_constructed: bool
    target_loader_forwarded: bool
    target_loss_or_gradient: bool
    source_only_method_identity: bool
    status: str = "blocked"

    def __post_init__(self) -> None:
        if self.status not in {"blocked", "proven"}:
            raise ValueError("source-only proof status must be blocked or proven")


@dataclass(frozen=True)
class EquivalenceManifest:
    requested_name: str
    canonical_id: str | None
    classification: str
    disposition: str
    blocked_reason: str | None
    source_only_proof: SourceOnlyProof | None
    equivalence_manifest_hash: str
    schema_version: ClassVar[str] = "phase17.equivalence.v1"

    def __post_init__(self) -> None:
        validate_sha256(self.equivalence_manifest_hash, "equivalence_manifest_hash")
        if self.disposition == "BLOCKED_NOT_PROVEN" and not self.blocked_reason:
            raise ValueError("blocked equivalence manifests require a reason")

    def to_dict(self) -> dict[str, object]:
        proof = None if self.source_only_proof is None else {
            "target_loader_constructed": self.source_only_proof.target_loader_constructed,
            "target_loader_forwarded": self.source_only_proof.target_loader_forwarded,
            "target_loss_or_gradient": self.source_only_proof.target_loss_or_gradient,
            "source_only_method_identity": self.source_only_proof.source_only_method_identity,
            "status": self.source_only_proof.status,
        }
        return {
            "schema_version": self.schema_version,
            "requested_name": self.requested_name,
            "canonical_id": self.canonical_id,
            "classification": self.classification,
            "disposition": self.disposition,
            "blocked_reason": self.blocked_reason,
            "source_only_proof": proof,
            "equivalence_manifest_hash": self.equivalence_manifest_hash,
        }


@dataclass(frozen=True)
class ArtifactIndexEntry:
    path: str
    role: str
    byte_size: int
    content_hash: str
    schema_version: str

    def __post_init__(self) -> None:
        if not self.path or not self.role or self.byte_size < 0:
            raise ValueError("artifact index path, role, and byte_size are invalid")
        validate_sha256(self.content_hash, "artifact.content_hash")


@dataclass(frozen=True)
class ArtifactIndex:
    identity: OutputIdentity
    entries: tuple[ArtifactIndexEntry, ...]
    target_adaptation_loader_role: str = "unlabeled_only"
    target_evaluation_loader_role: str = "monitoring_only"
    target_labels_in_adaptation: bool = False
    publication_metrics_present: bool = False
    real_data_run: bool = False
    schema_version: ClassVar[str] = "phase17.artifact-index.v1"

    def __post_init__(self) -> None:
        if self.target_adaptation_loader_role != "unlabeled_only" or self.target_evaluation_loader_role != "monitoring_only":
            raise ValueError("target loader roles violate the Phase 17 firewall")
        if self.target_labels_in_adaptation or self.publication_metrics_present or self.real_data_run:
            raise ValueError("synthetic/blocked output index contains forbidden evidence")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "entries": tuple(
                {
                    "path": entry.path,
                    "role": entry.role,
                    "byte_size": entry.byte_size,
                    "content_hash": entry.content_hash,
                    "schema_version": entry.schema_version,
                }
                for entry in self.entries
            ),
            "target_adaptation_loader_role": self.target_adaptation_loader_role,
            "target_evaluation_loader_role": self.target_evaluation_loader_role,
            "target_labels_in_adaptation": self.target_labels_in_adaptation,
            "publication_metrics_present": self.publication_metrics_present,
            "real_data_run": self.real_data_run,
        }
