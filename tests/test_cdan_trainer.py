from types import SimpleNamespace

import torch

from acda3d.adaptation import (
    CDANAdaptationMethod,
    DomainDiscriminator,
    DomainDiscriminatorConfig,
)
from acda3d.training.trainer import BaseFixedEpochTrainer
from acda3d.training.uda_trainer import _SUPPORTED_METHODS, UDATrainer
from tests.phase8_helpers import TinyACDA3D


def test_uda_trainer_accepts_only_approved_cdan_extension():
    assert {"coral", "mmd", "cdan"} == _SUPPORTED_METHODS


class _LossOutput:
    def __init__(self, total):
        self.total = total

    def detached(self):
        return {"source_objective": float(self.total.detach().cpu())}


class _DisabledScaler:
    def is_enabled(self):
        return False


class _CountingAdamW(torch.optim.AdamW):
    def __init__(self, params):
        super().__init__(params)
        self.step_calls = 0

    def step(self, closure=None):
        self.step_calls += 1
        return super().step(closure)


def _source_batch(value=1.0):
    return {
        "x": torch.full((2, 1, 2, 2, 2), value),
        "y": torch.tensor([0, 1]),
        "c_target": torch.zeros(2, 2),
        "g_bar": torch.zeros(2, 2),
    }


def _target_batch(value=2.0, cohort="OASIS"):
    return {
        "x": torch.full((2, 1, 2, 2, 2), value),
        "subject_id": [f"{cohort}-1", f"{cohort}-2"],
        "subject_hash": [f"{cohort}-hash-1", f"{cohort}-hash-2"],
        "cohort": [cohort, cohort],
    }


class _BatchLoader(list):
    def __init__(self, batches):
        super().__init__(batches)
        self.batch_size = len(batches[0]["x"])


def _make_full_stage_trainer():
    model = TinyACDA3D()
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(12, (5,), "relu", 0.0))
    method = CDANAdaptationMethod(discriminator, grl_coefficient=1.0)
    optimizer = _CountingAdamW([
        {"params": model.parameters(), "lr": 0.01, "weight_decay": 0.0},
        {"params": discriminator.parameters(), "lr": 0.01, "weight_decay": 0.0},
    ])
    trainer = UDATrainer.__new__(UDATrainer)
    trainer.model = model
    trainer.roi_masks = torch.ones(2, 1, 1, 1)
    trainer.device = torch.device("cpu")
    trainer.config = SimpleNamespace(
        mixed_precision=False,
        fail_on_nonfinite_loss=True,
        gradient_clip_norm=100.0,
    )
    trainer.scaler = _DisabledScaler()
    trainer.optimizer = optimizer
    trainer.loss_fn = lambda output, y, c_target, g_bar, stage: _LossOutput(output.latent_logits.pow(2).mean())
    trainer.adaptation_method = method
    trainer.adaptation_weight = 0.5
    trainer.global_step = 0
    return trainer, model, discriminator, optimizer


def test_cdan_trainer_builds_one_adamw_with_model_and_discriminator_groups(monkeypatch):
    def fake_base_init(self, *args, **kwargs):
        self.model = kwargs["model"]
        self.device = torch.device("cpu")
        self.config = SimpleNamespace(learning_rate=0.01, weight_decay=0.001)
        self.resolved_configuration = {}

    monkeypatch.setattr(BaseFixedEpochTrainer, "__init__", fake_base_init)
    model = TinyACDA3D()
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(12, (5,), "relu", 0.0))

    trainer = UDATrainer(
        model=model,
        adaptation_method=CDANAdaptationMethod(discriminator, grl_coefficient=1.0),
        adaptation_weight=0.5,
        adaptation_configuration={
            "grl": {"schedule": "constant", "coefficient": 1.0},
            "discriminator": {
                "optimizer_group": {"learning_rate": 0.02, "weight_decay": 0.003},
            },
        },
        source_split_assignment_hash="source-hash",
        target_adaptation_assignment_hash="target-adapt-hash",
        target_evaluation_assignment_hash="target-eval-hash",
    )

    assert isinstance(trainer.optimizer, torch.optim.AdamW)
    assert len(trainer.optimizer.param_groups) == 2
    assert trainer.optimizer.param_groups[0]["lr"] == 0.01
    assert trainer.optimizer.param_groups[0]["weight_decay"] == 0.001
    assert trainer.optimizer.param_groups[1]["lr"] == 0.02
    assert trainer.optimizer.param_groups[1]["weight_decay"] == 0.003
    assert set(trainer.optimizer.param_groups[0]["params"]) == set(model.parameters())
    assert set(trainer.optimizer.param_groups[1]["params"]) == set(discriminator.parameters())


def test_cdan_full_stage_updates_shared_model_and_discriminator_once_per_paired_batch():
    trainer, model, discriminator, optimizer = _make_full_stage_trainer()
    model_before = [parameter.detach().clone() for parameter in model.parameters()]
    discriminator_before = [parameter.detach().clone() for parameter in discriminator.parameters()]

    metrics = trainer._train_epoch_for_stage(
        _BatchLoader([_source_batch(1.0)]),
        _BatchLoader([_target_batch(2.0)]),
        "full",
    )

    assert optimizer.step_calls == 1
    assert trainer.global_step == 1
    assert metrics["weighted_cdan_loss"] > 0.0
    assert metrics["model_gradient_norm"] > 0.0
    assert metrics["discriminator_gradient_norm"] > 0.0
    assert any(not torch.equal(before, after) for before, after in zip(model_before, model.parameters(), strict=True))
    assert any(
        not torch.equal(before, after)
        for before, after in zip(discriminator_before, discriminator.parameters(), strict=True)
    )
