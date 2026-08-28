"""Typed common subject records for all Phase 6 dataset roles."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from acda3d.binary import (
    BINARY_CLASS_ORDER,
    BINARY_CLASS_TO_INDEX,
    BINARY_MAPPING_CONTRACT,
    OasisApprovalAttestation,
    OasisEvidence,
    validate_oasis_semantic_approval,
)
from acda3d.binary import (
    BinarySubjectRecord as _BinarySubjectRecord,
)
from acda3d.exceptions import DatasetContractError


class BinaryTaskRecord(_BinarySubjectRecord):
    """Task-scoped binary record with the OASIS no-MCI invariant."""

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.cohort == "OASIS" and self.original_label_name not in BINARY_CLASS_ORDER:
            raise DatasetContractError("OASIS binary records require verified CN/Impaired provenance; MCI is forbidden")


# Task-scoped name; the historical SubjectRecord remains unchanged.
BinarySubjectRecord = BinaryTaskRecord

CLASS_ORDER = ("CN", "MCI", "AD")
CLASS_TO_INDEX = {label: index for index, label in enumerate(CLASS_ORDER)}
SUPPORTED_COHORTS = {"ADNI", "OASIS"}


@dataclass(frozen=True)
class ArtifactRequirements:
    derivative: bool = True
    label: bool = True
    concept: bool = False
    jacobian: bool = False


REQUIREMENT_PROFILES = {
    "classification_only": ArtifactRequirements(),
    "source_with_concepts": ArtifactRequirements(concept=True),
    "source_with_anatomy": ArtifactRequirements(jacobian=True),
    "source_full_artifacts": ArtifactRequirements(concept=True, jacobian=True),
    "target_adaptation": ArtifactRequirements(label=False),
    "target_evaluation": ArtifactRequirements(),
}


@dataclass(frozen=True)
class SubjectRecord:
    subject_hash: str
    cohort: str
    class_label: str
    label_index: int
    derivative_path: Path
    subject_id: str | None = None
    concept_path: Path | None = None
    jacobian_path: Path | None = None
    preprocessing_configuration_hash: str | None = None
    precompute_configuration_hash: str | None = None
    atlas_hash: str | None = None
    concept_status: str | None = None
    jacobian_status: str | None = None
    original_inventory_row: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return f"{self.cohort}:{self.subject_hash}"

    @property
    def public_subject(self) -> str:
        return self.subject_id or self.subject_hash

    def validate(self) -> None:
        if self.cohort not in SUPPORTED_COHORTS:
            raise DatasetContractError(f"Unsupported cohort: {self.cohort!r}.")
        if self.class_label not in CLASS_TO_INDEX:
            raise DatasetContractError(f"Unsupported diagnostic label: {self.class_label!r}.")
        expected = CLASS_TO_INDEX[self.class_label]
        if self.label_index != expected:
            raise DatasetContractError(
                f"Label/index mismatch for {self.identity}: {self.class_label} requires {expected}, got {self.label_index}."
            )
        if not self.subject_hash.strip():
            raise DatasetContractError("subject_hash cannot be empty.")
        if not self.derivative_path.is_absolute():
            raise DatasetContractError(f"Derivative path is not resolved: {self.derivative_path}.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("derivative_path", "concept_path", "jacobian_path"):
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SubjectRecord:
        data = dict(payload)
        for key in ("derivative_path", "concept_path", "jacobian_path"):
            if data.get(key) is not None:
                data[key] = Path(data[key])
        record = cls(**data)
        record.validate()
        return record


def requirement_profile(name: str) -> ArtifactRequirements:
    try:
        return REQUIREMENT_PROFILES[name]
    except KeyError as error:
        raise DatasetContractError(f"Unknown dataset requirement profile: {name!r}.") from error


def _oasis_evidence_for_record(
    record: SubjectRecord,
    evidence: OasisEvidence | None,
    approval: OasisApprovalAttestation | None,
) -> tuple[OasisEvidence, Mapping[str, Any], str]:
    """Require an exact evidence object and a validator-minted approval."""
    if not isinstance(evidence, OasisEvidence):
        raise DatasetContractError("OASIS binary adaptation requires an OasisEvidence object")
    if not isinstance(approval, OasisApprovalAttestation) or approval._validated is not True:
        raise DatasetContractError("OASIS binary adaptation requires a validator-bound approval attestation")
    try:
        validate_oasis_semantic_approval(evidence, approval)
    except Exception as error:
        raise DatasetContractError(f"OASIS approval attestation is invalid: {error}") from error
    if evidence.evidence_verified is not True:
        raise DatasetContractError("OASIS binary evidence_verified must be true")
    if evidence.mapping_contract != BINARY_MAPPING_CONTRACT:
        raise DatasetContractError("OASIS binary evidence mapping contract is incompatible")
    matching = [item for item in evidence.records if isinstance(item, Mapping) and item.get("subject_hash") == record.subject_hash]
    if len(matching) != 1:
        raise DatasetContractError("OASIS binary evidence is not bound to this subject")
    matching_record = matching[0]
    required_record_fields = ("source_row_hash", "visit_hash", "person_hash", "original_metadata_value")
    if any(not isinstance(matching_record.get(field), str) or not matching_record.get(field) for field in required_record_fields):
        raise DatasetContractError("OASIS binary evidence record lacks complete de-identified provenance")
    for hash_field in ("source_row_hash", "visit_hash", "person_hash"):
        value = matching_record[hash_field]
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise DatasetContractError("OASIS binary evidence record contains an invalid provenance hash")
    if matching_record.get("person_hash") != record.subject_hash:
        raise DatasetContractError("OASIS binary evidence person provenance does not match the source record")
    try:
        source_cdr = float(matching_record["original_metadata_value"])
    except (TypeError, ValueError) as error:
        raise DatasetContractError("OASIS binary evidence original CDR is malformed") from error
    if not math.isfinite(source_cdr) or source_cdr not in {0.0, 0.5, 1.0, 2.0}:
        raise DatasetContractError("OASIS binary evidence original CDR is outside the verified domain")
    label = matching_record.get("binary_label_name")
    expected_label = "CN" if source_cdr == 0.0 else "Impaired"
    if label != expected_label or label not in BINARY_CLASS_ORDER or record.class_label != label:
        raise DatasetContractError("OASIS binary evidence label does not match the verified CDR source")
    return evidence, matching_record, label


def binary_record_from_subject_record(
    record: SubjectRecord,
    *,
    oasis_provenance_verified: bool = False,
    oasis_evidence: OasisEvidence | Mapping[str, Any] | None = None,
    oasis_approval: OasisApprovalAttestation | None = None,
) -> BinaryTaskRecord:
    """Adapt one historical record with validator-bound OASIS provenance."""
    if not isinstance(record, SubjectRecord):
        raise DatasetContractError("binary adaptation requires a SubjectRecord")
    record.validate()
    metadata = dict(record.metadata or {})
    subject_id = record.subject_id or record.subject_hash
    source_row = record.original_inventory_row if record.original_inventory_row is not None else record.identity
    evidence: OasisEvidence | None = None
    evidence_payload: Mapping[str, Any] | None = None
    if record.cohort == "ADNI":
        original_label = metadata.get("original_label_name", record.class_label)
    else:
        if oasis_provenance_verified:
            raise DatasetContractError("OASIS binary adaptation requires structured evidence, not a caller flag")
        evidence, matching_record, original_label = _oasis_evidence_for_record(
            record, oasis_evidence, oasis_approval
        )
        evidence_payload = evidence.to_dict()
        if metadata.get("mapping_contract") not in (None, BINARY_MAPPING_CONTRACT):
            raise DatasetContractError("OASIS binary mapping contract is incompatible")
    try:
        if record.cohort == "OASIS":
            adapted = BinaryTaskRecord(
                subject_hash=record.subject_hash,
                cohort="OASIS",
                original_label_name=original_label,
                binary_label_name=original_label,
                binary_label=BINARY_CLASS_TO_INDEX[original_label],
                source_row_hash=matching_record["source_row_hash"],
                derivative_path=record.derivative_path,
                mapping_contract=BINARY_MAPPING_CONTRACT,
                visit_hash=matching_record["visit_hash"],
                source_file_hash=metadata.get("source_file_hash") or evidence_payload["csv_sha256"],
                original_metadata_value=matching_record["original_metadata_value"],
                person_hash=record.subject_hash,
                visit_number=matching_record.get("visit_number"),
                canonical_visit=matching_record.get("canonical_visit") is True,
            )
        else:
            adapted = BinaryTaskRecord.from_source(
                cohort=record.cohort,
                subject_id=subject_id,
                original_label=original_label,
                source_row=source_row,
                derivative_path=record.derivative_path,
                visit_id=metadata.get("visit_id"),
                source_file_hash=metadata.get("source_file_hash"),
            )
            if record.subject_id is None and len(record.subject_hash) == 64 and all(char in "0123456789abcdef" for char in record.subject_hash):
                adapted = replace(adapted, subject_hash=record.subject_hash)
        return adapted
    except (TypeError, ValueError) as error:
        raise DatasetContractError(f"Invalid binary record provenance for {record.identity}: {error}") from error


# Explicit alias for callers that prefer adapter terminology.
adapt_subject_record_to_binary = binary_record_from_subject_record
