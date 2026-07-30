"""Deep CORAL covariance alignment on the PADA-3DACB subject embedding."""

from __future__ import annotations

import torch

from pada3dacb.adaptation.outputs import AdaptationLossOutput
from pada3dacb.exceptions import LossContractError
from pada3dacb.models import PADA3DACBOutput


def _validate_features(features: torch.Tensor, name: str) -> None:
    if not torch.is_tensor(features) or features.ndim != 2:
        shape = tuple(features.shape) if torch.is_tensor(features) else type(features).__name__
        raise LossContractError(f"{name} must be rank 2, got {shape}.")
    if features.shape[0] < 2:
        raise LossContractError(f"{name} requires at least two samples for covariance.")
    if not features.is_floating_point():
        raise LossContractError(f"{name} must use a floating-point dtype.")
    if not torch.isfinite(features).all():
        raise LossContractError(f"{name} must contain only finite values.")


def covariance_matrix(features: torch.Tensor) -> torch.Tensor:
    """Return the unbiased covariance matrix, always computed in float32."""
    _validate_features(features, "features")
    with torch.autocast(device_type=features.device.type, enabled=False):
        stable = features.float()
        centered = stable - stable.mean(dim=0, keepdim=True)
        return centered.transpose(0, 1).matmul(centered) / (stable.shape[0] - 1)


def coral_loss(source_features: torch.Tensor, target_features: torch.Tensor) -> torch.Tensor:
    """Compute ||C_s-C_t||_F^2 / (4 d^2) without mean alignment."""
    _validate_features(source_features, "source_features")
    _validate_features(target_features, "target_features")
    if source_features.shape[1] != target_features.shape[1]:
        raise LossContractError("Source and target CORAL feature dimensions must match.")
    if source_features.device != target_features.device:
        raise LossContractError("Source and target CORAL features must share a device.")
    source_covariance = covariance_matrix(source_features)
    target_covariance = covariance_matrix(target_features)
    feature_dim = source_features.shape[1]
    loss = (source_covariance - target_covariance).square().sum() / (4 * feature_dim**2)
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise LossContractError("CORAL loss must be a finite scalar.")
    return loss


class CORALAdaptationMethod:
    """Align only the shared subject embedding ``z`` during the full stage."""

    name = "coral"
    feature = "z"

    def compute(
        self,
        source_output: PADA3DACBOutput,
        target_output: PADA3DACBOutput,
        stage: str,
    ) -> AdaptationLossOutput:
        if stage not in {"warm", "full"}:
            raise LossContractError(f"stage must be 'warm' or 'full', got {stage!r}.")
        source_z = source_output.z
        target_z = target_output.z
        if stage == "warm":
            zero = source_z.float().sum() * 0.0
            return AdaptationLossOutput(total=zero, components={"coral": zero}, diagnostics={})
        source_covariance = covariance_matrix(source_z)
        target_covariance = covariance_matrix(target_z)
        difference = source_covariance - target_covariance
        loss = coral_loss(source_z, target_z)
        return AdaptationLossOutput(
            total=loss,
            components={"coral": loss},
            diagnostics={
                "source_embedding_mean_norm": source_z.float().mean(0).norm(),
                "target_embedding_mean_norm": target_z.float().mean(0).norm(),
                "source_covariance_frobenius": source_covariance.norm(),
                "target_covariance_frobenius": target_covariance.norm(),
                "covariance_difference_frobenius": difference.norm(),
            },
        )
