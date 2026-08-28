import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from acda3d.experiments.cdan import load_cdan_config
from acda3d.training.checkpointing import load_training_checkpoint
from scripts import train
from tests.phase12_helpers import make_cdan_environment


def test_cdan_cli_exposes_explicit_hyperparameter_flags(tmp_path):
    parser = train.build_parser()
    args = parser.parse_args(
        [
            "--config",
            str(make_cdan_environment(tmp_path)),
            "--method",
            "cdan",
            "--cdan-weight",
            "1.25",
            "--grl-coefficient",
            "0.5",
            "--domain-hidden-dims",
            "16",
            "8",
            "--domain-dropout",
            "0.1",
            "--domain-learning-rate",
            "0.0005",
            "--domain-weight-decay",
            "0.01",
            "--fold",
            "0",
            "--dry-run",
        ]
    )

    assert args.cdan_weight == 1.25
    assert args.grl_coefficient == 0.5
    assert args.domain_hidden_dims == [16, 8]
    assert args.domain_dropout == 0.1
    assert args.domain_learning_rate == 0.0005
    assert args.domain_weight_decay == 0.01


def test_cdan_cli_dry_run_and_validate_only_reach_runner(monkeypatch, tmp_path, capsys):
    calls = []

    class FakeRunner:
        def __init__(self, config):
            self.config = config

        def run(self, *, dry_run=False, validate_only=False, resume_from=None):
            calls.append({"dry_run": dry_run, "validate_only": validate_only, "resume_from": resume_from})
            return [Namespace(summary_row=lambda: {"fold": 0, "method": "cdan"})]

    monkeypatch.setattr(train, "CDANExperimentRunner", FakeRunner)
    args = train.build_parser().parse_args(
        ["--config", str(make_cdan_environment(tmp_path)), "--method", "cdan", "--fold", "0", "--dry-run", "--validate-only"]
    )

    train.run_cdan(args)

    assert calls == [{"dry_run": True, "validate_only": True, "resume_from": None}]
    assert json.loads(capsys.readouterr().out) == [{"fold": 0, "method": "cdan"}]


def test_cdan_cli_rejects_resume_with_multiple_fold_or_direction(tmp_path):
    args = train.build_parser().parse_args(
        [
            "--config",
            str(make_cdan_environment(tmp_path)),
            "--method",
            "cdan",
            "--all-folds",
            "--resume-from",
            str(tmp_path / "checkpoint.pt"),
        ]
    )

    with pytest.raises(ValueError, match="--resume-from requires exactly one direction, fold, and seed"):
        train.run_cdan(args)


def test_cdan_cli_validate_only_infers_synthetic_conditional_dimension(tmp_path):
    config_path = make_cdan_environment(tmp_path)
    command = [
        sys.executable,
        "scripts/train.py",
        "--config",
        str(config_path),
        "--method",
        "cdan",
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
    assert payload[0]["cdan_loss"] >= 0


def test_cdan_cli_interrupt_after_epoch_routes_to_single_fold(monkeypatch, tmp_path, capsys):
    calls = []

    class FakeRunner:
        def __init__(self, config):
            self.config = config

        def run_fold(self, fold, seed, *, interrupt_after_epoch=None):
            calls.append((fold, seed, interrupt_after_epoch))
            return Namespace(summary_row=lambda: {"fold": fold, "seed": seed, "status": "INTERRUPTED"})

    monkeypatch.setattr(train, "CDANExperimentRunner", FakeRunner)
    args = train.build_parser().parse_args(
        [
            "--config",
            str(make_cdan_environment(tmp_path)),
            "--method",
            "cdan",
            "--fold",
            "0",
            "--interrupt-after-epoch",
            "1",
        ]
    )

    train.run_cdan(args)

    assert calls == [(0, 42, 1)]
    assert json.loads(capsys.readouterr().out) == [{"fold": 0, "seed": 42, "status": "INTERRUPTED"}]


def test_cdan_cli_exact_interrupt_resume_preserves_hash_and_loader_state(tmp_path):
    config_path = make_cdan_environment(tmp_path)
    output_root = tmp_path / "runs"
    base_command = [
        sys.executable,
        "scripts/train.py",
        "--config",
        str(config_path),
        "--method",
        "cdan",
        "--fold",
        "0",
        "--output-root",
        str(output_root),
    ]
    interrupted = subprocess.run(
        [*base_command, "--interrupt-after-epoch", "1"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert interrupted.returncode == 0, interrupted.stderr
    interrupted_payload = json.loads(interrupted.stdout)[0]
    assert interrupted_payload["status"] == "INTERRUPTED"
    interrupted_hash = interrupted_payload["experiment_hash"]
    interrupted_config = load_cdan_config(config_path, overrides={"output_root": output_root})
    run_dir = interrupted_config.run_dir(0, 42)
    checkpoint = load_training_checkpoint(run_dir / "checkpoint_last.pt")
    assert checkpoint["epoch"] == 1
    assert set(checkpoint["loader_generator_states"]) == {"source_train", "target_adaptation"}

    resumed = subprocess.run(
        [*base_command, "--resume-from", str(run_dir / "checkpoint_last.pt")],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert resumed.returncode == 0, resumed.stderr
    resumed_payload = json.loads(resumed.stdout)[0]
    assert resumed_payload["status"] == "COMPLETED"
    assert resumed_payload["experiment_hash"] == interrupted_hash
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "COMPLETED"
    assert manifest["experiment_hash"] == interrupted_hash
