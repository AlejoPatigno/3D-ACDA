from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import torch
from torch import nn

from pada3dacb.experiments import baselines as baseline_module
from pada3dacb.experiments.baselines import load_baseline_config, train_baseline_cv_fold
from tests.phase14_helpers import make_baseline_environment


class _TinyBaseline(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.classifier = nn.Linear(1, 3)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = x.mean(dim=(1, 2, 3, 4)).unsqueeze(1)
        return {"logits": self.classifier(features), "features": features}


def test_completed_manifest_and_predictions_prove_source_only_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_baseline_config(make_baseline_environment(tmp_path))
    monkeypatch.setattr(baseline_module, "build_baseline", lambda *_args, **_kwargs: _TinyBaseline())

    result = train_baseline_cv_fold(config, "faster_snn", 0, 42)
    manifest = json.loads((result.run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(result.run_dir / "predictions.csv")

    assert manifest["method"] == "baseline"
    assert manifest["target_adaptation_loader_constructed"] is False
    assert manifest["source_train_count"] > 0
    assert manifest["source_validation_count"] > 0
    assert manifest["target_evaluation_count"] > 0
    assert set(predictions["split"]) == {"source_validation", "target_monitoring"}
    assert not any("adaptation" in column for column in predictions.columns)
    assert not {"c_target", "g_bar"} & set(predictions.columns)
