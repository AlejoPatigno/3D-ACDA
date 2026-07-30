from __future__ import annotations

import json
from pathlib import Path

from pada3dacb.evaluation.discovery import (
    ADAPTER_REGISTRY,
    BaselineCombinedAdapter,
    discover_candidates,
)
from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    CheckpointPolicy,
    Direction,
    EvaluationRequest,
    MethodId,
    RunMode,
)
from tests.phase15_integration_fixtures import (
    cli_module,
    matrix_argv,
    write_matrix,
)


def _request(*, policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,)) -> EvaluationRequest:
    return EvaluationRequest(
        tuple(MethodId), tuple(Direction), policies, AnalysisMode.SYNTHETIC_TEST_ONLY,
        RunMode.VALIDATE_ONLY, 10_000, 0,
    )


def test_seven_method_two_direction_matrix_validates_without_output(tmp_path: Path) -> None:
    runs, config = write_matrix(tmp_path)
    output = tmp_path / "must-not-exist"
    cli = cli_module()
    assert cli.main(matrix_argv(config, runs, "--validate-only", output=output)) == cli.ExitCode.SUCCESS
    assert not output.exists()
    candidates = discover_candidates(config, runs, _request(), (2,), (17,))
    assert len(candidates) == 14
    assert {candidate.method_id for candidate in candidates} == set(MethodId)
    assert {candidate.direction for candidate in candidates} == set(Direction)
    assert set(ADAPTER_REGISTRY) == set(MethodId)


def test_baseline_raw_ids_do_not_enter_canonical_predictions(tmp_path: Path) -> None:
    runs, config = write_matrix(tmp_path)
    candidate = next(
        item for item in discover_candidates(config, runs, _request(), (2,), (17,))
        if item.method_id is MethodId.AAGN
    )
    batch = BaselineCombinedAdapter().normalize(candidate, runs)
    assert not batch.issues
    assert batch.predictions
    assert all(not hasattr(row, "subject_id") for row in batch.predictions)
    assert "private-" not in repr(batch.predictions)


def test_primary_and_sensitivity_policies_remain_separate(tmp_path: Path) -> None:
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD,), include_sensitivity=True)
    cli = cli_module()
    argv = matrix_argv(config, runs, "--validate-only", methods=(MethodId.MMD,))
    argv.append("--include-sensitivity")
    assert cli.main(argv) == cli.ExitCode.SUCCESS
    candidates = discover_candidates(
        config, runs,
        EvaluationRequest(
            (MethodId.MMD,), tuple(Direction),
            (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, CheckpointPolicy.SENSITIVITY_LAST),
            AnalysisMode.SYNTHETIC_TEST_ONLY, RunMode.VALIDATE_ONLY, 10_000, 0,
        ),
        (2,), (17,),
    )
    assert {item.checkpoint_policy for item in candidates} == {
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, CheckpointPolicy.SENSITIVITY_LAST,
    }


def test_incomplete_and_conflicting_candidates_fail_closed(tmp_path: Path) -> None:
    runs, config = write_matrix(tmp_path, methods=(MethodId.MMD,))
    cli = cli_module()
    target = next(runs.rglob("target_monitoring_predictions/best_source_f1.csv"))
    target.unlink()
    assert cli.main(matrix_argv(config, runs, "--dry-run", methods=(MethodId.MMD,))) == cli.ExitCode.VALIDATION_INCOMPLETE

    runs, config = write_matrix(tmp_path / "conflict", methods=(MethodId.MMD,))
    manifest = next(runs.rglob("best_source_f1_run_manifest.json"))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["direction"] = "oasis_to_adni"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert cli.main(matrix_argv(config, runs, "--validate-only", methods=(MethodId.MMD,))) == cli.ExitCode.VALIDATION_INCOMPLETE
