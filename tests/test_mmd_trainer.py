from pathlib import Path

import pytest
import torch

from tests.phase8_helpers import make_loader
from tests.phase11_helpers import make_mmd_target_loader, make_mmd_trainer


def test_mmd_full_step_uses_unequal_batches_and_exact_weight(tmp_path: Path):
    trainer = make_mmd_trainer(tmp_path, warmup_epochs=0, full_epochs=1, weight=2.0)
    before = {key: value.clone() for key, value in trainer.model.state_dict().items()}
    history = trainer.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_mmd_target_loader(count=6, batch_size=3),
    )
    row = history.rows[0]
    assert row["adaptation_active"] is True
    assert row["train/source_batches"] == row["train/target_batches_consumed"] == 3
    assert row["train/weighted_mmd_loss"] == pytest.approx(2 * row["train/mmd_loss"])
    assert row["adaptation/kernel_bandwidths"] == "[0.5,1.0,2.0]"
    assert any(not torch.equal(before[key], value) for key, value in trainer.model.state_dict().items())
