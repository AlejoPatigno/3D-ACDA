from pathlib import Path

import pytest
from torch.utils.data import DataLoader

from acda3d.exceptions import TrainingRuntimeError
from tests.phase8_helpers import make_loader
from tests.phase11_helpers import make_mmd_target_loader, make_mmd_trainer


def test_mmd_source_controls_steps_and_target_cycles(tmp_path: Path):
    trainer = make_mmd_trainer(tmp_path, warmup_epochs=0)
    history = trainer.fit(
        make_loader(),
        make_loader(),
        target_adaptation_loader=make_mmd_target_loader(count=2, batch_size=2),
    )
    row = history.rows[0]
    assert row["train/source_batches"] == 3
    assert row["train/target_batches_consumed"] == 3
    assert row["train/target_batch_cycles"] == 2


@pytest.mark.parametrize("target", [DataLoader([], batch_size=2), DataLoader([1], batch_size=1)])
def test_mmd_rejects_zero_or_single_sample_target_loader(tmp_path: Path, target):
    with pytest.raises(TrainingRuntimeError):
        make_mmd_trainer(tmp_path, warmup_epochs=0).fit(
            make_loader(), make_loader(), target_adaptation_loader=target
        )
