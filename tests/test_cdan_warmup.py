import pytest
import torch

from pada3dacb.adaptation import (
    CDANAdaptationMethod,
    DomainDiscriminator,
    DomainDiscriminatorConfig,
)
from pada3dacb.training.trainer import BaseFixedEpochTrainer
from pada3dacb.training.uda_trainer import UDATrainer
from tests.phase8_helpers import TinyPADA3DACB


def test_cdan_warmup_loss_is_zero_and_has_no_domain_diagnostics():
    model = TinyPADA3DACB()
    masks = torch.ones(2, 1, 1, 1)
    output = model(torch.ones(2, 1, 2, 2, 2), masks)
    method = CDANAdaptationMethod(DomainDiscriminator(DomainDiscriminatorConfig(12, (4,), "relu", 0.0)), 1.0)
    result = method.compute(output, output, "warm")
    assert result.total.item() == 0 and result.components["cdan"].item() == 0


class _SourceLoader:
    def __len__(self):
        return 2


class _ExplodingTargetLoader:
    def __len__(self):
        raise AssertionError("warm-up must not inspect target loader length")

    def __iter__(self):
        raise AssertionError("warm-up must not consume target batches")


class _ExplodingCDAN(CDANAdaptationMethod):
    def __init__(self):
        super().__init__(DomainDiscriminator(DomainDiscriminatorConfig(12, (4,), "relu", 0.0)), 1.0)

    def compute(self, *args, **kwargs):
        raise AssertionError("warm-up must not compute CDAN features or call the discriminator")


def test_cdan_trainer_warmup_is_source_only_without_target_or_discriminator(monkeypatch):
    calls = []

    def source_only_epoch(self, source_loader, stage):
        calls.append((source_loader, stage))
        return {"total": 1.25}

    monkeypatch.setattr(BaseFixedEpochTrainer, "_train_epoch", source_only_epoch)
    trainer = UDATrainer.__new__(UDATrainer)
    trainer.adaptation_method = _ExplodingCDAN()
    source_loader = _SourceLoader()

    metrics = trainer._train_epoch_for_stage(source_loader, _ExplodingTargetLoader(), "warm")

    assert calls == [(source_loader, "warm")]
    assert metrics["total"] == pytest.approx(1.25)
    assert metrics["target_batches_consumed"] == 0.0
    assert metrics["cdan_loss"] == 0.0
    assert metrics["weighted_cdan_loss"] == 0.0
    assert metrics["discriminator_gradient_norm"] == 0.0
