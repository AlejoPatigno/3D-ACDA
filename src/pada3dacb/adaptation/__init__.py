"""Approved domain-adaptation methods."""

from pada3dacb.adaptation.base import AdaptationMethod
from pada3dacb.adaptation.cdan import CDANAdaptationMethod, conditional_outer_product
from pada3dacb.adaptation.coral import CORALAdaptationMethod, coral_loss, covariance_matrix
from pada3dacb.adaptation.domain_discriminator import DomainDiscriminator, DomainDiscriminatorConfig
from pada3dacb.adaptation.gradient_reversal import GradientReversal, gradient_reverse
from pada3dacb.adaptation.mmd import (
    MMDAdaptationMethod,
    gaussian_rbf_kernel_matrix,
    mmd_loss,
    pairwise_squared_distances,
    validate_bandwidths,
)
from pada3dacb.adaptation.outputs import AdaptationLossOutput

__all__ = [
    "AdaptationLossOutput", "AdaptationMethod", "CDANAdaptationMethod",
    "CORALAdaptationMethod", "DomainDiscriminator", "DomainDiscriminatorConfig",
    "GradientReversal", "MMDAdaptationMethod", "conditional_outer_product",
    "coral_loss", "covariance_matrix", "gaussian_rbf_kernel_matrix",
    "gradient_reverse", "mmd_loss", "pairwise_squared_distances", "validate_bandwidths",
]