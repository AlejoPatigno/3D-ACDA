"""Deterministic, fail-closed Phase 17 ablation registry."""

from __future__ import annotations

from types import MappingProxyType

from .schemas import (
    ARCHITECTURE_COMPONENTS,
    AblationSpec,
    ApprovalRecord,
    ApprovalStatus,
    CandidateClassification,
    Disposition,
    ExpectedLossTerms,
    Intervention,
    InterventionKind,
    ModelVariant,
    NotebookProvenance,
    sha256_payload,
)

_BASE_MODEL = ModelVariant(name="3D-ACDA", aggregator="AttentionAggregator")
_MEAN_MODEL = ModelVariant(name="3D-ACDA+MeanPoolAggregator", aggregator="MeanPoolAggregator")
_PRESERVED_LOSS = ARCHITECTURE_COMPONENTS + (
    "L_cls_z",
    "L_cls_c",
    "L_cons",
    "L_concept",
    "L_anat",
    "L_proto",
    "L_pl",
    "optimizer",
    "schedule",
    "epochs",
    "splits",
    "seeds",
    "immutable_artifacts",
)


def _approval(candidate_id: str) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id=f"approval_{candidate_id}",
        status=ApprovalStatus.APPROVED,
        scope="synthetic_only",
        approved_by="maintainer",
    )


def _loss_spec(
    candidate_id: str,
    display_name: str,
    question: str,
    parameter: str,
    old_value: float,
    preserved: tuple[str, ...],
    provenance_lines: str,
    disabled_term: str,
) -> AblationSpec:
    return AblationSpec(
        id=candidate_id,
        display_name=display_name,
        scientific_question=question,
        provenance=NotebookProvenance("notebooks/archive/training_original.ipynb", 19, provenance_lines),
        classification=CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED,
        base_method="3D-ACDA",
        changed_components=(parameter,),
        preserved_components=preserved,
        equivalent_method=None,
        requires_target_adaptation=True,
        model_variant=_BASE_MODEL,
        expected_loss_terms=ExpectedLossTerms.canonical(disabled_full_term=disabled_term),
        approval=_approval(candidate_id),
        blocked_reasons=(),
        aliases=(),
        intervention=Intervention(InterventionKind.LOSS_OVERRIDE, parameter, old_value, 0.0),
        disposition=Disposition.RUNNABLE_AFTER_APPROVAL,
    )


def _blocked(
    candidate_id: str,
    display_name: str,
    classification: CandidateClassification,
    disposition: Disposition,
    reason: str,
    provenance: NotebookProvenance,
    *,
    equivalent_method: str | None = None,
    requires_target_adaptation: bool = True,
    model_variant: ModelVariant = _BASE_MODEL,
) -> AblationSpec:
    return AblationSpec(
        id=candidate_id,
        display_name=display_name,
        scientific_question="Disposition is retained for auditability and is not runnable without new evidence.",
        provenance=provenance,
        classification=classification,
        base_method="3D-ACDA",
        changed_components=(),
        preserved_components=_PRESERVED_LOSS,
        equivalent_method=equivalent_method,
        requires_target_adaptation=requires_target_adaptation,
        model_variant=model_variant,
        expected_loss_terms=ExpectedLossTerms.canonical(),
        approval=None,
        blocked_reasons=(reason,),
        aliases=(),
        intervention=None,
        disposition=disposition,
    )


_SPECS = (
    _loss_spec(
        "no_proto",
        "3DACDA without prototype loss",
        "What is the effect of removing only the prototype adaptation term?",
        "lambda_proto",
        1.0,
        _PRESERVED_LOSS,
        "9-14",
        "L_proto",
    ),
    _loss_spec(
        "no_pl",
        "3DACDA without pseudo-label loss",
        "What is the effect of removing only the pseudo-label adaptation term?",
        "lambda_pl",
        0.1,
        _PRESERVED_LOSS,
        "15-20",
        "L_pl",
    ),
    _loss_spec(
        "no_cons",
        "3DACDA without consistency loss",
        "What is the effect of removing only the latent/concept consistency term?",
        "lambda_cons",
        0.1,
        _PRESERVED_LOSS,
        "21-26",
        "L_cons",
    ),
    _loss_spec(
        "no_concept",
        "3DACDA without concept supervision",
        "What is the effect of removing only concept-bottleneck supervision?",
        "lambda_cbm",
        0.5,
        _PRESERVED_LOSS,
        "27-32",
        "L_concept",
    ),
    _loss_spec(
        "no_anat",
        "3DACDA without anatomical consistency",
        "What is the effect of removing only anatomical consistency?",
        "lambda_anat",
        0.2,
        _PRESERVED_LOSS,
        "33-38",
        "L_anat",
    ),
    AblationSpec(
        id="mean_pool",
        display_name="3DACDA with uniform mean pooling",
        scientific_question="Does exact uniform ROI pooling change behavior while preserving every other component?",
        provenance=NotebookProvenance("notebooks/archive/training_original.ipynb", 19, "45-50"),
        classification=CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED,
        base_method="3D-ACDA",
        changed_components=("aggregator",),
        preserved_components=_PRESERVED_LOSS,
        equivalent_method=None,
        requires_target_adaptation=True,
        model_variant=_MEAN_MODEL,
        expected_loss_terms=ExpectedLossTerms.canonical(),
        approval=_approval("mean_pool"),
        blocked_reasons=(),
        aliases=(),
        intervention=Intervention(
            InterventionKind.AGGREGATOR_REPLACEMENT,
            "aggregator",
            "AttentionAggregator",
            "MeanPoolAggregator",
        ),
        disposition=Disposition.RUNNABLE_AFTER_APPROVAL,
    ),
    AblationSpec(
        id="no_da",
        display_name="3DACDA without domain adaptation",
        scientific_question="What is the effect of disabling only the protected MMD adaptation weight?",
        provenance=NotebookProvenance("notebooks/archive/training_original.ipynb", 19, "MMD-primary baseline"),
        classification=CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED,
        base_method="3D-ACDA",
        changed_components=("lambda_MMD",),
        preserved_components=_PRESERVED_LOSS,
        equivalent_method=None,
        requires_target_adaptation=True,
        model_variant=_BASE_MODEL,
        expected_loss_terms=ExpectedLossTerms.canonical(),
        approval=_approval("no_da"),
        blocked_reasons=(),
        aliases=(),
        intervention=Intervention(InterventionKind.LOSS_OVERRIDE, "lambda_MMD", 1.0, 0.0),
        disposition=Disposition.RUNNABLE_AFTER_APPROVAL,
    ),
    _blocked(
        "no_domain_adaptation",
        "Historical no-domain-adaptation helper",
        CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED,
        Disposition.BLOCKED_NOT_PROVEN,
        "source-only loader/forward/output proof is absent; do not substitute protected Source-Only",
        NotebookProvenance("notebooks/archive/training_original.ipynb", 19, "53-64"),
    ),
    _blocked(
        "no_ctx_encoder",
        "Historical contextual-encoder removal patch",
        CandidateClassification.EQUIVALENT_TO_EXISTING_METHOD,
        Disposition.EQUIVALENT_TO_EXISTING_METHOD,
        "current 3D-ACDA already is the explicit no-context architecture; identity patching Full is forbidden",
        NotebookProvenance("notebooks/archive/training_original.ipynb", 19, "39-44"),
        equivalent_method="3D-ACDA",
    ),
    _blocked(
        "identity_ctx",
        "Historical identity contextual patch helper",
        CandidateClassification.HELPER_ONLY,
        Disposition.HELPER_ONLY,
        "implementation helper only; not a production method or runtime switch",
        NotebookProvenance("notebooks/archive/training_original.ipynb", 18, "10-12;37-52"),
    ),
    _blocked(
        "full",
        "Historical contextual Full model",
        CandidateClassification.INVALID_AFTER_ARCHITECTURE_REVISION,
        Disposition.INVALID_AFTER_ARCHITECTURE_REVISION,
        "former contextual Full architecture is invalid after the production architecture revision",
        NotebookProvenance("notebooks/archive/training_original.ipynb", 19, "3-8"),
    ),
    _blocked(
        "CFS",
        "CFS",
        CandidateClassification.UNSUPPORTED,
        Disposition.BLOCKED_NOT_PROVEN,
        "authoritative equation and implementation are not proven",
        NotebookProvenance("specs/phase_17_ablations/ablation_inventory.yaml", 0, "CFS"),
    ),
    _blocked(
        "ACS",
        "ACS",
        CandidateClassification.UNSUPPORTED,
        Disposition.BLOCKED_NOT_PROVEN,
        "authoritative equation and implementation are not proven",
        NotebookProvenance("specs/phase_17_ablations/ablation_inventory.yaml", 0, "ACS"),
    ),
    _blocked(
        "PCS",
        "PCS",
        CandidateClassification.UNSUPPORTED,
        Disposition.BLOCKED_NOT_PROVEN,
        "authoritative equation and implementation are not proven",
        NotebookProvenance("specs/phase_17_ablations/ablation_inventory.yaml", 0, "PCS"),
    ),
    _blocked(
        "QIS",
        "QIS",
        CandidateClassification.UNSUPPORTED,
        Disposition.BLOCKED_NOT_PROVEN,
        "authoritative equation and implementation are not proven",
        NotebookProvenance("specs/phase_17_ablations/ablation_inventory.yaml", 0, "QIS"),
    ),
)

_BY_ID = MappingProxyType({spec.id: spec for spec in _SPECS})
_UNSUPPORTED_ALIASES = MappingProxyType(
    {
        "no_prototype": "no_proto",
        "no_pseudo_label": "no_pl",
        "no_head_consistency": "no_cons",
        "no_concept_supervision": "no_concept",
        "no_anatomical_consistency": "no_anat",
        "mean_pooling": "mean_pool",
        "source_only": "no_domain_adaptation",
    }
)
_UNRESOLVED_NAMES = frozenset({"lambda_proto_0.2", "lambda_proto=0.2", "lambda_proto_0_2"})
_VISIBLE_NAMES = tuple(spec.id for spec in _SPECS) + tuple(_UNSUPPORTED_ALIASES) + ("lambda_proto_0.2",)
_REGISTRY_HASH = sha256_payload({"specs": tuple(spec.to_dict() for spec in _SPECS), "aliases": dict(_UNSUPPORTED_ALIASES), "unresolved": tuple(sorted(_UNRESOLVED_NAMES))})


def list_ablations() -> tuple[str, ...]:
    """Return all canonical and visibly blocked registry request names in stable order."""
    return _VISIBLE_NAMES


def get_ablation_spec(name: str) -> AblationSpec:
    """Return an exact canonical spec; aliases are never silently resolved here."""
    if not isinstance(name, str):
        raise TypeError("ablation name must be a string")
    if name in _BY_ID:
        return _BY_ID[name]
    if name in _UNSUPPORTED_ALIASES or name in _UNRESOLVED_NAMES:
        raise KeyError(f"Unsupported or unresolved ablation name: {name!r}")
    raise KeyError(f"Unknown ablation name: {name!r}")


def registry_hash() -> str:
    """Return the hash of the complete ordered registry and blocked request map."""
    return _REGISTRY_HASH


def alias_target(name: str) -> str | None:
    return _UNSUPPORTED_ALIASES.get(name)


def is_unresolved_name(name: str) -> bool:
    return name in _UNRESOLVED_NAMES


def registry_specs() -> tuple[AblationSpec, ...]:
    """Return the immutable ordered canonical records for hashing and inspection."""
    return _SPECS
