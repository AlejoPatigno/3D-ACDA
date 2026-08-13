from __future__ import annotations

import hashlib
import json

import pytest
import yaml

from pada3dacb.publication.provenance import (
    ManifestValidation,
    ProvenanceStatus,
    check_assignment_disjointness,
    validate_manifest,
    validate_target_adaptation_batch,
    validate_target_evaluation_metadata,
)
from pada3dacb.publication.validation import aggregate_validators


def _write_json(tmp_path, name: str, payload: object) -> tuple[object, str]:
    path = tmp_path / name
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def _manifest(role: str, subjects: list[tuple[str, str]], *, one_scan: bool = False) -> dict:
    return {
        "schema_version": "phase18.manifest.v1",
        "role": role,
        "cohort": "OASIS",
        "one_scan_per_subject": one_scan,
        "records": [
            {"subject_id": subject_id, "subject_hash": subject_hash, "cohort": "OASIS", "role": role, "scan_id": f"scan-{index}"}
            for index, (subject_id, subject_hash) in enumerate(subjects)
        ],
    }


def test_exact_byte_hash_is_verified_before_json_schema_validation(tmp_path) -> None:
    path, digest = _write_json(tmp_path, "adaptation.json", _manifest("target_adaptation", [("s1", "h1")]))

    result = validate_manifest(
        path,
        adapter="json",
        declared_sha256=digest,
        expected_role="target_adaptation",
        expected_cohort="OASIS",
    )

    assert result.status is ProvenanceStatus.VERIFIED
    assert result.sha256 == digest
    assert result.subject_hashes == frozenset({"h1"})


def test_missing_file_is_blocked_data_and_hash_drift_is_provenance_mismatch(tmp_path) -> None:
    missing = validate_manifest(
        tmp_path / "missing.json", adapter="json", declared_sha256="0" * 64
    )
    assert missing.status is ProvenanceStatus.BLOCKED_DATA

    path, digest = _write_json(tmp_path, "drift.json", _manifest("target_adaptation", [("s1", "h1")]))
    path.write_bytes(path.read_bytes() + b" ")
    drift = validate_manifest(path, adapter="json", declared_sha256=digest)
    assert drift.status is ProvenanceStatus.PROVENANCE_MISMATCH
    assert drift.parsed is False


def test_schema_version_role_cohort_and_unique_subjects_are_required(tmp_path) -> None:
    bad_schema = _manifest("target_adaptation", [("s1", "h1")])
    bad_schema["schema_version"] = "phase17.manifest.v1"
    path, digest = _write_json(tmp_path, "bad-schema.json", bad_schema)
    result = validate_manifest(path, adapter="json", declared_sha256=digest)
    assert result.status is ProvenanceStatus.INVALID_SCHEMA

    duplicate = _manifest("target_adaptation", [("s1", "h1"), ("s2", "h1")])
    path, digest = _write_json(tmp_path, "duplicate.json", duplicate)
    result = validate_manifest(path, adapter="json", declared_sha256=digest)
    assert result.status is ProvenanceStatus.INVALID_SCHEMA


def test_one_scan_per_subject_is_enforced_when_declared(tmp_path) -> None:
    payload = _manifest("target_adaptation", [("s1", "h1"), ("s1b", "h1b")], one_scan=True)
    payload["records"][1]["subject_hash"] = "h1"
    path, digest = _write_json(tmp_path, "one-scan.json", payload)
    result = validate_manifest(path, adapter="json", declared_sha256=digest)
    assert result.status is ProvenanceStatus.INVALID_SCHEMA


def test_content_level_assignment_intersection_rejects_overlap(tmp_path) -> None:
    adaptation_path, adaptation_hash = _write_json(
        tmp_path, "adaptation.json", _manifest("target_adaptation", [("s1", "h1")])
    )
    evaluation_path, evaluation_hash = _write_json(
        tmp_path, "evaluation.json", _manifest("target_evaluation", [("s1", "h1")])
    )
    adaptation = validate_manifest(adaptation_path, adapter="json", declared_sha256=adaptation_hash)
    evaluation = validate_manifest(evaluation_path, adapter="json", declared_sha256=evaluation_hash)

    result = check_assignment_disjointness(adaptation, evaluation)
    assert result.status is ProvenanceStatus.OVERLAPPING_ASSIGNMENTS
    assert result.overlap == frozenset({"h1"})


def test_aggregate_hashes_do_not_substitute_for_content_intersection(tmp_path) -> None:
    adaptation_path, adaptation_hash = _write_json(
        tmp_path, "adaptation.json", _manifest("target_adaptation", [("s1", "h1")])
    )
    evaluation_path, evaluation_hash = _write_json(
        tmp_path, "evaluation.json", _manifest("target_evaluation", [("s2", "h2")])
    )
    adaptation = validate_manifest(adaptation_path, adapter="json", declared_sha256=adaptation_hash)
    evaluation = validate_manifest(evaluation_path, adapter="json", declared_sha256=evaluation_hash)

    result = check_assignment_disjointness(adaptation, evaluation)
    assert result.status is ProvenanceStatus.VERIFIED
    assert result.overlap == frozenset()


def test_manifest_coverage_is_checked_against_supplied_subject_hashes(tmp_path) -> None:
    path, digest = _write_json(tmp_path, "coverage.json", _manifest("target_adaptation", [("s1", "h1")]))

    result = validate_manifest(
        path,
        adapter="json",
        declared_sha256=digest,
        expected_subject_hashes={"h1", "h2"},
    )

    assert result.status is ProvenanceStatus.INVALID_SCHEMA


def test_yaml_is_an_explicit_schema_adapter(tmp_path) -> None:
    payload = _manifest("target_adaptation", [("s1", "h1")])
    data = yaml.safe_dump(payload, sort_keys=False).encode("utf-8")
    path = tmp_path / "manifest.yaml"
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    result = validate_manifest(path, adapter="yaml", declared_sha256=digest)
    assert result.status is ProvenanceStatus.VERIFIED


def test_csv_and_tsv_require_explicit_adapters(tmp_path) -> None:
    content = "schema_version,role,cohort,subject_id,subject_hash,scan_id\nphase18.manifest.v1,target_adaptation,OASIS,s1,h1,scan-1\n"
    csv_path = tmp_path / "manifest.csv"
    csv_path.write_text(content, encoding="utf-8", newline="")
    digest = hashlib.sha256(content.encode()).hexdigest()
    csv_result = validate_manifest(csv_path, adapter="csv", declared_sha256=digest)
    assert csv_result.status is ProvenanceStatus.VERIFIED

    tsv = content.replace(",", "\t")
    tsv_path = tmp_path / "manifest.tsv"
    tsv_path.write_text(tsv, encoding="utf-8", newline="")
    tsv_digest = hashlib.sha256(tsv.encode()).hexdigest()
    tsv_result = validate_manifest(tsv_path, adapter="tsv", declared_sha256=tsv_digest)
    assert tsv_result.status is ProvenanceStatus.VERIFIED


def test_csv_and_tsv_reject_mixed_record_schema_versions(tmp_path) -> None:
    header = "schema_version,role,cohort,subject_id,subject_hash,scan_id\n"
    rows = (
        "phase18.manifest.v1,target_adaptation,OASIS,s1,h1,scan-1\n"
        "phase17.manifest.v1,target_adaptation,OASIS,s2,h2,scan-2\n"
    )
    for adapter, suffix, delimiter in (("csv", ".csv", ","), ("tsv", ".tsv", "\t")):
        content = (header + rows).replace(",", delimiter)
        path = tmp_path / f"mixed{suffix}"
        path.write_text(content, encoding="utf-8", newline="")
        digest = hashlib.sha256(content.encode()).hexdigest()

        result = validate_manifest(path, adapter=adapter, declared_sha256=digest)

        assert result.status is ProvenanceStatus.INVALID_SCHEMA


def test_assignment_disjointness_rejects_mixed_target_cohorts(tmp_path) -> None:
    adaptation_path, adaptation_hash = _write_json(
        tmp_path, "adaptation.json", _manifest("target_adaptation", [("s1", "h1")])
    )
    evaluation_payload = _manifest("target_evaluation", [("s2", "h2")])
    evaluation_payload["cohort"] = "ADNI"
    evaluation_payload["records"][0]["cohort"] = "ADNI"
    evaluation_path, evaluation_hash = _write_json(tmp_path, "evaluation.json", evaluation_payload)

    adaptation = validate_manifest(
        adaptation_path, adapter="json", declared_sha256=adaptation_hash, expected_role="target_adaptation"
    )
    evaluation = validate_manifest(
        evaluation_path, adapter="json", declared_sha256=evaluation_hash, expected_role="target_evaluation"
    )

    result = check_assignment_disjointness(adaptation, evaluation)

    assert result.status is ProvenanceStatus.INVALID_SCHEMA
    assert result.reason == "target adaptation and evaluation cohorts must match"


def test_target_adaptation_firewall_rejects_nested_supervision_and_artifacts() -> None:
    valid = {"x": "synthetic", "subject_id": "s1", "subject_hash": "h1", "cohort": "OASIS"}

    validate_target_adaptation_batch(valid)
    for nested in (
        {"diagnosis": 2},
        {"probabilities": [0.2, 0.8]},
        {"concepts": [0.1], "artifact": {"sha256": "h"}},
        {"role": "target_evaluation", "cohort": "ADNI"},
    ):
        with pytest.raises(ValueError, match="supervision|artifact"):
            validate_target_adaptation_batch({**valid, "x": nested})


def test_target_adaptation_firewall_rejects_supervision_aliases_recursively() -> None:
    valid = {"x": "synthetic", "subject_id": "s1", "subject_hash": "h1", "cohort": "OASIS"}
    aliases = (
        "y",
        "label",
        "labels",
        "class_label",
        "diagnosis",
        "target",
        "targets",
        "probability",
        "probabilities",
        "concept_target",
        "concept_targets",
        "jacobian_target",
        "jacobian_targets",
        "anatomical_target",
        "anatomical_targets",
    )

    for alias in aliases:
        with pytest.raises(ValueError, match="supervision|artifact"):
            validate_target_adaptation_batch({**valid, "x": [{"nested": {alias: 1}}]})


def test_target_adaptation_firewall_validates_identity_fields() -> None:
    valid = {"x": "synthetic", "subject_id": "s1", "subject_hash": "h1", "cohort": "OASIS"}

    for field, value in (("subject_id", ""), ("subject_hash", None), ("cohort", "")):
        invalid = {**valid, field: value}
        with pytest.raises(ValueError, match="subject|cohort"):
            validate_target_adaptation_batch(invalid)


def test_target_evaluation_contract_rejects_nested_selection_bypass() -> None:
    valid = {
        "monitoring_label": "MONITORING ONLY — NOT A TRAINING LOSS",
        "selection_usage": False,
        "read_only": True,
        "metrics": {"accuracy": 0.5},
    }

    validate_target_evaluation_metadata(valid)
    with pytest.raises(ValueError, match="selection|monitoring"):
        validate_target_evaluation_metadata({**valid, "selection_usage": True})
    with pytest.raises(ValueError, match="selection|monitoring"):
        validate_target_evaluation_metadata(
            {**valid, "metrics": {"selection_usage": True}}
        )
    with pytest.raises(ValueError, match="monitoring"):
        validate_target_evaluation_metadata(
            {**valid, "monitoring_label": "TARGET METRICS"}
        )


def test_caller_constructed_verified_manifest_is_not_accepted() -> None:
    forged = ManifestValidation(
        status=ProvenanceStatus.VERIFIED,
        sha256="a" * 64,
        byte_size=10,
        records=(("not-a-record",),),
        subject_hashes=frozenset({"h1"}),
        parsed=True,
        role="target_adaptation",
        cohort="OASIS",
    )

    result = check_assignment_disjointness(forged, forged)

    assert result.status is ProvenanceStatus.INVALID_SCHEMA
    assert "verifier-issued" in (result.reason or "")


def test_aggregate_rejects_self_declared_manifest_and_disjointness_claims() -> None:
    report = aggregate_validators(
        provenance={
            "source": {"status": "VERIFIED", "records": []},
            "target_adaptation": {
                "status": "VERIFIED",
                "role": "target_adaptation",
                "cohort": "OASIS",
                "records": [{"subject_id": "s1", "subject_hash": "h1", "cohort": "OASIS"}],
            },
            "target_evaluation": {
                "status": "VERIFIED",
                "role": "target_evaluation",
                "cohort": "OASIS",
                "records": [{"subject_id": "s1", "subject_hash": "h1", "cohort": "OASIS"}],
            },
            "disjoint_assignments": {"status": "VERIFIED"},
        }
    )

    assert any(item.code == "provenance_conflict" for item in report.blockers)
    assert not any(item.code == "overlapping_assignments" for item in report.blockers)
