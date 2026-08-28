from __future__ import annotations

import hashlib
from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import tomllib
import yaml

from tests.phase15_discovery_fixtures import (
    add_identity_population_controls,
    write_shared_candidate,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "configs/evaluation/predictive.yaml"
PYPROJECT = ROOT / "pyproject.toml"
SCRIPT = ROOT / "scripts/evaluate.py"


def _cli():
    spec = spec_from_file_location("phase15_evaluate_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base(tmp_path: Path) -> list[str]:
    runs = tmp_path / "runs"
    runs.mkdir(parents=True)
    return [
        "--config", str(CONFIG), "--runs-root", str(runs),
        "--direction", "adni_to_oasis", "--method", "mmd",
    ]


def test_predictive_config_freezes_approved_inventory_and_source_defined_selectors() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema_version"] == "phase15-output-v2"
    assert config["protocol_version"] == "phase15-statistical-v2"
    assert config["class_order"] == {"CN": 0, "MCI": 1, "AD": 2}
    assert config["methods"] == [
        "source_only", "coral", "mmd", "cdan", "prototype_pseudo", "aagn", "faster_snn",
    ]
    assert config["directions"] == ["adni_to_oasis", "oasis_to_adni"]
    assert config["expected_folds"] == [0, 1, 2, 3, 4]
    assert config["expected_seeds"] == [42]
    assert config["checkpoint_policies"] == {
        "primary": "best_source_f1",
        "sensitivity": "last",
        "target_derived_selection": False,
    }
    assert config["defaults"] == {
        "checkpoint_policy": "best_source_f1",
        "bootstrap_replicates": 10_000,
    }


def test_predictive_config_has_explicit_read_only_schema_families_and_closed_real_gate() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert set(config["method_schema_families"]) == set(config["methods"])
    assert set(config["method_schema_families"].values()) == {
        "shared_method", "baseline_combined",
    }
    for family in ("shared_method", "baseline_combined"):
        assert config[family]["prediction_pattern"]
        assert config[family]["companion_patterns"]
    assert config["identity_companions"] == {
        "ADNI": {
            "relative_path": None, "sha256": None, "raw_identifier_field": None,
            "subject_hash_field": "subject_hash", "approved": False,
        },
        "OASIS": {
            "relative_path": None, "sha256": None, "raw_identifier_field": None,
            "subject_hash_field": "subject_hash", "approved": False,
        },
    }
    population = {"relative_path": None, "sha256": None}
    assert config["expected_population_companions"] == {
        direction: {"source_oof": population, "target_evaluation": population}
        for direction in ("adni_to_oasis", "oasis_to_adni")
    }
    assert config["completed_reuse"] == {"approved_output_roots": []}
    assert config["real_evaluation_gate"] == {
        "authorized_exports": {"sha256": None, "resolved": False},
        "D-14-001": {"sha256": None, "resolved": False},
        "D-14-002": {"sha256": None, "resolved": False},
        "protocol_approval": {"sha256": None, "resolved": False},
        "authorized": False,
    }
    serialized = CONFIG.read_text(encoding="utf-8").lower()
    for forbidden in ("subject_id", "secret", "salt", "target_metric", "target_f1"):
        assert forbidden not in serialized


def test_config_declares_direct_runtime_and_reference_only_dependencies() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    runtime = {item.lower() for item in project["dependencies"]}
    dev = {item.lower() for item in project["optional-dependencies"]["dev"]}
    assert {"numpy", "scikit-learn", "scipy", "pyyaml", "matplotlib"} <= runtime
    assert "statsmodels" not in runtime
    assert "statsmodels" in dev


def test_cli_requires_explicit_config_and_exactly_one_selector_kind() -> None:
    cli = _cli()
    with pytest.raises(SystemExit):
        cli.parse_cli(["--both-directions", "--all-methods", "--dry-run"])
    with pytest.raises(SystemExit):
        cli.parse_cli(["--config", str(CONFIG), "--both-directions", "--dry-run"])
    with pytest.raises(SystemExit):
        cli.parse_cli(["--config", str(CONFIG), "--all-methods", "--dry-run"])


def test_cli_resolves_single_and_all_selectors_with_separate_sensitivity(tmp_path: Path) -> None:
    cli = _cli()
    single = cli.parse_cli([*_base(tmp_path), "--dry-run", "--include-sensitivity"])
    assert [item.value for item in single.directions] == ["adni_to_oasis"]
    assert [item.value for item in single.methods] == ["mmd"]
    assert [item.value for item in single.checkpoint_policies] == [
        "primary_best_source_f1", "sensitivity_last",
    ]
    all_selected = cli.parse_cli([
        "--config", str(CONFIG), "--both-directions", "--all-methods", "--reuse",
    ])
    assert len(all_selected.directions) == 2
    assert len(all_selected.methods) == 7
    assert all_selected.runs_root is None
    assert all_selected.output_root is None


def test_cli_modes_enforce_evaluate_requirements_but_keep_inspection_nonwriting(tmp_path: Path) -> None:
    cli = _cli()
    for mode in ("--dry-run", "--validate-only"):
        selection = cli.parse_cli([*_base(tmp_path / mode[2:]), mode])
        assert selection.bootstrap_seed is None
        assert selection.output_root is None
    with pytest.raises(SystemExit):
        cli.parse_cli(_base(tmp_path / "missing-evaluate-output"))
    with pytest.raises(SystemExit):
        cli.parse_cli([*_base(tmp_path / "missing-seed"), "--output-root", str(tmp_path / "out")])
    selection = cli.parse_cli([
        *_base(tmp_path / "evaluate"), "--output-root", str(tmp_path / "out"),
        "--bootstrap-seed", "19",
    ])
    assert selection.run_mode.value == "evaluate"
    assert selection.bootstrap_seed == 19


@pytest.mark.parametrize(
    "extra",
    [
        ["--dry-run", "--validate-only"],
        ["--dry-run", "--reuse"],
        ["--validate-only", "--reuse"],
        ["--dry-run", "--overwrite"],
        ["--validate-only", "--overwrite"],
        ["--reuse", "--overwrite"],
        ["--checkpoint-policy", "last", "--include-sensitivity", "--dry-run"],
        ["--bootstrap-replicates", "0", "--dry-run"],
        ["--dry-run", "--bootstrap-seed", "1"],
        ["--validate-only", "--bootstrap-seed", "1"],
    ],
)
def test_cli_rejects_mode_policy_and_bootstrap_conflicts(tmp_path: Path, extra: list[str]) -> None:
    with pytest.raises(SystemExit):
        _cli().parse_cli([*_base(tmp_path), *extra])


def test_cli_rejects_overlapping_input_and_output_roots(tmp_path: Path) -> None:
    cli = _cli()
    base = _base(tmp_path)
    runs = Path(base[3])
    with pytest.raises(SystemExit):
        cli.parse_cli([*base, "--output-root", str(runs / "results"), "--bootstrap-seed", "1"])


def test_cli_main_maps_parser_failure_to_configuration_not_incomplete() -> None:
    cli = _cli()
    assert cli.main(["--dry-run"], executor=lambda _: cli.ExitCode.SUCCESS) == cli.ExitCode.CONFIGURATION_ERROR


def test_cli_maps_stable_exit_categories_without_exposing_details(tmp_path: Path) -> None:
    cli = _cli()
    argv = [*_base(tmp_path), "--dry-run"]
    cases = [
        (None, cli.ExitCode.SUCCESS),
        (cli.ConfigurationError("bad config"), cli.ExitCode.CONFIGURATION_ERROR),
        (cli.AuthorizationGateError("blocked"), cli.ExitCode.GATE_BLOCKED),
        (cli.ReuseVerificationError("mismatch"), cli.ExitCode.REUSE_REJECTED),
        (cli.OutputCommitError("output"), cli.ExitCode.OUTPUT_FAILURE),
        (RuntimeError("internal"), cli.ExitCode.INTERNAL_ERROR),
    ]
    for error, expected in cases:
        def executor(_selection, error=error):
            if error is not None:
                raise error
            return cli.ExitCode.SUCCESS

        assert cli.main(argv, executor=executor) == expected


def _fixture_config(tmp_path: Path, *, analysis_mode: str = "synthetic_test_only") -> Path:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["analysis_mode"] = analysis_mode
    config["expected_folds"] = [2]
    config["expected_seeds"] = [17]
    add_identity_population_controls(config, tmp_path / "runs")
    path = tmp_path / "predictive.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def test_default_dispatch_dry_run_reports_incomplete_without_writes(tmp_path: Path) -> None:
    cli = _cli()
    runs = tmp_path / "runs"
    runs.mkdir()
    output = tmp_path / "must-not-exist"
    result = cli.main([
        "--config", str(CONFIG), "--runs-root", str(runs), "--direction", "adni_to_oasis",
        "--method", "mmd", "--dry-run", "--output-root", str(output),
    ])
    assert result == cli.ExitCode.VALIDATION_INCOMPLETE
    assert not output.exists()


def test_default_dispatch_validate_only_normalizes_and_aggregates_without_writes(tmp_path: Path) -> None:
    cli = _cli()
    runs = tmp_path / "runs"
    write_shared_candidate(runs, seed=17, fold=2)
    output = tmp_path / "must-not-exist"
    result = cli.main([
        "--config", str(_fixture_config(tmp_path)), "--runs-root", str(runs),
        "--direction", "adni_to_oasis", "--method", "mmd", "--validate-only",
        "--output-root", str(output),
    ])
    assert result == cli.ExitCode.SUCCESS
    assert not output.exists()


def test_default_dispatch_validate_only_reports_invalid_rows(tmp_path: Path) -> None:
    cli = _cli()
    base = write_shared_candidate(tmp_path / "runs", seed=17, fold=2)
    prediction = base / "target_monitoring_predictions/best_source_f1.csv"
    prediction.write_text(
        prediction.read_text(encoding="utf-8").replace("0.8,0.1,0.1", "0.8,0.8,0.8"),
        encoding="utf-8",
    )
    result = cli.main([
        "--config", str(_fixture_config(tmp_path)), "--runs-root", str(tmp_path / "runs"),
        "--direction", "adni_to_oasis", "--method", "mmd", "--validate-only",
    ])
    assert result == cli.ExitCode.VALIDATION_INCOMPLETE


def test_default_dispatch_real_evaluation_stops_at_gate_before_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _cli()
    runs = tmp_path / "runs"
    write_shared_candidate(runs, seed=17, fold=2)
    output = tmp_path / "must-not-exist"
    argv = [
        "--config", str(_fixture_config(tmp_path, analysis_mode="real")),
        "--runs-root", str(runs), "--direction", "adni_to_oasis", "--method", "mmd",
        "--output-root", str(output), "--bootstrap-seed", "5",
    ]
    with pytest.raises(cli.AuthorizationGateError) as captured:
        cli._execute(cli.parse_cli(argv))
    message = str(captured.value)
    assert all(token in message for token in (
        "authorized_exports", "D-14-001", "D-14-002", "protocol_approval",
    ))
    assert cli.main(argv) == cli.ExitCode.GATE_BLOCKED
    public_message = capsys.readouterr().err
    assert all(token in public_message for token in (
        "authorized_exports", "D-14-001", "D-14-002", "protocol_approval",
    ))
    assert not output.exists()


def test_batch_validation_never_reconstructs_missing_external_population(tmp_path: Path) -> None:
    cli = _cli()
    runs = tmp_path / "runs"
    write_shared_candidate(runs, seed=17, fold=2)
    config_path = _fixture_config(tmp_path)
    selection = cli.parse_cli([
        "--config", str(config_path), "--runs-root", str(runs),
        "--direction", "adni_to_oasis", "--method", "mmd", "--validate-only",
    ])
    config = cli._load_configuration(selection)
    request = cli._evaluation_request(selection, config)
    candidates = cli.discover_candidates(config, runs, request, (2,), (17,))
    incomplete = tuple(
        replace(
            candidate,
            expected_populations=tuple(
                population for population in candidate.expected_populations
                if population.role is not cli.PredictionRole.TARGET_EVALUATION
            ),
        )
        for candidate in candidates
    )
    assert cli._validated_batches(incomplete, config, runs) is None


def test_default_dispatch_validate_only_rejects_population_subject_absent_from_every_export(
    tmp_path: Path,
) -> None:
    cli = _cli()
    runs = tmp_path / "runs"
    write_shared_candidate(runs, seed=17, fold=2)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config.update(analysis_mode="synthetic_test_only", expected_folds=[2], expected_seeds=[17])
    add_identity_population_controls(config, runs)
    population = runs / config["expected_population_companions"]["adni_to_oasis"][
        "target_evaluation"
    ]["relative_path"]
    population.write_text("subject_hash\nhash-a\nhash-b\nhash-c\n", encoding="utf-8")
    config["expected_population_companions"]["adni_to_oasis"]["target_evaluation"][
        "sha256"
    ] = hashlib.sha256(population.read_bytes()).hexdigest()
    config_path = tmp_path / "population.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    result = cli.main([
        "--config", str(config_path), "--runs-root", str(runs),
        "--direction", "adni_to_oasis", "--method", "mmd", "--validate-only",
    ])
    assert result == cli.ExitCode.VALIDATION_INCOMPLETE


def test_default_dispatch_reuse_never_returns_false_success(tmp_path: Path) -> None:
    cli = _cli()
    result = cli.main([
        "--config", str(CONFIG), "--direction", "adni_to_oasis", "--method", "mmd",
        "--reuse", "--output-root", str(tmp_path / "missing"),
    ])
    assert result == cli.ExitCode.REUSE_REJECTED


def test_cli_has_no_training_or_statistical_implementation_imports() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "acda3d.training" not in source
    assert "acda3d.experiments" not in source
    for module in ("metrics", "bootstrap", "paired_statistics", "multiple_testing", "confusion_matrices"):
        assert f"evaluation.{module}" not in source
