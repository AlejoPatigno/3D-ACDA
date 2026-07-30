from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import train
from tests.phase14_helpers import make_baseline_environment


def test_baseline_cli_routes_one_approved_baseline_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = train.build_parser().parse_args(
        [
            "--config",
            str(make_baseline_environment(tmp_path)),
            "--method",
            "baseline",
            "--baseline-name",
            "faster_snn",
            "--fold",
            "0",
            "--seed",
            "42",
            "--dry-run",
        ]
    )

    train.run_baseline(args)
    payload = json.loads(capsys.readouterr().out)

    assert tuple(payload) == ("faster_snn",)
    assert payload["faster_snn"][0]["status"] == "PENDING"
    assert payload["faster_snn"][0]["target_adaptation_loader_constructed"] is False


def test_baseline_cli_supports_all_baselines_and_both_directions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = train.build_parser().parse_args(
        [
            "--config",
            str(make_baseline_environment(tmp_path)),
            "--method",
            "baseline",
            "--all-baselines",
            "--all-folds",
            "--both-directions",
            "--dry-run",
        ]
    )

    train.run_baseline(args)
    payload = json.loads(capsys.readouterr().out)

    assert tuple(payload) == ("ADNI_to_OASIS", "OASIS_to_ADNI")
    assert tuple(payload["ADNI_to_OASIS"]) == ("aagn", "faster_snn")
    assert len(payload["ADNI_to_OASIS"]["aagn"]) == 2


def test_baseline_cli_rejects_ambiguous_selection_or_resume(tmp_path: Path) -> None:
    config = str(make_baseline_environment(tmp_path))
    both_selectors = train.build_parser().parse_args(
        ["--config", config, "--method", "baseline", "--baseline-name", "aagn", "--all-baselines"]
    )
    with pytest.raises(ValueError, match="not both"):
        train.run_baseline(both_selectors)

    ambiguous_resume = train.build_parser().parse_args(
        ["--config", config, "--method", "baseline", "--all-baselines", "--resume-from", str(tmp_path / "last.pt")]
    )
    with pytest.raises(ValueError, match="exactly one baseline"):
        train.run_baseline(ambiguous_resume)


def test_parser_preserves_previous_method_flags() -> None:
    args = train.build_parser().parse_args(
        ["--method", "prototype_pseudo", "--fold", "0", "--dry-run"]
    )

    assert args.method == "prototype_pseudo"
    assert args.fold == 0
    assert args.dry_run is True
