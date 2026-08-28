import pytest
import torch

from acda3d.adaptation.gradient_reversal import GradientReversal, gradient_reverse
from acda3d.exceptions import LossContractError


def test_gradient_reversal_keeps_forward_values_and_negates_scaled_gradient():
    value = torch.tensor([1.0, -2.0], requires_grad=True)
    result = gradient_reverse(value, 0.25)
    assert torch.equal(result, value)
    result.sum().backward()
    assert torch.equal(value.grad, torch.tensor([-0.25, -0.25]))


def test_gradient_reversal_zero_coefficient_blocks_input_gradient():
    value = torch.tensor([1.0, -2.0], requires_grad=True)
    result = gradient_reverse(value, 0.0)
    result.sum().backward()
    assert torch.equal(value.grad, torch.zeros_like(value))


@pytest.mark.parametrize("coefficient", [None, -1.0, float("nan"), float("inf"), lambda step: 1.0, "linear"])
def test_gradient_reversal_rejects_invalid_or_scheduled_coefficient(coefficient):
    with pytest.raises(LossContractError):
        gradient_reverse(torch.ones(2), coefficient)  # type: ignore[arg-type]


@pytest.mark.parametrize("coefficient", [None, -1.0, float("nan"), float("inf"), lambda step: 1.0, "linear"])
def test_gradient_reversal_module_rejects_invalid_or_scheduled_coefficient_at_construction(coefficient):
    with pytest.raises(LossContractError):
        GradientReversal(coefficient)  # type: ignore[arg-type]


def test_gradient_reversal_module_keeps_constant_coefficient_without_schedule_state():
    layer = GradientReversal(0.5)
    assert layer.coefficient == 0.5
    assert "step" not in layer.state_dict()
    assert "coefficient" not in layer.state_dict()

    first = torch.tensor([1.0], requires_grad=True)
    second = torch.tensor([1.0], requires_grad=True)
    layer(first).sum().backward()
    layer(second).sum().backward()
    assert torch.equal(first.grad, torch.tensor([-0.5]))
    assert torch.equal(second.grad, torch.tensor([-0.5]))


def test_gradient_reversal_does_not_reverse_downstream_discriminator_parameter_gradients():
    discriminator = torch.nn.Linear(2, 1, bias=False)
    discriminator.weight.data.copy_(torch.tensor([[2.0, -3.0]]))
    features = torch.tensor([[1.0, 4.0]], requires_grad=True)

    discriminator(gradient_reverse(features, 0.25)).sum().backward()

    assert torch.equal(features.grad, torch.tensor([[-0.5, 0.75]]))
    assert torch.equal(discriminator.weight.grad, torch.tensor([[1.0, 4.0]]))
