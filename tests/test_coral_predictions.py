from pathlib import Path

import pandas as pd

from acda3d.experiments import CORALExperimentRunner, load_coral_config
from acda3d.experiments.prediction_export import PREDICTION_COLUMNS
from tests.phase10_helpers import make_coral_environment


def test_coral_exports_only_labeled_evaluation_partitions(tmp_path: Path):
    config = load_coral_config(make_coral_environment(tmp_path))
    result = CORALExperimentRunner(config).run_fold(0, 42)
    assert result.status == "COMPLETED"
    for directory in ("source_validation_predictions", "target_monitoring_predictions"):
        frame = pd.read_csv(result.run_dir / directory / "last.csv")
        assert tuple(frame.columns) == PREDICTION_COLUMNS
        assert set(frame["method"]) == {"coral"}
        assert set(frame["model"]) == {"3D-ACDA + CORAL"}
    assert not (result.run_dir / "target_adaptation_predictions").exists()
    reused = CORALExperimentRunner(config).run_fold(0, 42)
    assert reused.reused is True and reused.experiment_hash == result.experiment_hash
