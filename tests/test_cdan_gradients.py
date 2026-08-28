import torch

from acda3d.adaptation import (
    CDANAdaptationMethod,
    DomainDiscriminator,
    DomainDiscriminatorConfig,
)
from tests.phase8_helpers import TinyACDA3D


def test_cdan_domain_loss_reaches_encoder_and_latent_classifier():
    model = TinyACDA3D()
    masks = torch.ones(2, 1, 1, 1)
    source, target = model(torch.ones(2, 1, 2, 2, 2), masks), model(torch.zeros(2, 1, 2, 2, 2), masks)
    method = CDANAdaptationMethod(DomainDiscriminator(DomainDiscriminatorConfig(12, (4,), "relu", 0.0)), 1.0)
    method.compute(source, target, "full").total.backward()
    assert model.encoder.weight.grad is not None
    assert model.latent.weight.grad is not None
    assert next(method.discriminator.parameters()).grad is not None
