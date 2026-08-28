from __future__ import annotations

from pathlib import Path

from acda3d.experiments.baselines import (
    load_baseline_config,
    run_baseline_both_directions,
    train_baseline_cv_fold,
)
from tests.phase14_helpers import make_baseline_environment


def test_every_approved_baseline_supports_synthetic_validate_only(tmp_path: Path) -> None:
    config = load_baseline_config(
        make_baseline_environment(tmp_path, tensor_shape=(32, 32, 32))
    )

    results = [
        train_baseline_cv_fold(config, baseline, 0, 42, validate_only=True)
        for baseline in config.baseline_names
    ]

    assert [result.status for result in results] == ["VALIDATED", "VALIDATED"]
    assert all(result.payload["parameter_count"] > 0 for result in results)
    assert all(not result.run_dir.exists() for result in results)


def test_all_five_folds_and_both_directions_are_planned_sequentially(tmp_path: Path) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path, n_splits=5))

    results = run_baseline_both_directions(config, dry_run=True)

    assert tuple(results) == ("ADNI_to_OASIS", "OASIS_to_ADNI")
    assert all(
        [result.fold for result in folds] == [0, 1, 2, 3, 4]
        for direction in results.values()
        for folds in direction.values()
    )
    assert all(
        result.payload["target_adaptation_loader_constructed"] is False
        for direction in results.values()
        for folds in direction.values()
        for result in folds
    )
