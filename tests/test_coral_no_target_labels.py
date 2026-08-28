from pathlib import Path

import pytest

from acda3d.exceptions import TrainingRuntimeError
from acda3d.experiments import load_coral_config, prepare_coral_fold_inputs
from tests.phase8_helpers import make_loader
from tests.phase10_helpers import make_coral_environment, make_coral_trainer, make_target_loader


def test_target_adaptation_dataset_and_trainer_exclude_labels(tmp_path: Path):
    config = load_coral_config(make_coral_environment(tmp_path / "environment"))
    prepared = prepare_coral_fold_inputs(config, 0)
    assert set(prepared.target_adaptation_dataset[0]) == {
        "x", "subject_id", "subject_hash", "cohort"
    }
    trainer = make_coral_trainer(tmp_path / "run", warmup_epochs=0)
    with pytest.raises(TrainingRuntimeError, match="forbidden label fields"):
        trainer.fit(
            make_loader(),
            make_loader(),
            target_adaptation_loader=make_target_loader(include_label=True),
        )
