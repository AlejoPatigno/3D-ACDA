"""Independent target-adaptation and monitoring firewall checks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from acda3d.ablations import AblationResolutionError, validate_target_adaptation_batch
from acda3d.ablations.schemas import AssignmentManifest, sha256_payload
from acda3d.training.monitoring import TARGET_MONITORING_LABEL, evaluate_labeled_loader
from acda3d.training.uda_trainer import UDATrainer


@pytest.fixture
def target_batch() -> dict[str, object]:
    return {
        "x": torch.zeros(2, 1, 4, 4, 4),
        "subject_id": ["target-adapt-0", "target-adapt-1"],
        "subject_hash": ["hash-adapt-0", "hash-adapt-1"],
        "cohort": ["OASIS", "OASIS"],
    }


def test_target_adaptation_accepts_exactly_the_four_allowed_keys(
    target_batch: dict[str, object],
) -> None:
    validate_target_adaptation_batch(target_batch)
    UDATrainer._validate_target_batch(target_batch, strict=True)

    for missing in tuple(target_batch):
        incomplete = dict(target_batch)
        del incomplete[missing]
        with pytest.raises(AblationResolutionError, match="exactly"):
            validate_target_adaptation_batch(incomplete)
        with pytest.raises(Exception, match="missing|required|exactly"):
            UDATrainer._validate_target_batch(incomplete, strict=True)


def test_target_supervision_is_rejected_before_loss_computation(
    target_batch: dict[str, object],
) -> None:
    forbidden = (
        "y",
        "label",
        "label_name",
        "true_label",
        "c_target",
        "g_bar",
        "diagnosis",
        "stored_diagnostic_probabilities",
        "stored_diagnostic_probability",
        "diagnostic_probabilities",
        "target_diagnostic_probabilities",
        "concept_target",
        "concept_targets",
        "jacobian_target",
        "jacobian_targets",
        "supervision",
        "supervision_targets",
        "artifact",
    )
    for field in forbidden:
        contaminated = {**target_batch, field: torch.zeros(2)}
        loss_called = False

        def loss() -> None:
            nonlocal loss_called
            loss_called = True

        with pytest.raises(AblationResolutionError) as resolver_error:
            validate_target_adaptation_batch(contaminated)
        assert resolver_error.value.reason == "target_label_firewall_violation"
        assert not loss_called

        with pytest.raises(Exception, match="forbidden|unsupported"):
            UDATrainer._validate_target_batch(contaminated, strict=True)
        assert not loss_called


def test_unknown_target_artifact_field_is_rejected_instead_of_dropped(
    target_batch: dict[str, object],
) -> None:
    contaminated = {**target_batch, "jacobian_summary": torch.zeros(2)}
    with pytest.raises(AblationResolutionError) as error:
        validate_target_adaptation_batch(contaminated)
    assert error.value.reason == "target_label_firewall_violation"
    with pytest.raises(Exception, match="unsupported"):
        UDATrainer._validate_target_batch(contaminated, strict=True)


def test_target_adaptation_and_evaluation_assignments_are_disjoint() -> None:
    assignments = AssignmentManifest(
        source=("source-0",),
        target_adaptation=("target-adapt-0",),
        target_evaluation=("target-eval-0",),
    )
    assert set(assignments.target_adaptation).isdisjoint(assignments.target_evaluation)
    assert assignments.to_dict()["target_adaptation"] != assignments.to_dict()["target_evaluation"]
    assert sha256_payload(assignments.target_adaptation) != sha256_payload(assignments.target_evaluation)
    with pytest.raises(ValueError, match="overlap"):
        AssignmentManifest(
            source=("source-0",),
            target_adaptation=("target-0",),
            target_evaluation=("target-0",),
        )


def test_target_monitoring_is_namespaced_no_grad_and_observational() -> None:
    class MonitoringModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.scale = nn.Parameter(torch.tensor(1.0))

        def forward(self, x: torch.Tensor, _roi_masks: torch.Tensor) -> object:
            logits = torch.stack(
                (
                    self.scale.expand(x.shape[0]),
                    torch.zeros(x.shape[0]),
                    torch.zeros(x.shape[0]),
                ),
                dim=1,
            )
            return SimpleNamespace(concept_probabilities=torch.softmax(logits, dim=-1))

    model = MonitoringModel()
    before = model.scale.detach().clone()
    metrics = evaluate_labeled_loader(
        model,
        [{"x": torch.zeros(2, 1), "y": torch.tensor([0, 0])}],
        torch.zeros(1),
        torch.device("cpu"),
        namespace="target_monitoring",
    )
    assert metrics["target_monitoring/label"] == TARGET_MONITORING_LABEL
    assert model.scale.grad is None
    assert torch.equal(model.scale.detach(), before)
    assert not any(key.startswith("train/") for key in metrics)
