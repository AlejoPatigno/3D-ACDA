import pytest
import torch

from pada3dacb.exceptions import LossContractError
from pada3dacb.losses import AnatomicalConsistencyLoss


def test_anatomical_exact_weighted_mean_and_gradient():
    concepts = torch.tensor([[0.0, 1.0]], requires_grad=True)
    g_bar = torch.tensor([[1.0, 0.0]])
    weights = torch.tensor([0.25, 0.75])
    actual = AnatomicalConsistencyLoss(2, weights)(concepts, g_bar)
    expected = (((concepts - g_bar) ** 2) * weights.unsqueeze(0)).mean()
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    actual.backward()
    assert torch.isfinite(concepts.grad).all()


def test_anatomical_rejects_nonfinite_gbar():
    with pytest.raises(LossContractError, match="finite"):
        AnatomicalConsistencyLoss(2)(torch.ones(1, 2), torch.tensor([[0.0, float("nan")]]))
