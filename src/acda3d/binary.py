"""Phase 18B binary task contracts and metadata-only utilities.

This module is deliberately separate from the historical three-class data contracts.
It permits deterministic synthetic validation and de-identified metadata processing,
not training or predictive evaluation on real cohorts.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import hmac
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from acda3d.ablations.registry import alias_target, get_ablation_spec
from acda3d.exceptions import CheckpointMigrationError

BINARY_CLASS_ORDER = ("CN", "Impaired")
BINARY_CLASS_TO_INDEX = {name: index for index, name in enumerate(BINARY_CLASS_ORDER)}
BINARY_MAPPING_CONTRACT = "phase-18b-binary-v1"
BINARY_MAPPING_CONTRACT_VERSION = "v1"
OASIS_POLICY_VERSION = "phase-18b-oasis-person-baseline-v2"
OASIS_ALLOWED_CDR_VALUES = frozenset({0.0, 0.5, 1.0, 2.0})
OASIS_SUBJECT_HASH_KEY_ID = "b729fd5dc4601de458fb0cdf074a237c4ee161fe1381bb79d6e0b9fbc2d2ae9d"
OASIS_SUBJECT_HASH_KEY_VERSION = "oasis-subject-hmac-v1"
OASIS_SUBJECT_HASH_KEY_ENV = "ACDA3D_OASIS_SUBJECT_HASH_KEY_FILE"
OASIS_SEMANTIC_AUTHORITY_MARKER = "ACDA3D-OASIS-SEMANTIC-REVIEW"
OASIS_POLICY_HASH = hashlib.sha256(
    json.dumps(
        {
            "policy_version": OASIS_POLICY_VERSION,
            "allowed_cdr_values": sorted(OASIS_ALLOWED_CDR_VALUES),
            "identity_level": "person",
            "canonical_visit": "MR1-preferred",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
OASIS_VISIT_SUFFIX_RE = re.compile(r"_MR(?P<number>\d+)$", re.IGNORECASE)
BINARY_TASK = "CN_vs_Impaired"
SPLIT_DISPOSITION = "REGENERATE_BINARY_SPLITS_REQUIRED"
SUPERSESSION_MARKER = "SUPERSEDED_BY_PHASE18B_BINARY_LABEL_SPACE"
BINARY_IDENTITY_FAMILIES = (
    "experiment", "ablation", "split", "model_checkpoint", "training_metadata", "evaluation_result", "freeze"
)
BINARY_BASELINES = ("aagn", "faster_snn")
BINARY_ABLATIONS = ("no_proto", "no_pl", "no_cons", "no_concept", "no_anat", "mean_pool")
MMD_BINARY_ABLATIONS = ("no_mmd", "no_cons", "no_concept", "no_anat", "mean_pool")
BINARY_MMD_ABLATIONS = MMD_BINARY_ABLATIONS
_PROTOTYPE_PSEUDO_BASE_METHOD = "prototype_pseudo"
_MMD_BASE_METHOD = "mmd"
BINARY_CANONICAL_LOSS_COMPONENTS = {
    "L_cls_z": 1.0,
    "L_cls_c": 2.0,
    "L_cons": 3.0,
    "L_concept": 4.0,
    "L_anat": 5.0,
    "L_proto": 6.0,
    "L_pl": 7.0,
}
BINARY_METRIC_NAMES = (
    "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "sensitivity",
    "specificity", "mcc", "cohen_kappa", "roc_auc", "pr_auc", "log_loss", "brier_score",
    "source_validation_macro_f1",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BinaryLabelError(ValueError):
    """Fail-closed error for a binary task contract violation."""


@dataclass(frozen=True)
class BinaryAblationPlan:
    """Explicit task-scoped intervention plan for one approved binary candidate."""

    candidate_id: str
    disabled_loss_components: tuple[str, ...] = ()
    model_variant: str = "canonical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "disabled_loss_components": list(self.disabled_loss_components),
            "model_variant": self.model_variant,
        }


_BINARY_ABLATION_PLANS = {
    "no_proto": BinaryAblationPlan("no_proto", ("L_proto",)),
    "no_pl": BinaryAblationPlan("no_pl", ("L_pl",)),
    "no_cons": BinaryAblationPlan("no_cons", ("L_cons",)),
    "no_concept": BinaryAblationPlan("no_concept", ("L_cls_c", "L_concept")),
    "no_anat": BinaryAblationPlan("no_anat", ("L_anat",)),
    "mean_pool": BinaryAblationPlan("mean_pool", (), "mean_pool"),
}


@dataclass(frozen=True)
class MMDBinaryAblationPlan:
    """MMD-scoped binary intervention contract.

    This namespace is intentionally separate from the historical prototype-pseudo
    plans: MMD ``no_concept`` disables concept supervision only and keeps concept
    classification active. Every plan retains the shared target adaptation forward.
    """

    candidate_id: str
    disabled_loss_components: tuple[str, ...] = ()
    model_variant: str = "canonical"
    base_method: str = _MMD_BASE_METHOD
    requires_target_adaptation: bool = True
    requires_target_forward: bool = True
    concept_classification_enabled: bool = True

    def __post_init__(self) -> None:
        expected_components = {
            "no_mmd": ("L_mmd",),
            "no_cons": ("L_cons",),
            "no_concept": ("L_concept",),
            "no_anat": ("L_anat",),
            "mean_pool": (),
        }
        if self.candidate_id not in expected_components:
            raise BinaryLabelError("unsupported or blocked MMD binary ablation")
        if self.disabled_loss_components != expected_components[self.candidate_id]:
            raise BinaryLabelError("MMD binary ablation intervention does not match its candidate")
        if self.base_method != _MMD_BASE_METHOD:
            raise BinaryLabelError("MMD binary ablation plans require base_method='mmd'")
        if not self.requires_target_adaptation or not self.requires_target_forward:
            raise BinaryLabelError("MMD binary ablations require target adaptation and target forward")
        if not self.concept_classification_enabled:
            raise BinaryLabelError("MMD no_concept must retain concept classification")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "base_method": self.base_method,
            "disabled_loss_components": list(self.disabled_loss_components),
            "model_variant": self.model_variant,
            "requires_target_adaptation": self.requires_target_adaptation,
            "requires_target_forward": self.requires_target_forward,
            "concept_classification_enabled": self.concept_classification_enabled,
        }


_MMD_BINARY_ABLATION_PLANS = {
    "no_mmd": MMDBinaryAblationPlan("no_mmd", ("L_mmd",)),
    "no_cons": MMDBinaryAblationPlan("no_cons", ("L_cons",)),
    "no_concept": MMDBinaryAblationPlan("no_concept", ("L_concept",)),
    "no_anat": MMDBinaryAblationPlan("no_anat", ("L_anat",)),
    "mean_pool": MMDBinaryAblationPlan("mean_pool", (), "mean_pool"),
}
MMD_BINARY_ABLATION_PLANS = _MMD_BINARY_ABLATION_PLANS


def mmd_binary_ablation_plan(
    candidate: str | MMDBinaryAblationPlan,
) -> MMDBinaryAblationPlan:
    """Resolve exactly one binary candidate in the explicit MMD namespace."""
    if isinstance(candidate, MMDBinaryAblationPlan):
        return candidate
    candidate_id = str(candidate).strip()
    if alias_target(candidate_id) is not None:
        raise BinaryLabelError(
            f"alias_not_approved: MMD binary alias {candidate_id!r} is not executable; "
            "use the exact canonical registry ID"
        )
    try:
        return _MMD_BINARY_ABLATION_PLANS[candidate_id]
    except KeyError as error:
        raise BinaryLabelError(
            f"unsupported or blocked MMD binary ablation: {candidate!r}; "
            "use the exact MMD candidates with base_method='mmd', not prototype_pseudo"
        ) from error


def binary_ablation_plan(
    candidate: str | BinaryAblationPlan | MMDBinaryAblationPlan,
    base_method: str = _PROTOTYPE_PSEUDO_BASE_METHOD,
) -> BinaryAblationPlan | MMDBinaryAblationPlan:
    """Resolve a binary plan within its explicit base-method namespace."""
    if base_method == _MMD_BASE_METHOD:
        return mmd_binary_ablation_plan(candidate)  # type: ignore[arg-type]
    if base_method != _PROTOTYPE_PSEUDO_BASE_METHOD:
        raise BinaryLabelError(f"unsupported binary ablation base_method: {base_method!r}")
    if isinstance(candidate, MMDBinaryAblationPlan):
        raise BinaryLabelError("MMD binary ablations require base_method='mmd'")
    if isinstance(candidate, BinaryAblationPlan):
        candidate = candidate.candidate_id
    candidate_id = str(candidate).strip()
    try:
        return _BINARY_ABLATION_PLANS[candidate_id]
    except KeyError as error:
        if candidate_id in MMD_BINARY_ABLATIONS:
            raise BinaryLabelError(
                f"MMD binary ablation {candidate_id!r} requires base_method='mmd'"
            ) from error
        raise BinaryLabelError(f"unsupported or blocked binary ablation: {candidate!r}") from error


def apply_binary_ablation_loss_plan(
    candidate: str | BinaryAblationPlan | MMDBinaryAblationPlan,
    components: Mapping[str, Any],
    base_method: str = _PROTOTYPE_PSEUDO_BASE_METHOD,
) -> dict[str, Any]:
    """Apply a binary loss mask to synthetic components without changing unrelated values."""
    if not isinstance(components, Mapping):
        raise BinaryLabelError("synthetic loss components must be a mapping")
    plan = binary_ablation_plan(candidate, base_method=base_method)
    effective = dict(components)
    for component in plan.disabled_loss_components:
        if component not in effective:
            continue
        value = effective[component]
        if isinstance(value, Mapping):
            nested = dict(value)
            for key in ("value", "raw", "weighted", "total"):
                if key in nested:
                    nested[key] = nested[key] * 0
            if "active" in nested:
                nested["active"] = False
            effective[component] = nested
        else:
            try:
                effective[component] = value * 0
            except TypeError as error:
                raise BinaryLabelError(
                    f"loss component {component!r} cannot be masked without changing its type"
                ) from error
    return effective


@dataclass(frozen=True)
class BinaryLabelMapping:
    original_label_name: str
    binary_label_name: str
    binary_label: int
    mapping_contract: str = BINARY_MAPPING_CONTRACT

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_label(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BinaryLabelError("original diagnosis must be a non-empty canonical token")
    label = value.strip().upper()
    if label not in {"CN", "MCI", "AD"}:
        raise BinaryLabelError(f"unsupported ADNI diagnosis: {value!r}")
    return label


def map_adni_label(original_label: object) -> BinaryLabelMapping:
    """Map one canonical ADNI diagnosis without losing its source meaning."""
    label = _canonical_label(original_label)
    binary = "CN" if label == "CN" else "Impaired"
    return BinaryLabelMapping(label, binary, BINARY_CLASS_TO_INDEX[binary])


def _hash_value(namespace: str, value: object) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise BinaryLabelError(f"{namespace} identity cannot be empty")
    return hashlib.sha256(f"phase18b:{namespace}:{normalized}".encode()).hexdigest()


def _resolve_oasis_subject_hash_key(
    subject_hash_key: bytes | bytearray | memoryview | None = None,
    subject_hash_key_file: str | Path | None = None,
) -> bytes:
    """Resolve the external OASIS HMAC key without ever persisting it."""
    if subject_hash_key is not None:
        key = bytes(subject_hash_key)
    else:
        source = subject_hash_key_file or os.environ.get(OASIS_SUBJECT_HASH_KEY_ENV)
        if not source:
            raise BinaryLabelError(
                "OASIS subject hash key is required; pass subject_hash_key or configure "
                f"{OASIS_SUBJECT_HASH_KEY_ENV}"
            )
        try:
            key = Path(source).read_bytes()
        except OSError as error:
            raise BinaryLabelError("OASIS subject hash key file could not be read") from error
    if len(key) != 32:
        raise BinaryLabelError("OASIS subject hash key must be exactly 32 bytes")
    return key


def _oasis_hmac_hash(namespace: str, value: object, key: bytes) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise BinaryLabelError(f"OASIS {namespace} identity cannot be empty")
    message = f"phase18b:oasis:{namespace}:{normalized}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def derive_oasis_person_identity(visit_id: object) -> tuple[str, int | None]:
    """Return a de-identified person's source key and terminal MR visit number."""
    raw = str(visit_id).strip()
    if not raw:
        raise BinaryLabelError("OASIS visit ID cannot be empty")
    match = OASIS_VISIT_SUFFIX_RE.search(raw)
    if match is None:
        return raw, None
    return raw[: match.start()], int(match.group("number"))


def _parse_oasis_cdr(value: object) -> tuple[float, str]:
    raw = "" if value is None else str(value).strip()
    if not raw:
        raise BinaryLabelError("missing OASIS CDR")
    try:
        parsed = float(raw)
    except (TypeError, ValueError) as error:
        raise BinaryLabelError(f"malformed OASIS CDR: {value!r}") from error
    if not math.isfinite(parsed):
        raise BinaryLabelError("nonfinite OASIS CDR")
    if parsed < 0:
        raise BinaryLabelError("negative OASIS CDR")
    if parsed not in OASIS_ALLOWED_CDR_VALUES:
        raise BinaryLabelError(f"out-of-domain OASIS CDR: {value!r}")
    return parsed, raw


@dataclass(frozen=True)
class BinarySubjectRecord:
    """De-identified subject provenance used by binary manifests."""

    subject_hash: str
    cohort: str
    original_label_name: str | None
    binary_label_name: str
    binary_label: int
    source_row_hash: str
    derivative_path: Path
    mapping_contract: str = BINARY_MAPPING_CONTRACT
    visit_hash: str | None = None
    source_file_hash: str | None = None
    metadata_only: bool = False
    original_metadata_value: str | None = None
    person_hash: str | None = None
    visit_number: int | None = None
    canonical_visit: bool = False

    def __post_init__(self) -> None:
        if not _SHA256_RE.fullmatch(self.subject_hash):
            raise BinaryLabelError("subject_hash must be a lowercase SHA-256 digest")
        if self.cohort not in {"ADNI", "OASIS"}:
            raise BinaryLabelError("cohort must be ADNI or OASIS")
        if self.original_label_name is None:
            raise BinaryLabelError("original diagnosis provenance is required")
        mapping = map_adni_label(self.original_label_name) if self.cohort == "ADNI" else None
        if self.cohort == "OASIS" and self.original_label_name not in BINARY_CLASS_ORDER:
            raise BinaryLabelError("OASIS binary records require verified CN/Impaired provenance; MCI is forbidden")
        if self.cohort == "ADNI" and mapping and (
            self.binary_label_name != mapping.binary_label_name or self.binary_label != mapping.binary_label
        ):
            raise BinaryLabelError("ADNI binary label does not match the canonical mapping")
        if self.binary_label_name not in BINARY_CLASS_TO_INDEX or self.binary_label != BINARY_CLASS_TO_INDEX[self.binary_label_name]:
            raise BinaryLabelError("binary label/name does not match fixed class order")
        if not _SHA256_RE.fullmatch(self.source_row_hash):
            raise BinaryLabelError("source_row_hash must be a lowercase SHA-256 digest")
        if self.visit_hash is not None and not _SHA256_RE.fullmatch(self.visit_hash):
            raise BinaryLabelError("visit_hash must be a lowercase SHA-256 digest")
        if self.source_file_hash is not None and not _SHA256_RE.fullmatch(self.source_file_hash):
            raise BinaryLabelError("source_file_hash must be a lowercase SHA-256 digest")
        if self.person_hash is not None and not _SHA256_RE.fullmatch(self.person_hash):
            raise BinaryLabelError("person_hash must be a lowercase SHA-256 digest")
        if self.visit_number is not None and (isinstance(self.visit_number, bool) or self.visit_number < 1):
            raise BinaryLabelError("visit_number must be a positive integer")
        if self.cohort == "OASIS" and self.person_hash not in (None, self.subject_hash):
            raise BinaryLabelError("OASIS person_hash must match subject_hash")
        if not self.derivative_path.is_absolute():
            raise BinaryLabelError("derivative_path must be resolved")

    @classmethod
    def from_source(
        cls,
        *,
        cohort: str,
        subject_id: object,
        original_label: object,
        source_row: object,
        derivative_path: str | Path,
        visit_id: object | None = None,
        source_file_hash: str | None = None,
        metadata_only: bool = False,
        subject_hash_key: bytes | bytearray | memoryview | None = None,
    ) -> BinarySubjectRecord:
        cohort_name = str(cohort).upper()
        original_metadata_value: str | None = None
        person_id = subject_id
        visit_number: int | None = None
        oasis_key = _resolve_oasis_subject_hash_key(subject_hash_key) if cohort_name == "OASIS" else None
        if cohort_name == "ADNI":
            mapping = map_adni_label(original_label)
        elif cohort_name == "OASIS":
            person_id, visit_number = derive_oasis_person_identity(subject_id)
            original = str(original_label).strip()
            if original in BINARY_CLASS_ORDER:
                mapping = BinaryLabelMapping(original, original, BINARY_CLASS_TO_INDEX[original])
            else:
                cdr, original_metadata_value = _parse_oasis_cdr(original_label)
                label = "CN" if cdr == 0.0 else "Impaired"
                mapping = BinaryLabelMapping(label, label, BINARY_CLASS_TO_INDEX[label])
            if original_metadata_value is None:
                original_metadata_value = original
        else:
            raise BinaryLabelError(f"unsupported cohort: {cohort!r}")
        subject_hash = (
            _oasis_hmac_hash("person", person_id, oasis_key)
            if cohort_name == "OASIS" and oasis_key is not None
            else _hash_value(f"subject:{cohort_name}", person_id)
        )
        visit_hash = (
            _oasis_hmac_hash("visit", visit_id if visit_id is not None else subject_id, oasis_key)
            if cohort_name == "OASIS" and oasis_key is not None
            else _hash_value(f"visit:{cohort_name}", visit_id if visit_id is not None else subject_id)
            if (visit_id is not None or cohort_name == "OASIS")
            else None
        )
        return cls(
            subject_hash=subject_hash,
            cohort=cohort_name,
            original_label_name=mapping.original_label_name,
            binary_label_name=mapping.binary_label_name,
            binary_label=mapping.binary_label,
            source_row_hash=_hash_value(f"row:{cohort_name}", source_row),
            derivative_path=Path(derivative_path).resolve(),
            mapping_contract=BINARY_MAPPING_CONTRACT,
            visit_hash=visit_hash,
            source_file_hash=source_file_hash,
            metadata_only=metadata_only,
            original_metadata_value=original_metadata_value,
            person_hash=subject_hash if cohort_name == "OASIS" else None,
            visit_number=visit_number,
            canonical_visit=cohort_name != "OASIS" or visit_number in (None, 1),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["derivative_path"] = str(self.derivative_path)
        return payload


def _header_map(fieldnames: Sequence[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise BinaryLabelError("metadata CSV has no header")
    return {str(name).strip().lower(): str(name) for name in fieldnames}


@dataclass(frozen=True)
class OasisEvidence:
    """De-identified, byte-bound evidence awaiting independent scientific review."""

    semantics_approved: bool
    accepted_count: int
    excluded_count: int
    cdr_values: tuple[float, ...]
    records: tuple[dict[str, Any], ...]
    csv_sha256: str
    notebook_sha256: str
    exclusion_reasons: Mapping[str, int] = frozenset()
    evidence_verified: bool = True
    scientific_review_status: str = "pending_independent_review"
    structural_validation: Mapping[str, Any] = frozenset()
    accepted_cdr_value_counts: Mapping[str, int] = frozenset()
    row_content_hashes: tuple[str, ...] = ()
    source_field_name: str = "CDR"
    mapping_contract: str = BINARY_MAPPING_CONTRACT
    policy_version: str = OASIS_POLICY_VERSION
    policy_hash: str = OASIS_POLICY_HASH
    subject_hash_key_id: str = OASIS_SUBJECT_HASH_KEY_ID
    subject_hash_key_version: str = OASIS_SUBJECT_HASH_KEY_VERSION
    total_visit_count: int = 0
    canonical_person_count: int = 0
    longitudinal_duplicate_count: int = 0
    conflicting_person_count: int = 0

    @property
    def exclusion_reason(self) -> str:
        """Compatibility summary for callers that used the old single reason."""
        return "missing_or_invalid_cdr_excluded"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["exclusion_reasons"] = dict(self.exclusion_reasons)
        payload["structural_validation"] = dict(self.structural_validation)
        payload["accepted_cdr_value_counts"] = dict(self.accepted_cdr_value_counts)
        payload["exclusion_reason"] = self.exclusion_reason
        payload["policy_version"] = self.policy_version
        payload["person_level"] = True
        return payload


@dataclass(frozen=True)
class OasisApprovalAttestation:
    """Authority-issued approval bound to one exact OASIS evidence object."""

    csv_sha256: str
    notebook_sha256: str
    mapping_contract: str
    mapping_contract_version: str
    policy_hash: str
    review_id: str
    authority_marker: str
    result: str
    evidence_hash: str
    _validated: bool = False

    def to_dict(self) -> dict[str, str]:
        return {
            "csv_sha256": self.csv_sha256,
            "notebook_sha256": self.notebook_sha256,
            "mapping_contract": self.mapping_contract,
            "mapping_contract_version": self.mapping_contract_version,
            "policy_hash": self.policy_hash,
            "review_id": self.review_id,
            "authority_marker": self.authority_marker,
            "result": self.result,
            "evidence_hash": self.evidence_hash,
        }


def oasis_evidence_hash(evidence: OasisEvidence) -> str:
    if not isinstance(evidence, OasisEvidence):
        raise BinaryLabelError("OASIS evidence hash requires an OasisEvidence object")
    payload = evidence.to_dict()
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def validate_oasis_semantic_approval(
    evidence: OasisEvidence,
    attestation: Mapping[str, Any] | OasisApprovalAttestation,
) -> OasisApprovalAttestation:
    """Validate and mint an authority-bound OASIS semantic approval attestation."""
    if not isinstance(evidence, OasisEvidence):
        raise BinaryLabelError("OASIS approval requires an OasisEvidence object")
    if evidence.evidence_verified is not True:
        raise BinaryLabelError("OASIS approval requires independently verified evidence")
    if evidence.semantics_approved is not True or evidence.scientific_review_status != "PASS":
        raise BinaryLabelError("OASIS approval requires an independently reviewed PASS evidence status")
    values = attestation.to_dict() if isinstance(attestation, OasisApprovalAttestation) else attestation
    if not isinstance(values, Mapping):
        raise BinaryLabelError("OASIS approval attestation must be structured")
    review_id = values.get("review_id")
    if not isinstance(review_id, str) or not review_id.strip():
        raise BinaryLabelError("OASIS approval review_id is required")
    expected = {
        "csv_sha256": evidence.csv_sha256,
        "notebook_sha256": evidence.notebook_sha256,
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "mapping_contract_version": BINARY_MAPPING_CONTRACT_VERSION,
        "policy_hash": evidence.policy_hash,
        "review_id": review_id,
        "authority_marker": OASIS_SEMANTIC_AUTHORITY_MARKER,
        "result": "PASS",
        "evidence_hash": oasis_evidence_hash(evidence),
    }
    for field, expected_value in expected.items():
        if values.get(field) != expected_value:
            raise BinaryLabelError(f"OASIS approval attestation field {field!r} is not bound to evidence")
    return OasisApprovalAttestation(**expected, _validated=True)



def _notebook_mapping_evidence(notebook_bytes: bytes) -> dict[str, Any]:
    """Prove executable ID/CDR handling and mapping logic, never notebook prose."""
    try:
        payload = json.loads(notebook_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BinaryLabelError("OASIS notebook structural validation failed: invalid JSON") from error
    cells = payload.get("cells") if isinstance(payload, Mapping) else None
    if not isinstance(cells, list):
        raise BinaryLabelError("OASIS notebook structural validation failed: cells are missing")
    code_sources = [
        "".join(cell.get("source", ()))
        for cell in cells
        if isinstance(cell, Mapping) and cell.get("cell_type") == "code"
    ]
    if not code_sources:
        raise BinaryLabelError("OASIS notebook structural validation failed: no code cells")
    try:
        trees = [ast.parse(source) for source in code_sources]
    except SyntaxError as error:
        raise BinaryLabelError("OASIS notebook structural validation failed: invalid code") from error

    nodes = [node for tree in trees for node in ast.walk(tree)]
    calls = [node for node in nodes if isinstance(node, ast.Call)]
    field_names = {
        str(node.slice.value).strip().lower()
        for node in nodes
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    has_id_handling = bool(field_names & {"id", "subject id", "subject_id", "subject"}) or any(
        isinstance(node, ast.Name) and node.id.lower() == "id_column" for node in nodes
    )
    has_cdr_handling = "cdr" in field_names or any(
        isinstance(node, ast.Name) and node.id.lower() in {"cdr", "cdr_column"} for node in nodes
    )
    has_numeric_coerce = any(
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "to_numeric"
        and any(
            keyword.arg == "errors"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == "coerce"
            for keyword in node.keywords
        )
        for node in calls
    )
    comparisons = [node for node in nodes if isinstance(node, ast.Compare)]
    comparison_text = [ast.unparse(node).lower() for node in comparisons]
    has_zero_condition = any("cdr" in text and "==" in text and re.search(r"\b0(?:\.0)?\b", text) for text in comparison_text)
    has_positive_condition = any(
        "cdr" in text and (">" in text or "!=" in text) and re.search(r"\b0(?:\.0)?\b", text)
        for text in comparison_text
    )
    has_negative_exclusion = any("cdr" in text and "<" in text for text in comparison_text)
    has_missing_exclusion = any(
        isinstance(node.func, ast.Attribute)
        and node.func.attr.lower() in {"isna", "isnull", "dropna"}
        for node in calls
    )

    def branch_has_label(node: ast.AST, label: str) -> bool:
        return any(isinstance(child, ast.Constant) and child.value == label for child in ast.walk(node))

    has_zero_mapping = False
    has_positive_mapping = False
    for node in nodes:
        if isinstance(node, ast.If):
            condition = ast.unparse(node.test).lower()
            if "cdr" in condition and "==" in condition and re.search(r"\b0(?:\.0)?\b", condition):
                has_zero_mapping = branch_has_label(node, "CN")
            if "cdr" in condition and (">" in condition or "!=" in condition) and re.search(r"\b0(?:\.0)?\b", condition):
                has_positive_mapping = branch_has_label(node, "Impaired")
        elif isinstance(node, ast.IfExp):
            condition = ast.unparse(node.test).lower()
            if (
                "cdr" in condition
                and "==" in condition
                and re.search(r"\b0(?:\.0)?\b", condition)
                and branch_has_label(node.body, "CN")
                and branch_has_label(node.orelse, "Impaired")
                and has_negative_exclusion
            ):
                has_zero_mapping = True
                has_positive_mapping = True
                has_positive_condition = True
    if not (
        has_id_handling
        and has_cdr_handling
        and has_numeric_coerce
        and has_missing_exclusion
        and has_negative_exclusion
        and has_zero_condition
        and has_positive_condition
        and has_zero_mapping
        and has_positive_mapping
    ):
        raise BinaryLabelError(
            "OASIS notebook structural validation failed: code must handle ID/CDR, coerce and exclude invalid values, "
            "and explicitly map CDR==0 to CN and positive CDR to Impaired"
        )
    return {
        "code_cells": len(code_sources),
        "id_field_handling": True,
        "cdr_field_handling": True,
        "numeric_coerce": True,
        "explicit_zero_to_cn": True,
        "explicit_positive_to_impaired": True,
        "invalid_values_excluded": True,
    }


def _canonical_row_hash(row: Mapping[str, Any]) -> str:
    """Hash complete CSV row content without returning any raw identifier."""
    encoded = json.dumps(
        {str(key): "" if value is None else str(value) for key, value in sorted(row.items())},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_verified_oasis_metadata(
    csv_path: str | Path,
    notebook_path: str | Path,
    *,
    subject_hash_key: bytes | bytearray | memoryview | None = None,
    subject_hash_key_file: str | Path | None = None,
) -> OasisEvidence:
    """Validate OASIS metadata using an external HMAC key.

    The key must be passed explicitly or supplied through
    ``ACDA3D_OASIS_SUBJECT_HASH_KEY_FILE`` (or ``subject_hash_key_file``).
    It is read only for hashing and is never returned or persisted.
    """
    csv_file, notebook_file = Path(csv_path), Path(notebook_path)
    csv_bytes = csv_file.read_bytes()
    notebook_bytes = notebook_file.read_bytes()
    structural = _notebook_mapping_evidence(notebook_bytes)
    oasis_key = _resolve_oasis_subject_hash_key(subject_hash_key, subject_hash_key_file)
    with csv_file.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = _header_map(reader.fieldnames)
        if len(columns) != len(reader.fieldnames or ()):
            raise BinaryLabelError("OASIS metadata CSV contains duplicate column names")
        id_column = next((columns[key] for key in ("id", "subject id", "subject_id", "subject") if key in columns), None)
        cdr_column = columns.get("cdr")
        if id_column is None or cdr_column is None:
            raise BinaryLabelError("OASIS metadata must contain ID and CDR columns")
        raw_rows = list(reader)

    grouped: dict[str, list[tuple[Mapping[str, Any], float, str, int | None]]] = {}
    exclusion_reasons: dict[str, int] = {}

    def exclude(reason: str) -> None:
        exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1

    for row in raw_rows:
        raw_id = str(row.get(id_column, "")).strip()
        raw_cdr = str(row.get(cdr_column, "")).strip()
        if not raw_id:
            exclude("missing_subject_id")
            continue
        if not raw_cdr:
            exclude("missing_or_invalid_cdr")
            continue
        try:
            cdr, canonical_raw_cdr = _parse_oasis_cdr(raw_cdr)
        except BinaryLabelError as error:
            message = str(error)
            if message.startswith("malformed"):
                exclude("malformed_cdr")
            elif message.startswith("nonfinite"):
                exclude("nonfinite_cdr")
            elif message.startswith("negative"):
                exclude("negative_cdr")
            elif message.startswith("out-of-domain"):
                exclude("out_of_domain_cdr")
            else:
                exclude("missing_or_invalid_cdr")
            continue
        person_id, visit_number = derive_oasis_person_identity(raw_id)
        grouped.setdefault(person_id, []).append((row, cdr, canonical_raw_cdr, visit_number))

    accepted: list[dict[str, Any]] = []
    accepted_cdr_value_counts: dict[str, int] = {}
    longitudinal_duplicate_count = 0
    conflicting_person_count = 0
    for person_id, entries in grouped.items():
        values = {entry[1] for entry in entries}
        if len(values) > 1:
            exclusion_reasons["conflicting_person_diagnosis"] = (
                exclusion_reasons.get("conflicting_person_diagnosis", 0) + len(entries)
            )
            conflicting_person_count += 1
            continue
        row, cdr, raw_cdr, visit_number = min(
            entries,
            key=lambda entry: (
                0 if entry[3] == 1 else 1,
                entry[3] if entry[3] is not None else math.inf,
                _canonical_row_hash(entry[0]),
            ),
        )
        duplicate_count = len(entries) - 1
        if duplicate_count:
            exclusion_reasons["longitudinal_duplicate"] = (
                exclusion_reasons.get("longitudinal_duplicate", 0) + duplicate_count
            )
            longitudinal_duplicate_count += duplicate_count
        raw_id = str(row.get(id_column, "")).strip()
        subject_hash = _oasis_hmac_hash("person", person_id, oasis_key)
        label = "CN" if cdr == 0.0 else "Impaired"
        accepted_cdr_value_counts[raw_cdr] = accepted_cdr_value_counts.get(raw_cdr, 0) + 1
        accepted.append({
            "subject_hash": subject_hash,
            "person_hash": subject_hash,
            "cohort": "OASIS",
            "original_label_name": label,
            "original_metadata_value": raw_cdr,
            "binary_label_name": label,
            "binary_label": BINARY_CLASS_TO_INDEX[label],
            "source_row_hash": _canonical_row_hash(row),
            "source_file_hash": hashlib.sha256(csv_bytes).hexdigest(),
            "visit_hash": _oasis_hmac_hash("visit", raw_id, oasis_key),
            "visit_number": visit_number,
            "canonical_visit": True,
            "mapping_contract": BINARY_MAPPING_CONTRACT,
            "metadata_only": True,
        })

    accepted.sort(key=lambda record: record["subject_hash"])
    row_content_hashes = tuple(record["source_row_hash"] for record in accepted)
    return OasisEvidence(
        semantics_approved=False,
        accepted_count=len(accepted),
        excluded_count=sum(exclusion_reasons.values()),
        cdr_values=tuple(sorted({float(value) for value in accepted_cdr_value_counts})),
        records=tuple(accepted),
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        notebook_sha256=hashlib.sha256(notebook_bytes).hexdigest(),
        exclusion_reasons=dict(sorted(exclusion_reasons.items())),
        evidence_verified=True,
        scientific_review_status="pending_independent_review",
        structural_validation=structural,
        accepted_cdr_value_counts=dict(sorted(accepted_cdr_value_counts.items())),
        row_content_hashes=row_content_hashes,
        source_field_name=cdr_column,
        mapping_contract=BINARY_MAPPING_CONTRACT,
        policy_version=OASIS_POLICY_VERSION,
        policy_hash=OASIS_POLICY_HASH,
        subject_hash_key_id=hashlib.sha256(oasis_key).hexdigest(),
        subject_hash_key_version=OASIS_SUBJECT_HASH_KEY_VERSION,
        total_visit_count=len(raw_rows),
        canonical_person_count=len(accepted),
        longitudinal_duplicate_count=longitudinal_duplicate_count,
        conflicting_person_count=conflicting_person_count,
    )


def _require_binary_records(records: Sequence[BinarySubjectRecord]) -> list[BinarySubjectRecord]:
    ordered = sorted(records, key=lambda record: (record.cohort, record.subject_hash))
    if not ordered:
        raise BinaryLabelError("binary records cannot be empty")
    if {record.binary_label for record in ordered} != {0, 1}:
        raise BinaryLabelError("binary split requires both CN and Impaired classes")
    if len({record.subject_hash for record in ordered}) != len(ordered):
        raise BinaryLabelError("duplicate subject hashes are not valid for binary splits")
    return ordered


def build_binary_target_partition(
    records: Sequence[BinarySubjectRecord], *, seed: int = 42, adaptation_fraction: float = 0.8
) -> dict[str, Any]:
    """Build a deterministic subject-hash partition for metadata/contract use."""
    if not 0 < adaptation_fraction < 1:
        raise BinaryLabelError("adaptation_fraction must be between zero and one")
    ordered = _require_binary_records(records)
    import numpy as np
    from sklearn.model_selection import train_test_split
    indices = np.arange(len(ordered))
    labels = np.asarray([record.binary_label for record in ordered])
    adaptation, evaluation = train_test_split(
        indices, train_size=adaptation_fraction, stratify=labels, random_state=seed, shuffle=True
    )
    return {
        "schema_version": "phase18b.binary-split.v1",
        "identity_level": "person",
        "person_disjoint": True,
        "task": BINARY_TASK,
        "class_order": list(BINARY_CLASS_ORDER),
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "disposition": SPLIT_DISPOSITION,
        "target_adaptation": [ordered[int(i)].subject_hash for i in sorted(adaptation)],
        "target_evaluation": [ordered[int(i)].subject_hash for i in sorted(evaluation)],
        "metadata_only": all(record.metadata_only for record in ordered),
        "real_run": False,
        "predictive_evaluation": False,
    }


def generate_binary_source_folds(
    records: Sequence[BinarySubjectRecord], *, n_splits: int = 5, seed: int = 42
) -> list[dict[str, Any]]:
    if n_splits < 2:
        raise BinaryLabelError("n_splits must be at least two")
    ordered = _require_binary_records(records)
    import numpy as np
    from sklearn.model_selection import StratifiedKFold
    labels = np.asarray([record.binary_label for record in ordered])
    if min(int((labels == label).sum()) for label in (0, 1)) < n_splits:
        raise BinaryLabelError("each binary class must contain at least n_splits records")
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds: list[dict[str, Any]] = []
    for fold, (train, validation) in enumerate(splitter.split(np.zeros(len(ordered)), labels)):
        folds.append({
            "fold": fold,
            "identity_level": "person",
            "person_disjoint": True,
            "source_train": [ordered[int(i)].subject_hash for i in sorted(train)],
            "source_validation": [ordered[int(i)].subject_hash for i in sorted(validation)],
            "class_order": list(BINARY_CLASS_ORDER),
            "mapping_contract": BINARY_MAPPING_CONTRACT,
            "disposition": SPLIT_DISPOSITION,
            "metadata_only": all(record.metadata_only for record in ordered),
            "real_run": False,
        })
    return folds


def validate_target_adaptation_batch(batch: Mapping[str, Any]) -> None:
    """Enforce the existing exact unlabeled target-adaptation contract."""
    allowed = {"x", "subject_id", "subject_hash", "cohort"}
    forbidden = {
        "y", "label", "labels", "binary_label", "binary_label_name",
        "original_label", "original_label_name", "diagnosis", "c_target",
        "g_bar", "target_label", "true_label",
    }
    keys = set(batch)
    if keys != allowed or keys & forbidden:
        raise BinaryLabelError("target adaptation must contain exactly x, subject_id, subject_hash, and cohort")
    if not isinstance(batch["subject_hash"], str) or not batch["subject_hash"]:
        raise BinaryLabelError("target adaptation subject_hash is required")


def validate_binary_prediction(payload: Mapping[str, Any]) -> BinaryPrediction:
    return BinaryPrediction.from_mapping(payload)


@dataclass(frozen=True)
class BinaryPrediction:
    prob_cn: float
    prob_impaired: float
    predicted_label: int
    dtype: str = "float64"
    original_label_name: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> BinaryPrediction:
        if {"prob_mci", "prob_ad", "probability_MCI", "probability_AD"}.intersection(payload):
            raise BinaryLabelError("legacy probability fields prob_mci and prob_ad are not active in binary schema")
        if "prob_cn" not in payload or "prob_impaired" not in payload:
            raise BinaryLabelError("binary prediction requires prob_cn and prob_impaired")
        dtype = str(payload.get("dtype", "float64"))
        tolerance = {"float64": 1e-6, "float32": 1e-5}.get(dtype)
        if tolerance is None:
            raise BinaryLabelError("prediction dtype must be float64 or float32")
        try:
            cn, impaired = float(payload["prob_cn"]), float(payload["prob_impaired"])
        except (TypeError, ValueError) as error:
            raise BinaryLabelError("binary probabilities must be numeric") from error
        if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in (cn, impaired)):
            raise BinaryLabelError("binary probabilities must be finite and within [0, 1]")
        if abs(cn + impaired - 1.0) > tolerance:
            raise BinaryLabelError(f"binary probabilities must sum to one within {tolerance}")
        return cls(cn, impaired, 0 if cn >= impaired else 1, dtype, payload.get("original_label_name"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "prob_cn": self.prob_cn,
            "prob_impaired": self.prob_impaired,
            "predicted_label": self.predicted_label,
            "dtype": self.dtype,
            **({"original_label_name": self.original_label_name} if self.original_label_name else {}),
        }


def _metric(value: float | None, reason: str | None = None) -> dict[str, Any]:
    return {"value": value, "reason": reason}




def select_best_checkpoint_by_source_validation_macro_f1(
    candidates: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Select only by source-validation macro-F1; target metrics are never read."""
    if not candidates:
        raise BinaryLabelError("checkpoint candidates cannot be empty")
    valid: list[tuple[float, int, Mapping[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        metrics = candidate.get("metrics") if isinstance(candidate, Mapping) else None
        if metrics is not None and not isinstance(metrics, Mapping):
            raise BinaryLabelError("checkpoint candidate metrics are required")
        score = (
            metrics.get("source_validation_macro_f1") if isinstance(metrics, Mapping)
            else candidate.get("source_validation_macro_f1") if isinstance(candidate, Mapping)
            else None
        )
        if isinstance(score, Mapping):
            score = score.get("value")
        if score is None or isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            raise BinaryLabelError("source-validation macro-F1 is required for checkpoint selection")
        valid.append((float(score), -index, candidate))
    return max(valid, key=lambda item: (item[0], item[1]))[2]


def _binary_auc(labels: Sequence[int], scores: Sequence[float]) -> dict[str, Any]:
    positives = [score for label, score in zip(labels, scores, strict=True) if label == 1]
    negatives = [score for label, score in zip(labels, scores, strict=True) if label == 0]
    if not positives or not negatives:
        return _metric(None, "zero_support")
    wins = sum(1.0 if positive > negative else 0.5 if positive == negative else 0.0 for positive in positives for negative in negatives)
    return _metric(wins / (len(positives) * len(negatives)))


@dataclass(frozen=True)
class BinaryEvaluationResult:
    confusion_matrix: tuple[tuple[int, int], tuple[int, int]]
    metrics: dict[str, dict[str, Any]]
    class_order: tuple[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "confusion_matrix": [list(row) for row in self.confusion_matrix],
            "class_order": list(self.class_order),
            "positive_class": "Impaired",
            "metrics": self.metrics,
            "real_run": False,
            "publication_metrics": False,
        }


def load_binary_checkpoint(model: Any, checkpoint: Any) -> Any:
    """Load only a complete, metadata-bound two-class checkpoint."""
    from acda3d.models.checkpoint_migration import _locate_state_dict
    from acda3d.training.checkpointing import validate_binary_checkpoint_metadata

    if isinstance(checkpoint, (str, Path)):
        import torch
        checkpoint = torch.load(checkpoint, weights_only=True, map_location="cpu")
    if not isinstance(checkpoint, Mapping):
        raise CheckpointMigrationError("binary checkpoint metadata is required; unsafe fallback is prohibited")
    try:
        validate_binary_checkpoint_metadata(dict(checkpoint), model=model)
    except Exception as error:
        if isinstance(error, CheckpointMigrationError):
            raise
        raise CheckpointMigrationError(str(error)) from error
    if getattr(model, "num_classes", 2) != 2:
        raise CheckpointMigrationError("binary model must expose exactly two classifier outputs")
    state = _locate_state_dict(checkpoint)
    target = model.state_dict()
    classifier_keys = [key for key in target if key.startswith(("cls_head", "classification_head", "cls."))]
    if not classifier_keys:
        raise CheckpointMigrationError("binary model has no classifier parameters")
    found_classifier = False
    for key, tensor in state.items():
        if key.startswith("module."):
            key = key[7:]
        if key in target and key in classifier_keys:
            found_classifier = True
            if tensor.ndim == 0 or tensor.shape[0] != 2:
                raise CheckpointMigrationError("binary checkpoint classifier cardinality must be two")
    if not found_classifier:
        raise CheckpointMigrationError("binary checkpoint omits classifier parameters; partial loading is prohibited")
    for key, tensor in state.items():
        normalized = key.removeprefix("module.")
        if normalized in target and tuple(target[normalized].shape) != tuple(tensor.shape):
            raise CheckpointMigrationError(
                f"binary checkpoint tensor {key!r} has incompatible shape {tuple(tensor.shape)}"
            )
    try:
        model.load_state_dict(state, strict=True)
    except (RuntimeError, KeyError) as error:
        raise CheckpointMigrationError("binary checkpoint must be complete and two-class compatible") from error
    return model


def binary_prototype_loss(logits: Any, targets: Any) -> Any:
    """Binary prototype/classification CE over raw two-logit tensors."""
    import torch
    from torch.nn import functional as F

    if not torch.is_tensor(logits) or logits.ndim != 2 or logits.shape[1] != 2:
        raise BinaryLabelError("binary logits must have shape (B,2)")
    if not torch.is_tensor(targets) or targets.ndim != 1 or targets.shape[0] != logits.shape[0]:
        raise BinaryLabelError("binary targets must have shape (B,)")
    if targets.dtype not in (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8):
        raise BinaryLabelError("binary targets must be integer class IDs")
    if targets.numel() and ((targets < 0).any() or (targets > 1).any()):
        raise BinaryLabelError("binary targets must be in {0,1}")
    return F.cross_entropy(logits, targets.long())


def binary_pseudo_label_loss(logits: Any, *, tau: float = 0.95) -> tuple[Any, Any, Any]:
    """Return CE, pseudo labels, and acceptance mask for two-logit target rows."""
    import torch
    from torch.nn import functional as F

    if not torch.is_tensor(logits) or logits.ndim != 2 or logits.shape[1] != 2:
        raise BinaryLabelError("binary pseudo logits must have shape (B,2)")
    if not math.isfinite(float(tau)) or not 0 <= float(tau) <= 1:
        raise BinaryLabelError("pseudo-label threshold must be within [0,1]")
    probabilities = F.softmax(logits, dim=-1)
    confidence, labels = probabilities.max(dim=-1)
    accepted = confidence >= float(tau)
    loss = logits.sum() * 0.0 if not bool(accepted.any()) else F.cross_entropy(logits[accepted], labels[accepted])
    return loss, labels, accepted


def binary_task_class_count(config: Mapping[str, Any] | Any) -> int:
    """Resolve the classifier cardinality from the binary task, never from labels."""
    task_id = getattr(config, "task_id", None)
    class_order = getattr(config, "class_order", None)
    if isinstance(config, Mapping):
        task_id = config.get("task_id", config.get("task"))
        class_order = config.get("class_order", class_order)
        model = config.get("model", config)
        configured = model.get("num_classes") if isinstance(model, Mapping) else None
    else:
        model = getattr(config, "model", None)
        configured = getattr(model, "num_classes", None)
    if isinstance(task_id, str) and task_id.strip().lower() in {"cn_vs_impaired", "cn_vs_impaired_task"}:
        task_id = "cn_vs_impaired"
    if task_id != "cn_vs_impaired":
        raise BinaryLabelError("binary task_id=cn_vs_impaired is required")
    if class_order not in (None, list(BINARY_CLASS_ORDER), tuple(BINARY_CLASS_ORDER)):
        raise BinaryLabelError("binary task class_order must be CN, Impaired")
    if configured not in (None, 2):
        raise BinaryLabelError("binary task rejects a three-class classifier configuration")
    return 2


def build_binary_model(method: str, config: Mapping[str, Any]) -> Any:
    """Build any Phase 18B model with the task-derived two-class head."""
    method_name = str(method).lower()
    if method_name in {"aagn", "faster_snn"}:
        return build_binary_baseline(method_name, config)
    if method_name not in {"source_only", "coral", "mmd", "cdan", "prototype_pseudo"}:
        raise BinaryLabelError(f"unsupported binary method: {method!r}")
    from acda3d.models.acda3d import build_acda3d

    values = dict(config)
    values["task_id"] = "cn_vs_impaired"
    values["class_order"] = list(BINARY_CLASS_ORDER)
    model = dict(values.get("model", values))
    model["num_classes"] = binary_task_class_count(values)
    values["model"] = model
    return build_acda3d(values)


def _binary_constructor_values(config: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise BinaryLabelError("binary model configuration must be a mapping")
    binary_task_class_count(config)
    if config.get("task_type") not in (None, "binary_classification"):
        raise BinaryLabelError("binary task requires task_type=binary_classification")
    if config.get("class_ids") not in (None, {"CN": 0, "Impaired": 1}):
        raise BinaryLabelError("binary class_ids must be CN=0 and Impaired=1")
    values = dict(config.get("model", {})) if isinstance(config.get("model"), Mapping) else {}
    if values.get("n_classes") not in (None, 2):
        raise BinaryLabelError("binary task rejects a three-class baseline configuration")
    reserved = {"task_id", "task", "task_type", "class_order", "class_ids", "model"}
    values.update({key: value for key, value in config.items() if key not in reserved})
    values.pop("num_classes", None)
    values["n_classes"] = 2
    return values


def build_binary_baseline(name: str, config: Mapping[str, Any]) -> Any:
    """Build AAGN or FasterSNN from the explicit CN-vs-Impaired task contract."""
    from acda3d.models.baselines.faster_snn import FasterSNNBaseline
    from acda3d.models.baselines.roi_aware_gating import ROIAwareGatingBaseline

    baseline_id = str(name).strip().lower()
    if baseline_id not in BINARY_BASELINES:
        raise BinaryLabelError(f"unsupported binary baseline: {name!r}")
    values = _binary_constructor_values(config)
    if baseline_id == "aagn":
        if values.get("roi_masks") is None:
            raise BinaryLabelError("binary AAGN requires roi_masks")
        model = ROIAwareGatingBaseline(**values)
    else:
        values.pop("roi_masks", None)
        model = FasterSNNBaseline(**values)
    constructor_identity = dict(values)
    roi_masks = constructor_identity.get("roi_masks")
    if hasattr(roi_masks, "detach"):
        constructor_identity["roi_masks"] = {
            "dtype": str(roi_masks.dtype),
            "shape": list(roi_masks.shape),
            "sha256": hashlib.sha256(roi_masks.detach().cpu().contiguous().numpy().tobytes()).hexdigest(),
        }
    identity = build_binary_identity(
        "model_checkpoint",
        {"method": "baseline", "baseline_id": baseline_id, "constructor": constructor_identity},
    )
    model.binary_metadata = {
        "task_id": "cn_vs_impaired",
        "task_type": "binary_classification",
        "class_order": list(BINARY_CLASS_ORDER),
        "class_to_index": dict(BINARY_CLASS_TO_INDEX),
        "n_classes": 2,
        "identity_hash": identity["identity_hash"],
        "validate_only": True,
        "real_run": False,
    }
    return model


def validate_binary_baseline(name: str, config: Mapping[str, Any]) -> dict[str, Any]:
    """Run one baseline forward on a deterministic synthetic CPU batch only."""
    import torch

    baseline_id = str(name).strip().lower()
    model_config = dict(config)
    if baseline_id == "aagn" and "roi_masks" not in model_config:
        model_config["roi_masks"] = torch.ones(2, 2, 2, 2)
    torch.manual_seed(18_004)
    model = build_binary_baseline(baseline_id, model_config)
    model.eval()
    with torch.no_grad():
        output = model(torch.randn(2, 1, 17, 17, 17))
    logits = output["logits"] if isinstance(output, Mapping) else output
    if tuple(logits.shape) != (2, 2) or not torch.isfinite(logits).all():
        raise BinaryLabelError("binary baseline validation requires finite logits shaped (B,2)")
    return {
        "method": baseline_id,
        "logits_shape": tuple(logits.shape),
        "class_order": BINARY_CLASS_ORDER,
        "prediction_keys": ("prob_cn", "prob_impaired"),
        "device": logits.device.type,
        "validate_only": True,
        "real_run": False,
        "identity_hash": model.binary_metadata["identity_hash"],
    }


def binary_model_architecture_identity(model: Any) -> str:
    """Return a stable architecture identity for task-scoped binary validation."""
    model_name = getattr(model, "model_variant", None) or getattr(model, "public_name", None)
    if model_name:
        return str(model_name)
    return f"{type(model).__module__}.{type(model).__qualname__}"


def build_binary_ablation(
    candidate: str,
    config: Mapping[str, Any],
    *,
    base_method: str = _PROTOTYPE_PSEUDO_BASE_METHOD,
) -> Any:
    """Build one task-bound binary ablation in its explicit method namespace.

    The default remains the historical prototype-pseudo namespace. MMD candidates
    opt in explicitly so their registry semantics cannot alter legacy behavior.
    """
    from acda3d.models.ablations.mean_pooling import build_mean_pool_model
    from acda3d.models.acda3d import build_acda3d

    candidate_id = str(candidate).strip()
    plan = binary_ablation_plan(candidate_id, base_method=base_method)
    values = dict(config)
    binary_task_class_count(values)
    model_values = dict(values.get("model", values)) if isinstance(values.get("model", values), Mapping) else {}
    model_values["num_classes"] = 2
    model_values.setdefault("name", "3D-ACDA")
    model_values.setdefault("num_rois", 2)
    encoder = dict(model_values.get("encoder") or {})
    tokenizer = dict(model_values.get("tokenizer") or {})
    concept = dict(model_values.get("concept_bottleneck") or {})
    token_processing = dict(model_values.get("token_processing") or {})
    kwargs = {
        "num_rois": int(model_values.get("num_rois", 2)),
        "feature_dim": int(tokenizer.get("feature_dim", encoder.get("output_channels", 8))),
        "token_dim": int(tokenizer.get("token_dim", 8)),
        "num_classes": 2,
        "base_channels": int(encoder.get("base_channels", 2)),
        "concept_hidden_dim": int(concept.get("hidden_dim", 4)),
        "token_dropout": float(token_processing.get("dropout", 0.0)),
        "concept_dropout": float(concept.get("dropout", 0.0)),
    }
    model = build_mean_pool_model(**kwargs) if candidate_id == "mean_pool" else build_acda3d({
        "task_id": "cn_vs_impaired",
        "task_type": "binary_classification",
        "class_order": list(BINARY_CLASS_ORDER),
        "class_ids": dict(BINARY_CLASS_TO_INDEX),
        **model_values,
    })
    if base_method == _MMD_BASE_METHOD:
        intervention = plan.to_dict()
    else:
        spec = get_ablation_spec(candidate_id)
        intervention = spec.intervention.to_dict() if spec.intervention is not None else None
    identity = build_binary_identity(
        "experiment",
        {
            "method": "ablation",
            "base_method": base_method,
            "candidate_id": candidate_id,
            "intervention": intervention,
        },
    )
    model.binary_metadata = {
        "task_id": "cn_vs_impaired",
        "task_type": "binary_classification",
        "class_order": list(BINARY_CLASS_ORDER),
        "class_to_index": dict(BINARY_CLASS_TO_INDEX),
        "n_classes": 2,
        "base_method": base_method,
        "candidate_id": candidate_id,
        "intervention": intervention,
        "ablation_plan": plan.to_dict(),
        "architecture_identity": binary_model_architecture_identity(model),
        "identity_hash": identity["identity_hash"],
        "validate_only": True,
        "real_run": False,
    }
    return model


def binary_prediction_from_logits(logits: Any) -> dict[str, Any]:
    """Serialize only the active binary probability schema from two logits."""
    import torch
    from torch.nn import functional as F

    if not torch.is_tensor(logits) or logits.ndim != 2 or logits.shape[1] != 2:
        raise BinaryLabelError("binary prediction logits must have shape (B,2)")
    probabilities = F.softmax(logits, dim=-1)
    if probabilities.shape[0] != 1:
        raise BinaryLabelError("binary prediction serializer expects one row")
    row = probabilities[0]
    return {
        "prob_cn": float(row[0]),
        "prob_impaired": float(row[1]),
        "predicted_label": int(row.argmax()),
    }


def binary_experiment_matrix() -> dict[str, Any]:
    methods = ("source_only", "coral", "mmd", "cdan", "prototype_pseudo", "aagn", "faster_snn")
    ablations = BINARY_ABLATIONS
    return {
        "schema_version": "phase18b.matrix.v1",
        "task": BINARY_TASK,
        "class_order": list(BINARY_CLASS_ORDER),
        "methods": list(methods),
        "ablations": list(ablations),
        "directions": ["ADNI_to_OASIS", "OASIS_to_ADNI"],
        "real_run": False,
        "publication_metrics": False,
        "phase_19_forbidden": True,
    }


def binary_freeze_identity(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    identity = build_binary_identity("freeze", payload or {})
    identity.update({
        "freeze_approved": False,
        "real_execution_authorized": False,
        "publication_authorized": False,
        "phase_19_forbidden": True,
    })
    return identity


def build_binary_identity(family: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if family not in BINARY_IDENTITY_FAMILIES:
        raise BinaryLabelError(f"unsupported binary identity family: {family!r}")
    data = dict(payload)
    historical = json.dumps(data, sort_keys=True).lower()
    if (
        "cn_vs_mci_vs_ad" in historical
        or data.get("num_classes") == 3
        or data.get("class_order") == ["CN", "MCI", "AD"]
        or data.get("class_order") == ("CN", "MCI", "AD")
    ):
        raise BinaryLabelError("historical three-class identity collision")
    identity = {
        "schema_version": "phase18b.identity.v1",
        "phase": "18B",
        "identity_family": family,
        "task_id": "cn_vs_impaired",
        "task": BINARY_TASK,
        "class_order": list(BINARY_CLASS_ORDER),
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "provenance": {"source": "binary-contract", "real_run": False},
        "inputs": data,
    }
    identity["identity_hash"] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return identity

# Task-scoped Phase 18B evaluation implementation.  Historical three-class
# helpers above remain intentionally unchanged.
_BINARY_REQUIRED_METRICS = (
    "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "sensitivity",
    "specificity", "mcc", "cohen_kappa", "roc_auc", "pr_auc", "log_loss", "brier_score",
)


def _binary_metric(value: float | None, reason: str | None = None) -> dict[str, Any]:
    return {"value": value, "reason": reason}


def _binary_missing_class(labels: Sequence[int]) -> str | None:
    return None if set(labels) == {0, 1} else "missing_true_class"


def evaluate_binary_predictions(rows: Sequence[Mapping[str, Any]]) -> BinaryEvaluationResult:
    """Evaluate subject rows in the fixed ``CN, Impaired`` task space.

    Every unavailable metric is represented as ``{"value": None, "reason": ...}``.
    This task-scoped entry point deliberately does not call the historical
    three-class evaluator.
    """
    predictions: list[BinaryPrediction] = []
    labels: list[int] = []
    for row in rows:
        label = row.get("true_label", row.get("true_label_index"))
        if isinstance(label, bool) or label not in (0, 1):
            raise BinaryLabelError("true_label must be 0 or 1")
        predictions.append(BinaryPrediction.from_mapping(row))
        labels.append(int(label))
    matrix = [[0, 0], [0, 0]]
    for label, prediction in zip(labels, predictions, strict=True):
        matrix[label][prediction.predicted_label] += 1
    total = len(labels)
    support_reason = _binary_missing_class(labels)
    tp = matrix[1][1]
    fp = matrix[0][1]
    fn = matrix[1][0]
    tn = matrix[0][0]
    accuracy = _binary_metric(
        (tn + tp) / total if total else None,
        None if total else "zero_support",
    )
    recalls = []
    f1_values = []
    weighted_terms = []
    for index in (0, 1):
        support = sum(matrix[index])
        predicted = matrix[0][index] + matrix[1][index]
        class_tp = matrix[index][index]
        class_fp = predicted - class_tp
        class_fn = support - class_tp
        recalls.append(None if support == 0 else class_tp / support)
        denominator = 2 * class_tp + class_fp + class_fn
        f1_values.append(None if denominator == 0 else 2 * class_tp / denominator)
        if support:
            weighted_terms.append((support, f1_values[-1]))
    balanced = _binary_metric(
        math.fsum(value for value in recalls if value is not None) / 2
        if support_reason is None else None,
        support_reason,
    )
    macro_f1 = _binary_metric(
        math.fsum(value for value in f1_values if value is not None) / 2
        if support_reason is None else None,
        support_reason,
    )
    weighted_f1 = _binary_metric(
        math.fsum(support * float(value) for support, value in weighted_terms) / total
        if total and all(value is not None for _, value in weighted_terms) and support_reason is None
        else None,
        None if total and support_reason is None else ("zero_support" if not total else support_reason),
    )
    sensitivity = _binary_metric(
        tp / (tp + fn) if tp + fn else None,
        None if tp + fn else "zero_support",
    )
    specificity = _binary_metric(
        tn / (tn + fp) if tn + fp else None,
        None if tn + fp else "zero_support",
    )
    mcc_denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = _binary_metric(
        (tp * tn - fp * fn) / mcc_denominator if mcc_denominator else None,
        None if mcc_denominator else "zero_denominator",
    )
    expected = ((tn + fp) * (tn + fn) + (fn + tp) * (fp + tp)) / (total * total) if total else 0.0
    observed = (tn + tp) / total if total else 0.0
    kappa_denominator = 1.0 - expected
    kappa = _binary_metric(
        (observed - expected) / kappa_denominator if total and kappa_denominator else None,
        "zero_support" if total == 0 else (None if kappa_denominator else "zero_denominator"),
    )
    scores = [prediction.prob_impaired for prediction in predictions]
    roc_auc = _binary_auc(labels, scores) if support_reason is None else _binary_metric(None, support_reason)
    if support_reason is None:
        order = sorted(range(total), key=lambda index: (-scores[index], index))
        positives = sum(labels)
        precision_sum = 0.0
        seen_positives = 0
        for rank, index in enumerate(order, start=1):
            if labels[index] == 1:
                seen_positives += 1
                precision_sum += seen_positives / rank
        pr_auc = _binary_metric(precision_sum / positives if positives else None, None if positives else "missing_positive_support")
    else:
        pr_auc = _binary_metric(None, support_reason)
    if total and support_reason is None:
        clipped = [min(max(score, 1e-15), 1.0 - 1e-15) for score in scores]
        log_loss_value = -math.fsum(
            math.log(clipped[index] if labels[index] else 1.0 - clipped[index])
            for index in range(total)
        ) / total
    else:
        log_loss_value = None
    log_loss_metric = _binary_metric(log_loss_value, None if log_loss_value is not None else ("zero_support" if not total else support_reason))
    brier = _binary_metric(
        math.fsum((scores[index] - labels[index]) ** 2 for index in range(total)) / total if total else None,
        None if total else "zero_support",
    )
    metrics = {
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "mcc": mcc,
        "cohen_kappa": kappa,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "log_loss": log_loss_metric,
        "brier_score": brier,
        # Compatibility aliases retained for task-scoped callers.
        "precision_impaired": _binary_metric(
            tp / (tp + fp) if tp + fp else None,
            None if tp + fp else "zero_denominator",
        ),
        "recall_impaired": sensitivity,
        "sensitivity_impaired": sensitivity,
        "specificity_cn": specificity,
        "f1_impaired": _binary_metric(
            2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            None if 2 * tp + fp + fn else "zero_denominator",
        ),
        "auc_roc": roc_auc,
        "source_validation_macro_f1": macro_f1,
    }
    return BinaryEvaluationResult(
        confusion_matrix=(tuple(matrix[0]), tuple(matrix[1])),
        metrics=metrics,
        class_order=BINARY_CLASS_ORDER,
    )
