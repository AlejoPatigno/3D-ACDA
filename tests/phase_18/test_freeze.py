from __future__ import annotations

import json

import pytest

from pada3dacb.publication.canonical_json import identity_sha256
from pada3dacb.publication.freeze import (
    FreezeValidationError,
    build_freeze_payload,
    freeze_payload_hash,
    read_freeze,
    verify_freeze_hash,
    write_freeze,
)
from pada3dacb.publication.schemas import FreezePayload


def _payload() -> dict[str, object]:
    return {
        "schema_version": "phase18.freeze.v1",
        "phase": 18,
        "status": "blocked_planning",
        "phase_18_authorized": True,
        "freeze_approved": False,
        "real_execution_authorized": False,
        "publication_authorized": False,
        "phase_19_forbidden": True,
        "scientific_resolution_hash": "unresolved",
        "matrix_hash": "unresolved",
        "provenance_freeze_hash": "unresolved",
        "feasibility_hash": "unresolved",
        "resource_budget_hash": "unresolved",
        "independent_review_hash": "unresolved",
        "human_authorization_hash": "unresolved",
        "blockers": ["lambda_proto_0.2_vs_1.0_unresolved"],
        "rows": [{"state": "BLOCKED", "completion_allowed": False}],
    }


def test_freeze_round_trip_is_byte_identical_and_hash_is_external(tmp_path) -> None:
    path = tmp_path / "freeze.json"
    payload = build_freeze_payload(_payload())
    write_freeze(path, payload)

    original = path.read_bytes()
    loaded = read_freeze(path)

    assert path.read_bytes() == original
    assert loaded["payload"] == payload
    assert loaded["freeze_hash"] == identity_sha256(payload)
    assert "freeze_hash" not in payload
    assert verify_freeze_hash(path) is True


def test_freeze_hash_tampering_is_rejected(tmp_path) -> None:
    path = tmp_path / "freeze.json"
    payload = build_freeze_payload(_payload())
    write_freeze(path, payload)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["freeze_hash"] = "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(FreezeValidationError, match="freeze_hash"):
        read_freeze(path)


def test_freeze_propagates_unresolved_blockers_and_never_completed_rows() -> None:
    payload = build_freeze_payload(_payload())

    assert "lambda_proto_0.2_vs_1.0_unresolved" in payload["blockers"]
    assert payload["rows"][0]["state"] == "BLOCKED"

    completed = {**_payload(), "rows": [{"state": "COMPLETED"}]}
    with pytest.raises(FreezeValidationError, match="COMPLETED"):
        build_freeze_payload(completed)


def test_freeze_requires_fields_instead_of_inventing_defaults() -> None:
    incomplete = _payload()
    del incomplete["matrix_hash"]

    with pytest.raises(FreezeValidationError, match="matrix_hash"):
        build_freeze_payload(incomplete)


def test_schema_and_freeze_module_share_one_payload_identity_path() -> None:
    mapping = build_freeze_payload(_payload())
    typed = FreezePayload.from_mapping(mapping)

    assert typed.to_mapping() == mapping
    assert freeze_payload_hash(typed) == identity_sha256(mapping)


def test_freeze_module_rejects_internal_hash_instead_of_double_hashing() -> None:
    mapping = build_freeze_payload(_payload())
    internal_hash = identity_sha256(mapping)

    with pytest.raises(ValueError, match="outside"):
        freeze_payload_hash({**mapping, "freeze_hash": internal_hash})
    with pytest.raises(FreezeValidationError, match="outside"):
        build_freeze_payload({**mapping, "freeze_hash": internal_hash})
