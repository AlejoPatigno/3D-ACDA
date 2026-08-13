"""Exact-byte, fail-closed provenance validation for Phase 18 planning inputs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .schemas import CANONICALIZATION_PROFILE

SCHEMA_VERSION = "phase18.manifest.v1"
_TARGET_VERIFIER_AUTHORITY = object()
TARGET_ADAPTATION_FIELDS = frozenset({"x", "subject_id", "subject_hash", "cohort"})
TARGET_MONITORING_LABEL = "MONITORING ONLY — NOT A TRAINING LOSS"
_TARGET_FORBIDDEN_FIELDS = frozenset(
    {
        "anatomical_target",
        "anatomical_targets",
        "artifact",
        "artifacts",
        "checkpoint",
        "class_label",
        "concept",
        "concept_target",
        "concept_targets",
        "concepts",
        "diagnosis",
        "gradient",
        "gradients",
        "jacobian",
        "jacobian_target",
        "jacobian_targets",
        "jacobians",
        "label",
        "labels",
        "loss",
        "model",
        "optimizer",
        "probability",
        "probabilities",
        "pseudo_label",
        "pseudo_labels",
        "selection",
        "selection_usage",
        "supervision",
        "target",
        "targets",
        "training_loss",
        "true_label",
        "y",
    }
    )
_TARGET_BATCH_NESTED_FORBIDDEN_FIELDS = _TARGET_FORBIDDEN_FIELDS | {
    "cohort",
    "role",
    "subject_hash",
    "subject_id",
}
_TARGET_EVALUATION_USAGE_FIELDS = frozenset(
    {
        "checkpoint",
        "epoch",
        "fold",
        "hyperparameter",
        "loss",
        "method",
        "read_only",
        "seed",
        "selection",
        "selection_usage",
        "training_loss",
    }
)


def validate_target_adaptation_batch(batch: Mapping[str, Any]) -> None:
    """Enforce the four-key, unlabeled target-adaptation firewall."""

    if not isinstance(batch, Mapping) or set(batch) != TARGET_ADAPTATION_FIELDS:
        raise ValueError("target adaptation batch must contain exactly x, subject_id, subject_hash, cohort")
    if batch["x"] is None:
        raise ValueError("target adaptation x is required")
    _validate_identity_text(batch["subject_id"], "subject_id")
    _validate_identity_text(batch["subject_hash"], "subject_hash")
    _validate_identity_text(batch["cohort"], "cohort")
    for key, value in batch.items():
        _reject_nested_fields(
            value,
            context=f"target adaptation {key}",
            fields=_TARGET_BATCH_NESTED_FORBIDDEN_FIELDS,
        )


def validate_target_evaluation_metadata(metadata: Mapping[str, Any]) -> None:
    """Require target evaluation to be exactly monitoring-only and read-only."""

    if not isinstance(metadata, Mapping):
        raise ValueError("target evaluation metadata must be a mapping")
    if metadata.get("monitoring_label") != TARGET_MONITORING_LABEL:
        raise ValueError("target evaluation monitoring label is required")
    if type(metadata.get("selection_usage")) is not bool or metadata["selection_usage"] is not False:
        raise ValueError("target evaluation metadata must be read-only and selection_usage=false")
    if type(metadata.get("read_only")) is not bool or metadata["read_only"] is not True:
        raise ValueError("target evaluation metadata must be read-only and selection_usage=false")
    for key, value in metadata.items():
        if key in {"monitoring_label", "selection_usage", "read_only"}:
            continue
        _reject_nested_fields(value, context="target evaluation metadata", fields=_TARGET_EVALUATION_USAGE_FIELDS)


def _validate_identity_text(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty identity string")


def _reject_nested_fields(
    value: Any, *, context: str, fields: frozenset[str] = _TARGET_FORBIDDEN_FIELDS
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = key.casefold() if isinstance(key, str) else str(key).casefold()
            if normalized in fields:
                raise ValueError(f"{context} contains forbidden supervision or artifact field: {key}")
            _reject_nested_fields(nested, context=context, fields=fields)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _reject_nested_fields(nested, context=context, fields=fields)


def _validate_target_manifest_records(
    records: Sequence[Mapping[str, Any]], *, role: str, cohort: str
) -> None:
    if role not in {"target_adaptation", "target_evaluation"}:
        return
    _validate_identity_text(cohort, "cohort")
    seen_subject_ids: set[str] = set()
    seen_subject_hashes: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("target manifest records must be objects")
        _validate_identity_text(record.get("subject_id"), "subject_id")
        _validate_identity_text(record.get("subject_hash"), "subject_hash")
        if record.get("cohort") != cohort:
            raise ValueError("target manifest record cohort does not match manifest cohort")
        if record.get("role") not in {None, role}:
            raise ValueError("target manifest record role does not match manifest role")
        if record["subject_id"] in seen_subject_ids or record["subject_hash"] in seen_subject_hashes:
            raise ValueError("target manifest subject identities must be unique")
        seen_subject_ids.add(record["subject_id"])
        seen_subject_hashes.add(record["subject_hash"])
        _reject_nested_fields(record, context=f"{role} manifest record")


def _validate_target_manifest_value(value: Any, *, role: str) -> None:
    if isinstance(value, ManifestValidation):
        if not _is_verifier_issued_manifest(value, expected_role=role):
            raise ValueError(f"{role} manifest is not verifier-issued")
        return
    if not isinstance(value, Mapping):
        raise ValueError(f"{role} manifest must contain verified records")
    if set(value) == TARGET_ADAPTATION_FIELDS and role == "target_adaptation":
        validate_target_adaptation_batch(value)
        return
    raise ValueError(f"{role} manifest must be a verifier-issued validated record")


class ProvenanceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    BLOCKED_DATA = "BLOCKED_DATA"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    OVERLAPPING_ASSIGNMENTS = "OVERLAPPING_ASSIGNMENTS"


@dataclass(frozen=True)
class ExactFileHash:
    path: str
    algorithm: str
    canonicalization_version: str
    sha256: str
    byte_size: int


@dataclass(frozen=True)
class ManifestValidation:
    status: ProvenanceStatus
    sha256: str | None
    byte_size: int | None
    records: tuple[Mapping[str, Any], ...]
    subject_hashes: frozenset[str]
    parsed: bool
    role: str | None
    cohort: str | None
    schema_version: str | None = None
    reason: str | None = None
    overlap: frozenset[str] = frozenset()
    _raw_bytes: bytes | None = field(default=None, repr=False, compare=False)
    _adapter: str | None = field(default=None, repr=False, compare=False)
    _authority_marker: object | None = field(default=None, repr=False, compare=False)
    _disjoint_fingerprint: tuple[Any, ...] | None = field(default=None, repr=False, compare=False)

    @property
    def ok(self) -> bool:
        return self.status is ProvenanceStatus.VERIFIED


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(nested) for key, nested in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_value(nested) for nested in value)
    return value


def _is_verifier_issued_manifest(
    value: ManifestValidation, *, expected_role: str | None = None
) -> bool:
    if (
        value._authority_marker is not _TARGET_VERIFIER_AUTHORITY
        or value.status is not ProvenanceStatus.VERIFIED
        or value.parsed is not True
        or value.schema_version != SCHEMA_VERSION
        or (expected_role is not None and value.role != expected_role)
        or not isinstance(value.role, str)
        or not isinstance(value.cohort, str)
        or not isinstance(value._raw_bytes, bytes)
        or value._adapter not in {"json", "yaml", "csv", "tsv"}
        or value.sha256 != hash_exact_bytes(value._raw_bytes)
        or value.byte_size != len(value._raw_bytes)
    ):
        return False
    try:
        document = parse_manifest_bytes(value._raw_bytes, adapter=value._adapter)
        records, role, cohort, one_scan = _extract_document(
            document, value._adapter, SCHEMA_VERSION
        )
        _validate_records(
            records,
            role=role,
            cohort=cohort,
            expected_role=value.role,
            expected_cohort=value.cohort,
            one_scan_per_subject=one_scan,
        )
        _validate_record_identity_consistency(records)
        if role in {"target_adaptation", "target_evaluation"}:
            _validate_target_manifest_records(records, role=role, cohort=cohort)
        expected_records = tuple(_freeze_value(record) for record in records)
        actual_subject_hashes = frozenset(str(record["subject_hash"]) for record in records)
    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        expected_records == value.records
        and actual_subject_hashes == value.subject_hashes
        and role == value.role
        and cohort == value.cohort
    )


def _validate_record_identity_consistency(records: Sequence[Mapping[str, Any]]) -> None:
    subject_ids: set[str] = set()
    subject_hashes: set[str] = set()
    for record in records:
        subject_id = record.get("subject_id")
        subject_hash = record.get("subject_hash")
        _validate_identity_text(subject_id, "subject_id")
        _validate_identity_text(subject_hash, "subject_hash")
        if subject_id in subject_ids or subject_hash in subject_hashes:
            raise ValueError("subject identities must be unique")
        subject_ids.add(subject_id)
        subject_hashes.add(subject_hash)


def hash_exact_bytes(data: bytes) -> str:
    """Hash the supplied bytes without decoding, normalizing, or rewriting them."""

    return hashlib.sha256(data).hexdigest()


def hash_exact_file(path: str | Path) -> ExactFileHash:
    """Return the SHA-256 identity of exact file bytes."""

    file_path = Path(path)
    data = file_path.read_bytes()
    return ExactFileHash(
        path=str(file_path),
        algorithm="sha256",
        canonicalization_version=CANONICALIZATION_PROFILE,
        sha256=hash_exact_bytes(data),
        byte_size=len(data),
    )


def parse_manifest_bytes(data: bytes, *, adapter: str) -> Mapping[str, Any]:
    """Parse only through a named adapter; extension-based inference is forbidden."""

    if adapter == "json":
        value = json.loads(data.decode("utf-8"))
    elif adapter == "yaml":
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise ValueError("yaml adapter is unavailable") from exc
        value = yaml.safe_load(data.decode("utf-8"))
    elif adapter in {"csv", "tsv"}:
        delimiter = "," if adapter == "csv" else "\t"
        reader = csv.DictReader(io.StringIO(data.decode("utf-8")), delimiter=delimiter)
        value = {"records": [dict(row) for row in reader]}
    else:
        raise ValueError("adapter must be one of json, yaml, csv, or tsv")
    if not isinstance(value, Mapping):
        raise ValueError("manifest root must be an object")
    return value


def validate_manifest(
    path: str | Path,
    *,
    adapter: str,
    declared_sha256: str | None,
    expected_schema_version: str = SCHEMA_VERSION,
    expected_role: str | None = None,
    expected_cohort: str | None = None,
    expected_subject_hashes: set[str] | frozenset[str] | None = None,
) -> ManifestValidation:
    """Verify exact bytes, then validate one explicit manifest schema adapter."""

    file_path = Path(path)
    try:
        data = file_path.read_bytes()
    except FileNotFoundError:
        return _failure(ProvenanceStatus.BLOCKED_DATA, "manifest file is missing")
    actual_sha256 = hash_exact_bytes(data)
    if declared_sha256 is None or actual_sha256 != declared_sha256:
        return ManifestValidation(
            status=ProvenanceStatus.PROVENANCE_MISMATCH,
            sha256=actual_sha256,
            byte_size=len(data),
            records=(),
            subject_hashes=frozenset(),
            parsed=False,
            role=None,
            cohort=None,
            reason="declared SHA-256 does not match exact file bytes",
        )
    try:
        document = parse_manifest_bytes(data, adapter=adapter)
        records, role, cohort, one_scan_per_subject = _extract_document(
            document, adapter, expected_schema_version
        )
        _validate_records(
            records,
            role=role,
            cohort=cohort,
            expected_role=expected_role,
            expected_cohort=expected_cohort,
            one_scan_per_subject=one_scan_per_subject,
        )
        _validate_target_manifest_records(records, role=role, cohort=cohort)
    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ManifestValidation(
            status=ProvenanceStatus.INVALID_SCHEMA,
            sha256=actual_sha256,
            byte_size=len(data),
            records=(),
            subject_hashes=frozenset(),
            parsed=True,
            role=None,
            cohort=None,
            reason=str(exc),
        )
    subject_hashes = frozenset(str(record["subject_hash"]) for record in records)
    frozen_records = tuple(_freeze_value(record) for record in records)
    if expected_subject_hashes is not None and subject_hashes != frozenset(expected_subject_hashes):
        return ManifestValidation(
            status=ProvenanceStatus.INVALID_SCHEMA,
            sha256=actual_sha256,
            byte_size=len(data),
            records=frozen_records,
            subject_hashes=subject_hashes,
            parsed=True,
            role=role,
            cohort=cohort,
            schema_version=expected_schema_version,
            reason="manifest subject coverage does not match the supplied expectation",
        )
    return ManifestValidation(
        status=ProvenanceStatus.VERIFIED,
        sha256=actual_sha256,
        byte_size=len(data),
        records=frozen_records,
        subject_hashes=subject_hashes,
        parsed=True,
        role=role,
        cohort=cohort,
        schema_version=expected_schema_version,
        _raw_bytes=data,
        _adapter=adapter,
        _authority_marker=_TARGET_VERIFIER_AUTHORITY,
    )


def check_assignment_disjointness(
    target_adaptation: ManifestValidation,
    target_evaluation: ManifestValidation,
) -> ManifestValidation:
    """Check parsed subject identities, never aggregate manifest hashes."""

    if not _is_verifier_issued_manifest(target_adaptation, expected_role="target_adaptation"):
        return _failure(
            ProvenanceStatus.INVALID_SCHEMA,
            "target adaptation must be verifier-issued and byte/hash bound",
        )
    if not _is_verifier_issued_manifest(target_evaluation, expected_role="target_evaluation"):
        return _failure(
            ProvenanceStatus.INVALID_SCHEMA,
            "target evaluation must be verifier-issued and byte/hash bound",
        )
    if target_adaptation.role != "target_adaptation":
        return _failure(ProvenanceStatus.INVALID_SCHEMA, "adaptation role is invalid")
    if target_evaluation.role != "target_evaluation":
        return _failure(ProvenanceStatus.INVALID_SCHEMA, "evaluation role is invalid")
    if target_adaptation.cohort != target_evaluation.cohort:
        return _failure(
            ProvenanceStatus.INVALID_SCHEMA,
            "target adaptation and evaluation cohorts must match",
        )
    overlap = target_adaptation.subject_hashes & target_evaluation.subject_hashes
    fingerprint = _disjoint_fingerprint(target_adaptation, target_evaluation)
    if overlap:
        return ManifestValidation(
            status=ProvenanceStatus.OVERLAPPING_ASSIGNMENTS,
            sha256=None,
            byte_size=None,
            records=(),
            subject_hashes=frozenset(),
            parsed=True,
            role="disjoint_assignments",
            cohort=target_adaptation.cohort,
            reason="target adaptation and evaluation subject identities overlap",
            overlap=frozenset(overlap),
            _authority_marker=_TARGET_VERIFIER_AUTHORITY,
            _disjoint_fingerprint=fingerprint,
        )
    return ManifestValidation(
        status=ProvenanceStatus.VERIFIED,
        sha256=None,
        byte_size=None,
        records=(),
        subject_hashes=frozenset(),
        parsed=True,
        role="disjoint_assignments",
        cohort=target_adaptation.cohort,
        _authority_marker=_TARGET_VERIFIER_AUTHORITY,
        _disjoint_fingerprint=fingerprint,
    )


def _disjoint_fingerprint(
    target_adaptation: ManifestValidation, target_evaluation: ManifestValidation
) -> tuple[Any, ...]:
    return (
        target_adaptation.sha256,
        target_evaluation.sha256,
        target_adaptation.role,
        target_evaluation.role,
        target_adaptation.cohort,
        target_evaluation.cohort,
        tuple(sorted(target_adaptation.subject_hashes)),
        tuple(sorted(target_evaluation.subject_hashes)),
    )


def _is_verified_disjoint_result(value: Any) -> bool:
    return (
        isinstance(value, ManifestValidation)
        and value._authority_marker is _TARGET_VERIFIER_AUTHORITY
        and value._disjoint_fingerprint is not None
        and value.role == "disjoint_assignments"
        and value.parsed is True
        and value.status in {
            ProvenanceStatus.VERIFIED,
            ProvenanceStatus.OVERLAPPING_ASSIGNMENTS,
        }
    )


def _extract_document(
    document: Mapping[str, Any], adapter: str, expected_schema_version: str
) -> tuple[list[Mapping[str, Any]], str, str, bool]:
    schema_version = document.get("schema_version")
    if adapter in {"csv", "tsv"}:
        records_value = document.get("records")
        if not isinstance(records_value, list) or not records_value:
            raise ValueError("manifest records are required")
        first = records_value[0]
        if not isinstance(first, Mapping):
            raise ValueError("manifest records must be objects")
        schema_version = first.get("schema_version")
        role = first.get("role")
        cohort = first.get("cohort")
        one_scan = _as_bool(first.get("one_scan_per_subject", False))
    else:
        records_value = document.get("records")
        if not isinstance(records_value, list) or not records_value:
            raise ValueError("manifest records are required")
        role = document.get("role")
        cohort = document.get("cohort")
        one_scan = _as_bool(document.get("one_scan_per_subject", False))
    if schema_version != expected_schema_version:
        raise ValueError(f"schema_version must be {expected_schema_version}")
    if not isinstance(role, str) or not role:
        raise ValueError("manifest role is required")
    if not isinstance(cohort, str) or not cohort:
        raise ValueError("manifest cohort is required")
    records = [record for record in records_value if isinstance(record, Mapping)]
    if len(records) != len(records_value):
        raise ValueError("manifest records must be objects")
    if adapter in {"csv", "tsv"}:
        for record in records:
            if record.get("schema_version") != expected_schema_version:
                raise ValueError(f"every record schema_version must be {expected_schema_version}")
    return records, role, cohort, one_scan


def _validate_records(
    records: list[Mapping[str, Any]],
    *,
    role: str,
    cohort: str,
    expected_role: str | None,
    expected_cohort: str | None,
    one_scan_per_subject: bool,
) -> None:
    if expected_role is not None and role != expected_role:
        raise ValueError("manifest role does not match expected role")
    if expected_cohort is not None and cohort != expected_cohort:
        raise ValueError("manifest cohort does not match expected cohort")
    identities: set[str] = set()
    for record in records:
        subject_id = record.get("subject_id")
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("each record requires a supplied subject_id")
        subject_hash = record.get("subject_hash")
        if not isinstance(subject_hash, str) or not subject_hash.strip():
            raise ValueError("each record requires a supplied subject_hash")
        if subject_hash in identities:
            raise ValueError("subject identities must be unique")
        identities.add(subject_hash)
        if record.get("role") not in {None, role}:
            raise ValueError("record role does not match manifest role")
        if record.get("cohort") not in {None, cohort}:
            raise ValueError("record cohort does not match manifest cohort")
    _validate_record_identity_consistency(records)
    if one_scan_per_subject and len(identities) != len(records):
        raise ValueError("one scan per subject is violated")


def _as_bool(value: Any) -> bool:
    if type(value) is not bool:
        raise ValueError("one_scan_per_subject must be a bool")
    return value


def _failure(status: ProvenanceStatus, reason: str) -> ManifestValidation:
    return ManifestValidation(
        status=status,
        sha256=None,
        byte_size=None,
        records=(),
        subject_hashes=frozenset(),
        parsed=False,
        role=None,
        cohort=None,
        reason=reason,
    )
