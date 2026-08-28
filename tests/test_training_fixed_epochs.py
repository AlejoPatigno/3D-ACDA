from pathlib import Path

import pytest
from torch.utils.data import DataLoader

from acda3d.exceptions import TrainingRuntimeError
from tests.phase8_helpers import make_loader, make_trainer


def test_training_executes_all_fixed_warm_and_full_epochs(tmp_path: Path):
    trainer = make_trainer(tmp_path, warmup_epochs=2, full_epochs=2)
    history = trainer.fit(make_loader(), make_loader())
    assert [row["epoch"] for row in history.rows] == [1, 2, 3, 4]
    assert [row["stage"] for row in history.rows] == ["warm", "warm", "full", "full"]
    assert trainer.completed_epoch == 4
    assert (tmp_path / "training_history.csv").is_file()


def test_zero_batch_loader_fails_before_training(tmp_path: Path):
    empty = DataLoader([1], batch_size=2, drop_last=True)
    with pytest.raises(TrainingRuntimeError, match="zero batches"):
        make_trainer(tmp_path).fit(empty, make_loader())
