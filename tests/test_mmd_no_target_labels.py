from pathlib import Path

import pytest

from acda3d.exceptions import TrainingRuntimeError
from acda3d.experiments import load_mmd_config
from acda3d.experiments.coral import prepare_coral_fold_inputs
from tests.phase8_helpers import make_loader
from tests.phase11_helpers import (
    make_mmd_environment,
    make_mmd_target_loader,
    make_mmd_trainer,
)


def test_mmd_dataset_runner_and_trainer_exclude_target_labels(tmp_path: Path):
    config = load_mmd_config(make_mmd_environment(tmp_path / "environment"))
    prepared = prepare_coral_fold_inputs(config, 0)
    assert set(prepared.target_adaptation_dataset[0]) == {
        "x", "subject_id", "subject_hash", "cohort"
    }
    trainer = make_mmd_trainer(tmp_path / "run", warmup_epochs=0)
    with pytest.raises(TrainingRuntimeError, match="forbidden label fields"):
        trainer.fit(
            make_loader(),
            make_loader(),
            target_adaptation_loader=make_mmd_target_loader(include_label=True),
        )
