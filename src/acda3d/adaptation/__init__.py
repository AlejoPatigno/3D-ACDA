"""Approved domain-adaptation methods."""

from acda3d.adaptation.base import AdaptationMethod
from acda3d.adaptation.cdan import CDANAdaptationMethod, conditional_outer_product
from acda3d.adaptation.coral import CORALAdaptationMethod, coral_loss, covariance_matrix
from acda3d.adaptation.domain_discriminator import DomainDiscriminator, DomainDiscriminatorConfig
from acda3d.adaptation.gradient_reversal import GradientReversal, gradient_reverse
from acda3d.adaptation.mmd import (
    MMDAdaptationMethod,
    gaussian_rbf_kernel_matrix,
    mmd_loss,
    pairwise_squared_distances,
    validate_bandwidths,
)
from acda3d.adaptation.outputs import AdaptationLossOutput

__all__ = [
    "AdaptationLossOutput", "AdaptationMethod", "CDANAdaptationMethod",
    "CORALAdaptationMethod", "DomainDiscriminator", "DomainDiscriminatorConfig",
    "GradientReversal", "MMDAdaptationMethod", "conditional_outer_product",
    "coral_loss", "covariance_matrix", "gaussian_rbf_kernel_matrix",
    "gradient_reverse", "mmd_loss", "pairwise_squared_distances", "validate_bandwidths",
]