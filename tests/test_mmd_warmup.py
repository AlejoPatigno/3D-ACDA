from pathlib import Path

from tests.phase8_helpers import make_loader
from tests.phase11_helpers import make_mmd_target_loader, make_mmd_trainer


def test_mmd_warmup_is_source_only_and_preserves_target_rng(tmp_path: Path):
    trainer = make_mmd_trainer(tmp_path, warmup_epochs=1, full_epochs=0)
    target = make_mmd_target_loader()
    before = target.generator.get_state().clone()
    history = trainer.fit(
        make_loader(), make_loader(), target_adaptation_loader=target
    )
    row = history.rows[0]
    assert row["train/mmd_loss"] == row["train/weighted_mmd_loss"] == 0
    assert row["train/target_batches_consumed"] == 0
    assert row["adaptation_active"] is False
    assert target.generator.get_state().equal(before)
