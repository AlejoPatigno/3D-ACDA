from tests.test_cdan_trainer import _BatchLoader, _source_batch
from tests.test_proposed_method_trainer import make_proposed_epoch_trainer, proposed_target_batch


def test_proposed_full_stage_cycles_target_batches_from_source_length():
    trainer, _, optimizer = make_proposed_epoch_trainer()
    source_loader = _BatchLoader([_source_batch(1.0), _source_batch(1.5), _source_batch(2.0)])
    target_loader = _BatchLoader([proposed_target_batch(2.0), proposed_target_batch(2.5)])

    metrics = trainer._train_epoch_for_stage(source_loader, target_loader, "full")

    assert optimizer.step_calls == 3
    assert trainer.global_step == 3
    assert metrics["source_batches"] == 3.0
    assert metrics["target_batches_consumed"] == 3.0
    assert metrics["target_batch_cycles"] == 1.0
    assert metrics["prototype_pseudo_loss"] > 0.0
