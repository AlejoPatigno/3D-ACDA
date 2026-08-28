from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from acda3d.evaluation.discovery import (
    ADAPTER_REGISTRY,
    BaselineCombinedAdapter,
    CandidateFiles,
    SharedMethodAdapter,
    discover_candidates,
)
from acda3d.evaluation.schemas import (
    AnalysisMode,
    CandidateStatus,
    CheckpointPolicy,
    Direction,
    EvaluationRequest,
    IssueCode,
    MethodId,
    RunMode,
    UnsafePathError,
)
from tests.phase15_discovery_fixtures import (
    add_identity_population_controls,
    shared_discovery_config,
    write_baseline_candidate,
    write_shared_candidate,
)


def _request(*methods: MethodId) -> EvaluationRequest:
    return EvaluationRequest(
        methods=methods,
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        analysis_mode=AnalysisMode.SYNTHETIC_TEST_ONLY,
        run_mode=RunMode.VALIDATE_ONLY,
        bootstrap_replicates=10,
        bootstrap_seed=7,
    )


def test_shared_registry_is_literal_and_public_names_are_fixed() -> None:
    assert ADAPTER_REGISTRY[MethodId.SOURCE_ONLY].public_name == "3D-ACDA Source-Only"
    assert ADAPTER_REGISTRY[MethodId.CORAL].public_name == "3D-ACDA + CORAL"
    assert ADAPTER_REGISTRY[MethodId.MMD].public_name == "3D-ACDA + MMD"
    assert ADAPTER_REGISTRY[MethodId.CDAN].public_name == "3D-ACDA + CDAN"
    assert ADAPTER_REGISTRY[MethodId.PROTOTYPE_PSEUDO].public_name == "3D-ACDA"
    shared = set(MethodId) - {MethodId.AAGN, MethodId.FASTER_SNN}
    assert all(ADAPTER_REGISTRY[method].schema_family == "shared_method" for method in shared)


def test_configured_discovery_is_deterministic_and_complete(tmp_path: Path) -> None:
    write_shared_candidate(tmp_path)
    candidates = discover_candidates(shared_discovery_config(), tmp_path, _request(MethodId.MMD), (2,), (17,))
    assert len(candidates) == 1
    candidate = candidates[0]
    assert isinstance(candidate, CandidateFiles)
    assert candidate.issues == ()
    assert [role.value for role, _ in candidate.prediction_files] == ["source_oof", "target_evaluation"]
    assert candidate.companion_files[0].name == "run_manifest.json"


def test_missing_expected_file_remains_visible(tmp_path: Path) -> None:
    base = write_shared_candidate(tmp_path)
    (base / "target_monitoring_predictions" / "best_source_f1.csv").unlink()
    candidate = discover_candidates(shared_discovery_config(), tmp_path, _request(MethodId.MMD), (2,), (17,))[0]
    assert {issue.code for issue in candidate.issues} == {IssueCode.MISSING_REQUIRED_FIELD}
    assert all(issue.status is CandidateStatus.INCOMPLETE for issue in candidate.issues)


def test_configured_path_escape_is_rejected_before_parsing(tmp_path: Path) -> None:
    config = shared_discovery_config()
    config["shared_method"]["prediction_pattern"] = "../{method}.csv"
    with pytest.raises(UnsafePathError):
        discover_candidates(config, tmp_path, _request(MethodId.MMD), (2,), (17,))


def test_shared_adapter_normalizes_both_roles_without_mutating_inputs(tmp_path: Path) -> None:
    write_shared_candidate(tmp_path)
    candidate = discover_candidates(shared_discovery_config(), tmp_path, _request(MethodId.MMD), (2,), (17,))[0]
    before = {path: path.read_bytes() for _, path in candidate.prediction_files}
    batch = SharedMethodAdapter().normalize(candidate, tmp_path)
    assert batch.schema_family == "shared_method"
    assert len(batch.predictions) == 4
    assert {prediction.role.value for prediction in batch.predictions} == {"source_oof", "target_evaluation"}
    assert {prediction.subject_hash for prediction in batch.predictions} == {"hash-a", "hash-b"}
    assert batch.issues == ()
    assert all(path.read_bytes() == before[path] for _, path in candidate.prediction_files)


def test_shared_adapter_reports_manifest_conflicts(tmp_path: Path) -> None:
    base = write_shared_candidate(tmp_path)
    manifest_path = base / "run_manifest.json"
    manifest_path.write_text(manifest_path.read_text().replace('"mmd"', '"coral"'), encoding="utf-8")
    candidate = discover_candidates(shared_discovery_config(), tmp_path, _request(MethodId.MMD), (2,), (17,))[0]
    batch = SharedMethodAdapter().normalize(candidate, tmp_path)
    assert batch.predictions == ()
    assert IssueCode.PROVENANCE_CONFLICT in {issue.code for issue in batch.issues}


def test_baseline_registry_and_seven_method_matrix_are_explicit(tmp_path: Path) -> None:
    assert ADAPTER_REGISTRY[MethodId.AAGN].public_name == "AAGN"
    assert ADAPTER_REGISTRY[MethodId.FASTER_SNN].public_name == "FasterSNN"
    assert ADAPTER_REGISTRY[MethodId.AAGN].schema_family == "baseline_combined"
    request = _request(*tuple(MethodId))
    candidates = discover_candidates(shared_discovery_config(), tmp_path, request, (2,), (17,))
    assert [candidate.method_id for candidate in candidates] == list(MethodId)
    assert all(candidate.issues for candidate in candidates)


def test_discovery_binds_approved_identity_and_external_populations(tmp_path: Path) -> None:
    write_baseline_candidate(tmp_path)
    config = add_identity_population_controls(shared_discovery_config(), tmp_path)
    candidate = discover_candidates(config, tmp_path, _request(MethodId.AAGN), (2,), (17,))[0]
    assert {role.value for role, _, _ in candidate.identity_mappings} == {
        "source_oof", "target_evaluation",
    }
    assert {item.role.value for item in candidate.expected_populations} == {
        "source_oof", "target_evaluation",
    }
    assert all(item.subject_hashes == ("hash-a", "hash-b") for item in candidate.expected_populations)
    batch = BaselineCombinedAdapter().normalize(candidate, tmp_path)
    assert batch.issues == ()
    assert len(batch.predictions) == 4
    assert "private-a" not in repr(batch)


def test_identity_companion_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    write_baseline_candidate(tmp_path)
    config = add_identity_population_controls(shared_discovery_config(), tmp_path)
    (tmp_path / "identity/ADNI.csv").write_text("changed", encoding="utf-8")
    candidate = discover_candidates(config, tmp_path, _request(MethodId.AAGN), (2,), (17,))[0]
    assert IssueCode.UNAPPROVED_IDENTITY_MAPPING in {issue.code for issue in candidate.issues}


def test_source_only_requires_exact_target_evaluation_membership(tmp_path: Path) -> None:
    base = write_shared_candidate(tmp_path, method="source_only")
    manifest_path = base / "run_manifest.json"
    manifest = manifest_path.read_text(encoding="utf-8").replace(
        '"target_evaluation_assignment_hash": "value-target_evaluation_assignment_hash", ', ""
    )
    manifest_path.write_text(manifest, encoding="utf-8")
    config = add_identity_population_controls(shared_discovery_config(), tmp_path)
    candidate = discover_candidates(config, tmp_path, _request(MethodId.SOURCE_ONLY), (2,), (17,))[0]
    batch = SharedMethodAdapter().normalize(candidate, tmp_path)
    assert batch.predictions == ()
    assert IssueCode.TARGET_EVALUATION_MEMBERSHIP_UNPROVABLE in {
        issue.code for issue in batch.issues
    }


def test_baseline_adapter_partitions_roles_and_discards_raw_ids(tmp_path: Path) -> None:
    write_baseline_candidate(tmp_path)
    candidate = discover_candidates(shared_discovery_config(), tmp_path, _request(MethodId.AAGN), (2,), (17,))[0]
    batch = BaselineCombinedAdapter().normalize(candidate, tmp_path)
    assert len(batch.predictions) == 4
    assert {prediction.role.value for prediction in batch.predictions} == {"source_oof", "target_evaluation"}
    assert "private-a" not in repr(batch)
    assert batch.issues == ()


def test_baseline_requires_exact_target_evaluation_membership(tmp_path: Path) -> None:
    base = write_baseline_candidate(tmp_path)
    manifest = (base / "run_manifest.json").read_text(encoding="utf-8")
    manifest = manifest.replace('"target_evaluation_assignment_hash": "value-target_evaluation_assignment_hash", ', "")
    (base / "run_manifest.json").write_text(manifest, encoding="utf-8")
    candidate = discover_candidates(shared_discovery_config(), tmp_path, _request(MethodId.AAGN), (2,), (17,))[0]
    batch = BaselineCombinedAdapter().normalize(candidate, tmp_path)
    assert batch.predictions == ()
    assert IssueCode.TARGET_EVALUATION_MEMBERSHIP_UNPROVABLE in {issue.code for issue in batch.issues}


def test_discovery_has_no_training_or_model_registry_imports() -> None:
    import acda3d.evaluation.discovery as discovery

    tree = ast.parse(inspect.getsource(discovery))
    imported = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith(("acda3d.training", "acda3d.models", "acda3d.experiments")) for name in imported)
