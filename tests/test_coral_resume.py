from pathlib import Path

import torch

from tests.phase8_helpers import make_loader
from tests.phase10_helpers import make_coral_trainer, make_target_loader


def test_coral_resume_restores_source_and_target_loader_state_exactly(tmp_path: Path):
    continuous = make_coral_trainer(tmp_path / "continuous", full_epochs=2)
    continuous.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_target_loader(),
    )
    interrupted = make_coral_trainer(tmp_path / "resumed", full_epochs=2)
    interrupted.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_target_loader(),
        interrupt_after_epoch=2,
    )
    resumed = make_coral_trainer(tmp_path / "resumed", full_epochs=2)
    resumed.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=make_target_loader(),
        resume_from=tmp_path / "resumed" / "checkpoint_last.pt",
    )
    assert resumed.global_step == continuous.global_step
    for key, value in continuous.model.state_dict().items():
        torch.testing.assert_close(resumed.model.state_dict()[key], value, rtol=0, atol=0)
