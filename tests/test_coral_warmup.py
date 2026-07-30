from pathlib import Path

from tests.phase8_helpers import make_loader
from tests.phase10_helpers import make_coral_trainer, make_target_loader


def test_warmup_does_not_consume_target_or_activate_coral(tmp_path: Path):
    trainer = make_coral_trainer(tmp_path, warmup_epochs=1, full_epochs=1)
    history = trainer.fit(
        make_loader(), make_loader(), target_adaptation_loader=make_target_loader()
    )
    warm, full = history.rows
    assert warm["train/coral_loss"] == 0
    assert warm["train/weighted_coral_loss"] == 0
    assert warm["train/target_batches_consumed"] == 0
    assert warm["adaptation_active"] is False
    assert full["adaptation_active"] is True


def test_pure_warmup_preserves_target_loader_generator_state(tmp_path: Path):
    trainer = make_coral_trainer(tmp_path, warmup_epochs=1, full_epochs=0)
    target = make_target_loader()
    before = target.generator.get_state().clone()
    trainer.fit(make_loader(), make_loader(), target_adaptation_loader=target)
    assert target.generator.get_state().equal(before)
