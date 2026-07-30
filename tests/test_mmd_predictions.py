from pathlib import Path

import pandas as pd

from pada3dacb.experiments import MMDExperimentRunner, load_mmd_config
from pada3dacb.experiments.prediction_export import PREDICTION_COLUMNS
from tests.phase11_helpers import make_mmd_environment


def test_mmd_exports_evaluation_predictions_and_reuses_completed_fold(tmp_path: Path):
    config = load_mmd_config(make_mmd_environment(tmp_path))
    result = MMDExperimentRunner(config).run_fold(0, 42)
    assert result.status == "COMPLETED"
    for directory in ("source_validation_predictions", "target_monitoring_predictions"):
        frame = pd.read_csv(result.run_dir / directory / "last.csv")
        assert tuple(frame.columns) == PREDICTION_COLUMNS
        assert set(frame["method"]) == {"mmd"}
        assert set(frame["model"]) == {"PADA-3DACB + MMD"}
    assert not (result.run_dir / "target_adaptation_predictions").exists()
    reused = MMDExperimentRunner(config).run_fold(0, 42)
    assert reused.reused is True and reused.experiment_hash == result.experiment_hash
