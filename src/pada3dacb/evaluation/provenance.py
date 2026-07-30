"""Read-only hashing, provenance hydration, and canonical row validation."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .schemas import (
    REQUIRED_PROVENANCE_FIELDS,
    CandidateIssue,
    CandidateStatus,
    CanonicalPrediction,
    Direction,
    IdentityMapping,
    InputFile,
    IssueCode,
    MethodId,
    PredictionRole,
    ProvenanceRecord,
    ProvenanceValue,
    UnsafePathError,
    canonical_json,
)

ApprovedSource = tuple[str, str, Mapping[str, Any]]
DerivationRule = tuple[str, str, str]


def _issue(code: IssueCode, status: CandidateStatus = CandidateStatus.EXCLUDED) -> CandidateIssue:
    return CandidateIssue(code=code, status=status)


def sha256_exact(path: Path, *, chunk_size: int = 1_048_576) -> str:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def confined_relative_path(root: Path, candidate: Path) -> str:
    resolved_root = root.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=True)
    try:
        relative = resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise UnsafePathError("configured input escapes runs_root") from error
    return relative.as_posix()


def inspect_input_file(
    root: Path,
    path: Path,
    schema_family: str,
    schema_version: str,
    declared_hash: str | None = None,
) -> tuple[InputFile | None, tuple[CandidateIssue, ...]]:
    try:
        relative_path = confined_relative_path(root, path)
    except FileNotFoundError:
        return None, (_issue(IssueCode.MISSING_REQUIRED_FIELD, CandidateStatus.INCOMPLETE),)
    digest = sha256_exact(path)
    if declared_hash is not None and digest != declared_hash:
        return None, (_issue(IssueCode.INPUT_HASH_MISMATCH),)
    return InputFile(relative_path, digest, path.stat().st_size, schema_family, schema_version), ()


def hydrate_provenance(
    row_values: Mapping[str, Any],
    row_sha256: str,
    approved_sources: Sequence[ApprovedSource] = (),
    derivation_rules: Mapping[str, DerivationRule] | None = None,
) -> tuple[ProvenanceRecord | None, tuple[CandidateIssue, ...]]:
    sources: tuple[ApprovedSource, ...] = (("row", row_sha256, row_values), *approved_sources)
    rules = derivation_rules or {}
    hydrated: dict[str, ProvenanceValue[Any]] = {}
    checks: list[str] = []
    issues: list[CandidateIssue] = []

    for field_name in REQUIRED_PROVENANCE_FIELDS:
        direct = [(kind, digest, values[field_name]) for kind, digest, values in sources if field_name in values]
        if direct:
            canonical_values = {canonical_json(item[2]) for item in direct}
            if len(canonical_values) != 1:
                issues.append(_issue(IssueCode.PROVENANCE_CONFLICT))
                continue
            kind, digest, value = direct[0]
            if len(direct) > 1:
                checks.append(f"{field_name}:equal")
            hydrated[field_name] = ProvenanceValue(field_name, value, kind, digest)
            continue

        rule = rules.get(field_name)
        derived = None
        if rule is not None:
            source_kind, source_field, rule_name = rule
            for kind, digest, values in sources:
                if kind == source_kind and source_field in values:
                    derived = ProvenanceValue(field_name, values[source_field], kind, digest, rule_name)
                    break
        if derived is None:
            issues.append(_issue(IssueCode.MISSING_REQUIRED_FIELD))
        else:
            hydrated[field_name] = derived

    if issues:
        return None, tuple(issues)
    ordered = {field: hydrated[field] for field in REQUIRED_PROVENANCE_FIELDS}
    input_hashes = tuple(dict.fromkeys(digest for _, digest, _ in sources))
    return ProvenanceRecord(ordered, input_hashes, tuple(checks)), ()


def raw_identifier_persistence_issues(
    value: Any,
    raw_identifier_fields: Sequence[str],
    raw_identifier_values: Sequence[str] = (),
) -> tuple[CandidateIssue, ...]:
    """Reject raw identifier keys or values before canonical/log/output serialization."""
    fields = frozenset(raw_identifier_fields)
    values = frozenset(raw_identifier_values)

    def contains_raw(item: Any) -> bool:
        if isinstance(item, Mapping):
            return any(key in fields or contains_raw(nested) for key, nested in item.items())
        if isinstance(item, (list, tuple)):
            return any(contains_raw(nested) for nested in item)
        return isinstance(item, str) and item in values

    return (_issue(IssueCode.RAW_IDENTIFIER_PERSISTENCE_ATTEMPT),) if contains_raw(value) else ()


def verify_identity_mapping(
    prediction_rows: Sequence[Mapping[str, Any]],
    mapping_rows: Sequence[Mapping[str, Any]],
    mapping: IdentityMapping | None,
    mapping_path: Path,
) -> tuple[tuple[dict[str, Any], ...], tuple[CandidateIssue, ...]]:
    """Verify one approved supplied mapping and immediately discard transient raw identifiers."""
    requires_mapping = any("subject_hash" not in row for row in prediction_rows)
    if not requires_mapping and all(
        mapping is None or mapping.raw_identifier_field not in row for row in prediction_rows
    ):
        return tuple(dict(row) for row in prediction_rows), ()
    if mapping is None:
        return (), (_issue(IssueCode.UNAPPROVED_IDENTITY_MAPPING),)
    try:
        if sha256_exact(mapping_path) != mapping.sha256:
            return (), (_issue(IssueCode.UNAPPROVED_IDENTITY_MAPPING),)
    except OSError:
        return (), (_issue(IssueCode.UNAPPROVED_IDENTITY_MAPPING),)

    supplied: dict[str, str] = {}
    supplied_hashes: set[str] = set()
    for row in mapping_rows:
        raw_value = row.get(mapping.raw_identifier_field)
        subject_hash = row.get(mapping.subject_hash_field)
        if (
            not isinstance(raw_value, str)
            or not raw_value
            or not isinstance(subject_hash, str)
            or not subject_hash
            or raw_value in supplied
            or subject_hash in supplied_hashes
        ):
            return (), (_issue(IssueCode.UNSTABLE_SUBJECT_IDENTITY),)
        supplied[raw_value] = subject_hash
        supplied_hashes.add(subject_hash)

    normalized: list[dict[str, Any]] = []
    for row in prediction_rows:
        item = dict(row)
        raw_value = item.pop(mapping.raw_identifier_field, None)
        existing_hash = item.get(mapping.subject_hash_field)
        if raw_value is None:
            if not isinstance(existing_hash, str) or not existing_hash:
                return (), (_issue(IssueCode.UNSTABLE_SUBJECT_IDENTITY),)
        elif (
            not isinstance(raw_value, str)
            or raw_value not in supplied
            or (existing_hash is not None and existing_hash != supplied[raw_value])
        ):
            return (), (_issue(IssueCode.UNSTABLE_SUBJECT_IDENTITY),)
        else:
            item[mapping.subject_hash_field] = supplied[raw_value]
        normalized.append(item)

    persistence = raw_identifier_persistence_issues(
        normalized, (mapping.raw_identifier_field,), tuple(supplied)
    )
    return ((), persistence) if persistence else (tuple(normalized), ())


def _probability_issue(probabilities: Any) -> IssueCode | None:
    try:
        values = tuple(float(value) for value in probabilities)
    except (TypeError, ValueError):
        return IssueCode.PROBABILITY_SUM_INVALID
    if len(values) != 3:
        return IssueCode.PROBABILITY_SUM_INVALID
    if any(not math.isfinite(value) for value in values):
        return IssueCode.NON_FINITE_PROBABILITY
    if any(value < 0.0 or value > 1.0 for value in values):
        return IssueCode.PROBABILITY_OUT_OF_RANGE
    if abs(math.fsum(values) - 1.0) > 1e-6:
        return IssueCode.PROBABILITY_SUM_INVALID
    return None


def validate_prediction_rows(
    rows: Sequence[Mapping[str, Any]],
    method_id: MethodId,
    direction: Direction,
    seed: int,
    fold: int,
    logical_checkpoint: str,
    role: PredictionRole,
    provenance_ref: str,
) -> tuple[tuple[CanonicalPrediction, ...], tuple[CandidateIssue, ...]]:
    predictions: list[CanonicalPrediction] = []
    issues: list[CandidateIssue] = []
    labels: dict[str, int] = {}
    seen: set[str] = set()

    for row in rows:
        subject_hash = row.get("subject_hash")
        if not isinstance(subject_hash, str) or not subject_hash:
            issues.append(_issue(IssueCode.UNSTABLE_SUBJECT_IDENTITY))
            continue
        true_label = row.get("true_label")
        if not isinstance(true_label, int) or isinstance(true_label, bool) or true_label not in (0, 1, 2):
            issues.append(_issue(IssueCode.INCONSISTENT_TRUE_LABEL))
            continue
        if subject_hash in labels and labels[subject_hash] != true_label:
            issues.append(_issue(IssueCode.INCONSISTENT_TRUE_LABEL))
        labels.setdefault(subject_hash, true_label)
        if subject_hash in seen:
            issues.append(_issue(IssueCode.DUPLICATE_PREDICTION))
            continue
        seen.add(subject_hash)
        probability_issue = _probability_issue(row.get("probabilities"))
        if probability_issue is not None:
            issues.append(_issue(probability_issue))
            continue
        probabilities = tuple(float(value) for value in row["probabilities"])
        predictions.append(
            CanonicalPrediction(
                method_id, direction, seed, fold, logical_checkpoint, role,
                subject_hash, true_label, probabilities, provenance_ref,
            )
        )
    return tuple(predictions), tuple(issues)
