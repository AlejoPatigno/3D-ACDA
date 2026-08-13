from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from pada3dacb.publication.authorization import check_authorization
from pada3dacb.publication.canonical_json import canonical_json_bytes, identity_sha256
from pada3dacb.publication.experiment_matrix import (
    MatrixValidationError,
    RowKind,
    generate_matrix,
    matrix_content_hash,
)
from pada3dacb.publication.feasibility import (
    EvidenceType,
    ProductionShapeMetadata,
    ResourceBudgetStatus,
    build_resource_budget,
    run_synthetic_feasibility,
    validate_budget_closure,
)
from pada3dacb.publication.freeze import (
    build_freeze_payload,
    read_freeze,
    write_freeze,
)
from pada3dacb.publication.provenance import (
    ProvenanceStatus,
    check_assignment_disjointness,
    validate_manifest,
)
from pada3dacb.publication.schemas import ValueClass, ValueClassification
from pada3dacb.publication.validation import (
    aggregate_validators,
    validate_target_adaptation_batch,
    validate_target_evaluation_metadata,
)

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_ROOT = ROOT / "src" / "pada3dacb" / "publication"
CLI_PATHS = (
    ROOT / "scripts" / "prepare_publication_run.py",
    ROOT / "scripts" / "check_real_run_authorization.py",
)
CLASS_LABELS = ("CN", "MCI", "AD")
ROI_LABELS = tuple(f"roi_{index:03d}" for index in range(102))


def _shape(batch_size: int = 2) -> ProductionShapeMetadata:
    return ProductionShapeMetadata(
        input_shape=(batch_size, 1, 8, 10, 12),
        feature_shape=(batch_size, 256, 2, 3, 3),
        roi_mask_shape=(102, 2, 3, 3),
        token_shape=(batch_size, 102, 128),
        embedding_shape=(batch_size, 128),
        concepts_shape=(batch_size, 102),
        c_target_shape=(batch_size, 102),
        g_bar_shape=(batch_size, 102),
        diagnosis_logits_shape=(batch_size, 3),
        class_labels=CLASS_LABELS,
        roi_labels=ROI_LABELS,
    )


def _manifest(role: str, cohort: str, subject_hashes: list[str]) -> dict[str, object]:
    return {
        "schema_version": "phase18.manifest.v1",
        "role": role,
        "cohort": cohort,
        "one_scan_per_subject": True,
        "records": [
            {
                "subject_id": f"synthetic-{index}",
                "subject_hash": subject_hash,
                "role": role,
                "cohort": cohort,
            }
            for index, subject_hash in enumerate(subject_hashes)
        ],
    }


def _write_manifest(tmp_path: Path, name: str, payload: object) -> tuple[Path, str]:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    path = tmp_path / name
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def test_canonical_bytes_and_freeze_round_trip_preserve_identity(tmp_path: Path) -> None:
    value = {"z": [-0.0, 1e6], "é": "e\u0301", "a": [True, None]}
    assert canonical_json_bytes(value) == '{"a":[true,null],"z":[0,1000000],"é":"é"}'.encode()

    payload = yaml.safe_load(
        (ROOT / "configs" / "publication" / "publication_experiment_freeze.yaml").read_text(
            encoding="utf-8"
        )
    )
    path = tmp_path / "freeze.json"
    envelope = write_freeze(path, build_freeze_payload(payload))
    loaded = read_freeze(path)

    assert path.read_bytes() == canonical_json_bytes(envelope)
    assert loaded["freeze_hash"] == identity_sha256(loaded["payload"])
    assert loaded["payload"]["real_execution_authorized"] is False
    assert loaded["payload"]["publication_authorized"] is False
    assert loaded["payload"]["phase_19_forbidden"] is True


def test_value_classes_and_unresolved_science_propagate_without_defaults() -> None:
    classifications = (
        ValueClassification("fixed", 42, ValueClass.CANONICAL_FIXED, "config", None),
        ValueClassification("selected", "manual", ValueClass.MANUALLY_SELECTED_PRE_RUN, None, "approval"),
        ValueClassification("probe", 0.1, ValueClass.ENGINEERING_ONLY, "synthetic", None),
        ValueClassification("lambda_proto", "unresolved", ValueClass.UNRESOLVED_BLOCKING, None, "0.2 vs 1.0"),
    )
    assert {item.value_class for item in classifications} == set(ValueClass)

    config = yaml.safe_load(
        (ROOT / "configs" / "publication" / "publication_experiment_freeze.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload = build_freeze_payload(config)
    blocker_text = "\n".join(payload["blockers"])

    assert "lambda_proto" in blocker_text
    assert "coral_mmd_cdan_parameters" in blocker_text
    assert "publication_ablation_subset" in blocker_text
    assert payload["real_execution_authorized"] is False


def test_matrix_and_aggregate_validation_keep_the_full_planning_contract() -> None:
    matrix = generate_matrix(seeds=[42])
    training = matrix.training_rows
    projections = matrix.projection_rows

    assert matrix.counts == {"training": 70, "checkpoint_projection": 70, "total": 140}
    assert {row.direction for row in training} == {"adni_to_oasis", "oasis_to_adni"}
    assert {row.fold for row in training} == {0, 1, 2, 3, 4}
    assert {row.seed for row in training} == {42}
    assert sum(row.training_invocation for row in training) == 70
    assert all(row.row_kind is RowKind.TRAINING for row in training)
    assert all(row.row_kind is RowKind.CHECKPOINT_PROJECTION for row in projections)
    assert {row.parent_training_id for row in projections} == {row.row_id for row in training}
    assert all(row.state.value != "COMPLETED" for row in matrix.rows)
    assert aggregate_validators(matrix=matrix).valid

    with pytest.raises(MatrixValidationError, match="direction"):
        generate_matrix(seeds=[42], directions=["ADNI_to_OASIS", "oasis_to_adni"])


def test_aggregate_validation_binds_matrix_content_hash_not_dimensions_only_id() -> None:
    matrix = generate_matrix(seeds=[42])
    mapping = matrix.to_mapping()
    mapping["matrix_content_hash"] = "0" * 64

    report = aggregate_validators(matrix=mapping)

    assert any(item.code == "hash_mismatch" for item in report.blockers)
    assert matrix_content_hash(matrix) != mapping["matrix_content_hash"]


def test_hash_verified_manifests_enforce_identity_roles_cohorts_and_subject_overlap(
    tmp_path: Path,
) -> None:
    source_path, source_hash = _write_manifest(
        tmp_path, "source.json", _manifest("source", "ADNI", ["source-1"])
    )
    adaptation_path, adaptation_hash = _write_manifest(
        tmp_path,
        "adaptation.json",
        _manifest("target_adaptation", "OASIS", ["target-1"]),
    )
    evaluation_path, evaluation_hash = _write_manifest(
        tmp_path,
        "evaluation.json",
        _manifest("target_evaluation", "OASIS", ["target-2"]),
    )
    source = validate_manifest(
        source_path,
        adapter="json",
        declared_sha256=source_hash,
        expected_role="source",
        expected_cohort="ADNI",
    )
    adaptation = validate_manifest(
        adaptation_path,
        adapter="json",
        declared_sha256=adaptation_hash,
        expected_role="target_adaptation",
        expected_cohort="OASIS",
    )
    evaluation = validate_manifest(
        evaluation_path,
        adapter="json",
        declared_sha256=evaluation_hash,
        expected_role="target_evaluation",
        expected_cohort="OASIS",
    )

    assert all(result.status is ProvenanceStatus.VERIFIED for result in (source, adaptation, evaluation))
    assert check_assignment_disjointness(adaptation, evaluation).status is ProvenanceStatus.VERIFIED

    overlap_payload = _manifest("target_evaluation", "OASIS", ["target-1"])
    overlap_path, overlap_hash = _write_manifest(tmp_path, "overlap.json", overlap_payload)
    overlap = validate_manifest(
        overlap_path,
        adapter="json",
        declared_sha256=overlap_hash,
        expected_role="target_evaluation",
        expected_cohort="OASIS",
    )
    assert check_assignment_disjointness(adaptation, overlap).status is ProvenanceStatus.OVERLAPPING_ASSIGNMENTS

    wrong_hash = validate_manifest(
        evaluation_path,
        adapter="json",
        declared_sha256="0" * 64,
        expected_role="target_evaluation",
    )
    assert wrong_hash.status is ProvenanceStatus.PROVENANCE_MISMATCH


def test_synthetic_feasibility_and_resource_evidence_cannot_close_real_budget() -> None:
    observation = run_synthetic_feasibility(
        _shape(),
        requested_batch_size=2,
        forward_callback=lambda batch: set(batch) == {
            "x",
            "feature_map",
            "roi_masks",
            "tokens",
            "z",
            "concepts",
            "c_target",
            "g_bar",
            "logits",
        },
        backward_callback=lambda batch, output: output is True,
        matrix_identity_hash=identity_sha256({"matrix": "synthetic"}),
        peak_memory_bytes=1024,
        step_time_seconds=0.01,
    )
    budget = build_resource_budget(
        synthetic_peak_memory_bytes=1024,
        synthetic_step_time_seconds=0.01,
    )

    assert observation.evidence_type is EvidenceType.MEASURED_SYNTHETIC
    assert observation.real_data_accessed is False
    assert observation.real_resource_fields_resolved is False
    assert budget.status is ResourceBudgetStatus.UNRESOLVED_BLOCKING
    assert budget.fields["gpu_vram"].conservative == "UNRESOLVED"
    assert budget.fields["wall_time_per_primary_cell"].engineering_value == 0.01
    with pytest.raises(ValueError, match="real evidence"):
        validate_budget_closure(budget)


def test_publication_package_and_clis_have_no_real_runtime_import_boundary() -> None:
    forbidden_modules = {"torch", "nibabel", "pada3dacb.training", "pada3dacb.data"}
    paths = tuple(PUBLICATION_ROOT.glob("*.py")) + CLI_PATHS
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imported.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            module in forbidden_modules or module.startswith("pada3dacb.training")
            for module in imported
        ), path
        source = path.read_text(encoding="utf-8")
        assert "MRI loader" not in source
        assert "pada3dacb.experiments" not in source
        assert "optimizer.step(" not in source


def test_target_adaptation_firewall_rejects_extra_and_missing_fields() -> None:
    valid = {"x": "synthetic", "subject_id": "s1", "subject_hash": "h1", "cohort": "OASIS"}

    assert validate_target_adaptation_batch(valid) is None
    with pytest.raises(ValueError, match="exactly"):
        validate_target_adaptation_batch({**valid, "diagnosis": 2})
    with pytest.raises(ValueError, match="exactly"):
        validate_target_adaptation_batch({key: value for key, value in valid.items() if key != "cohort"})


def test_target_evaluation_metadata_is_monitoring_only_and_read_only() -> None:
    valid = {
        "monitoring_label": "MONITORING ONLY — NOT A TRAINING LOSS",
        "selection_usage": False,
        "read_only": True,
    }

    assert validate_target_evaluation_metadata(valid) is None
    report = aggregate_validators(target_evaluation=valid)
    assert report.valid
    blocked = aggregate_validators(
        target_evaluation={**valid, "selection_usage": True}
    )
    assert any(item.code == "target_isolation_violation" for item in blocked.blockers)


def test_aggregate_validation_rejects_self_declared_verified_target_manifest() -> None:
    report = aggregate_validators(
        provenance={
            "source": {"status": "VERIFIED"},
            "target_adaptation": {"status": "VERIFIED", "role": "target_adaptation"},
            "target_evaluation": {"status": "VERIFIED", "role": "target_evaluation"},
            "disjoint_assignments": {"status": "VERIFIED"},
        }
    )

    assert any(
        blocker.code == "provenance_conflict"
        and blocker.field == "target_adaptation"
        for blocker in report.blockers
    )


def test_aggregate_validation_checks_target_manifest_records_before_disjointness(
    tmp_path: Path,
) -> None:
    adaptation_path, adaptation_hash = _write_manifest(
        tmp_path, "adaptation.json", _manifest("target_adaptation", "OASIS", ["target-1"])
    )
    evaluation_path, evaluation_hash = _write_manifest(
        tmp_path, "evaluation.json", _manifest("target_evaluation", "OASIS", ["target-2"])
    )
    adaptation = validate_manifest(
        adaptation_path,
        adapter="json",
        declared_sha256=adaptation_hash,
        expected_role="target_adaptation",
        expected_cohort="OASIS",
    )
    evaluation = validate_manifest(
        evaluation_path,
        adapter="json",
        declared_sha256=evaluation_hash,
        expected_role="target_evaluation",
        expected_cohort="OASIS",
    )

    report = aggregate_validators(
        provenance={
            "source": {"status": "VERIFIED"},
            "target_adaptation": adaptation,
            "target_evaluation": evaluation,
            "disjoint_assignments": check_assignment_disjointness(adaptation, evaluation),
        }
    )

    assert not any(
        blocker.field in {"target_adaptation", "target_evaluation"}
        and blocker.code == "provenance_conflict"
        for blocker in report.blockers
    )


def test_authorization_binds_complete_matrix_rows_not_matrix_id() -> None:
    matrix = generate_matrix(seeds=[42])
    manifest = {
        "matrix": matrix.to_mapping(),
        "matrix_hash": identity_sha256({"forged": "matrix"}),
    }

    result = check_authorization(manifest)

    assert any(blocker.code == "hash_mismatch" for blocker in result.blockers)
    assert any("complete matrix" in blocker.message for blocker in result.blockers)


def test_authorization_rejects_unsubstantiated_hash_placeholders() -> None:
    manifest = {
        "method_parameter_ledger_hash": "a" * 64,
        "resource_budget_hash": "b" * 64,
    }

    result = check_authorization(manifest)

    assert any(blocker.code == "missing_evidence" for blocker in result.blockers)


def test_authorization_aggregates_unresolved_lambda_overlap_and_approval_blockers() -> None:
    manifest = yaml.safe_load(
        (ROOT / "configs" / "publication" / "real_run_authorization.yaml").read_text(
            encoding="utf-8"
        )
    )
    result = check_authorization(manifest)
    codes = {blocker.code for blocker in result.blockers}

    assert result.authorized is False
    assert result.data_access_opened is False
    assert {"unresolved_scientific_value", "missing_required_field", "missing_assignment"} <= codes
    assert any("lambda_proto" in blocker.message for blocker in result.blockers)
    assert manifest["real_execution_authorized"] is False
    assert manifest["publication_authorized"] is False
    assert manifest["phase_19_forbidden"] is True


def test_authorization_recomputes_bound_assignment_overlap(tmp_path: Path) -> None:
    source_path, source_hash = _write_manifest(
        tmp_path, "source.json", _manifest("source", "ADNI", ["source-1"])
    )
    adaptation_path, adaptation_hash = _write_manifest(
        tmp_path, "adaptation.json", _manifest("target_adaptation", "OASIS", ["same-subject"])
    )
    evaluation_path, evaluation_hash = _write_manifest(
        tmp_path, "evaluation.json", _manifest("target_evaluation", "OASIS", ["same-subject"])
    )
    source = validate_manifest(source_path, adapter="json", declared_sha256=source_hash)
    adaptation = validate_manifest(
        adaptation_path,
        adapter="json",
        declared_sha256=adaptation_hash,
        expected_role="target_adaptation",
        expected_cohort="OASIS",
    )
    evaluation = validate_manifest(
        evaluation_path,
        adapter="json",
        declared_sha256=evaluation_hash,
        expected_role="target_evaluation",
        expected_cohort="OASIS",
    )

    result = check_authorization(
        {
            "provenance": {
                "source": source,
                "target_adaptation": adaptation,
                "target_evaluation": evaluation,
                "disjoint_assignments": {"status": "VERIFIED"},
            }
        }
    )

    assert any(blocker.code == "overlapping_assignments" for blocker in result.blockers)
