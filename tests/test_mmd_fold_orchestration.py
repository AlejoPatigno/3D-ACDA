from pathlib import Path

from pada3dacb.experiments import (
    MMDExperimentRunner,
    load_mmd_config,
    run_mmd_both_directions,
)
from tests.phase11_helpers import make_mmd_environment


def test_mmd_dry_run_supports_all_folds_and_both_directions(tmp_path: Path):
    config = load_mmd_config(make_mmd_environment(tmp_path))
    config.folds = list(range(5))
    results = MMDExperimentRunner(config).run(dry_run=True)
    assert [result.fold for result in results] == list(range(5))
    assert all(result.metrics["planned_target_adaptation"] > 0 for result in results)
    directions = run_mmd_both_directions(config, dry_run=True)
    assert set(directions) == {"ADNI_to_OASIS", "OASIS_to_ADNI"}
    assert directions["ADNI_to_OASIS"][0].experiment_hash != directions["OASIS_to_ADNI"][0].experiment_hash
