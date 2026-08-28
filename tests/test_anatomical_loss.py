import pytest
import torch

from acda3d.exceptions import LossContractError
from acda3d.losses import AnatomicalConsistencyLoss


def test_anatomical_exact_weighted_mse_no_extra_K_division():
    """L_anat = sum(w_k * r^2) / (B * sum(w)). For sum(w)=1 this is (1/B) * sum(w*r^2)."""
    concepts = torch.tensor([[0.0, 1.0]], requires_grad=True)
    g_bar = torch.tensor([[1.0, 0.0]])
    weights = torch.tensor([0.25, 0.75])
    actual = AnatomicalConsistencyLoss(2, weights)(concepts, g_bar)
    # residuals = [[1,1]], weighted = [[0.25, 0.75]], sum = 1.0
    # B=1, weight_sum=1.0 → 1.0 / (1 * 1.0) = 1.0
    expected = torch.tensor(1.0)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    actual.backward()
    assert torch.isfinite(concepts.grad).all()


def test_anatomical_rejects_nonfinite_gbar():
    with pytest.raises(LossContractError, match="finite"):
        AnatomicalConsistencyLoss(2)(torch.ones(1, 2), torch.tensor([[0.0, float("nan")]]))


def test_anatomical_rejects_zero_weight_sum():
    with pytest.raises(LossContractError, match="positive sum"):
        AnatomicalConsistencyLoss(2, torch.zeros(2))(torch.ones(1, 2), torch.ones(1, 2))


def test_anatomical_no_roi_dependency():
    """L_anat should not depend on K when residuals and weights are constant per ROI."""
    for K in [2, 5, 10, 20]:
        weights = torch.ones(K) / K
        loss_fn = AnatomicalConsistencyLoss(K, weights)
        B = 3
        # Constant residual: each ROI has squared error = 0.25
        concepts = torch.full((B, K), 0.5)
        g_bar = torch.full((B, K), 0.0)
        loss = loss_fn(concepts, g_bar)
        # Expected: sum(1/K * 0.25) / (B * 1) = B * 0.25 / B = 0.25
        torch.testing.assert_close(loss, torch.tensor(0.25), rtol=1e-5, atol=1e-6)
