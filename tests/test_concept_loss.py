import pytest
import torch
from torch.nn import functional as functional

from acda3d.exceptions import LossContractError
from acda3d.losses import ConceptSupervisionLoss


def test_concept_loss_is_mean_mse_for_constant_targets():
    concepts = torch.tensor([[0.2, 0.8], [0.5, 0.5]], requires_grad=True)
    targets = torch.full((2, 2), 0.5)
    actual = ConceptSupervisionLoss()(concepts, targets)
    torch.testing.assert_close(actual, functional.mse_loss(concepts, targets), rtol=0, atol=0)
    actual.backward()
    assert torch.isfinite(concepts.grad).all()


def test_concept_loss_rejects_roi_mismatch():
    with pytest.raises(LossContractError, match="identical shapes"):
        ConceptSupervisionLoss()(torch.ones(2, 3), torch.ones(2, 2))
