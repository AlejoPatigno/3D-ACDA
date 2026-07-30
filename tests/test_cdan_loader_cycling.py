from tests.phase11_helpers import make_mmd_target_loader
from tests.test_cdan_trainer import (
    _BatchLoader,
    _make_full_stage_trainer,
    _source_batch,
    _target_batch,
)


def test_cdan_target_fixture_loader_uses_drop_last_batches():
    loader = make_mmd_target_loader(count=5, batch_size=2)
    assert loader.drop_last and len(loader) == 2


def test_cdan_full_stage_cycles_target_batches_from_source_length():
    trainer, _, _, optimizer = _make_full_stage_trainer()
    source_loader = _BatchLoader([_source_batch(1.0), _source_batch(1.5), _source_batch(2.0)])
    target_loader = _BatchLoader([_target_batch(2.0, "OASIS-A"), _target_batch(2.5, "OASIS-B")])

    metrics = trainer._train_epoch_for_stage(source_loader, target_loader, "full")

    assert optimizer.step_calls == 3
    assert trainer.global_step == 3
    assert metrics["source_batches"] == 3.0
    assert metrics["target_batches_consumed"] == 3.0
    assert metrics["target_batch_cycles"] == 1.0
    assert metrics["weighted_cdan_loss"] > 0.0
