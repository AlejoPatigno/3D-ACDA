import json
from pathlib import Path

from pada3dacb.experiments.prototype_pseudo import (
    PrototypePseudoExperimentRunner,
    load_prototype_pseudo_config,
    run_prototype_pseudo_both_directions,
)
from pada3dacb.experiments.run_manifest import atomic_json
from tests.test_proposed_method_config import make_proposed_environment


def test_prototype_pseudo_dry_run_supports_five_folds_and_both_directions(tmp_path: Path):
    config = load_prototype_pseudo_config(make_proposed_environment(tmp_path))
    config.folds = list(range(5))

    results = PrototypePseudoExperimentRunner(config).run(dry_run=True)
    directions = run_prototype_pseudo_both_directions(config, dry_run=True)

    assert [result.fold for result in results] == list(range(5))
    assert all(result.metrics["planned_target_adaptation"] > 0 for result in results)
    assert set(directions) == {"ADNI_to_OASIS", "OASIS_to_ADNI"}
    assert directions["ADNI_to_OASIS"][0].experiment_hash != directions["OASIS_to_ADNI"][0].experiment_hash


def test_prototype_pseudo_run_directory_contains_configuration_identity(tmp_path: Path):
    config = load_prototype_pseudo_config(make_proposed_environment(tmp_path))
    config.paths.output_root = tmp_path / "runs"

    run_dir = str(config.run_dir(0, 42))

    assert "prototype_pseudo" in run_dir
    assert config.adaptation.sha256()[:16] in run_dir


def test_prototype_pseudo_completed_fold_reuse_checks_manifest_identity(tmp_path: Path):
    config = load_prototype_pseudo_config(make_proposed_environment(tmp_path))
    config.paths.output_root = tmp_path / "runs"
    runner = PrototypePseudoExperimentRunner(config)
    prepared = runner._prepare_fold(0)
    run_dir = config.run_dir(0, 42)
    run_dir.mkdir(parents=True)
    expected_hash = config.sha256()
    metrics = {"best_source_macro_f1": 0.5}
    atomic_json(run_dir / "fold_metrics.json", metrics)
    for name in ["checkpoint_last.pt", "checkpoint_best_source_f1.pt", "training_history.csv"]:
        (run_dir / name).write_text("placeholder", encoding="utf-8")
    atomic_json(
        run_dir / "run_manifest.json",
        {
            "status": "COMPLETED",
            "direction": config.direction,
            "seed": 42,
            "fold": 0,
            "experiment_hash": expected_hash,
            "method": "prototype_pseudo",
            "adaptation_method": "prototype_pseudo",
            "source_split_assignment_hash": prepared.base.source_assignment_hash,
            "target_adaptation_assignment_hash": prepared.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": prepared.target_evaluation_assignment_hash,
        },
    )

    reused = runner._completed_reuse(run_dir, expected_hash, prepared)

    assert reused is not None
    assert reused.reused is True
    assert reused.metrics == metrics
    assert json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))["method"] == "prototype_pseudo"
