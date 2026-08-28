from pathlib import Path

import pytest
import torch

from acda3d.exceptions import TrainingRuntimeError
from tests.phase8_helpers import make_loader
from tests.phase11_helpers import make_mmd_target_loader, make_mmd_trainer


def test_mmd_resume_restores_both_loader_states_exactly(tmp_path: Path):
    continuous = make_mmd_trainer(tmp_path / "continuous", full_epochs=2)
    continuous.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_mmd_target_loader(),
    )
    interrupted = make_mmd_trainer(tmp_path / "resumed", full_epochs=2)
    interrupted.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_mmd_target_loader(),
        interrupt_after_epoch=2,
    )
    resumed = make_mmd_trainer(tmp_path / "resumed", full_epochs=2)
    resumed.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_mmd_target_loader(),
        resume_from=tmp_path / "resumed" / "checkpoint_last.pt",
    )
    assert resumed.global_step == continuous.global_step
    for key, value in continuous.model.state_dict().items():
        torch.testing.assert_close(resumed.model.state_dict()[key], value, rtol=0, atol=0)

    incompatible = make_mmd_trainer(tmp_path / "changed", bandwidths=[1.0, 3.0])
    with pytest.raises(TrainingRuntimeError, match="Incompatible MMD"):
        incompatible.fit(
            make_loader(shuffle=True),
            make_loader(),
            target_adaptation_loader=make_mmd_target_loader(),
            resume_from=tmp_path / "resumed" / "checkpoint_last.pt",
        )
