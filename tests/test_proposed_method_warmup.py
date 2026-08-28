import pytest

from acda3d.training.trainer import BaseFixedEpochTrainer
from tests.test_proposed_method_trainer import make_proposed_epoch_trainer


class _SourceLoader:
    def __len__(self):
        return 2


class _ExplodingTargetLoader:
    def __len__(self):
        raise AssertionError("warm-up must not inspect target loader length")

    def __iter__(self):
        raise AssertionError("warm-up must not consume target batches")


def test_proposed_warmup_is_source_only_and_reports_inactive_adaptation(monkeypatch):
    trainer, _, _ = make_proposed_epoch_trainer()
    calls = []

    def source_only_epoch(self, source_loader, stage):
        calls.append((source_loader, stage))
        return {"total": 1.25}

    monkeypatch.setattr(BaseFixedEpochTrainer, "_train_epoch", source_only_epoch)
    source_loader = _SourceLoader()

    metrics = trainer._train_epoch_for_stage(source_loader, _ExplodingTargetLoader(), "warm")

    assert calls == [(source_loader, "warm")]
    assert metrics["total"] == pytest.approx(1.25)
    assert metrics["target_batches_consumed"] == 0.0
    assert metrics["prototype_pseudo_loss"] == 0.0
    assert metrics["weighted_prototype_pseudo_loss"] == 0.0
    assert metrics["prototype_raw"] == 0.0
    assert metrics["pseudo_label_raw"] == 0.0
    assert metrics["accepted_count"] == 0.0
    assert metrics["adaptation_active"] == 0.0
