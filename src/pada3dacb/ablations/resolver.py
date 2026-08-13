"""Pure, deterministic resolution of approved Phase 17 ablations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .registry import alias_target, get_ablation_spec, is_unresolved_name, registry_hash
from .schemas import (
    FORBIDDEN_TARGET_FIELDS,
    TARGET_ADAPTATION_FIELDS,
    AblationBaseConfig,
    AblationSpec,
    ApprovalRecord,
    ApprovalStatus,
    AssignmentManifest,
    CandidateClassification,
    Intervention,
    LossCoefficients,
    ModelVariant,
    RunMatrix,
    sha256_payload,
)


class AblationResolutionError(ValueError):
    """Structured fail-closed error emitted before data loading or training."""

    def __init__(self, reason: str, message: str, *, candidate: str | None = None, field: str | None = None, remediation: str | None = None) -> None:
        self.reason = reason
        self.candidate = candidate
        self.field = field
        self.remediation = remediation
        detail = message
        if field:
            detail = f"{detail} (field={field})"
        if remediation:
            detail = f"{detail}; remediation: {remediation}"
        super().__init__(detail)


@dataclass(frozen=True)
class ResolvedAblationConfig:
    requested_name: str
    candidate_id: str
    candidate_classification: CandidateClassification
    approval: ApprovalRecord
    base_method: str
    losses: LossCoefficients
    model_variant: ModelVariant
    intervention: Intervention
    matrix: RunMatrix
    assignments: AssignmentManifest
    epochs_warm: int
    epochs_full: int
    precomputed_artifacts: tuple[str, ...]
    registry_hash: str
    candidate_hash: str
    resolved_config_hash: str
    model_variant_hash: str
    source_split_assignment_hash: str
    target_adaptation_assignment_hash: str
    target_evaluation_assignment_hash: str
    precomputed_artifacts_hash: str
    alias_mapping: str | None = None

    def __post_init__(self) -> None:
        if self.requested_name == self.candidate_id and self.alias_mapping is not None:
            raise ValueError("exact requests cannot carry an alias mapping")
        if self.candidate_classification is not CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED:
            raise ValueError("only approved canonical candidates can be resolved")

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_name": self.requested_name,
            "candidate_id": self.candidate_id,
            "candidate_classification": self.candidate_classification.value,
            "candidate_approval_id": self.approval.approval_id,
            "alias_mapping": self.alias_mapping,
            "base_method": self.base_method,
            "losses": self.losses.to_dict(),
            "model_variant": self.model_variant.to_dict(),
            "intervention": self.intervention.to_dict(),
            "matrix": self.matrix.to_dict(),
            "assignments": self.assignments.to_dict(),
            "epochs": {"warm": self.epochs_warm, "full": self.epochs_full},
            "precomputed_artifacts": self.precomputed_artifacts,
            "registry_hash": self.registry_hash,
            "candidate_hash": self.candidate_hash,
            "resolved_config_hash": self.resolved_config_hash,
            "model_variant_hash": self.model_variant_hash,
            "source_split_assignment_hash": self.source_split_assignment_hash,
            "target_adaptation_assignment_hash": self.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": self.target_evaluation_assignment_hash,
            "precomputed_artifacts_hash": self.precomputed_artifacts_hash,
            "hash_algorithm": "sha256",
            "canonicalization_version": "phase17.canonical-json.v1",
        }

    def sha256(self) -> str:
        return sha256_payload(self.to_dict())


def _error(reason: str, message: str, candidate: str | None, *, field: str | None = None, remediation: str | None = None) -> AblationResolutionError:
    return AblationResolutionError(reason, message, candidate=candidate, field=field, remediation=remediation)


def _validate_target_batch_mapping(batch: object, candidate: str | None) -> tuple[str, ...]:
    if not isinstance(batch, Mapping):
        raise _error(
            "target_label_firewall_violation",
            "target adaptation batch must be a mapping with exactly the four allowed fields",
            candidate,
            field="target_adaptation_batch",
            remediation="pass x, subject_id, subject_hash, and cohort without supervision or artifacts",
        )
    keys = tuple(batch)
    allowed = set(TARGET_ADAPTATION_FIELDS)
    missing = sorted(allowed - set(keys))
    extra = sorted((key for key in keys if key not in allowed), key=repr)
    if missing or extra:
        forbidden = sorted((key for key in keys if key in FORBIDDEN_TARGET_FIELDS), key=repr)
        detail = (
            "target adaptation batch must contain exactly the four allowed fields "
            f"{TARGET_ADAPTATION_FIELDS!r}; missing={missing!r}, extra={extra!r}"
        )
        if forbidden:
            detail += f"; forbidden={forbidden!r}"
        raise _error(
            "target_label_firewall_violation",
            detail,
            candidate,
            field="target_adaptation_batch",
            remediation="remove supervision and artifact fields; provide all four unlabeled fields",
        )
    return TARGET_ADAPTATION_FIELDS


def _parse_model(value: object) -> ModelVariant:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise ValueError("model must be a typed mapping")
    name = value.get("name", "PADA-3DACB")
    aggregator = value.get("aggregator", "AttentionAggregator")
    if isinstance(value.get("contextual_encoder"), bool) and value.get("contextual_encoder") is False:
        contextual = None
    else:
        contextual = value.get("contextual_encoder")
    components = value.get("architecture_components")
    if components is None:
        components = ModelVariant(name="PADA-3DACB", aggregator="AttentionAggregator").architecture_components
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        raise ValueError("model.architecture_components must be a sequence")
    return ModelVariant(
        name=str(name),
        aggregator=str(aggregator),
        architecture_components=tuple(str(item) for item in components),
        contextual_encoder=contextual,
        runtime_variant_switch=bool(value.get("runtime_variant_switch", False)),
    )


def _parse_approval(value: object) -> ApprovalRecord:
    if not isinstance(value, Mapping):
        raise ValueError("approval must be an explicit mapping")
    status = value.get("status")
    try:
        status = status if isinstance(status, ApprovalStatus) else ApprovalStatus(str(status))
    except ValueError as exc:
        raise ValueError("approval.status must be approved, unapproved, or not_applicable") from exc
    return ApprovalRecord(
        approval_id=str(value.get("approval_id", "")),
        status=status,
        scope=str(value.get("scope", "synthetic_only")),
        approved_by=str(value.get("approved_by", "maintainer")),
    )


def _parse_epochs(data: Mapping[str, object]) -> tuple[int, int]:
    value = data.get("epochs")
    if not isinstance(value, Mapping):
        training = data.get("training")
        if isinstance(training, Mapping):
            value = {
                "warm": training.get("warm", training.get("warmup_epochs")),
                "full": training.get("full", training.get("full_epochs")),
            }
    if not isinstance(value, Mapping) or "warm" not in value or "full" not in value:
        raise ValueError("explicit warm and full epoch counts are required")
    warm, full = value["warm"], value["full"]
    if isinstance(warm, bool) or not isinstance(warm, int) or warm < 0:
        raise ValueError("epochs.warm must be a non-negative integer")
    if isinstance(full, bool) or not isinstance(full, int) or full <= 0:
        raise ValueError("epochs.full must be a positive integer")
    return warm, full


def _coerce_base_config(data: AblationBaseConfig | Mapping[str, object], candidate: str) -> AblationBaseConfig:
    if isinstance(data, AblationBaseConfig):
        return data
    if not isinstance(data, Mapping):
        raise _error("unapproved_override", "base configuration must be a typed config or mapping", candidate)
    try:
        losses_value = data.get("losses", data.get("loss_coefficients"))
        if not isinstance(losses_value, Mapping):
            raise ValueError("canonical losses mapping is required")
        model = _parse_model(data.get("model"))
        approval = _parse_approval(data.get("approval"))
        epochs_warm, epochs_full = _parse_epochs(data)
        matrix_value = data.get("matrix")
        if not isinstance(matrix_value, Mapping):
            raise ValueError("complete matrix is required")
        matrix = RunMatrix.from_mapping(matrix_value)
        assignments_value = data.get("assignments")
        if not isinstance(assignments_value, Mapping):
            raise ValueError("source, target adaptation, and target evaluation assignments are required")
        assignments = AssignmentManifest.from_mapping(assignments_value)
        artifacts_value = data.get("precomputed_artifacts")
        if isinstance(artifacts_value, Mapping):
            artifacts = tuple(f"{key}={artifacts_value[key]}" for key in sorted(artifacts_value))
        elif isinstance(artifacts_value, Sequence) and not isinstance(artifacts_value, (str, bytes)):
            artifacts = tuple(str(item) for item in artifacts_value)
        else:
            raise ValueError("immutable precomputed_artifacts are required")
        batch = data.get("target_adaptation_batch")
        if batch is None:
            target_keys = TARGET_ADAPTATION_FIELDS
        else:
            target_keys = _validate_target_batch_mapping(batch, candidate)
        return AblationBaseConfig(
            base_method=str(data.get("base_method", "")),
            losses=LossCoefficients.from_mapping(losses_value),
            model=model,
            approval=approval,
            epochs_warm=epochs_warm,
            epochs_full=epochs_full,
            matrix=matrix,
            assignments=assignments,
            precomputed_artifacts=artifacts,
            target_adaptation_keys=target_keys,
            real_data_run=bool(
                data.get("real_data_run", data.get("real_data", False))
                or data.get("mode") in {"real", "real_data"}
                or data.get("run_mode") in {"real", "real_data"}
            ),
            publication_metrics=bool(
                data.get("publication_metrics", data.get("publication", False))
                or data.get("mode") == "publication"
                or data.get("evaluation_mode") == "publication"
            ),
        )
    except AblationResolutionError:
        raise
    except ValueError as exc:
        text = str(exc)
        if "overlap" in text:
            raise _error("overlapping_target_assignments", text, candidate) from exc
        if "approval" in text:
            raise _error("candidate_not_approved", text, candidate, remediation="provide the explicit synthetic-only maintainer approval") from exc
        if "matrix" in text or "epoch" in text or "assignment" in text:
            raise _error("incomplete_matrix", text, candidate, remediation="provide the complete direction/fold/seed matrix and disjoint assignments") from exc
        if "target adaptation" in text:
            raise _error("target_label_firewall_violation", text, candidate) from exc
        if "real data" in text or "publication" in text:
            raise _error("real_run_not_authorized", text, candidate) from exc
        if "contextual" in text or "runtime" in text or "Full/Lite" in text:
            raise _error("architecture_disposition_blocked", text, candidate, field="model") from exc
        raise _error("unapproved_override", text, candidate) from exc


def _validate_target_fields(data: Mapping[str, object], candidate: str) -> None:
    batch = data.get("target_adaptation_batch")
    if batch is not None:
        _validate_target_batch_mapping(batch, candidate)
    if data.get("target_labels_in_adaptation") is True or data.get("target_adaptation_labels") is not None:
        raise _error(
            "target_label_firewall_violation",
            "target diagnosis labels are forbidden in adaptation",
            candidate,
            field="target_adaptation_labels",
        )


def _validate_overrides(data: Mapping[str, object], spec: AblationSpec, candidate: str) -> None:
    overrides = data.get("overrides", data.get("loss_overrides"))
    if overrides is None:
        return
    if not isinstance(overrides, Mapping):
        raise _error("unapproved_override", "overrides must be a typed mapping", candidate)
    if len(overrides) != 1:
        raise _error("multiple_interventions", "exactly one intervention is permitted", candidate)
    if spec.intervention is None or next(iter(overrides)) != spec.intervention.parameter:
        raise _error("unapproved_override", "override is outside the candidate whitelist", candidate)
    value = overrides[spec.intervention.parameter]
    if value != spec.intervention.new_value:
        raise _error("unapproved_override", "candidate override must use its approved value 0.0", candidate)


def _validate_primary_coefficients(base: AblationBaseConfig, candidate: str) -> None:
    primary = {
        "lambda_z": 1.0,
        "lambda_c": 1.0,
        "lambda_cons": 0.1,
        "lambda_cbm": 0.5,
        "lambda_anat": 0.2,
        "lambda_proto": 1.0,
        "lambda_pl": 0.1,
        "tau_p": 0.95,
        "proto_margin": 1.0,
        "lambda_sep": 0.1,
        "label_smoothing": 0.1,
        "warm_lambda_z": 0.1,
        "warm_lambda_c": 1.0,
        "warm_lambda_cbm": 1.0,
        "warm_lambda_anat": 1.0,
        "warm_lambda_cons": 0.0,
    }
    for name, expected in primary.items():
        actual = getattr(base.losses, name)
        if name == "lambda_proto" and actual == 0.2:
            raise _error(
                "unresolved_coefficient",
                "lambda_proto=0.2 is the unresolved later-helper value; canonical primary is 1.0",
                candidate,
                field=name,
                remediation="provide the canonical primary lambda_proto=1.0",
            )
        if actual != expected:
            raise _error(
                "unapproved_override",
                f"base coefficient {name} must remain canonical at {expected}",
                candidate,
                field=name,
            )


def _validate_model(base: AblationBaseConfig, spec: AblationSpec, candidate: str) -> None:
    model = base.model
    if model.name in {"Full", "PADA-3DACB-Full", "PADA-3DACB-Lite", "Lite", "Contextual"} or model.contextual_encoder is not None or model.runtime_variant_switch:
        raise _error("architecture_disposition_blocked", "contextual and Full/Lite model variants are forbidden", candidate, field="model")
    if model.name != "PADA-3DACB" or model.aggregator != "AttentionAggregator":
        raise _error("unapproved_override", "base model must be canonical PADA-3DACB with AttentionAggregator", candidate, field="model")
    if spec.id == "mean_pool" and model.aggregator != "AttentionAggregator":
        raise _error("unapproved_override", "mean_pool may replace only the canonical attention aggregator", candidate)


def _resolve_name(name: str) -> tuple[str, str | None]:
    if not isinstance(name, str):
        raise TypeError("ablation name must be a string")
    if alias_target(name) is not None:
        raise _error("alias_not_approved", f"alias {name!r} is not explicitly approved", name, remediation="use the exact canonical registry ID")
    if is_unresolved_name(name):
        raise _error("unresolved_coefficient", "lambda_proto=0.2 remains unresolved and is not a candidate", name)
    try:
        get_ablation_spec(name)
    except KeyError as exc:
        raise _error("unknown_candidate", f"unknown ablation candidate {name!r}", name) from exc
    return name, None


def resolve_ablation_config(
    base_config: AblationBaseConfig | Mapping[str, object],
    ablation_name: str,
) -> ResolvedAblationConfig:
    """Resolve one exact approved candidate without loading data or constructing a model."""
    requested_name, alias_mapping = _resolve_name(ablation_name)
    spec = get_ablation_spec(requested_name)
    if not spec.is_runnable:
        reason = "source_only_not_proven" if spec.id == "no_domain_adaptation" else "architecture_disposition_blocked" if spec.id in {"full", "no_ctx_encoder", "identity_ctx"} else "unsupported_candidate"
        raise _error(reason, spec.blocked_reasons[0], requested_name, remediation="retain the blocked disposition until independently reviewed evidence exists")
    raw_mapping = base_config if isinstance(base_config, Mapping) else None
    base = _coerce_base_config(base_config, requested_name)
    if not base.approval.is_approved:
        raise _error("candidate_not_approved", "candidate requires explicit approved maintainer record", requested_name)
    if base.approval.scope != "synthetic_only":
        raise _error("candidate_not_approved", "approval scope must be synthetic_only", requested_name)
    if raw_mapping is not None:
        _validate_target_fields(raw_mapping, requested_name)
        _validate_overrides(raw_mapping, spec, requested_name)
    _validate_primary_coefficients(base, requested_name)
    _validate_model(base, spec, requested_name)
    if spec.intervention is None:
        raise _error("unsupported_candidate", "candidate has no runnable intervention", requested_name)

    losses = base.losses
    if spec.intervention.kind.value == "loss_override":
        values = losses.to_dict()
        values[spec.intervention.parameter] = float(spec.intervention.new_value)
        losses = LossCoefficients.from_mapping(values)
    model_variant = spec.model_variant
    registry_digest = registry_hash()
    candidate_digest = sha256_payload({"spec": spec.to_dict(), "approval": base.approval.to_dict()})
    source_assignment_hash = sha256_payload(base.assignments.source)
    target_adaptation_hash = sha256_payload(base.assignments.target_adaptation)
    target_evaluation_hash = sha256_payload(base.assignments.target_evaluation)
    artifacts_hash = sha256_payload(base.precomputed_artifacts)
    resolved_payload = {
        "base_method": base.base_method,
        "losses": losses.to_dict(),
        "model_variant": model_variant.to_dict(),
        "intervention": spec.intervention.to_dict(),
        "approval": base.approval.to_dict(),
        "epochs": {"warm": base.epochs_warm, "full": base.epochs_full},
        "matrix": base.matrix.to_dict(),
        "assignments": base.assignments.to_dict(),
        "precomputed_artifacts_hash": artifacts_hash,
    }
    resolved_digest = sha256_payload(resolved_payload)
    model_digest = sha256_payload(model_variant.to_dict())
    return ResolvedAblationConfig(
        requested_name=requested_name,
        candidate_id=spec.id,
        candidate_classification=spec.classification,
        approval=base.approval,
        base_method=base.base_method,
        losses=losses,
        model_variant=model_variant,
        intervention=spec.intervention,
        matrix=base.matrix,
        assignments=base.assignments,
        epochs_warm=base.epochs_warm,
        epochs_full=base.epochs_full,
        precomputed_artifacts=base.precomputed_artifacts,
        registry_hash=registry_digest,
        candidate_hash=candidate_digest,
        resolved_config_hash=resolved_digest,
        model_variant_hash=model_digest,
        source_split_assignment_hash=source_assignment_hash,
        target_adaptation_assignment_hash=target_adaptation_hash,
        target_evaluation_assignment_hash=target_evaluation_hash,
        precomputed_artifacts_hash=artifacts_hash,
        alias_mapping=alias_mapping,
    )


def validate_target_adaptation_batch(batch: Mapping[str, object]) -> None:
    """Reject target supervision before any model or loss code can consume it."""
    _validate_target_batch_mapping(batch, None)
