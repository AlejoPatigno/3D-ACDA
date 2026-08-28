import pytest
import torch
from torch import nn

from acda3d.adaptation.domain_discriminator import DomainDiscriminator, DomainDiscriminatorConfig
from acda3d.exceptions import ConfigurationError, LossContractError


def test_domain_discriminator_returns_one_raw_logit_per_sample_without_sigmoid():
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(6, (5, 4), "relu", 0.0))
    with torch.no_grad():
        final_linear = next(module for module in reversed(discriminator.network) if isinstance(module, nn.Linear))
        final_linear.weight.zero_()
        final_linear.bias.fill_(2.0)

    logits = discriminator(torch.randn(3, 6))

    assert logits.shape == (3,)
    assert torch.equal(logits, torch.full((3,), 2.0))
    assert not any(isinstance(module, nn.Sigmoid) for module in discriminator.modules())


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (DomainDiscriminatorConfig(0, (4,), "relu", 0.0), "positive input"),
        (DomainDiscriminatorConfig(6, (), "relu", 0.0), "positive input and hidden"),
        (DomainDiscriminatorConfig(6, (4,), "tanh", 0.0), "activation"),
        (DomainDiscriminatorConfig(6, (4,), "relu", -0.1), "dropout"),
        (DomainDiscriminatorConfig(6, (4,), "relu", 1.0), "dropout"),
        (DomainDiscriminatorConfig(6, (4,), "relu", 0.0, output_dim=2), "output_dim=1"),
    ],
)
def test_domain_discriminator_rejects_invalid_configuration(config, message):
    with pytest.raises(ConfigurationError, match=message):
        config.validate()


def test_domain_discriminator_rejects_missing_hidden_dimensions_as_configuration_error():
    with pytest.raises(ConfigurationError, match="hidden dimensions"):
        DomainDiscriminatorConfig(6, None, "relu", 0.0).validate()


@pytest.mark.parametrize(
    ("activation", "module_type"),
    [("relu", nn.ReLU), ("gelu", nn.GELU), ("leaky_relu", nn.LeakyReLU)],
)
def test_domain_discriminator_supports_explicit_activation_choices(activation, module_type):
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(6, (5,), activation, 0.0))

    assert any(isinstance(module, module_type) for module in discriminator.network)


def test_domain_discriminator_rejects_invalid_conditional_features_shape_and_values():
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(6, (5,), "relu", 0.0))

    with pytest.raises(LossContractError, match="input shape"):
        discriminator(torch.randn(2, 5))
    with pytest.raises(LossContractError, match="finite floating-point"):
        discriminator(torch.tensor([[float("nan")] * 6]))


def test_domain_discriminator_has_no_batch_norm_or_spectral_norm():
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(6, (5, 4), "relu", 0.2))

    assert not any(isinstance(module, nn.modules.batchnorm._BatchNorm) for module in discriminator.modules())
    assert not any(hasattr(module, "weight_orig") for module in discriminator.modules())


def test_domain_discriminator_initialization_is_deterministic_under_torch_seed():
    torch.manual_seed(1234)
    first = DomainDiscriminator(DomainDiscriminatorConfig(6, (5, 4), "relu", 0.0))
    first_parameters = [parameter.detach().clone() for parameter in first.parameters()]

    torch.manual_seed(1234)
    second = DomainDiscriminator(DomainDiscriminatorConfig(6, (5, 4), "relu", 0.0))

    for first_parameter, second_parameter in zip(first_parameters, second.parameters(), strict=True):
        assert torch.equal(first_parameter, second_parameter)


def test_domain_discriminator_parameter_and_input_gradients_are_not_reversed():
    discriminator = DomainDiscriminator(DomainDiscriminatorConfig(2, (2,), "relu", 0.0))
    with torch.no_grad():
        first_linear = discriminator.network[0]
        final_linear = discriminator.network[-1]
        first_linear.weight.copy_(torch.eye(2))
        first_linear.bias.zero_()
        final_linear.weight.fill_(1.0)
        final_linear.bias.zero_()
    conditional_features = torch.tensor([[1.0, 2.0]], requires_grad=True)

    discriminator(conditional_features).sum().backward()

    assert torch.equal(conditional_features.grad, torch.ones_like(conditional_features))
    assert torch.equal(discriminator.network[0].weight.grad, torch.tensor([[1.0, 2.0], [1.0, 2.0]]))
    assert torch.equal(discriminator.network[-1].weight.grad, torch.tensor([[1.0, 2.0]]))
