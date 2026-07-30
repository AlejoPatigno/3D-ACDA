from pathlib import Path

import torch

from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.training.trainer import FixedEpochTrainingConfig
from pada3dacb.training.uda_trainer import ProposedPrototypePseudoAdaptationMethod, UDATrainer
from tests.phase8_helpers import TinyPADA3DACB, make_loader
from tests.test_cdan_trainer import _BatchLoader
from tests.test_proposed_method_trainer import proposed_target_batch


def make_fit_trainer(run_dir: Path, *, warmup_epochs=0, full_epochs=2, method=None):
    torch.manual_seed(123)
    model = TinyPADA3DACB()
    config = FixedEpochTrainingConfig(
        warmup_epochs=warmup_epochs,
        full_epochs=full_epochs,
        learning_rate=1e-2,
        weight_decay=1e-4,
        checkpoint_every=1,
        mixed_precision=False,
        seed=123,
    )
    return UDATrainer(
        model,
        CorePADA3DACBLoss(2),
        torch.ones(2, 1, 1, 1),
        run_dir,
        config=config,
        adaptation_method=method or ProposedPrototypePseudoAdaptationMethod(tau_p=0.0),
        adaptation_weight=1.0,
        adaptation_configuration={"method": "prototype_pseudo", "tau_p": 0.0},
        source_split_assignment_hash="source-hash",
        target_adaptation_assignment_hash="target-adapt-hash",
        target_evaluation_assignment_hash="target-eval-hash",
        split_assignment_hash="split",
        atlas_hash="atlas",
        roi_order_hash="roi-order",
    )


def test_proposed_best_checkpoint_is_selected_only_by_source_macro_f1(monkeypatch, tmp_path: Path):
    source_scores = iter([0.1, 0.9])
    target_scores = iter([0.99, 0.01])

    def fake_evaluate(model, loader, roi_masks, device, *, loss_fn=None, stage="full", namespace="source_validation"):
        if namespace == "source_validation":
            return {"source_validation/macro_f1": next(source_scores)}
        return {"target_monitoring/macro_f1": next(target_scores), "target_monitoring/label": "monitoring only"}

    monkeypatch.setattr("pada3dacb.training.trainer.evaluate_labeled_loader", fake_evaluate)
    trainer = make_fit_trainer(tmp_path)
    trainer.fit(
        make_loader(),
        make_loader(),
        make_loader(target_only=True),
        target_adaptation_loader=_BatchLoader([proposed_target_batch(2.0)]),
    )

    checkpoint = torch.load(tmp_path / "checkpoint_best_source_f1.pt", map_location="cpu", weights_only=False)
    assert checkpoint["epoch"] == 2
    assert checkpoint["best_source_macro_f1"] == 0.9
    assert "target_monitoring/macro_f1" not in checkpoint
    assert "prototype_cache" not in checkpoint
    assert "pseudo_label_cache" not in checkpoint
