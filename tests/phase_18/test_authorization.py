from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import pada3dacb.publication.authorization as authorization_module
from pada3dacb.publication.authorization import check_authorization
from pada3dacb.publication.canonical_json import identity_sha256
from pada3dacb.publication.experiment_matrix import generate_matrix
from pada3dacb.publication.provenance import ManifestValidation, ProvenanceStatus

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "publication" / "real_run_authorization.yaml"


class _PrivateVerifierToken:
    pass


class _VerifierFixture:
    def __init__(self) -> None:
        self.token = _PrivateVerifierToken()

    def verify(self, candidate: object) -> bool:
        return candidate is self.token


def _verifier_fixture() -> _VerifierFixture:
    return _VerifierFixture()


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "phase18.real-run-gate.v1",
        "phase_18_authorized": True,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "publication_authorized": False,
        "phase_19_forbidden": True,
        "authorized": True,
        "freeze_payload": {"marker": "freeze"},
        "freeze_hash": _digest("freeze"),
        "scientific_resolution_hash": _digest("science"),
        "method_parameter_ledger_hash": _digest("params"),
        "canonicalization_conformance_hash": _digest("canonical"),
        "matrix_hash": _digest("matrix"),
        "method_inventory_hash": _digest("methods"),
        "seed_policy": [42],
        "seed_policy_hash": _digest("seed-policy"),
        "split_manifest_hashes": {"ADNI": _digest("adni"), "OASIS": _digest("oasis")},
        "assignment_hashes": {
            "source": _digest("source"),
            "target_adaptation": _digest("adaptation"),
            "target_evaluation": _digest("evaluation"),
        },
        "assignment_manifest_contents": {
            "target_adaptation_subject_hashes": ["adaptation-subject"],
            "target_evaluation_subject_hashes": ["evaluation-subject"],
            "required_intersection": [],
            "aggregate_hashes_alone_are_insufficient": True,
        },
        "artifact_hashes": {
            name: _digest(name)
            for name in (
                "atlas",
                "roi_order",
                "roi_masks",
                "concept_normalizer",
                "concept_targets",
                "jacobians",
            )
        },
        "artifact_index": {name: _digest(name) for name in ("atlas", "roi_order", "roi_masks", "concept_normalizer", "concept_targets", "jacobians")},
        "configuration_hash": _digest("configuration"),
        "code_revision": _digest("code"),
        "environment_hash": _digest("environment"),
        "command_hash": _digest("command"),
        "privacy_data_access_record_hash": _digest("privacy"),
        "resource_budget_hash": _digest("budget"),
        "feasibility_observation_hash": _digest("feasibility"),
        "independent_review_hash": _digest("review"),
        "human_authorization_hash": _digest("human"),
        "native_receipt_hash": _digest("receipt"),
        "target_identity": "target-manifest-v1",
        "target_hash": _digest("target-manifest-v1"),
        "scientific_resolution": {"lambda_proto": 1.0},
        "matrix": {"matrix_id": _digest("matrix")},
        "resource_budget": {"status": "approved"},
        "feasibility": {
            "mode": "synthetic_only",
            "real_data_accessed": False,
            "publication_metrics_present": False,
            "real_resource_fields_resolved": False,
            "status": "pass",
        },
    }


def test_authorized_true_alone_is_insufficient() -> None:
    result = check_authorization({"authorized": True})

    assert result.authorized is False
    assert any(blocker.code == "missing_required_field" for blocker in result.blockers)


def test_missing_field_and_wrong_freeze_hash_fail_closed() -> None:
    manifest = _manifest()
    del manifest["privacy_data_access_record_hash"]
    manifest["freeze_hash"] = "0" * 64

    result = check_authorization(manifest)

    codes = {blocker.code for blocker in result.blockers}
    assert "missing_required_field" in codes
    assert "hash_mismatch" in codes


def test_unresolved_science_and_overlapping_assignments_are_explicit_blockers() -> None:
    manifest = _manifest()
    manifest["scientific_resolution"] = {"lambda_proto": "unresolved"}
    manifest["assignment_manifest_contents"]["required_intersection"] = ["same-subject"]

    result = check_authorization(manifest)

    codes = {blocker.code for blocker in result.blockers}
    assert "unresolved_scientific_value" in codes
    assert "overlapping_assignments" in codes


def test_privacy_human_and_native_receipt_are_required() -> None:
    manifest = _manifest()
    for field in (
        "privacy_data_access_record_hash",
        "human_authorization_hash",
        "native_receipt_hash",
    ):
        del manifest[field]

    result = check_authorization(manifest)
    codes = {blocker.code for blocker in result.blockers}

    assert {"privacy_missing", "human_authorization_missing", "native_receipt_missing"} <= codes


def test_read_only_checker_reports_blockers_and_nonzero_closure() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_real_run_authorization.py"), "--config", str(CONFIG)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "REAL RUN NOT AUTHORIZED" in completed.stdout
    assert "PASS — FAIL-CLOSED AUTHORIZATION VERIFIED" in completed.stdout
    assert "lambda_proto" in completed.stdout


def test_prepare_cli_prints_matrix_and_blockers_without_training() -> None:
    script = ROOT / "scripts" / "prepare_publication_run.py"
    matrix = subprocess.run(
        [sys.executable, str(script), "--config", str(CONFIG), "--print-matrix"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    blockers = subprocess.run(
        [sys.executable, str(script), "--config", str(CONFIG), "--print-blockers"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert matrix.returncode != 0
    assert "source_only" in matrix.stdout
    assert "adni_to_oasis" in matrix.stdout
    assert blockers.returncode != 0
    assert "lambda_proto" in blockers.stdout
    assert "train" not in matrix.stdout.lower() or "training" in matrix.stdout.lower()


def test_prepare_cli_write_freeze_refuses_overwrite(tmp_path) -> None:
    script = ROOT / "scripts" / "prepare_publication_run.py"
    first = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(CONFIG),
            "--output-root",
            str(tmp_path),
            "--write-freeze",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    second = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(CONFIG),
            "--output-root",
            str(tmp_path),
            "--write-freeze",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert first.returncode == 0
    assert (tmp_path / "publication_freeze.json").exists()
    assert second.returncode != 0
    assert "overwrite" in second.stdout.lower()


def test_configs_are_planning_only() -> None:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))

    assert payload["real_execution_authorized"] is False
    assert payload["publication_authorized"] is False
    assert payload["phase_19_forbidden"] is True


def test_missing_structured_freeze_payload_and_method_ledger_are_blockers() -> None:
    manifest = _manifest()
    manifest.pop("freeze_payload")
    manifest.pop("method_parameter_ledger", None)

    result = check_authorization(manifest)

    fields = {blocker.field for blocker in result.blockers}
    assert "freeze_payload" in fields
    assert "method_parameter_ledger" in fields


def test_authorization_requires_external_native_content_bound_evidence() -> None:
    manifest = _manifest()
    manifest["authorization_evidence"] = {
        "source": "local",
        "external": False,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "native_receipt": {"sha256": "a" * 64, "content": {"placeholder": True}},
    }

    result = check_authorization(manifest)

    assert any(blocker.code == "external_evidence_missing" for blocker in result.blockers)


def test_fabricated_sha256_hashes_are_not_authorization_evidence() -> None:
    manifest = _manifest()
    manifest["authorization_evidence"] = {
        "source": "native",
        "external": True,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "native_receipt": {"sha256": "f" * 64, "content": {"placeholder": True}},
    }

    result = check_authorization(manifest)

    assert any(blocker.code == "hash_evidence_invalid" for blocker in result.blockers)


def test_degenerate_matrix_is_rejected_even_with_a_matching_matrix_hash() -> None:
    from pada3dacb.publication.experiment_matrix import generate_matrix, matrix_content_hash

    matrix = generate_matrix(seeds=[42]).to_mapping()
    matrix["rows"] = matrix["rows"][:1]
    manifest = _manifest()
    manifest["matrix"] = matrix
    manifest["matrix_hash"] = matrix_content_hash(matrix)

    result = check_authorization(manifest)

    assert any(blocker.code == "incomplete_matrix" for blocker in result.blockers)


def test_explicit_resolved_seed_cardinality_is_not_rejected_as_140_rows() -> None:
    from pada3dacb.publication.experiment_matrix import generate_matrix, matrix_content_hash

    matrix = generate_matrix(
        seeds=[7, 42],
        resolved_seed_policy={"resolved": True, "seeds": [7, 42], "source": "external"},
    ).to_mapping()
    manifest = _manifest()
    manifest["matrix"] = matrix
    manifest["matrix_hash"] = matrix_content_hash(matrix)

    result = check_authorization(manifest)

    assert not any(
        blocker.code == "incomplete_matrix" and blocker.field == "matrix.rows"
        for blocker in result.blockers
    )


def test_unresolved_blockers_propagate_from_required_evidence_mappings() -> None:
    manifest = _manifest()
    manifest["freeze_payload"] = {"status": "unresolved_blocking"}
    manifest["method_parameter_ledger"] = {
        method: {"parameters": "unresolved", "value_class": "unresolved_blocking", "evidence": "pending"}
        for method in ("source_only", "coral", "mmd", "cdan", "prototype_pseudo", "aagn", "faster_snn")
    }

    result = check_authorization(manifest)

    fields = {blocker.field for blocker in result.blockers}
    assert "freeze_payload" in fields
    assert "method_parameter_ledger" in fields
    assert any(blocker.code == "unresolved_method_parameter" for blocker in result.blockers)


def test_arbitrary_resource_budget_mapping_cannot_close_the_budget() -> None:
    manifest = _manifest()
    manifest["resource_budget"] = {
        "real_budget_closed": True,
        "evidence": {"approved": True},
        "closure": {"closed": True},
    }

    result = check_authorization(manifest)

    assert any(blocker.code == "resource_budget_unresolved" for blocker in result.blockers)


def test_hash_evidence_must_bind_exact_ledger_and_budget_objects() -> None:
    ledger = {
        method: {"parameters": {"weight": 1}, "value_class": "fixed", "evidence": {"source": "config"}}
        for method in ("source_only", "coral", "mmd", "cdan", "prototype_pseudo", "aagn", "faster_snn")
    }
    budget = {"real_budget_closed": True, "status": "measured"}
    forged_ledger = {"forged": "ledger"}
    forged_budget = {"forged": "budget"}
    manifest = _manifest()
    manifest["method_parameter_ledger"] = ledger
    manifest["resource_budget"] = budget
    manifest["method_parameter_ledger_hash"] = identity_sha256(forged_ledger)
    manifest["resource_budget_hash"] = identity_sha256(forged_budget)
    manifest["hash_evidence"] = {
        "method_parameter_ledger_hash": {"content": forged_ledger, "sha256": identity_sha256(forged_ledger)},
        "resource_budget_hash": {"content": forged_budget, "sha256": identity_sha256(forged_budget)},
        "freeze_hash": {"content": manifest["freeze_payload"], "sha256": manifest["freeze_hash"]},
    }

    result = check_authorization(manifest)

    fields = {blocker.field for blocker in result.blockers}
    assert "hash_evidence.method_parameter_ledger_hash" in fields
    assert "hash_evidence.resource_budget_hash" in fields


def test_approval_hashes_require_structured_external_attestations() -> None:
    manifest = _manifest()
    digest = _digest("attestation")
    manifest["statistical_review_hash"] = digest
    for field in (
        "privacy_data_access_record_hash",
        "independent_review_hash",
        "statistical_review_hash",
        "human_authorization_hash",
    ):
        manifest[field] = digest

    result = check_authorization(manifest)

    fields = {blocker.field for blocker in result.blockers}
    assert "privacy_data_access_record" in fields
    assert "independent_review" in fields
    assert "statistical_review" in fields
    assert "human_authorization" in fields


def test_top_level_seed_policy_must_match_matrix_seed_set() -> None:
    from pada3dacb.publication.experiment_matrix import matrix_content_hash

    matrix = generate_matrix(
        seeds=[7, 42],
        resolved_seed_policy={"resolved": True, "seeds": [7, 42], "source": "external"},
    ).to_mapping()
    manifest = _manifest()
    manifest["matrix"] = matrix
    manifest["matrix_hash"] = matrix_content_hash(matrix)

    result = check_authorization(manifest)

    assert any(
        blocker.code == "seed_policy_mismatch" and blocker.field == "matrix.seeds"
        for blocker in result.blockers
    )


def test_attestation_content_binding_also_requires_external_provenance() -> None:
    manifest = _manifest()
    content = {"decision": "approved", "reviewer": "independent"}
    digest = identity_sha256(content)
    for record_field, hash_field in (
        ("privacy_data_access_record", "privacy_data_access_record_hash"),
        ("independent_review", "independent_review_hash"),
        ("statistical_review", "statistical_review_hash"),
        ("human_authorization", "human_authorization_hash"),
    ):
        manifest[record_field] = {"source": "local", "external": False, "content": content, "sha256": digest}
        manifest[hash_field] = digest

    result = check_authorization(manifest)

    assert {blocker.field for blocker in result.blockers} >= {
        "privacy_data_access_record",
        "independent_review",
        "statistical_review",
        "human_authorization",
    }


def test_self_asserted_external_native_authority_mapping_fails_closed() -> None:
    content = {"decision": "approved", "issuer": "claimed"}
    digest = identity_sha256(content)

    for source in ("external", "native"):
        manifest = _manifest()
        manifest["native_receipt_hash"] = digest
        manifest["authorization_evidence"] = {
            "source": source,
            "external": True,
            "freeze_approved": True,
            "real_execution_authorized": True,
            "native_receipt": {
                "source": source,
                "external": True,
                "content": content,
                "sha256": digest,
            },
        }

        result = check_authorization(manifest)

        assert any(
            blocker.code == "external_evidence_missing"
            and blocker.field == "authorization_evidence.authority_marker"
            for blocker in result.blockers
        )


def test_self_asserted_external_native_attestations_fail_closed() -> None:
    content = {"decision": "approved", "reviewer": "claimed"}
    digest = identity_sha256(content)

    for source in ("external", "native"):
        manifest = _manifest()
        for record_field, hash_field in (
            ("privacy_data_access_record", "privacy_data_access_record_hash"),
            ("independent_review", "independent_review_hash"),
            ("statistical_review", "statistical_review_hash"),
            ("human_authorization", "human_authorization_hash"),
        ):
            manifest[record_field] = {
                "source": source,
                "external": True,
                "content": content,
                "sha256": digest,
            }
            manifest[hash_field] = digest

        result = check_authorization(manifest)

        assert {
            blocker.field
            for blocker in result.blockers
            if blocker.code == "attestation_missing"
        } >= {
            "privacy_data_access_record",
            "independent_review",
            "statistical_review",
            "human_authorization",
        }


def test_exported_verifier_sentinel_is_not_available() -> None:
    assert not hasattr(authorization_module, "VERIFIER_AUTHORITY_SENTINEL")


def test_production_authorization_has_no_importable_issuer() -> None:
    assert not hasattr(authorization_module, "_issue_verifier_authority_for_testing")
    assert not hasattr(authorization_module, "_issue_authority")


def test_verifier_authority_accepts_content_bound_attestations() -> None:
    content = {"decision": "approved", "reviewer": "verifier"}
    digest = identity_sha256(content)
    verifier_fixture = _verifier_fixture()
    authority = verifier_fixture.token
    manifest = _manifest()
    for record_field, hash_field in (
        ("privacy_data_access_record", "privacy_data_access_record_hash"),
        ("independent_review", "independent_review_hash"),
        ("statistical_review", "statistical_review_hash"),
        ("human_authorization", "human_authorization_hash"),
    ):
        manifest[record_field] = {
            "source": "external",
            "external": True,
            "authority_marker": authority,
            "content": content,
            "sha256": digest,
        }
        manifest[hash_field] = digest

    result = check_authorization(manifest, verifier=verifier_fixture.verify)

    assert not {
        blocker.field
        for blocker in result.blockers
        if blocker.code == "attestation_missing"
    } & {
        "privacy_data_access_record",
        "independent_review",
        "statistical_review",
        "human_authorization",
    }


def test_arbitrary_receipt_mapping_with_verifier_token_fails_closed() -> None:
    verifier_fixture = _verifier_fixture()
    authority = verifier_fixture.token
    manifest = _manifest()
    manifest["native_receipt_hash"] = identity_sha256({"receipt": "verifier-issued"})
    manifest["authorization_evidence"] = {
        "source": "native",
        "external": True,
        "authority_marker": authority,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "native_receipt": {
            "source": "native",
            "external": True,
            "authority_marker": authority,
            "content": {"receipt": "verifier-issued"},
            "sha256": manifest["native_receipt_hash"],
        },
    }

    result = check_authorization(manifest, verifier=verifier_fixture.verify)

    assert any(
        blocker.code == "hash_evidence_invalid"
        and blocker.field == "authorization_evidence.native_receipt"
        for blocker in result.blockers
    )


def test_native_receipt_requires_matching_lineage_gate_and_result() -> None:
    verifier_fixture = _verifier_fixture()
    authority = verifier_fixture.token
    valid_content = {"lineage": "review-123", "gate": "post-apply", "result": "allow"}
    manifest = _manifest()
    manifest["native_receipt_hash"] = identity_sha256(valid_content)
    manifest["authorization_evidence"] = {
        "source": "native",
        "external": True,
        "authority_marker": authority,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "native_receipt": {
            "schema": "gentle-ai.review-receipt/v1",
            "lineage": "review-other",
            "gate": "pre-commit",
            "result": "deny",
            "authority_marker": authority,
            "content": valid_content,
            "sha256": manifest["native_receipt_hash"],
        },
    }

    result = check_authorization(manifest, verifier=verifier_fixture.verify)

    assert any(
        blocker.code == "hash_evidence_invalid"
        and blocker.field == "authorization_evidence.native_receipt"
        for blocker in result.blockers
    )


def test_verifier_authority_binds_strict_native_receipt() -> None:
    verifier_fixture = _verifier_fixture()
    authority = verifier_fixture.token
    content = {
        "lineage": "review-123",
        "gate": "post-apply",
        "result": "allow",
        "target_identity": "target-manifest-v1",
        "target_hash": _digest("target-manifest-v1"),
    }
    digest = identity_sha256(content)
    manifest = _manifest()
    manifest["native_receipt_hash"] = digest
    manifest["authorization_evidence"] = {
        "source": "native",
        "external": True,
        "authority_marker": authority,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "native_receipt": {
            "source": "native",
            "external": True,
            "schema": "gentle-ai.review-receipt/v1",
            "lineage": "review-123",
            "gate": "post-apply",
            "result": "allow",
            "target_identity": "target-manifest-v1",
            "target_hash": _digest("target-manifest-v1"),
            "authority_marker": authority,
            "content": content,
            "sha256": digest,
        },
    }

    result = check_authorization(manifest, verifier=verifier_fixture.verify)

    assert not {
        blocker.field
        for blocker in result.blockers
        if blocker.code in {"external_evidence_missing", "hash_evidence_invalid"}
    } & {"authorization_evidence.authority_marker", "authorization_evidence.native_receipt"}


def test_authorization_invokes_target_firewalls_for_supplied_manifests() -> None:
    manifest = _manifest()
    manifest["target_adaptation_batch"] = {
        "x": {"diagnosis": 2},
        "subject_id": "s1",
        "subject_hash": "h1",
        "cohort": "OASIS",
    }
    manifest["target_evaluation_metadata"] = {
        "monitoring_label": "TARGET METRICS",
        "selection_usage": True,
        "read_only": False,
    }

    result = check_authorization(manifest)

    isolation = {
        blocker.field
        for blocker in result.blockers
        if blocker.code == "target_isolation_violation"
    }
    assert {"target_adaptation", "target_evaluation"} <= isolation


def test_authorization_does_not_accept_self_declared_target_manifest_status() -> None:
    manifest = _manifest()
    manifest["target_adaptation_batch"] = {
        "status": "VERIFIED",
        "role": "target_adaptation",
    }
    manifest["target_evaluation_metadata"] = {
        "monitoring_label": "MONITORING ONLY — NOT A TRAINING LOSS",
        "selection_usage": False,
        "read_only": True,
    }

    result = check_authorization(manifest)

    assert any(
        blocker.code == "target_isolation_violation"
        and blocker.field == "target_adaptation"
        for blocker in result.blockers
    )


def test_authorization_rejects_caller_constructed_verified_manifest() -> None:
    forged = ManifestValidation(
        status=ProvenanceStatus.VERIFIED,
        sha256="a" * 64,
        byte_size=10,
        records=(),
        subject_hashes=frozenset({"h1"}),
        parsed=True,
        role="target_adaptation",
        cohort="OASIS",
    )
    manifest = _manifest()
    manifest["provenance"] = {
        "source": forged,
        "target_adaptation": forged,
        "target_evaluation": forged,
        "disjoint_assignments": {"status": "VERIFIED"},
    }

    result = check_authorization(manifest)

    assert any(
        blocker.code == "provenance_conflict" and blocker.field == "source"
        for blocker in result.blockers
    )


@pytest.mark.parametrize(
    ("replay_identity", "replay_hash"),
    (
        ("different-target", _digest("different-target")),
        ("target-manifest-v1", _digest("different-target-hash")),
    ),
)
def test_native_receipt_replay_for_different_target_fails_closed(
    replay_identity: str, replay_hash: str
) -> None:
    verifier_fixture = _verifier_fixture()
    authority = verifier_fixture.token
    content = {
        "lineage": "review-123",
        "gate": "post-apply",
        "result": "allow",
        "target_identity": replay_identity,
        "target_hash": replay_hash,
    }
    digest = identity_sha256(content)
    manifest = _manifest()
    manifest["native_receipt_hash"] = digest
    manifest["authorization_evidence"] = {
        "source": "native",
        "external": True,
        "authority_marker": authority,
        "freeze_approved": True,
        "real_execution_authorized": True,
        "native_receipt": {
            "source": "native",
            "external": True,
            "schema": "gentle-ai.review-receipt/v1",
            "lineage": "review-123",
            "gate": "post-apply",
            "result": "allow",
            "target_identity": replay_identity,
            "target_hash": replay_hash,
            "authority_marker": authority,
            "content": content,
            "sha256": digest,
        },
    }

    result = check_authorization(manifest, verifier=verifier_fixture.verify)

    assert any(
        blocker.code == "hash_evidence_invalid"
        and blocker.field == "authorization_evidence.native_receipt"
        for blocker in result.blockers
    )
