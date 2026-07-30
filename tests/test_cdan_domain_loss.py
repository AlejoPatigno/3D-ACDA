from types import SimpleNamespace

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from pada3dacb.adaptation.cdan import CDANAdaptationMethod
from pada3dacb.exceptions import LossContractError


class QueueDiscriminator(nn.Module):
    def __init__(self, input_dimension: int, outputs: tuple[torch.Tensor, ...]):
        super().__init__()
        self.input_dimension = input_dimension
        self._outputs = list(outputs)
        self.seen_inputs: list[torch.Tensor] = []

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        self.seen_inputs.append(values)
        return self._outputs.pop(0).to(values)


class LinearDiscriminator(nn.Module):
    def __init__(self, input_dimension: int):
        super().__init__()
        self.input_dimension = input_dimension
        self.projection = nn.Linear(input_dimension, 1, bias=False)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.projection(values).squeeze(-1)


def _output(z: torch.Tensor, probabilities: torch.Tensor) -> SimpleNamespace:
    return SimpleNamespace(z=z, latent_probabilities=probabilities)


def test_cdan_domain_loss_uses_internal_labels_and_exact_concatenated_mean_bce_for_unequal_batches():
    source_logits = torch.tensor([-2.0, 0.25])
    target_logits = torch.tensor([-0.5, 1.5, 3.0])
    discriminator = QueueDiscriminator(input_dimension=6, outputs=(source_logits, target_logits))
    method = CDANAdaptationMethod(discriminator, grl_coefficient=1.0)
    source = _output(
        torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        torch.tensor([[0.2, 0.3, 0.5], [0.1, 0.6, 0.3]]),
    )
    target = _output(
        torch.tensor([[5.0, 6.0], [7.0, 8.0], [9.0, 10.0]]),
        torch.tensor([[0.4, 0.4, 0.2], [0.7, 0.2, 0.1], [0.25, 0.25, 0.5]]),
    )

    output = method.compute(source, target, "full")

    concatenated_logits = torch.cat((source_logits, target_logits))
    internal_domain_labels = torch.tensor([0.0, 0.0, 1.0, 1.0, 1.0])
    expected = F.binary_cross_entropy_with_logits(concatenated_logits, internal_domain_labels, reduction="mean")
    assert output.total.ndim == 0
    assert torch.equal(output.total, expected)
    assert torch.equal(output.components["cdan"], expected)
    assert len(discriminator.seen_inputs) == 2
    assert discriminator.seen_inputs[0].shape == (2, 6)
    assert discriminator.seen_inputs[1].shape == (3, 6)


def test_cdan_domain_loss_does_not_apply_sigmoid_class_weighting_entropy_weighting_or_pseudo_labels():
    source_logits = torch.tensor([0.0])
    target_logits = torch.tensor([0.0, 0.0, 0.0])
    method = CDANAdaptationMethod(QueueDiscriminator(6, (source_logits, target_logits)), grl_coefficient=1.0)
    source = _output(torch.ones(1, 2), torch.tensor([[0.9, 0.05, 0.05]]))
    target = _output(torch.ones(3, 2), torch.tensor([[1.0, 0.0, 0.0], [0.34, 0.33, 0.33], [0.0, 0.0, 1.0]]))

    output = method.compute(source, target, "full")

    exact_unweighted_bce_at_zero_logit = torch.tensor(0.6931471824645996)
    assert torch.allclose(output.total, exact_unweighted_bce_at_zero_logit)
    assert "entropy" not in output.diagnostics
    assert "pseudo" not in output.diagnostics


def test_cdan_validates_discriminator_dimension_before_training():
    method = CDANAdaptationMethod(QueueDiscriminator(input_dimension=7, outputs=(torch.zeros(1), torch.zeros(1))), 1.0)
    source = _output(torch.ones(1, 2), torch.tensor([[1.0, 0.0, 0.0]]))
    target = _output(torch.ones(1, 2), torch.tensor([[0.0, 1.0, 0.0]]))

    with pytest.raises(LossContractError, match="dimension"):
        method.compute(source, target, "full")


def test_cdan_domain_loss_backpropagates_to_source_target_features_probabilities_and_discriminator():
    source_z = torch.tensor([[1.0, -2.0]], requires_grad=True)
    source_p = torch.tensor([[0.2, 0.3, 0.5]], requires_grad=True)
    target_z = torch.tensor([[0.5, 1.5]], requires_grad=True)
    target_p = torch.tensor([[0.1, 0.7, 0.2]], requires_grad=True)
    discriminator = LinearDiscriminator(input_dimension=6)
    method = CDANAdaptationMethod(discriminator, grl_coefficient=0.5)

    output = method.compute(_output(source_z, source_p), _output(target_z, target_p), "full")
    output.total.backward()

    assert source_z.grad is not None and torch.count_nonzero(source_z.grad) > 0
    assert source_p.grad is not None and torch.count_nonzero(source_p.grad) > 0
    assert target_z.grad is not None and torch.count_nonzero(target_z.grad) > 0
    assert target_p.grad is not None and torch.count_nonzero(target_p.grad) > 0
    assert discriminator.projection.weight.grad is not None
    assert torch.count_nonzero(discriminator.projection.weight.grad) > 0


def test_cdan_warm_stage_has_zero_loss_and_does_not_call_discriminator():
    method = CDANAdaptationMethod(QueueDiscriminator(input_dimension=6, outputs=()), grl_coefficient=1.0)
    source = _output(torch.ones(1, 2, requires_grad=True), torch.tensor([[1.0, 0.0, 0.0]], requires_grad=True))
    target = _output(torch.ones(1, 2, requires_grad=True), torch.tensor([[0.0, 1.0, 0.0]], requires_grad=True))

    output = method.compute(source, target, "warm")

    assert output.total.item() == 0.0
    assert output.components["cdan"].item() == 0.0
    assert method.discriminator.seen_inputs == []
