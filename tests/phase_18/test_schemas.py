from __future__ import annotations

from dataclasses import replace

import pytest

from pada3dacb.publication.canonical_json import identity_sha256
from pada3dacb.publication.freeze import freeze_payload_hash as freeze_module_payload_hash
from pada3dacb.publication.schemas import (
    BlockerCode,
    BlockerRecord,
    FreezePayload,
    FreezePayloadEnvelope,
    MatrixRow,
    MatrixRowKind,
    MatrixStatus,
    ValueClass,
    ValueClassification,
    validate_freeze_payload,
    validate_matrix_row,
)
from pada3dacb.publication.schemas import freeze_payload_hash as schema_payload_hash


def test_value_classification_requires_explicit_class_and_evidence() -> None:
    record = ValueClassification(
        name="lambda_proto",
        value=None,
        value_class=ValueClass.UNRESOLVED_BLOCKING,
        source=None,
        reason="primary and helper values conflict",
    )
    assert record.value_class is ValueClass.UNRESOLVED_BLOCKING
    assert record.reason == "primary and helper values conflict"

    with pytest.raises(ValueError, match="source or reason"):
        ValueClassification(
            name="seed",
            value=42,
            value_class=ValueClass.CANONICAL_FIXED,
            source=None,
            reason=None,
        )


def test_blocker_record_is_structured_and_typed() -> None:
    blocker = BlockerRecord(
        code=BlockerCode.UNRESOLVED_SCIENTIFIC_VALUE,
        message="lambda_proto is not resolved",
        evidence=None,
    )
    assert blocker.code.value == "unresolved_scientific_value"
    assert blocker.message == "lambda_proto is not resolved"


def _payload() -> FreezePayload:
    return FreezePayload(
        schema_version="phase18.freeze.v1",
        phase=18,
        status="blocked_planning",
        phase_18_authorized=True,
        freeze_approved=False,
        real_execution_authorized=False,
        publication_authorized=False,
        phase_19_forbidden=True,
        scientific_resolution_hash="unresolved",
        matrix_hash="unresolved",
        provenance_freeze_hash="unresolved",
        feasibility_hash="unresolved",
        resource_budget_hash="unresolved",
        independent_review_hash="unresolved",
        human_authorization_hash="unresolved",
    )


def test_freeze_payload_preserves_blocked_authorization_boundary() -> None:
    payload = _payload()
    assert validate_freeze_payload(payload) == ()
    assert payload.real_execution_authorized is False
    assert payload.publication_authorized is False
    assert payload.phase_19_forbidden is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("phase_18_authorized", 1),
        ("real_execution_authorized", 0),
        ("publication_authorized", "yes"),
        ("phase_19_forbidden", None),
    ],
)
def test_freeze_payload_rejects_non_bool_authorization_flags(
    field_name: str, value: object
) -> None:
    with pytest.raises(TypeError, match=field_name):
        FreezePayload(**{**_payload().__dict__, field_name: value})


def _training_row() -> MatrixRow:
    return MatrixRow(
        matrix_id="a" * 64,
        row_kind=MatrixRowKind.TRAINING,
        parent_training_id=None,
        training_invocation=True,
        method_id="source_only",
        public_method_name="PADA-3DACB Source-Only",
        direction="adni_to_oasis",
        source_cohort="ADNI",
        target_cohort="OASIS",
        fold=0,
        seed=42,
        checkpoint_policy="best_source_f1",
        resolved_config_hash="unresolved",
        split_assignment_hash="unresolved",
        target_adaptation_assignment_hash="unresolved",
        target_evaluation_assignment_hash="unresolved",
        immutable_artifacts_hash="unresolved",
        state=MatrixStatus.BLOCKED,
        completion_allowed=False,
        blocked_reasons=("missing_assignment",),
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("training_invocation", 1), ("completion_allowed", 0), ("completion_allowed", "no")],
)
def test_matrix_row_rejects_non_bool_authorization_flags(
    field_name: str, value: object
) -> None:
    with pytest.raises(TypeError, match=field_name):
        replace(_training_row(), **{field_name: value})


def test_schema_matrix_row_accepts_a_resolved_non_default_seed() -> None:
    row = replace(_training_row(), seed=43)

    assert validate_matrix_row(row) == ()


def test_matrix_row_requires_kind_specific_parent_and_invocation() -> None:
    training = MatrixRow(
        matrix_id="a" * 64,
        row_kind=MatrixRowKind.TRAINING,
        parent_training_id=None,
        training_invocation=True,
        method_id="source_only",
        public_method_name="PADA-3DACB Source-Only",
        direction="adni_to_oasis",
        source_cohort="ADNI",
        target_cohort="OASIS",
        fold=0,
        seed=42,
        checkpoint_policy="best_source_f1",
        resolved_config_hash="unresolved",
        split_assignment_hash="unresolved",
        target_adaptation_assignment_hash="unresolved",
        target_evaluation_assignment_hash="unresolved",
        immutable_artifacts_hash="unresolved",
        state=MatrixStatus.BLOCKED,
        completion_allowed=False,
        blocked_reasons=("missing_assignment",),
    )
    assert validate_matrix_row(training) == ()

    with pytest.raises(ValueError, match="parent_training_id"):
        MatrixRow(
            **{**training.__dict__, "row_kind": MatrixRowKind.CHECKPOINT_PROJECTION,
               "parent_training_id": None, "training_invocation": False}
        )


def test_matrix_completed_state_is_forbidden_in_phase_18() -> None:
    with pytest.raises(ValueError, match="COMPLETED"):
        MatrixStatus("COMPLETED")


def test_freeze_hash_is_external_to_the_hashed_payload() -> None:
    payload = _payload()
    expected_hash = identity_sha256(payload.to_mapping())
    envelope = FreezePayloadEnvelope(payload=payload, freeze_hash=expected_hash)
    assert "freeze_hash" not in payload.to_mapping()
    assert envelope.freeze_hash == expected_hash
    with pytest.raises(ValueError, match="does not match payload identity"):
        FreezePayloadEnvelope(payload=payload, freeze_hash="a" * 64)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        FreezePayloadEnvelope(payload=payload, freeze_hash="not-a-hash")


def test_freeze_payload_schema_includes_approval_field_and_round_trips_freeze_mapping() -> None:
    payload = _payload()

    assert payload.freeze_approved is False
    assert payload.to_mapping()["freeze_approved"] is False
    assert FreezePayload.from_mapping(payload.to_mapping()) == payload


def test_schema_and_freeze_share_one_versioned_payload_hash_path() -> None:
    payload = _payload()
    mapping = {**payload.to_mapping(), "future_extension": {"approved": False}}
    typed = FreezePayload.from_mapping(mapping)

    assert schema_payload_hash(mapping) == freeze_module_payload_hash(mapping)
    assert schema_payload_hash(typed) == identity_sha256(typed.to_mapping())
    assert FreezePayload.from_mapping(typed.to_mapping()) == typed


def test_freeze_hash_is_rejected_inside_typed_or_mapping_payloads() -> None:
    payload = _payload()
    internal_hash = identity_sha256(payload.to_mapping())

    with pytest.raises(ValueError, match="outside"):
        FreezePayload.from_mapping({**payload.to_mapping(), "freeze_hash": internal_hash})
    with pytest.raises(ValueError, match="outside"):
        FreezePayload(**{**payload.__dict__, "extensions": {"freeze_hash": internal_hash}})
    with pytest.raises(ValueError, match="outside"):
        schema_payload_hash({**payload.to_mapping(), "freeze_hash": internal_hash})
