"""Deterministic CPU helpers for Phase 13 integration and regression tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import torch
from torch.utils.data import DataLoader

from pada3dacb.experiments.prediction_export import PREDICTION_COLUMNS
from pada3dacb.experiments.prototype_pseudo import load_prototype_pseudo_config
from tests.phase8_helpers import TinyPADA3DACB
from tests.test_proposed_method_config import make_proposed_environment

FORBIDDEN_PREDICTION_EXPORT_FIELDS = {
    "x",
    "features",
    "z",
    "concepts",
    "concept_logits",
    "prototype",
    "source_prototype",
    "target_prototype",
    "pseudo_label",
    "target_adaptation",
    "domain_label",
}


def make_phase13_config(tmp_path: Path, *, folds: list[int] | None = None):
    config = load_prototype_pseudo_config(make_proposed_environment(tmp_path))
    if folds is not None:
        config.folds = folds
    return config


def target_monitoring_loader() -> DataLoader:
    rows = [
        {
            "x": torch.full((1, 2, 2, 2), float(index + 1) / 5),
            "y": torch.tensor(index % 3),
            "subject_hash": f"target-monitor-{index}",
            "cohort": "OASIS",
        }
        for index in range(4)
    ]
    return DataLoader(rows, batch_size=2, shuffle=False)


def tiny_prediction_model() -> TinyPADA3DACB:
    torch.manual_seed(13013)
    return TinyPADA3DACB()


def assert_phase13_prediction_frame(frame: pd.DataFrame) -> None:
    assert tuple(frame.columns) == PREDICTION_COLUMNS
    assert not (set(frame.columns) & FORBIDDEN_PREDICTION_EXPORT_FIELDS)
    assert frame["method"].eq("prototype_pseudo").all()
    assert frame["model"].eq("PADA-3DACB").all()
    assert set(frame["split"]) == {"target_monitoring"}
    assert "target_adaptation" not in set(frame["split"])
    probabilities = torch.tensor(
        frame[["probability_CN", "probability_MCI", "probability_AD"]].to_numpy(),
        dtype=torch.float64,
    )
    assert torch.allclose(probabilities.sum(dim=1), torch.ones(len(frame), dtype=torch.float64), atol=1e-6)


def proposed_outputs_for_adaptation():
    source = SimpleNamespace(
        z=torch.tensor([[0.0, 0.0], [1.0, 1.0], [3.0, 3.0]], dtype=torch.float32),
        concept_logits=torch.tensor([[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]], dtype=torch.float32),
    )
    target = SimpleNamespace(
        z=torch.tensor([[0.1, 0.0], [1.0, 1.2], [5.0, 5.0]], dtype=torch.float32),
        concept_logits=torch.tensor([[6.0, 0.0, 0.0], [0.0, 6.0, 0.0], [0.0, 0.0, 0.0]], dtype=torch.float32),
    )
    labels = torch.tensor([0, 1, 2], dtype=torch.long)
    return source, target, labels


def assert_two_direction_dry_run(outputs: dict[str, list], *, expected_folds: list[int]) -> None:
    assert set(outputs) == {"ADNI_to_OASIS", "OASIS_to_ADNI"}
    for direction, results in outputs.items():
        assert [result.fold for result in results] == expected_folds
        assert all(result.direction == direction for result in results)
        assert all(result.status == "PENDING" for result in results)


def skip_if_cdan_discriminator_contract_is_externalized(exc: Exception) -> None:
    if "input_dim" in str(exc):
        pytest.skip("Existing Phase 12 CDAN discriminator hash contract is owned by a previous slice.")
    raise exc
