from pathlib import Path

import pytest

from pada3dacb.exceptions import TrainingRuntimeError
from pada3dacb.training.checkpointing import load_training_checkpoint
from tests.phase8_helpers import make_loader
from tests.test_cdan_trainer import _BatchLoader
from tests.test_proposed_method_checkpoint_policy import make_fit_trainer
from tests.test_proposed_method_trainer import proposed_target_batch


def test_proposed_checkpoint_has_no_adaptation_specific_cache_and_preserves_loader_state(tmp_path: Path):
    trainer = make_fit_trainer(tmp_path, full_epochs=1)
    trainer.fit(
        make_loader(shuffle=True),
        make_loader(),
        target_adaptation_loader=_BatchLoader([proposed_target_batch(2.0)]),
    )

    checkpoint = load_training_checkpoint(tmp_path / "checkpoint_last.pt")
    assert checkpoint["adaptation_method"] == "prototype_pseudo"
    assert set(checkpoint["loader_generator_states"]) == {"source_train", "target_adaptation"}
    assert "prototype_cache" not in checkpoint
    assert "prototype_state_dict" not in checkpoint
    assert "pseudo_label_cache" not in checkpoint
    assert "pseudo_label_threshold_schedule" not in checkpoint


def test_proposed_exact_resume_preserves_training_state_and_rejects_incompatible_config(tmp_path: Path):
    interrupted_dir = tmp_path / "interrupted"
    resumed_dir = tmp_path / "resumed"
    trainer = make_fit_trainer(interrupted_dir, full_epochs=2)
    trainer.fit(
        make_loader(shuffle=True, seed=21),
        make_loader(seed=22),
        target_adaptation_loader=_BatchLoader([proposed_target_batch(2.0)]),
        interrupt_after_epoch=1,
    )

    resumed = make_fit_trainer(resumed_dir, full_epochs=2)
    history = resumed.fit(
        make_loader(shuffle=True, seed=21),
        make_loader(seed=22),
        target_adaptation_loader=_BatchLoader([proposed_target_batch(2.0)]),
        resume_from=interrupted_dir / "checkpoint_last.pt",
    )

    assert history.rows[0]["epoch"] == 1
    assert history.rows[-1]["epoch"] == 2
    assert resumed.global_step == 6
    assert resumed.completed_epoch == 2

    incompatible = make_fit_trainer(tmp_path / "bad", full_epochs=2)
    incompatible.adaptation_configuration["tau_p"] = 0.75
    incompatible.adaptation_configuration_hash = "changed"
    incompatible.resolved_configuration["adaptation"] = incompatible.adaptation_configuration
    with pytest.raises(TrainingRuntimeError, match="Incompatible PROTOTYPE_PSEUDO resume checkpoint fields"):
        incompatible.fit(
            make_loader(shuffle=True, seed=21),
            make_loader(seed=22),
            target_adaptation_loader=_BatchLoader([proposed_target_batch(2.0)]),
            resume_from=interrupted_dir / "checkpoint_last.pt",
        )
