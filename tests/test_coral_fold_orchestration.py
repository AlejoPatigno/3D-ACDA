from pathlib import Path

from pada3dacb.experiments import (
    CORALExperimentRunner,
    load_coral_config,
    run_coral_both_directions,
)
from tests.phase10_helpers import make_coral_environment


def test_coral_dry_run_supports_five_folds_and_both_directions(tmp_path: Path):
    config = load_coral_config(make_coral_environment(tmp_path))
    config.folds = list(range(5))
    results = CORALExperimentRunner(config).run(dry_run=True)
    assert [result.fold for result in results] == list(range(5))
    assert all(result.metrics["planned_target_adaptation"] > 0 for result in results)
    directions = run_coral_both_directions(config, dry_run=True)
    assert set(directions) == {"ADNI_to_OASIS", "OASIS_to_ADNI"}
    assert directions["ADNI_to_OASIS"][0].experiment_hash != directions["OASIS_to_ADNI"][0].experiment_hash
