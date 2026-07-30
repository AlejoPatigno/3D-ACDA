from pathlib import Path

import torch

from tests.phase8_helpers import make_loader, make_trainer


def test_interrupted_resume_matches_uninterrupted_parameters_and_steps(tmp_path: Path):
    uninterrupted = make_trainer(tmp_path / "continuous", warmup_epochs=1, full_epochs=3)
    uninterrupted.fit(make_loader(shuffle=True), make_loader())

    interrupted = make_trainer(tmp_path / "resumed", warmup_epochs=1, full_epochs=3)
    interrupted.fit(
        make_loader(shuffle=True), make_loader(), interrupt_after_epoch=2
    )
    resumed = make_trainer(tmp_path / "resumed", warmup_epochs=1, full_epochs=3)
    history = resumed.fit(
        make_loader(shuffle=True),
        make_loader(),
        resume_from=tmp_path / "resumed" / "checkpoint_last.pt",
    )
    assert resumed.global_step == uninterrupted.global_step
    assert [row["epoch"] for row in history.rows] == [1, 2, 3, 4]
    for key, value in uninterrupted.model.state_dict().items():
        torch.testing.assert_close(resumed.model.state_dict()[key], value, rtol=0, atol=0)
    assert resumed.optimizer.state_dict()["state"].keys() == uninterrupted.optimizer.state_dict()["state"].keys()
