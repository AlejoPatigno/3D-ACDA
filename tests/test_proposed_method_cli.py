import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from scripts import train
from tests.test_proposed_method_config import make_proposed_environment


def test_prototype_pseudo_cli_exposes_method_and_routes_to_runner(monkeypatch, tmp_path, capsys):
    calls = []

    class FakeRunner:
        def __init__(self, config):
            self.config = config

        def run(self, *, dry_run=False, validate_only=False, resume_from=None):
            calls.append({"method": self.config.method, "dry_run": dry_run, "validate_only": validate_only, "resume_from": resume_from})
            return [Namespace(summary_row=lambda: {"fold": 0, "method": "prototype_pseudo", "display_name": self.config.display_name})]

    monkeypatch.setattr(train, "PrototypePseudoExperimentRunner", FakeRunner)
    args = train.build_parser().parse_args(
        ["--config", str(make_proposed_environment(tmp_path)), "--method", "prototype_pseudo", "--fold", "0", "--dry-run"]
    )

    train.run_prototype_pseudo(args)

    assert calls == [{"method": "prototype_pseudo", "dry_run": True, "validate_only": False, "resume_from": None}]
    assert json.loads(capsys.readouterr().out) == [{"fold": 0, "method": "prototype_pseudo", "display_name": "3D-ACDA"}]


def test_prototype_pseudo_cli_dry_run_all_five_folds(tmp_path: Path):
    command = [
        sys.executable,
        "scripts/train.py",
        "--config",
        str(make_proposed_environment(tmp_path)),
        "--method",
        "prototype_pseudo",
        "--all-folds",
        "--dry-run",
        "--output-root",
        str(tmp_path / "runs"),
    ]

    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [row["fold"] for row in payload] == [0, 1, 2, 3, 4]
    assert {row["method"] for row in payload} == {"prototype_pseudo"}
    assert all(row["planned_target_adaptation"] > 0 for row in payload)


def test_prototype_pseudo_cli_validate_only_uses_finite_synthetic_losses(tmp_path: Path):
    command = [
        sys.executable,
        "scripts/train.py",
        "--config",
        str(make_proposed_environment(tmp_path)),
        "--method",
        "prototype_pseudo",
        "--fold",
        "0",
        "--validate-only",
        "--output-root",
        str(tmp_path / "runs"),
    ]

    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload[0]["validated"] is True
    assert payload[0]["prototype_pseudo_loss"] >= 0
    assert payload[0]["target_training_labels_available"] is False


def test_prototype_pseudo_cli_rejects_resume_with_multiple_fold_or_direction(tmp_path: Path):
    args = train.build_parser().parse_args(
        [
            "--config",
            str(make_proposed_environment(tmp_path)),
            "--method",
            "prototype_pseudo",
            "--all-folds",
            "--resume-from",
            str(tmp_path / "checkpoint.pt"),
        ]
    )

    with pytest.raises(ValueError, match="--resume-from requires exactly one direction, fold, and seed"):
        train.run_prototype_pseudo(args)


def test_no_unapproved_phase15_or_evaluation_modules_created():
    root = Path(__file__).resolve().parents[1]
    forbidden = [
        root / "src" / "acda3d" / "experiments" / "phase14.py",
        root / "src" / "acda3d" / "evaluation" / "statistics.py",
    ]
    assert not any(path.exists() for path in forbidden)
