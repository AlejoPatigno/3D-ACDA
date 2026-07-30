from types import SimpleNamespace

import pytest
import torch

from pada3dacb.exceptions import TrainingRuntimeError
from pada3dacb.training.uda_trainer import ProposedPrototypePseudoAdaptationMethod, UDATrainer
from tests.phase8_helpers import TinyPADA3DACB
from tests.test_cdan_trainer import _BatchLoader, _DisabledScaler, _LossOutput, _source_batch


class _CountingAdamW(torch.optim.AdamW):
    def __init__(self, params):
        super().__init__(params, lr=0.01)
        self.step_calls = 0

    def step(self, closure=None):
        self.step_calls += 1
        return super().step(closure)


def proposed_target_batch(value=2.0, **extra):
    batch = {"x": torch.full((2, 1, 2, 2, 2), value)}
    batch.update(extra)
    return batch


def make_proposed_epoch_trainer():
    model = TinyPADA3DACB()
    optimizer = _CountingAdamW(model.parameters())
    trainer = UDATrainer.__new__(UDATrainer)
    trainer.model = model
    trainer.roi_masks = torch.ones(2, 1, 1, 1)
    trainer.device = torch.device("cpu")
    trainer.config = SimpleNamespace(mixed_precision=False, fail_on_nonfinite_loss=True, gradient_clip_norm=100.0)
    trainer.scaler = _DisabledScaler()
    trainer.optimizer = optimizer
    trainer.loss_fn = lambda output, y, c_target, g_bar, stage: _LossOutput(output.latent_logits.pow(2).mean())
    trainer.adaptation_method = ProposedPrototypePseudoAdaptationMethod(tau_p=0.0, lambda_proto=0.7, lambda_pl=0.3)
    trainer.adaptation_weight = 1.0
    trainer.global_step = 0
    return trainer, model, optimizer


def test_proposed_full_stage_combines_source_core_and_adaptation_once_in_one_step():
    trainer, model, optimizer = make_proposed_epoch_trainer()
    before = [parameter.detach().clone() for parameter in model.parameters()]

    metrics = trainer._train_epoch_for_stage(
        _BatchLoader([_source_batch(1.0)]),
        _BatchLoader([proposed_target_batch(2.0)]),
        "full",
    )

    assert optimizer.step_calls == 1
    assert trainer.global_step == 1
    assert metrics["prototype_pseudo_loss"] == pytest.approx(metrics["weighted_prototype_pseudo_loss"])
    assert metrics["prototype_weighted"] == pytest.approx(0.7 * metrics["prototype_raw"])
    assert metrics["pseudo_label_weighted"] == pytest.approx(0.3 * metrics["pseudo_label_raw"])
    assert metrics["prototype_pseudo_loss"] == pytest.approx(metrics["prototype_weighted"] + metrics["pseudo_label_weighted"])
    assert any(not torch.equal(old, new) for old, new in zip(before, model.parameters(), strict=True))


def test_proposed_target_label_firewall_rejects_diagnostic_and_artifact_keys():
    trainer, _, _ = make_proposed_epoch_trainer()

    for forbidden_key in ("y", "diagnosis", "c_target", "g_bar"):
        with pytest.raises(TrainingRuntimeError, match="forbidden label fields"):
            trainer._train_epoch_for_stage(
                _BatchLoader([_source_batch(1.0)]),
                _BatchLoader([proposed_target_batch(2.0, **{forbidden_key: torch.zeros(2)})]),
                "full",
            )


def test_proposed_trainer_accepts_target_x_with_optional_identity_only():
    trainer, _, optimizer = make_proposed_epoch_trainer()

    metrics = trainer._train_epoch_for_stage(
        _BatchLoader([_source_batch(1.0)]),
        _BatchLoader([proposed_target_batch(2.0, subject_id=["a", "b"], subject_hash=["ha", "hb"], cohort=["OASIS", "OASIS"])]),
        "full",
    )

    assert optimizer.step_calls == 1
    assert metrics["adaptation_active"] == 1.0
