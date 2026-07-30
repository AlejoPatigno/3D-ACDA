from pathlib import Path

import pandas as pd
import pytest
import torch

from pada3dacb.experiments.prediction_export import collect_predictions, export_predictions
from pada3dacb.experiments.prototype_pseudo import PROTOTYPE_PSEUDO_DISPLAY_NAME
from tests.phase13_helpers import (
    FORBIDDEN_PREDICTION_EXPORT_FIELDS,
    assert_phase13_prediction_frame,
    target_monitoring_loader,
    tiny_prediction_model,
)


def test_proposed_prediction_export_uses_monitoring_schema_without_adaptation_leakage(tmp_path: Path):
    frame = collect_predictions(
        tiny_prediction_model(),
        target_monitoring_loader(),
        torch.ones(2, 1, 1, 1),
        torch.device("cpu"),
        direction="ADNI_to_OASIS",
        fold=0,
        seed=42,
        checkpoint_name="best_source_f1",
        checkpoint_epoch=5,
        split="target_monitoring",
        experiment_hash="phase13-proposed-hash",
        method="prototype_pseudo",
        model_name=PROTOTYPE_PSEUDO_DISPLAY_NAME,
    )

    assert_phase13_prediction_frame(frame)
    assert not frame["subject_hash"].duplicated().any()
    assert set(frame["true_label"]) <= {"CN", "MCI", "AD"}

    path = export_predictions(frame, tmp_path / "target_monitoring_predictions" / "best_source_f1.csv")
    reloaded = pd.read_csv(path)
    pd.testing.assert_frame_equal(reloaded, frame, check_dtype=False)


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_PREDICTION_EXPORT_FIELDS))
def test_proposed_prediction_export_contract_has_no_private_phase13_columns(forbidden: str):
    frame = collect_predictions(
        tiny_prediction_model(),
        target_monitoring_loader(),
        torch.ones(2, 1, 1, 1),
        torch.device("cpu"),
        direction="OASIS_to_ADNI",
        fold=4,
        seed=42,
        checkpoint_name="last",
        checkpoint_epoch=55,
        split="target_monitoring",
        experiment_hash="phase13-proposed-hash",
        method="prototype_pseudo",
        model_name=PROTOTYPE_PSEUDO_DISPLAY_NAME,
    )

    assert forbidden not in frame.columns
