from pathlib import Path

import torch

from acda3d.training.monitoring import TARGET_MONITORING_LABEL, evaluate_labeled_loader
from tests.phase8_helpers import make_loader, make_trainer


def test_target_monitoring_is_namespaced_no_grad_and_not_checkpoint_selector(tmp_path: Path):
    trainer = make_trainer(tmp_path, warmup_epochs=1, full_epochs=1)
    history = trainer.fit(make_loader(), make_loader(), make_loader(target_only=True))
    for row in history.rows:
        assert row["target_monitoring/label"] == TARGET_MONITORING_LABEL
        assert "target_monitoring/macro_f1" in row
    checkpoint = torch.load(tmp_path / "checkpoint_best_source_f1.pt", weights_only=False)
    assert checkpoint["best_source_macro_f1"] == max(
        row["source_validation/macro_f1"] for row in history.rows
    )
    assert not any("target_monitoring" in key for key in checkpoint if key != "history_rows")


def test_monitoring_restores_mode_and_creates_no_gradients(tmp_path: Path):
    trainer = make_trainer(tmp_path)
    trainer.model.train()
    metrics = evaluate_labeled_loader(
        trainer.model,
        make_loader(target_only=True),
        trainer.roi_masks,
        trainer.device,
        namespace="target_monitoring",
    )
    assert trainer.model.training
    assert metrics["target_monitoring/label"] == TARGET_MONITORING_LABEL
    assert all(parameter.grad is None for parameter in trainer.model.parameters())
