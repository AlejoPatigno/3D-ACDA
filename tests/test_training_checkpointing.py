from pathlib import Path

import torch

from acda3d.training.checkpointing import load_training_checkpoint
from tests.phase8_helpers import make_loader, make_trainer


def test_periodic_last_and_best_source_checkpoints_are_complete(tmp_path: Path):
    trainer = make_trainer(tmp_path, warmup_epochs=1, full_epochs=1)
    trainer.fit(make_loader(), make_loader(), make_loader(target_only=True))
    expected = {
        "checkpoint_epoch_001.pt", "checkpoint_epoch_002.pt",
        "checkpoint_last.pt", "checkpoint_best_source_f1.pt",
    }
    assert expected.issubset({path.name for path in tmp_path.glob("checkpoint*.pt")})
    checkpoint = load_training_checkpoint(tmp_path / "checkpoint_last.pt")
    required = {
        "model_state_dict", "optimizer_state_dict", "scheduler_state_dict",
        "scaler_state_dict", "epoch", "global_step", "best_source_macro_f1",
        "training_stage", "resolved_configuration", "configuration_hash",
        "split_assignment_hash", "atlas_hash", "roi_order_hash", "random_seed",
        "rng_state", "software_version", "git_commit",
    }
    assert required.issubset(checkpoint)
    assert checkpoint["epoch"] == 2
    assert not list(tmp_path.glob("*.tmp"))
    assert all(not torch.is_tensor(value) or value.numel() < 1_000_000 for value in checkpoint.values())
