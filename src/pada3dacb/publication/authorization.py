"""Strict, read-only authorization checks for the Phase 18 real-run gate."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .canonical_json import identity_sha256, is_sha256
from .experiment_matrix import ExperimentMatrix, MatrixValidationError, matrix_content_hash
from .freeze import build_freeze_payload, collect_unresolved_blockers
from .provenance import (
    ManifestValidation,
    _is_verifier_issued_manifest,
)
from .schemas import FreezePayload, freeze_payload_hash
from .validation import ValidationBlocker, aggregate_validators, validate_matrix_input

PUBLICATION_SEEDS = (42, 43, 44)

HASH_FIELDS = (
    "freeze_hash",
    "scientific_resolution_hash",
    "method_parameter_ledger_hash",
    "canonicalization_conformance_hash",
    "matrix_hash",
    "method_inventory_hash",
    "seed_policy_hash",
    "configuration_hash",
    "code_revision",
    "environment_hash",
    "command_hash",
    "privacy_data_access_record_hash",
    "resource_budget_hash",
    "feasibility_observation_hash",
    "independent_review_hash",
    "statistical_review_hash",
    "human_authorization_hash",
    "native_receipt_hash",
    "target_identity",
    "target_hash",
)
_PLACEHOLDER_HASHES = {char * 64 for char in "0abcdef"}
ARTIFACT_HASH_FIELDS = (
    "atlas",
    "roi_order",
    "roi_masks",
    "concept_normalizer",
    "concept_targets",
    "jacobians",
)
_REQUIRED_FIELDS = (
    "schema_version",
    "phase_18_authorized",
    "freeze_approved",
    "real_execution_authorized",
    "publication_authorized",
    "phase_19_forbidden",
    "authorized",
    "freeze_payload",
    "method_parameter_ledger",
    "hash_evidence",
    "authorization_evidence",
    "privacy_data_access_record",
    "independent_review",
    "statistical_review",
    "human_authorization",
    *HASH_FIELDS,
    "method_inventory",
    "seed_policy",
    "split_manifest_hashes",
    "assignment_hashes",
    "assignment_manifest_contents",
    "provenance",
    "artifact_hashes",
    "configuration",
    "scientific_resolution",
    "resource_budget",
    "feasibility",
    "target_adaptation_batch",
    "target_evaluation_metadata",
)
_UNRESOLVED_STRINGS = {"", "null", "none", "unresolved", "unresolved_blocking", "pending"}
_NATIVE_RECEIPT_SCHEMA = "gentle-ai.review-receipt/v1"
_NATIVE_RECEIPT_GATE = "post-apply"
_NATIVE_RECEIPT_FIELDS = frozenset(
    {
        "source",
        "external",
        "schema",
        "lineage",
        "gate",
        "result",
        "authority_marker",
        "content",
        "sha256",
        "target_identity",
        "target_hash",
    }
)
_NATIVE_RECEIPT_CONTENT_FIELDS = frozenset(
    {"lineage", "gate", "result", "target_identity", "target_hash"}
)


@dataclass(frozen=True)
class AuthorizationBlocker:
    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class AuthorizationResult:
    authorized: bool
    blockers: tuple[AuthorizationBlocker, ...]
    data_access_opened: bool = False

    @property
    def ok(self) -> bool:
        return self.authorized and not self.blockers and not self.data_access_opened


def check_authorization(
    manifest: Mapping[str, Any],
    *,
    freeze_payload: Mapping[str, Any] | None = None,
    verifier: Callable[[object], bool] | None = None,
) -> AuthorizationResult:
    """Check every gate invariant; this function never opens a data path."""

    blockers: list[AuthorizationBlocker] = []
    if not isinstance(manifest, Mapping):
        return AuthorizationResult(False, (AuthorizationBlocker("missing_required_field", "authorization manifest is not a mapping"),))
    for field in _REQUIRED_FIELDS:
        if field not in manifest:
            blockers.append(AuthorizationBlocker("missing_required_field", f"required field is missing: {field}", field))
    blockers.extend(_check_flags(manifest))
    blockers.extend(_check_hashes(manifest))
    blockers.extend(_check_freeze_hash(manifest, freeze_payload))
    blockers.extend(_check_evidence(manifest))
    blockers.extend(_check_authorization_evidence(manifest, verifier))
    blockers.extend(_check_science(manifest))
    blockers.extend(_check_seed_policy(manifest))
    blockers.extend(_check_matrix(manifest))
    blockers.extend(_check_bound_provenance(manifest))
    blockers.extend(_check_assignments(manifest))
    blockers.extend(_check_artifacts(manifest))
    blockers.extend(_check_feasibility_and_budget(manifest))
    blockers.extend(_check_target_isolation(manifest))
    blockers.extend(_check_approval_records(manifest, verifier))
    blockers.extend(_check_explicit_blockers(manifest))
    unique = _unique(blockers)
    return AuthorizationResult(authorized=not unique, blockers=tuple(unique), data_access_opened=False)


def format_blockers(result: AuthorizationResult) -> str:
    """Render every blocker in stable order for the read-only checker CLI."""

    if not result.blockers:
        return "No authorization blockers."
    return "\n".join(
        f"- {blocker.code}: {blocker.message}"
        + (f" [{blocker.field}]" if blocker.field else "")
        for blocker in result.blockers
    )


def _check_flags(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    blockers: list[AuthorizationBlocker] = []
    for field in (
        "phase_18_authorized",
        "freeze_approved",
        "authorized",
        "real_execution_authorized",
        "publication_authorized",
        "phase_19_forbidden",
    ):
        if field in manifest and type(manifest[field]) is not bool:
            blockers.append(AuthorizationBlocker("invalid_authorization_flag", f"{field} must be a bool", field))
    if manifest.get("authorized") is not True:
        blockers.append(AuthorizationBlocker("authorization_blocked", "authorized must be explicitly true after all checks", "authorized"))
    if manifest.get("phase_18_authorized") is not True:
        blockers.append(AuthorizationBlocker("authorization_blocked", "Phase 18 authorization boundary is not true", "phase_18_authorized"))
    if manifest.get("publication_authorized") is not False:
        blockers.append(AuthorizationBlocker("publication_not_authorized", "publication authorization must remain separate and false", "publication_authorized"))
    if manifest.get("phase_19_forbidden") is not True:
        blockers.append(AuthorizationBlocker("authorization_blocked", "Phase 19 must remain forbidden", "phase_19_forbidden"))
    if manifest.get("authorized") is True and len(manifest) <= 2:
        blockers.append(AuthorizationBlocker("authorization_blocked", "authorized:true cannot bypass the gate", "authorized"))
    return blockers


def _check_hashes(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    blockers: list[AuthorizationBlocker] = []
    for field in HASH_FIELDS:
        if field not in manifest:
            continue
        if not _valid_hash(manifest[field]):
            code = "missing_required_field" if _is_unresolved(manifest[field]) else "hash_mismatch"
            blockers.append(AuthorizationBlocker(code, f"{field} is missing, unresolved, or not a lowercase SHA-256 digest", field))
    for name, value in (manifest.get("split_manifest_hashes") or {}).items() if isinstance(manifest.get("split_manifest_hashes"), Mapping) else ():
        if not _valid_hash(value):
            blockers.append(AuthorizationBlocker("missing_assignment", f"split hash for {name} is unresolved", f"split_manifest_hashes.{name}"))
    for name, value in (manifest.get("assignment_hashes") or {}).items() if isinstance(manifest.get("assignment_hashes"), Mapping) else ():
        if not _valid_hash(value):
            blockers.append(AuthorizationBlocker("missing_assignment", f"assignment hash for {name} is unresolved", f"assignment_hashes.{name}"))
    return blockers


def _check_freeze_hash(manifest: Mapping[str, Any], freeze_payload: Mapping[str, Any] | None) -> list[AuthorizationBlocker]:
    payload = freeze_payload if freeze_payload is not None else manifest.get("freeze_payload")
    if not isinstance(payload, Mapping):
        return [AuthorizationBlocker("missing_evidence", "complete freeze payload identity is required", "freeze_payload")]
    blockers: list[AuthorizationBlocker] = []
    try:
        FreezePayload.from_mapping(payload)
    except (TypeError, ValueError) as exc:
        blockers.append(AuthorizationBlocker("missing_evidence", f"freeze payload schema is invalid: {exc}", "freeze_payload"))
    unresolved_paths = collect_unresolved_blockers(payload)
    if unresolved_paths:
        blockers.extend(
            AuthorizationBlocker("unresolved_scientific_value", path, "freeze_payload")
            for path in unresolved_paths
        )
    if not _valid_hash(manifest.get("freeze_hash")):
        blockers.append(AuthorizationBlocker("missing_evidence", "freeze_hash must bind the complete freeze payload", "freeze_hash"))
    else:
        try:
            expected_hash = freeze_payload_hash(build_freeze_payload(payload))
        except (TypeError, ValueError) as exc:
            blockers.append(AuthorizationBlocker("missing_evidence", f"freeze payload identity is invalid: {exc}", "freeze_payload"))
        else:
            if manifest.get("freeze_hash") != expected_hash:
                blockers.append(AuthorizationBlocker("hash_mismatch", "freeze_hash does not match the freeze payload", "freeze_hash"))
    return blockers


def _check_evidence(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    blockers: list[AuthorizationBlocker] = []
    ledger = manifest.get("method_parameter_ledger")
    required = {"source_only", "coral", "mmd", "cdan", "prototype_pseudo", "aagn", "faster_snn"}
    if (
        not isinstance(ledger, Mapping)
        or set(ledger) != required
        or any(
            not isinstance(value, Mapping)
            or not {"parameters", "value_class", "evidence"} <= set(value)
            or not isinstance(value["parameters"], Mapping)
            or not isinstance(value["evidence"], Mapping)
            for value in ledger.values()
        )
    ):
        blockers.append(AuthorizationBlocker("missing_evidence", "complete scientific method-parameter ledger is required", "method_parameter_ledger"))
    evidence = manifest.get("hash_evidence")
    if not isinstance(evidence, Mapping):
        blockers.append(AuthorizationBlocker("missing_evidence", "hash evidence must include referenced canonical contents", "hash_evidence"))
    else:
        expected_contents = {
            "method_parameter_ledger_hash": manifest.get("method_parameter_ledger"),
            "resource_budget_hash": manifest.get("resource_budget"),
            "freeze_hash": manifest.get("freeze_payload"),
        }
        for field, expected_content in expected_contents.items():
            item = evidence.get(field)
            if not _content_bound_evidence(
                item,
                manifest.get(field),
                expected_content=expected_content,
                require_external=True,
            ):
                blockers.append(AuthorizationBlocker("missing_evidence", f"content evidence is missing or invalid for {field}", f"hash_evidence.{field}"))
    return blockers


def _check_authorization_evidence(
    manifest: Mapping[str, Any], verifier: Callable[[object], bool] | None
) -> list[AuthorizationBlocker]:
    evidence = manifest.get("authorization_evidence")
    if not isinstance(evidence, Mapping):
        return [AuthorizationBlocker("external_evidence_missing", "explicit external authorization evidence is required", "authorization_evidence")]
    blockers: list[AuthorizationBlocker] = []
    if evidence.get("source") not in {"external", "native"} or evidence.get("external") is not True:
        blockers.append(AuthorizationBlocker("external_evidence_missing", "authorization evidence must be external/native, not local or self-issued", "authorization_evidence.source"))
    if not _has_verifier_authority(evidence, verifier):
        blockers.append(AuthorizationBlocker("external_evidence_missing", "authorization evidence must carry an opaque verifier-issued authority marker", "authorization_evidence.authority_marker"))
    for field in ("freeze_approved", "real_execution_authorized"):
        if evidence.get(field) is not True:
            blockers.append(AuthorizationBlocker("external_evidence_missing", f"external evidence must explicitly record {field}=true", f"authorization_evidence.{field}"))
    receipt = evidence.get("native_receipt")
    if not _valid_native_receipt(
            receipt,
            manifest.get("native_receipt_hash"),
            verifier,
            manifest.get("target_identity"),
            manifest.get("target_hash"),
        ):
        blockers.append(AuthorizationBlocker("hash_evidence_invalid", "native receipt must be structurally and authority-bound external evidence", "authorization_evidence.native_receipt"))
    return blockers


def _check_science(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    blockers: list[AuthorizationBlocker] = []
    science = manifest.get("scientific_resolution")
    if _contains_unresolved(science):
        blockers.append(AuthorizationBlocker("unresolved_scientific_value", "scientific resolution contains unresolved values", "scientific_resolution"))
    if not isinstance(science, Mapping) or "lambda_proto" not in science:
        blockers.append(AuthorizationBlocker("unresolved_scientific_value", "lambda_proto resolution is missing", "scientific_resolution.lambda_proto"))
    else:
        lambda_record = science["lambda_proto"]
        lambda_value = (
            lambda_record.get("value")
            if isinstance(lambda_record, Mapping)
            else lambda_record
        )
        if type(lambda_value) is not float or lambda_value != 1.0:
            blockers.append(AuthorizationBlocker("scientific_value_mismatch", "publication lambda_proto must be exactly float 1.0", "scientific_resolution.lambda_proto"))
    if manifest.get("method_parameter_ledger") is not None and _contains_unresolved(manifest["method_parameter_ledger"]):
        blockers.append(AuthorizationBlocker("unresolved_method_parameter", "method parameter ledger contains unresolved values", "method_parameter_ledger"))
    if _contains_unresolved(manifest.get("method_inventory")):
        blockers.append(AuthorizationBlocker("unresolved_scientific_value", "method inventory is unresolved", "method_inventory"))
    if manifest.get("method_inventory") != ["source_only", "coral", "mmd", "cdan", "prototype_pseudo", "aagn", "faster_snn"]:
        blockers.append(AuthorizationBlocker("unresolved_scientific_value", "method inventory is not the protected ordered inventory", "method_inventory"))
    if _contains_unresolved(manifest.get("configuration")):
        blockers.append(AuthorizationBlocker("provenance_conflict", "configuration identity is unresolved", "configuration"))
    return blockers


def _check_seed_policy(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    policy = manifest.get("resolved_seed_policy")
    seeds = manifest.get("seed_policy")
    blockers: list[AuthorizationBlocker] = []
    if not (
        type(seeds) is list
        and seeds == list(PUBLICATION_SEEDS)
        and all(type(seed) is int for seed in seeds)
    ):
        blockers.append(
            AuthorizationBlocker(
                "seed_policy_mismatch",
                "publication seed policy must be exactly integer seeds [42, 43, 44]",
                "seed_policy",
            )
        )
    required_policy = {
        "resolved": True,
        "seeds": list(PUBLICATION_SEEDS),
        "source": "pre_run_human_decision",
        "source_split_random_state": 42,
        "target_partition_seed": 42,
        "predeclared": True,
        "posthoc_selection_forbidden": True,
    }
    policy_types_valid = (
        isinstance(policy, Mapping)
        and type(policy.get("resolved")) is bool
        and type(policy.get("seeds")) is list
        and all(type(seed) is int for seed in policy.get("seeds", ()))
        and type(policy.get("source_split_random_state")) is int
        and type(policy.get("target_partition_seed")) is int
        and type(policy.get("predeclared")) is bool
        and type(policy.get("posthoc_selection_forbidden")) is bool
    )
    if not policy_types_valid or dict(policy) != required_policy:
        blockers.append(
            AuthorizationBlocker(
                "seed_policy_mismatch",
                "resolved publication seed policy is incomplete or inconsistent",
                "resolved_seed_policy",
            )
        )
        expected = None
    else:
        expected = identity_sha256(policy)
    if expected is not None and manifest.get("seed_policy_hash") != expected:
        blockers.append(AuthorizationBlocker("hash_mismatch", "seed_policy_hash does not match the resolved seed policy", "seed_policy_hash"))
    matrix = manifest.get("matrix")
    raw_matrix_seeds = matrix.seeds if isinstance(matrix, ExperimentMatrix) else matrix.get("seeds") if isinstance(matrix, Mapping) else None
    matrix_seeds = (
        list(raw_matrix_seeds)
        if isinstance(raw_matrix_seeds, Sequence) and not isinstance(raw_matrix_seeds, (str, bytes))
        else raw_matrix_seeds
    )
    if matrix_seeds is not None and matrix_seeds != seeds:
        blockers.append(AuthorizationBlocker("seed_policy_mismatch", "top-level seed policy does not match matrix seeds", "matrix.seeds"))
    matrix_policy = (
        matrix.resolved_seed_policy
        if isinstance(matrix, ExperimentMatrix)
        else matrix.get("resolved_seed_policy")
        if isinstance(matrix, Mapping)
        else None
    )
    if matrix_policy is not None and (
        not isinstance(matrix_policy, Mapping) or dict(matrix_policy) != required_policy
    ):
        blockers.append(
            AuthorizationBlocker(
                "seed_policy_mismatch",
                "matrix resolved seed policy does not match the frozen publication policy",
                "matrix.resolved_seed_policy",
            )
        )
    return blockers


def _check_matrix(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    matrix = manifest.get("matrix")
    if matrix is None:
        return (AuthorizationBlocker("incomplete_matrix", "complete matrix is missing", "matrix"),)
    blockers: list[AuthorizationBlocker] = []
    if isinstance(matrix, (ExperimentMatrix, Mapping)) and (isinstance(matrix, ExperimentMatrix) or "rows" in matrix):
        blockers.extend(_as_authorization_blocker(item) for item in validate_matrix_input(matrix))
        try:
            expected = matrix_content_hash(matrix)
        except (MatrixValidationError, TypeError, ValueError) as exc:
            expected = None
            blockers.append(AuthorizationBlocker("incomplete_matrix", str(exc), "matrix.rows"))
    else:
        blockers.append(AuthorizationBlocker("incomplete_matrix", "complete matrix rows are required", "matrix.rows"))
        expected = None
    if expected is None or manifest.get("matrix_hash") != expected:
        blockers.append(AuthorizationBlocker("hash_mismatch", "matrix_hash does not match the complete matrix rows", "matrix_hash"))
    return blockers


def _check_bound_provenance(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    report = aggregate_validators(provenance=manifest.get("provenance"))
    return [_as_authorization_blocker(item) for item in report.blockers]


def _check_assignments(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    contents = manifest.get("assignment_manifest_contents")
    provenance = manifest.get("provenance")
    if not isinstance(contents, Mapping):
        return (AuthorizationBlocker("missing_assignment", "hash-verified assignment contents are missing", "assignment_manifest_contents"),)
    adaptation = contents.get("target_adaptation_subject_hashes")
    evaluation = contents.get("target_evaluation_subject_hashes")
    if not isinstance(adaptation, Sequence) or isinstance(adaptation, (str, bytes)) or not isinstance(evaluation, Sequence) or isinstance(evaluation, (str, bytes)):
        return (AuthorizationBlocker("missing_assignment", "parsed assignment subject sets are required", "assignment_manifest_contents"),)
    required = contents.get("required_intersection")
    blockers: list[AuthorizationBlocker] = []
    if isinstance(required, Sequence) and not isinstance(required, (str, bytes)) and required:
        blockers.append(AuthorizationBlocker("overlapping_assignments", "caller-declared assignment intersection is not accepted", "assignment_manifest_contents"))
    if not isinstance(provenance, Mapping):
        blockers.append(AuthorizationBlocker("missing_assignment", "opaque verified assignment manifests are required", "provenance"))
        return blockers
    adaptation_manifest = provenance.get("target_adaptation")
    evaluation_manifest = provenance.get("target_evaluation")
    if not (
        isinstance(adaptation_manifest, ManifestValidation)
        and isinstance(evaluation_manifest, ManifestValidation)
        and _is_verifier_issued_manifest(adaptation_manifest, expected_role="target_adaptation")
        and _is_verifier_issued_manifest(evaluation_manifest, expected_role="target_evaluation")
    ):
        blockers.append(AuthorizationBlocker("missing_assignment", "assignment contents must bind verifier-issued manifests", "provenance"))
        return blockers
    actual_adaptation = set(adaptation_manifest.subject_hashes)
    actual_evaluation = set(evaluation_manifest.subject_hashes)
    if actual_adaptation & actual_evaluation:
        blockers.append(AuthorizationBlocker("overlapping_assignments", "target adaptation and evaluation assignments overlap", "assignment_manifest_contents"))
    if set(adaptation) != actual_adaptation or set(evaluation) != actual_evaluation:
        blockers.append(AuthorizationBlocker("provenance_conflict", "assignment contents do not match concrete verified records", "assignment_manifest_contents"))
    if contents.get("aggregate_hashes_alone_are_insufficient") is not True:
        blockers.append(AuthorizationBlocker("missing_assignment", "content-level assignment verification is not declared", "assignment_manifest_contents"))
    return blockers


def _check_artifacts(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    hashes = manifest.get("artifact_hashes")
    index = manifest.get("artifact_index")
    if not isinstance(hashes, Mapping):
        return (AuthorizationBlocker("missing_immutable_artifact", "artifact hashes are missing", "artifact_hashes"),)
    blockers: list[AuthorizationBlocker] = []
    for name in ARTIFACT_HASH_FIELDS:
        value = hashes.get(name)
        if not _valid_hash(value):
            blockers.append(AuthorizationBlocker("missing_immutable_artifact", f"artifact hash is unresolved: {name}", f"artifact_hashes.{name}"))
        if isinstance(index, Mapping) and index.get(name) != value:
            blockers.append(AuthorizationBlocker("hash_mismatch", f"artifact index does not match {name}", f"artifact_index.{name}"))
    if not isinstance(index, Mapping):
        blockers.append(AuthorizationBlocker("missing_immutable_artifact", "exact artifact index is missing", "artifact_index"))
    return blockers


def _check_feasibility_and_budget(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    report = aggregate_validators(feasibility=manifest.get("feasibility"))
    blockers = [_as_authorization_blocker(item) for item in report.blockers]
    budget = manifest.get("resource_budget")
    if _contains_unresolved(budget) or not isinstance(budget, Mapping):
        blockers.append(AuthorizationBlocker("resource_budget_unresolved", "resource budget contains unresolved fields", "resource_budget"))
    elif not _valid_resource_budget_closure(budget, manifest.get("resource_budget_hash")):
        blockers.append(AuthorizationBlocker("resource_budget_unresolved", "resource budget requires explicit external, content-bound closure evidence", "resource_budget"))
    return blockers


def _check_target_isolation(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    report = aggregate_validators(
        target_adaptation=manifest.get("target_adaptation_batch"),
        target_evaluation=manifest.get("target_evaluation_metadata"),
    )
    return [_as_authorization_blocker(item) for item in report.blockers]


def _check_approval_records(
    manifest: Mapping[str, Any], verifier: Callable[[object], bool] | None
) -> list[AuthorizationBlocker]:
    blockers: list[AuthorizationBlocker] = []
    for field, code in (
        ("privacy_data_access_record_hash", "privacy_missing"),
        ("independent_review_hash", "review_missing"),
        ("statistical_review_hash", "statistical_review_missing"),
        ("human_authorization_hash", "human_authorization_missing"),
        ("native_receipt_hash", "native_receipt_missing"),
    ):
        if not _valid_hash(manifest.get(field)):
            blockers.append(AuthorizationBlocker(code, f"{field} is required", field))
    for record_field, hash_field in (
        ("privacy_data_access_record", "privacy_data_access_record_hash"),
        ("independent_review", "independent_review_hash"),
        ("statistical_review", "statistical_review_hash"),
        ("human_authorization", "human_authorization_hash"),
    ):
        if not _structured_attestation(
                manifest.get(record_field), manifest.get(hash_field), verifier
            ):
            blockers.append(
                AuthorizationBlocker(
                    "attestation_missing",
                    f"{record_field} must be a structured external/native content-bound attestation",
                    record_field,
                )
            )
    return blockers


def _check_explicit_blockers(manifest: Mapping[str, Any]) -> list[AuthorizationBlocker]:
    values = manifest.get("blockers", ())
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return (AuthorizationBlocker("authorization_blocked", "blockers must be an explicit list", "blockers"),)
    return tuple(AuthorizationBlocker("authorization_blocked", str(item), "blockers") for item in values if item)


def _as_authorization_blocker(blocker: ValidationBlocker) -> AuthorizationBlocker:
    return AuthorizationBlocker(blocker.code, blocker.message, blocker.field)


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and is_sha256(value) and value not in _PLACEHOLDER_HASHES and not _is_unresolved(value)


def _content_bound_evidence(
    item: Any,
    expected_hash: Any,
    *,
    expected_content: Mapping[str, Any] | None = None,
    require_external: bool = False,
    require_authority: bool = False,
    verifier: Callable[[object], bool] | None = None,
) -> bool:
    if not isinstance(item, Mapping) or not isinstance(item.get("content"), Mapping):
        return False
    if require_external and (item.get("source") not in {"external", "native"} or item.get("external") is not True):
        return False
    if require_authority and not _has_verifier_authority(item, verifier):
        return False
    recorded = item.get("sha256")
    return (
        _valid_hash(recorded)
        and recorded == expected_hash
        and identity_sha256(item["content"]) == recorded
        and (expected_content is None or item["content"] == expected_content)
        and not _contains_unresolved(item["content"])
    )


def _has_verifier_authority(
    item: Mapping[str, Any], verifier: Callable[[object], bool] | None
) -> bool:
    if verifier is None:
        return False
    try:
        return verifier(item.get("authority_marker")) is True
    except Exception:
        return False


def _valid_native_receipt(
    receipt: Any,
    expected_hash: Any,
    verifier: Callable[[object], bool] | None,
    expected_target_identity: Any,
    expected_target_hash: Any,
) -> bool:
    if not isinstance(receipt, Mapping) or set(receipt) != _NATIVE_RECEIPT_FIELDS:
        return False
    if (
        receipt.get("source") != "native"
        or receipt.get("external") is not True
        or receipt.get("schema") != _NATIVE_RECEIPT_SCHEMA
        or not isinstance(receipt.get("lineage"), str)
        or not receipt["lineage"]
        or receipt.get("gate") != _NATIVE_RECEIPT_GATE
        or receipt.get("result") != "allow"
        or not _has_verifier_authority(receipt, verifier)
        or receipt.get("target_identity") != expected_target_identity
        or receipt.get("target_hash") != expected_target_hash
        or not isinstance(expected_target_identity, str)
        or not expected_target_identity
        or not _valid_hash(expected_target_hash)
    ):
        return False
    content = receipt.get("content")
    if not isinstance(content, Mapping) or set(content) != _NATIVE_RECEIPT_CONTENT_FIELDS:
        return False
    if any(content.get(field) != receipt.get(field) for field in _NATIVE_RECEIPT_CONTENT_FIELDS):
        return False
    return _content_bound_evidence(
        receipt,
        expected_hash,
        require_external=True,
        require_authority=True,
        verifier=verifier,
    )


def _structured_attestation(
    record: Any, expected_hash: Any, verifier: Callable[[object], bool] | None
) -> bool:
    return _content_bound_evidence(
        record,
        expected_hash,
        require_external=True,
        require_authority=True,
        verifier=verifier,
    )


def _valid_resource_budget_closure(budget: Mapping[str, Any], expected_hash: Any) -> bool:
    if budget.get("real_budget_closed") is not True:
        return False
    evidence = budget.get("evidence")
    closure = budget.get("closure")
    if not isinstance(evidence, Mapping) or not isinstance(closure, Mapping):
        return False
    if evidence.get("source") not in {"external", "native"} or evidence.get("external") is not True:
        return False
    if evidence.get("evidence_type") in {"measured_synthetic", "extrapolated_from_synthetic", "not_recorded", "blocked"}:
        return False
    if not _content_bound_evidence(evidence, expected_hash):
        return False
    closure_evidence = closure.get("evidence")
    return closure.get("closed") is True and isinstance(closure_evidence, Mapping) and not _contains_unresolved(closure_evidence)


def _is_unresolved(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.lower() in _UNRESOLVED_STRINGS)


def _contains_unresolved(value: Any) -> bool:
    if _is_unresolved(value):
        return True
    if isinstance(value, Mapping):
        return any(_contains_unresolved(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_unresolved(item) for item in value)
    return False


def _unique(blockers: Sequence[AuthorizationBlocker]) -> list[AuthorizationBlocker]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[AuthorizationBlocker] = []
    for blocker in blockers:
        identity = (blocker.code, blocker.message, blocker.field)
        if identity not in seen:
            seen.add(identity)
            result.append(blocker)
    return result
