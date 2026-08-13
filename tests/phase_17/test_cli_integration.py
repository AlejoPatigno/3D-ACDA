from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pada3dacb.experiments.ablations import (
    build_parser,
    load_ablation_config,
    planned_run_path,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "experiments" / "ablations.yaml"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_ablations.py", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_dry_run_reports_approved_and_blocked_without_forward_or_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "results"
    result = _run(
        "--config", str(CONFIG),
        "--ablation", "no_proto",
        "--source-domain", "ADNI",
        "--target-domain", "OASIS",
        "--fold", "0",
        "--seed", "42",
        "--output-root", str(output_root),
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["approved_ids"] == ["no_proto"]
    assert "no_domain_adaptation" in payload["blocked_ids"]
    assert payload["plans"][0]["target_loader_use"] == "unlabeled_target_adaptation"
    assert payload["plans"][0]["forward_executed"] is False
    assert not output_root.exists()


def test_validate_only_is_deterministic_and_target_monitoring_does_not_change_objective(
    tmp_path: Path,
) -> None:
    common = (
        "--config", str(CONFIG),
        "--ablation", "mean_pool",
        "--source-domain", "ADNI",
        "--target-domain", "OASIS",
        "--fold", "0",
        "--seed", "42",
        "--output-root", str(tmp_path / "results"),
        "--validate-only",
        "--device", "cpu",
    )
    enabled = _run(*common, "--target-monitoring")
    disabled = _run(*common, "--no-target-monitoring")
    assert enabled.returncode == disabled.returncode == 0
    left = json.loads(enabled.stdout)
    right = json.loads(disabled.stdout)
    assert left["plans"][0]["validated"] is True
    assert right["plans"][0]["validated"] is True
    assert left["plans"][0]["resolved_objective"] == right["plans"][0]["resolved_objective"]
    assert left["plans"][0]["target_monitoring_enabled"] is True
    assert right["plans"][0]["target_monitoring_enabled"] is False
    assert not (tmp_path / "results").exists()


def test_all_folds_and_both_directions_are_planned(tmp_path: Path) -> None:
    result = _run(
        "--config", str(CONFIG),
        "--ablation", "no_pl",
        "--both-directions",
        "--all-folds",
        "--seed", "42",
        "--output-root", str(tmp_path / "results"),
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["plans"]) == 10
    assert {item["direction"] for item in payload["plans"]} == {
        "ADNI_to_OASIS",
        "OASIS_to_ADNI",
    }
    assert {item["fold"] for item in payload["plans"]} == set(range(5))


def test_blocked_alias_and_real_mode_fail_closed(tmp_path: Path) -> None:
    alias = _run(
        "--config", str(CONFIG),
        "--ablation", "no_prototype",
        "--output-root", str(tmp_path / "alias"),
        "--dry-run",
    )
    assert alias.returncode != 0
    assert "alias_not_approved" in alias.stderr
    real = _run(
        "--config", str(CONFIG),
        "--ablation", "no_proto",
        "--output-root", str(tmp_path / "real"),
    )
    assert real.returncode != 0
    assert "real_run_not_authorized" in real.stderr
    assert not (tmp_path / "real").exists()


def test_output_path_and_parser_contract() -> None:
    config = load_ablation_config(CONFIG)
    assert planned_run_path(config, "no_proto", "ADNI_to_OASIS", 42, 3).as_posix().endswith(
        "ablations/no_proto/ADNI_to_OASIS/seed_42/fold_3"
    )
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--config", str(CONFIG), "--dry-run", "--target-monitoring", "--no-target-monitoring"])
    for flag in (
        "--config", "--ablation", "--all-approved-ablations", "--source-domain",
        "--target-domain", "--fold", "--all-folds", "--seed", "--all-seeds",
        "--both-directions", "--artifact-index", "--artifact-root", "--split-root",
        "--roi-masks", "--atlas-metadata", "--output-root", "--device", "--resume-from",
        "--overwrite", "--dry-run", "--validate-only", "--target-monitoring",
        "--no-target-monitoring",
    ):
        assert any(action.option_strings and flag in action.option_strings for action in parser._actions)
