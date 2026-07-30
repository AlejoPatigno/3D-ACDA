from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import yaml

from pada3dacb.evaluation.report import (
    ReportState,
    build_completion_manifest,
    build_output_plan,
    commit_output,
    orchestrate_report,
    verify_reuse,
)
from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    CheckpointPolicy,
    Direction,
    EvaluationRequest,
    MethodId,
    RunMode,
    SubjectPrediction,
)
from tests.phase15_integration_fixtures import cli_module, matrix_argv, write_matrix


def _table() -> tuple[SubjectPrediction, ...]:
    return tuple(
        SubjectPrediction(
            MethodId.MMD, Direction.ADNI_TO_OASIS,
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, f"subject-{label}", label,
            tuple(0.9 if index == label else 0.05 for index in range(3)),
            1, 1, (f"{label + 1:064x}",),
        )
        for label in range(3)
    )


def test_injected_synthetic_executor_reaches_completed_report_without_real_gate(tmp_path: Path) -> None:
    cli = cli_module()
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD,))
    output = tmp_path / "synthetic-results"
    outcomes = []

    def executor(selection):
        request = EvaluationRequest(
            selection.methods, selection.directions, selection.checkpoint_policies,
            AnalysisMode.SYNTHETIC_TEST_ONLY, RunMode.EVALUATE,
            selection.bootstrap_replicates, selection.bootstrap_seed,
        )
        plan = build_output_plan(
            "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY, selection.methods,
            selection.directions, selection.checkpoint_policies,
            included_methods=selection.methods,
        )
        outcome = orchestrate_report(
            request, plan, gate_allowed=False,
            load_validated=lambda: ({"mmd": _table()}, ()),
            build_statistics=lambda _: {"synthetic-metrics.csv": b"synthetic-only"},
            write_bundle=outcomes.append,
        )
        assert outcome.state is ReportState.COMPLETED
        return cli.ExitCode.SUCCESS

    argv = [
        "--config", config["_config_path"], "--runs-root", str(runs),
        "--both-directions", "--method", "mmd", "--output-root", str(output),
        "--bootstrap-seed", "29",
    ]
    assert cli.main(argv, executor=executor) == cli.ExitCode.SUCCESS
    assert len(outcomes) == 1
    assert not output.exists()


def test_injected_completed_reuse_verifies_existing_tree_read_only(tmp_path: Path) -> None:
    cli = cli_module()
    plan = build_output_plan(
        "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY, (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,), (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.MMD,),
    )
    artifacts = {
        path: path.encode() for path in plan.intended_relative_paths
        if path != "evaluation_manifest.json"
    }
    identity = {"configuration_sha256": "b" * 64}
    libraries = {"numpy": "test"}
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, artifacts, identity_inputs=identity, library_versions=libraries
    )
    output = tmp_path / "completed"
    commit_output(output, plan, artifacts)
    before = {path: path.stat().st_mtime_ns for path in output.rglob("*") if path.is_file()}

    def executor(_selection):
        assert verify_reuse(
            output, plan, expected_identity_inputs=identity,
            expected_library_versions=libraries,
        ).state is ReportState.REUSED
        return cli.ExitCode.SUCCESS

    assert cli.main([
        "--config", "configs/evaluation/predictive.yaml", "--direction", "adni_to_oasis",
        "--method", "mmd", "--reuse", "--output-root", str(output),
    ], executor=executor) == cli.ExitCode.SUCCESS
    assert {path: path.stat().st_mtime_ns for path in output.rglob("*") if path.is_file()} == before


def test_default_synthetic_evaluate_produces_exact_immutable_tree(tmp_path: Path) -> None:
    cli = cli_module()
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD,))
    output = tmp_path / "default-results"
    inputs_before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in runs.rglob("*") if path.is_file()
    }
    evaluate_argv = [
        "--config", config["_config_path"], "--runs-root", str(runs),
        "--both-directions", "--method", "mmd", "--output-root", str(output),
        "--bootstrap-replicates", "3", "--bootstrap-seed", "29",
    ]
    assert cli.main(evaluate_argv) == cli.ExitCode.SUCCESS
    assert (output / "evaluation_manifest.json").is_file()
    assert (output / "artifact_index.json").is_file()
    assert len(list(csv.DictReader((output / "method_status.csv").open(encoding="utf-8")))) == 2
    provenance = json.loads((output / "provenance_report.json").read_text(encoding="utf-8"))
    assert provenance["candidates"]
    assert len(list(csv.DictReader((output / "computational_summary.csv").open(encoding="utf-8")))) == 14
    for direction in Direction:
        inclusion = output / f"predictive/{direction.value}/primary_best_source_f1/inclusion_report.csv"
        assert list(csv.DictReader(inclusion.open(encoding="utf-8")))
    inputs_after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in runs.rglob("*") if path.is_file()
    }
    assert inputs_after == inputs_before



def test_default_mixed_selection_reports_excluded_method_without_its_artifacts(
    tmp_path: Path,
) -> None:
    cli = cli_module()
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD, MethodId.CDAN))
    shutil.rmtree(runs / "shared/cdan")
    output = tmp_path / "mixed-results"
    assert cli.main([
        "--config", config["_config_path"], "--runs-root", str(runs),
        "--both-directions", "--method", "mmd", "--method", "cdan",
        "--output-root", str(output), "--bootstrap-replicates", "3",
        "--bootstrap-seed", "29",
    ]) == cli.ExitCode.SUCCESS
    rows = list(csv.DictReader((output / "method_status.csv").open(encoding="utf-8")))
    statuses = {(row["method_id"], row["direction"]): row["status"] for row in rows}
    assert all(statuses[("mmd", direction.value)] == "included" for direction in Direction)
    assert all(statuses[("cdan", direction.value)] == "excluded" for direction in Direction)
    assert not any("subject_predictions/cdan.csv" in path.as_posix() for path in output.rglob("*"))
    provenance = json.loads((output / "provenance_report.json").read_text(encoding="utf-8"))
    assert any(item.get("method_id") == "cdan" and item["status"] == "excluded"
               for item in provenance["candidates"] if isinstance(item, dict))


def test_default_completed_reuse_is_read_only(tmp_path: Path) -> None:
    cli = cli_module()
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD,))
    output = tmp_path / "reuse-results"
    payload = yaml.safe_load(Path(config["_config_path"]).read_text(encoding="utf-8"))
    payload["completed_reuse"]["approved_output_roots"] = [str(output.resolve())]
    Path(config["_config_path"]).write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )
    assert cli.main([
        "--config", config["_config_path"], "--runs-root", str(runs),
        "--both-directions", "--method", "mmd", "--output-root", str(output),
        "--bootstrap-replicates", "3", "--bootstrap-seed", "29",
    ]) == cli.ExitCode.SUCCESS
    before = {path: path.stat().st_mtime_ns for path in output.rglob("*") if path.is_file()}
    assert cli.main([
        "--config", config["_config_path"], "--runs-root", str(runs),
        "--both-directions", "--method", "mmd",
        "--bootstrap-replicates", "3", "--bootstrap-seed", "29", "--reuse",
    ]) == cli.ExitCode.SUCCESS
    assert {path: path.stat().st_mtime_ns for path in output.rglob("*") if path.is_file()} == before


def test_default_modes_remain_nonwriting_and_fail_closed_without_evidence(tmp_path: Path) -> None:
    cli = cli_module()
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD,))
    output = tmp_path / "must-not-exist"
    assert cli.main(matrix_argv(
        config, runs, "--dry-run", methods=(MethodId.MMD,), output=output
    )) == cli.ExitCode.SUCCESS
    assert not output.exists()
    assert cli.main([
        "--config", config["_config_path"], "--direction", "adni_to_oasis",
        "--method", "mmd", "--reuse", "--output-root", str(output),
    ]) == cli.ExitCode.REUSE_REJECTED
