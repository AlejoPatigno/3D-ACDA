import pytest
import torch

from pada3dacb.adaptation import CORALAdaptationMethod, coral_loss, covariance_matrix
from pada3dacb.exceptions import LossContractError
from tests.phase8_helpers import TinyPADA3DACB


def test_coral_matches_direct_equation_and_unbiased_covariance():
    source = torch.tensor([[1.0, 2.0], [3.0, 5.0], [6.0, 8.0]], requires_grad=True)
    target = torch.tensor([[2.0, 1.0], [4.0, 7.0], [8.0, 3.0]], requires_grad=True)
    centered = source - source.mean(0)
    expected_covariance = centered.T @ centered / (source.shape[0] - 1)
    torch.testing.assert_close(covariance_matrix(source), expected_covariance)
    target_centered = target - target.mean(0)
    target_covariance = target_centered.T @ target_centered / (target.shape[0] - 1)
    expected = (expected_covariance - target_covariance).square().sum() / (4 * 2**2)
    actual = coral_loss(source, target)
    torch.testing.assert_close(actual, expected)
    assert actual.ndim == 0 and torch.isfinite(actual) and actual > 0
    actual.backward()
    assert torch.isfinite(source.grad).all() and torch.isfinite(target.grad).all()


def test_coral_ignores_mean_shift_and_computes_float32():
    features = torch.tensor([[1.0, 2.0], [2.0, 4.0], [4.0, 1.0]], dtype=torch.float64)
    result = coral_loss(features, features + 20)
    assert result.dtype == torch.float32
    torch.testing.assert_close(result, torch.tensor(0.0), atol=1e-12, rtol=0)


def test_coral_reaches_shared_encoder_and_stays_float32_under_cpu_autocast():
    model = TinyPADA3DACB()
    source = torch.rand(2, 1, 2, 2, 2)
    target = torch.rand(2, 1, 2, 2, 2) * 2
    masks = torch.ones(2, 1, 1, 1)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        output = CORALAdaptationMethod().compute(
            model(source, masks), model(target, masks), "full"
        )
    assert output.total.dtype == torch.float32
    output.total.backward()
    assert model.encoder.weight.grad is not None
    assert torch.isfinite(model.encoder.weight.grad).all()


@pytest.mark.parametrize("features", [torch.ones(1, 3), torch.ones(2, 3, dtype=torch.long)])
def test_covariance_rejects_invalid_inputs(features):
    with pytest.raises(LossContractError):
        covariance_matrix(features)
