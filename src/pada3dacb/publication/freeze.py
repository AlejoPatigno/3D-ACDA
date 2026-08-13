"""Canonical, planning-only Phase 18 freeze artifacts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .canonical_json import canonical_json_bytes, is_sha256
from .schemas import (
    FREEZE_PAYLOAD_REQUIRED_FIELDS,
    SCHEMA_VERSION,
    FreezePayload,
    freeze_payload_hash,
)

FREEZE_SCHEMA_VERSION = SCHEMA_VERSION
FREEZE_FILE_NAME = "publication_freeze.json"
_REQUIRED_FIELDS = FREEZE_PAYLOAD_REQUIRED_FIELDS
_HASH_FIELDS = (
    "scientific_resolution_hash",
    "matrix_hash",
    "provenance_freeze_hash",
    "feasibility_hash",
    "resource_budget_hash",
    "independent_review_hash",
    "human_authorization_hash",
)
_UNRESOLVED = {None, "", "unresolved", "UNRESOLVED", "unresolved_blocking", "pending"}


class FreezeValidationError(ValueError):
    """Raised when a freeze artifact cannot be safely represented or verified."""


def build_freeze_payload(source: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy an explicit freeze payload without adding defaults.

    ``source`` may be an already extracted payload or a document containing a
    ``payload`` member.  The returned mapping is the exact object whose canonical
    bytes are hashed; ``freeze_hash`` is never accepted inside it.
    """

    if not isinstance(source, Mapping):
        raise FreezeValidationError("freeze payload must be a mapping")
    raw = source.get("payload", source)
    if not isinstance(raw, Mapping):
        raise FreezeValidationError("payload must be a mapping")
    if "freeze_hash" in raw:
        raise FreezeValidationError("freeze_hash must remain outside payload")
    payload = dict(raw)
    missing = [field for field in _REQUIRED_FIELDS if field not in payload]
    if missing:
        raise FreezeValidationError(f"missing required freeze field: {missing[0]}")
    if payload["schema_version"] != FREEZE_SCHEMA_VERSION:
        raise FreezeValidationError(f"schema_version must be {FREEZE_SCHEMA_VERSION}")
    if payload["phase"] != 18:
        raise FreezeValidationError("phase must be 18")
    if payload["status"] != "blocked_planning":
        raise FreezeValidationError("freeze status must remain blocked_planning")
    _require_bool_fields(payload)
    if payload["phase_18_authorized"] is not True:
        raise FreezeValidationError("phase_18_authorized must remain true")
    if payload["freeze_approved"] is not False:
        raise FreezeValidationError("freeze_approved must remain false")
    if payload["real_execution_authorized"] is not False:
        raise FreezeValidationError("real_execution_authorized must remain false")
    if payload["publication_authorized"] is not False:
        raise FreezeValidationError("publication_authorized must remain false")
    if payload["phase_19_forbidden"] is not True:
        raise FreezeValidationError("phase_19_forbidden must remain true")
    for field in _HASH_FIELDS:
        value = payload[field]
        if value not in _UNRESOLVED and not is_sha256(value):
            raise FreezeValidationError(f"{field} must be unresolved or a SHA-256 digest")
    _reject_completed_rows(payload)
    blockers = collect_unresolved_blockers(payload)
    explicit = payload.get("blockers", [])
    if explicit is None:
        raise FreezeValidationError("blockers must be explicit; null is not allowed")
    if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
        raise FreezeValidationError("blockers must be a list")
    if any(not isinstance(item, str) or not item for item in explicit):
        raise FreezeValidationError("blockers must contain non-empty strings")
    # Preserve supplied order while propagating newly discovered unresolved values.
    payload["blockers"] = list(dict.fromkeys([*explicit, *blockers]))
    try:
        FreezePayload.from_mapping(payload)
    except (TypeError, ValueError) as exc:
        raise FreezeValidationError(str(exc)) from exc
    return payload


def collect_unresolved_blockers(value: Any, *, _path: str = "") -> list[str]:
    """Return explicit blocker codes for unresolved values, without resolving them."""

    blockers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            path = f"{_path}.{key}" if _path else str(key)
            if _is_unresolved(item) and key != "blockers":
                if "resource" in path or "budget" in path:
                    code = "resource_budget_unresolved"
                elif "hash" in path or "artifact" in path or "assignment" in path:
                    code = "missing_immutable_artifact"
                else:
                    code = "unresolved_scientific_value"
                blockers.append(f"{code}:{path}")
            else:
                blockers.extend(collect_unresolved_blockers(item, _path=path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            blockers.extend(collect_unresolved_blockers(item, _path=f"{_path}[{index}]"))
    return blockers


def write_freeze(path: str | Path, payload: Mapping[str, Any], *, overwrite: bool = True) -> dict[str, Any]:
    """Write one canonical planning artifact and return its verified envelope."""

    file_path = Path(path)
    if file_path.exists() and not overwrite:
        raise FreezeValidationError("freeze artifact exists; pass overwrite=True to replace it")
    normalized = build_freeze_payload(payload)
    envelope = {"payload": normalized, "freeze_hash": freeze_payload_hash(normalized)}
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(canonical_json_bytes(envelope))
    return envelope


def read_freeze(path: str | Path) -> dict[str, Any]:
    """Read a canonical envelope and verify its external hash before returning it."""

    file_path = Path(path)
    try:
        raw_bytes = file_path.read_bytes()
        document = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreezeValidationError(f"cannot read freeze artifact: {exc}") from exc
    if not isinstance(document, Mapping) or set(document) != {"payload", "freeze_hash"}:
        raise FreezeValidationError("freeze artifact must contain payload and freeze_hash only")
    if raw_bytes != canonical_json_bytes(document):
        raise FreezeValidationError("freeze artifact is not canonical JSON; freeze_hash cannot be verified")
    payload = build_freeze_payload(document["payload"])
    recorded_hash = document["freeze_hash"]
    if not isinstance(recorded_hash, str) or not is_sha256(recorded_hash):
        raise FreezeValidationError("freeze_hash must be a lowercase SHA-256 digest")
    actual_hash = freeze_payload_hash(payload)
    if recorded_hash != actual_hash:
        raise FreezeValidationError("freeze_hash does not match payload identity")
    return {"payload": payload, "freeze_hash": recorded_hash}


def verify_freeze_hash(path: str | Path) -> bool:
    """Verify a freeze envelope, returning ``True`` only when it is intact."""

    read_freeze(path)
    return True


def _is_unresolved(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value in _UNRESOLVED)


def _require_bool_fields(payload: Mapping[str, Any]) -> None:
    for field in (
        "phase_18_authorized",
        "freeze_approved",
        "real_execution_authorized",
        "publication_authorized",
        "phase_19_forbidden",
    ):
        if field in payload and type(payload[field]) is not bool:
            raise FreezeValidationError(f"{field} must be a bool")


def _reject_completed_rows(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"state", "status"} and item == "COMPLETED":
                raise FreezeValidationError("COMPLETED rows are forbidden in Phase 18")
            _reject_completed_rows(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_completed_rows(item)
