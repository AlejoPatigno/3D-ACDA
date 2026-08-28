from pathlib import Path

from acda3d.experiments import (
    SourceOnlyExperimentRunner,
    load_source_only_config,
    run_both_directions,
)
from tests.phase9_helpers import make_source_only_environment


def test_all_folds_are_enumerated_without_training_in_dry_run(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    config.folds = list(range(5))
    results = SourceOnlyExperimentRunner(config).run(dry_run=True)
    assert [result.fold for result in results] == list(range(5))
    assert all(result.status == "PENDING" for result in results)
    assert not config.paths.output_root.exists()


def test_both_directions_use_independent_immutable_manifests(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    results = run_both_directions(config, dry_run=True)
    assert set(results) == {"ADNI_to_OASIS", "OASIS_to_ADNI"}
    assert results["ADNI_to_OASIS"][0].metrics["planned_source_train"] == 12
    assert results["OASIS_to_ADNI"][0].metrics["planned_source_train"] == 12
