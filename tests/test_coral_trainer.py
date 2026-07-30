from pathlib import Path

import pytest
import torch
from torch.utils.data import DataLoader

from pada3dacb.exceptions import TrainingRuntimeError
from tests.phase8_helpers import make_loader
from tests.phase10_helpers import make_coral_trainer, make_target_loader


def test_full_stage_pairs_batches_and_adds_weighted_coral_once(tmp_path: Path):
    trainer = make_coral_trainer(tmp_path, warmup_epochs=0, full_epochs=1, weight=2.0)
    before = {key: value.clone() for key, value in trainer.model.state_dict().items()}
    history = trainer.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_target_loader(),
    )
    row = history.rows[0]
    assert row["adaptation_active"] is True
    assert row["train/target_batches_consumed"] == row["train/source_batches"] == 3
    assert row["train/target_batch_cycles"] == 1
    assert row["train/total"] == pytest.approx(
        row["train/total"] - row["train/weighted_coral_loss"]
        + 2.0 * row["train/coral_loss"]
    )
    assert any(not torch.equal(before[key], value) for key, value in trainer.model.state_dict().items())


@pytest.mark.parametrize(
    "target",
    [
        DataLoader([], batch_size=2),
        DataLoader(
            [
                {
                    "x": torch.ones(1, 2, 2, 2),
                    "subject_id": "one",
                    "subject_hash": "one",
                    "cohort": "OASIS",
                }
            ],
            batch_size=1,
        ),
    ],
)
def test_coral_rejects_zero_or_single_sample_target_batches(tmp_path: Path, target):
    trainer = make_coral_trainer(tmp_path, warmup_epochs=0)
    with pytest.raises(TrainingRuntimeError):
        trainer.fit(make_loader(), make_loader(), target_adaptation_loader=target)
