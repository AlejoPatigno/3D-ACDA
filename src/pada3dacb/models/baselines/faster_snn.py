"""Notebook-faithful FasterSNN surrogate 3D classifier."""

from __future__ import annotations

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from pada3dacb.models.baselines.common import validate_baseline_output, validate_mri_input

_MIN_SPATIAL_SIZE = 17


class SurrogateSpikeFn(torch.autograd.Function):
    """Binary forward spike with the notebook's smooth surrogate gradient."""

    @staticmethod
    def forward(ctx: object, x: Tensor) -> Tensor:
        ctx.save_for_backward(x)  # type: ignore[attr-defined]
        return (x > 0).float()

    @staticmethod
    def backward(ctx: object, grad_output: Tensor) -> Tensor:
        (x,) = ctx.saved_tensors  # type: ignore[attr-defined]
        return grad_output * (1.0 / (1.0 + x.abs()).pow(2))


class SpikeAct(nn.Module):
    """Module wrapper for the local surrogate spike function."""

    def forward(self, x: Tensor) -> Tensor:
        return SurrogateSpikeFn.apply(x)


class FasterSNNBaseline(nn.Module):
    """Four-block spiking-style 3D surrogate from the participating notebook."""

    def __init__(
        self,
        n_classes: int = 3,
        base_ch: int = 24,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if n_classes <= 0 or base_ch <= 0:
            raise ValueError("class and channel counts must be positive")
        if not 0.0 <= dropout <= 1.0:
            raise ValueError("dropout must be between zero and one")

        self.features = nn.Sequential(
            nn.Conv3d(1, base_ch, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch, affine=True),
            SpikeAct(),
            nn.Conv3d(base_ch, base_ch * 2, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch * 2, affine=True),
            SpikeAct(),
            nn.Conv3d(base_ch * 2, base_ch * 4, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch * 4, affine=True),
            SpikeAct(),
            nn.Conv3d(base_ch * 4, base_ch * 8, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch * 8, affine=True),
            SpikeAct(),
        )
        self.cls = nn.Linear(base_ch * 8, n_classes)
        self.n_classes = n_classes

    def forward(self, x: Tensor) -> dict[str, Tensor]:
        x = validate_mri_input(x)
        if any(size < _MIN_SPATIAL_SIZE for size in x.shape[-3:]):
            raise ValueError("MRI spatial dimensions must each be at least 17")
        feature_map = self.features(x)
        features = F.adaptive_avg_pool3d(feature_map, 1).flatten(1)
        output = {"logits": self.cls(features), "features": features}
        validate_baseline_output(output, batch_size=x.shape[0], output_classes=self.n_classes)
        return output
