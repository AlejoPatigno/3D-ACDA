from pathlib import Path

import torch

from tests.phase8_helpers import make_loader
from tests.phase10_helpers import make_coral_trainer, make_target_loader


def test_best_checkpoint_is_selected_only_by_source_macro_f1(tmp_path: Path):
    trainer = make_coral_trainer(tmp_path, warmup_epochs=1, full_epochs=2)
    history = trainer.fit(
        make_loader(), make_loader(), target_adaptation_loader=make_target_loader()
    )
    checkpoint = torch.load(
        tmp_path / "checkpoint_best_source_f1.pt", map_location="cpu", weights_only=False
    )
    expected = max(
        history.rows, key=lambda row: row["source_validation/macro_f1"]
    )["epoch"]
    assert checkpoint["epoch"] == expected
    assert checkpoint["adaptation_method"] == "coral"
    assert checkpoint["coral_weight"] == 1.0
    assert "target_adaptation" in checkpoint["loader_generator_states"]
