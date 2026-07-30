from pathlib import Path

import torch

from tests.phase8_helpers import make_loader, make_trainer


def test_repeated_cpu_runs_with_same_seed_match(tmp_path: Path):
    first = make_trainer(tmp_path / "first")
    second = make_trainer(tmp_path / "second")
    first.fit(make_loader(), make_loader())
    second.fit(make_loader(), make_loader())
    for key, value in first.model.state_dict().items():
        torch.testing.assert_close(second.model.state_dict()[key], value, rtol=0, atol=0)
    assert first.global_step == second.global_step
    assert not first.scaler.is_enabled() and not second.scaler.is_enabled()
