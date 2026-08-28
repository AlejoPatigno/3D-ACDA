"""Biased multi-bandwidth Gaussian-kernel MMD on subject embeddings."""

from __future__ import annotations

import math
from collections.abc import Sequence

import torch

from acda3d.adaptation.outputs import AdaptationLossOutput
from acda3d.exceptions import LossContractError
from acda3d.models import ACDA3DOutput


def _validate_features(features: torch.Tensor, name: str) -> None:
    if not torch.is_tensor(features) or features.ndim != 2:
        shape = tuple(features.shape) if torch.is_tensor(features) else type(features).__name__
        raise LossContractError(f"{name} must be rank 2, got {shape}.")
    if not features.is_floating_point():
        raise LossContractError(f"{name} must use a floating-point dtype.")
    if not torch.isfinite(features).all():
        raise LossContractError(f"{name} must contain only finite values.")


def validate_bandwidths(bandwidths: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in bandwidths)
    if not values:
        raise LossContractError("MMD requires at least one explicit bandwidth.")
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise LossContractError("Every MMD bandwidth must be finite and strictly positive.")
    if len(set(values)) != len(values):
        raise LossContractError("Duplicate MMD bandwidths are not permitted.")
    return values


def pairwise_squared_distances(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """Compute stable squared Euclidean distances in float32."""
    _validate_features(x, "x")
    _validate_features(y, "y")
    if x.shape[1] != y.shape[1]:
        raise LossContractError("Pairwise feature dimensions must match.")
    if x.device != y.device:
        raise LossContractError("Pairwise features must share a device.")
    with torch.autocast(device_type=x.device.type, enabled=False):
        x32 = x.float()
        y32 = y.float()
        distances = (
            x32.square().sum(dim=1, keepdim=True)
            + y32.square().sum(dim=1).unsqueeze(0)
            - 2.0 * x32.matmul(y32.transpose(0, 1))
        )
        distances = distances.clamp_min(0.0)
    if not torch.isfinite(distances).all():
        raise LossContractError("Pairwise squared distances must be finite.")
    return distances


def gaussian_rbf_kernel_matrix(
    x: torch.Tensor,
    y: torch.Tensor,
    bandwidths: Sequence[float],
) -> torch.Tensor:
    """Arithmetic mean of Gaussian RBF kernels for declared bandwidths."""
    values = validate_bandwidths(bandwidths)
    distances = pairwise_squared_distances(x, y)
    with torch.autocast(device_type=x.device.type, enabled=False):
        kernels = [torch.exp(-distances / (2.0 * sigma**2)) for sigma in values]
        result = torch.stack(kernels, dim=0).mean(dim=0)
    if not torch.isfinite(result).all() or (result < 0).any() or (result > 1.0 + 1e-6).any():
        raise LossContractError("Gaussian RBF kernel values must be finite and within [0, 1].")
    return result


def _mmd_components(
    source_features: torch.Tensor,
    target_features: torch.Tensor,
    bandwidths: Sequence[float],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    _validate_features(source_features, "source_features")
    _validate_features(target_features, "target_features")
    if source_features.shape[0] < 2 or target_features.shape[0] < 2:
        raise LossContractError("MMD source and target batches require at least two samples.")
    if source_features.shape[1] != target_features.shape[1]:
        raise LossContractError("Source and target MMD feature dimensions must match.")
    if source_features.device != target_features.device:
        raise LossContractError("Source and target MMD features must share a device.")
    validate_bandwidths(bandwidths)
    return (
        gaussian_rbf_kernel_matrix(source_features, source_features, bandwidths),
        gaussian_rbf_kernel_matrix(target_features, target_features, bandwidths),
        gaussian_rbf_kernel_matrix(source_features, target_features, bandwidths),
    )


def mmd_loss(
    source_features: torch.Tensor,
    target_features: torch.Tensor,
    bandwidths: Sequence[float],
) -> torch.Tensor:
    """Biased squared MMD including diagonal self-kernel entries."""
    source_kernel, target_kernel, cross_kernel = _mmd_components(
        source_features, target_features, bandwidths
    )
    loss = source_kernel.mean() + target_kernel.mean() - 2.0 * cross_kernel.mean()
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise LossContractError("MMD loss must be a finite scalar.")
    return loss


class MMDAdaptationMethod:
    """Align distributions of the shared subject embedding ``z``."""

    name = "mmd"
    feature = "z"

    def __init__(self, bandwidths: Sequence[float]):
        self.bandwidths = validate_bandwidths(bandwidths)

    def compute(
        self,
        source_output: ACDA3DOutput,
        target_output: ACDA3DOutput,
        stage: str,
    ) -> AdaptationLossOutput:
        if stage not in {"warm", "full"}:
            raise LossContractError(f"stage must be 'warm' or 'full', got {stage!r}.")
        source_z = source_output.z
        target_z = target_output.z
        if stage == "warm":
            zero = source_z.float().sum() * 0.0
            return AdaptationLossOutput(total=zero, components={"mmd": zero}, diagnostics={})
        source_kernel, target_kernel, cross_kernel = _mmd_components(
            source_z, target_z, self.bandwidths
        )
        loss = source_kernel.mean() + target_kernel.mean() - 2.0 * cross_kernel.mean()
        if loss.ndim != 0 or not torch.isfinite(loss):
            raise LossContractError("MMD loss must be a finite scalar.")
        source_mean = source_z.float().mean(0)
        target_mean = target_z.float().mean(0)
        return AdaptationLossOutput(
            total=loss,
            components={"mmd": loss},
            diagnostics={
                "source_kernel_mean": source_kernel.mean(),
                "target_kernel_mean": target_kernel.mean(),
                "cross_kernel_mean": cross_kernel.mean(),
                "source_embedding_mean_norm": source_mean.norm(),
                "target_embedding_mean_norm": target_mean.norm(),
                "source_target_mean_distance": (source_mean - target_mean).norm(),
                "minimum_bandwidth": source_z.new_tensor(min(self.bandwidths)).float(),
                "maximum_bandwidth": source_z.new_tensor(max(self.bandwidths)).float(),
                "number_of_bandwidths": source_z.new_tensor(len(self.bandwidths)).float(),
            },
        )
