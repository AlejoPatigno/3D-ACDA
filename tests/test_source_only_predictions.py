from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader

from pada3dacb.experiments.prediction_export import (
    PREDICTION_COLUMNS,
    collect_predictions,
    export_predictions,
)
from tests.phase8_helpers import TinyPADA3DACB


def test_prediction_export_schema_uniqueness_and_probabilities(tmp_path: Path):
    rows = [
        {"x": torch.ones(1, 2, 2, 2) * index, "y": torch.tensor(index % 3),
         "subject_hash": f"subject-{index}", "cohort": "ADNI"}
        for index in range(3)
    ]
    frame = collect_predictions(
        TinyPADA3DACB(), DataLoader(rows, batch_size=2), torch.ones(2, 1, 1, 1),
        torch.device("cpu"), direction="ADNI_to_OASIS", fold=0, seed=42,
        checkpoint_name="last", checkpoint_epoch=2, split="source_validation",
        experiment_hash="experiment",
    )
    assert tuple(frame.columns) == PREDICTION_COLUMNS
    assert frame.subject_hash.is_unique
    assert torch.allclose(
        torch.tensor(
            frame[["probability_CN", "probability_MCI", "probability_AD"]]
            .sum(axis=1)
            .to_numpy()
        ),
        torch.ones(3, dtype=torch.float64),
        atol=1e-6,
    )
    path = export_predictions(frame, tmp_path / "predictions.csv")
    pd.testing.assert_frame_equal(pd.read_csv(path), frame, check_dtype=False)
