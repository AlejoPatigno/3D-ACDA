from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from pada3dacb.publication.freeze import read_freeze

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "scripts" / "prepare_publication_run.py"
CHECKER = ROOT / "scripts" / "check_real_run_authorization.py"
FREEZE_CONFIG = ROOT / "configs" / "publication" / "publication_experiment_freeze.yaml"
AUTH_CONFIG = ROOT / "configs" / "publication" / "real_run_authorization.yaml"


def _run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_default_configs_keep_every_authorization_boundary_closed() -> None:
    freeze = yaml.safe_load(FREEZE_CONFIG.read_text(encoding="utf-8"))
    authorization = yaml.safe_load(AUTH_CONFIG.read_text(encoding="utf-8"))

    for payload in (freeze, authorization):
        assert payload["phase_18_authorized"] is True
        assert payload["real_execution_authorized"] is False
        assert payload["publication_authorized"] is False
        assert payload["phase_19_forbidden"] is True
    assert authorization["authorized"] is False


def test_checker_is_nonzero_and_reports_fail_closed_closure() -> None:
    result = _run(CHECKER, "--config", str(AUTH_CONFIG))

    assert result.returncode != 0
    assert "REAL RUN NOT AUTHORIZED" in result.stdout
    assert "PASS — FAIL-CLOSED AUTHORIZATION VERIFIED" in result.stdout
    assert "BLOCKED_EXTERNAL_PROVENANCE" in result.stdout
    assert "native_receipt" in result.stdout


def test_prepare_cli_prints_matrix_and_blockers_without_opening_runtime_paths() -> None:
    matrix = _run(PREPARE, "--config", str(AUTH_CONFIG), "--print-matrix")
    blockers = _run(PREPARE, "--config", str(AUTH_CONFIG), "--print-blockers")

    assert matrix.returncode != 0
    assert '"rows"' in matrix.stdout
    assert '"row_kind": "training"' in matrix.stdout
    assert "source_only" in matrix.stdout
    assert "adni_to_oasis" in matrix.stdout
    assert "BLOCKERS:" in matrix.stdout
    assert blockers.returncode != 0
    assert "BLOCKERS:" in blockers.stdout
    assert "BLOCKED_EXTERNAL_PROVENANCE" in blockers.stdout
    assert "REAL RUN AUTHORIZED" not in matrix.stdout


def test_prepare_cli_validate_and_feasibility_only_are_closed_modes() -> None:
    validate = _run(PREPARE, "--config", str(FREEZE_CONFIG), "--validate-only")
    feasibility = _run(PREPARE, "--config", str(FREEZE_CONFIG), "--feasibility-only")

    assert validate.returncode == 4
    assert "BLOCKERS:" in validate.stdout
    assert "training" not in validate.stdout.lower()
    assert feasibility.returncode == 4
    assert "FEASIBILITY-ONLY: synthetic contracts only; no real data access." in feasibility.stdout
    assert "PREPARATION ONLY" not in feasibility.stdout


def test_prepare_cli_writes_only_a_canonical_planning_freeze_and_requires_overwrite(
    tmp_path: Path,
) -> None:
    first = _run(
        PREPARE,
        "--config",
        str(FREEZE_CONFIG),
        "--output-root",
        str(tmp_path),
        "--write-freeze",
    )
    destination = tmp_path / "publication_freeze.json"
    second = _run(
        PREPARE,
        "--config",
        str(FREEZE_CONFIG),
        "--output-root",
        str(tmp_path),
        "--write-freeze",
    )

    assert first.returncode == 0
    assert "PLANNING FREEZE WRITTEN" in first.stdout
    assert destination.exists()
    envelope = read_freeze(destination)
    assert envelope["payload"]["status"] == "blocked_planning"
    assert envelope["payload"]["real_execution_authorized"] is False
    assert second.returncode != 0
    assert "overwrite" in second.stdout.lower()


def test_prepare_cli_rejects_non_cpu_validation_without_real_execution() -> None:
    result = _run(
        PREPARE,
        "--config",
        str(FREEZE_CONFIG),
        "--device",
        "cuda",
        "--validate-only",
    )

    assert result.returncode == 4
    assert "only CPU planning validation is supported" in result.stdout
    assert "PREPARATION ONLY" not in result.stdout


def test_phase_19_has_no_production_files_or_open_authorization_fields() -> None:
    production_paths = (
        ROOT / "src" / "pada3dacb" / "publication",
        ROOT / "scripts",
        ROOT / "configs" / "publication",
    )
    names = [path.name.lower() for root in production_paths for path in root.iterdir()]
    assert not any("phase19" in name or "phase_19" in name for name in names)

    for config_path in (FREEZE_CONFIG, AUTH_CONFIG):
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert payload["real_execution_authorized"] is False
        assert payload["publication_authorized"] is False
        assert payload["phase_19_forbidden"] is True


def test_cli_outputs_are_json_matrix_or_explicit_blocker_text_only() -> None:
    result = _run(PREPARE, "--config", str(AUTH_CONFIG), "--print-matrix")
    matrix_text, _, blocker_text = result.stdout.partition("BLOCKERS:")
    document = json.loads(matrix_text)

    assert len(document["rows"]) == 420
    assert document["counts"] == {
        "training": 210,
        "checkpoint_projection": 210,
        "total": 420,
    }
    assert document["seeds"] == [42, 43, 44]
    assert document["resolved_seed_policy"]["seeds"] == [42, 43, 44]
    assert document["ablations"]["section"] == "ablations"
    assert document["ablations"]["training_invocation"] is False
    assert blocker_text.startswith("\n")
    assert "authorization" in blocker_text.lower()
