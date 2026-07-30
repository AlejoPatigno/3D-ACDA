from pathlib import Path

import pytest
import torch

from pada3dacb.exceptions import TrainingRuntimeError
from pada3dacb.experiments.prototype_pseudo import PrototypePseudoExperimentRunner
from pada3dacb.training.uda_trainer import ProposedPrototypePseudoAdaptationMethod, UDATrainer
from tests.phase13_helpers import make_phase13_config, proposed_outputs_for_adaptation
from tests.test_cdan_trainer import _BatchLoader, _source_batch
from tests.test_proposed_method_trainer import make_proposed_epoch_trainer, proposed_target_batch


def test_proposed_target_adaptation_dataset_and_loader_expose_identity_only(tmp_path: Path):
    config = make_phase13_config(tmp_path)
    runner = PrototypePseudoExperimentRunner(config)

    prepared = runner._prepare_fold(0)
    source_train, target_adaptation, _source_validation, _target_evaluation = runner._loaders(prepared, seed=42)
    batch = next(iter(target_adaptation))

    assert set(prepared.target_adaptation_dataset[0]) == {"x", "subject_id", "subject_hash", "cohort"}
    assert set(batch) == {"x", "subject_id", "subject_hash", "cohort"}
    assert batch["x"].shape[0] >= 2
    assert len(source_train) > 0


@pytest.mark.parametrize("forbidden_key", ["y", "true_label", "diagnosis", "diagnosis_label", "c_target", "g_bar"])
def test_proposed_target_label_firewall_rejects_forbidden_batch_boundaries(forbidden_key: str):
    value = torch.zeros(2, dtype=torch.long) if forbidden_key not in {"true_label", "diagnosis"} else ["CN", "AD"]

    with pytest.raises(TrainingRuntimeError, match="forbidden label fields"):
        UDATrainer._validate_target_batch(proposed_target_batch(2.0, **{forbidden_key: value}))


def test_proposed_runner_validate_only_reports_target_labels_unavailable(tmp_path: Path):
    config = make_phase13_config(tmp_path)

    result = PrototypePseudoExperimentRunner(config).run_fold(0, 42, validate_only=True)

    assert result.metrics["validated"] is True
    assert result.metrics["target_training_labels_available"] is False
    assert "prototype_pseudo_loss" in result.metrics


def test_proposed_adaptation_loss_accepts_target_model_outputs_without_target_labels():
    source_output, target_output, labels_src = proposed_outputs_for_adaptation()
    method = ProposedPrototypePseudoAdaptationMethod(
        lambda_proto=1.0,
        lambda_pl=0.1,
        tau_p=0.5,
        proto_margin=1.0,
        lambda_sep=0.1,
        num_classes=3,
    )

    loss = method.compute(source_output, target_output, "full", labels_src=labels_src)

    assert torch.isfinite(loss.total)
    assert loss.diagnostics["accepted_count"].item() == 2.0
    assert "prototype_raw" in loss.components and "pseudo_label_raw" in loss.components


def test_proposed_trainer_stops_before_accessing_target_sentinel_labels():
    trainer, _model, _optimizer = make_proposed_epoch_trainer()

    class ExplodingTargetLabel:
        def to(self, *args, **kwargs):
            raise AssertionError("target label sentinel was moved into the training computation")

    with pytest.raises(TrainingRuntimeError, match="forbidden label fields"):
        trainer._train_epoch_for_stage(
            _BatchLoader([_source_batch(1.0)]),
            _BatchLoader([proposed_target_batch(2.0, y=ExplodingTargetLabel())]),
            "full",
        )
