"""Canonical hierarchical 3D CNN extracted from the training notebook."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as functional

from acda3d.exceptions import ModelContractError


class ResBlock3D(nn.Module):
    """Two-convolution residual block with GroupNorm and ReLU."""

    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        groups = min(8, out_channels)
        self.conv1 = nn.Conv3d(
            in_channels, out_channels, 3, stride=stride, padding=1, bias=False
        )
        self.gn1 = nn.GroupNorm(groups, out_channels)
        self.conv2 = nn.Conv3d(out_channels, out_channels, 3, padding=1, bias=False)
        self.gn2 = nn.GroupNorm(groups, out_channels)
        self.skip = (
            nn.Sequential(
                nn.Conv3d(in_channels, out_channels, 1, stride=stride, bias=False),
                nn.GroupNorm(groups, out_channels),
            )
            if in_channels != out_channels or stride != 1
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = functional.relu(self.gn1(self.conv1(x)), inplace=True)
        out = self.gn2(self.conv2(out))
        return functional.relu(out + self.skip(x), inplace=True)


class Encoder3D(nn.Module):
    """Encode ``(B,1,H,W,D)`` MRI tensors at one-eighth spatial resolution."""

    def __init__(self, feature_dim: int = 256, base_channels: int = 32):
        super().__init__()
        if feature_dim <= 0 or base_channels <= 0:
            raise ModelContractError("Encoder channel dimensions must be positive.")
        self.feature_dim = feature_dim
        self.stem = nn.Sequential(
            nn.Conv3d(1, base_channels, kernel_size=7, stride=2, padding=3, bias=False),
            nn.GroupNorm(min(8, base_channels), base_channels),
            nn.ReLU(inplace=True),
        )
        self.layer1 = self._make_layer(base_channels, base_channels * 2, stride=2)
        self.layer2 = self._make_layer(base_channels * 2, base_channels * 4, stride=2)
        self.layer3 = self._make_layer(base_channels * 4, feature_dim, stride=1)

    @staticmethod
    def _make_layer(in_channels: int, out_channels: int, stride: int) -> nn.Sequential:
        return nn.Sequential(
            ResBlock3D(in_channels, out_channels, stride=stride),
            ResBlock3D(out_channels, out_channels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 5:
            raise ModelContractError(f"MRI input must be 5D (B,1,H,W,D), got {tuple(x.shape)}.")
        if x.shape[1] != 1:
            raise ModelContractError(f"MRI input must have one channel, got {x.shape[1]}.")
        return self.layer3(self.layer2(self.layer1(self.stem(x))))

    @torch.no_grad()
    def infer_output_shape(self, input_shape: tuple[int, ...]) -> tuple[int, ...]:
        """Report output shape with a CPU synthetic input, preserving train/eval state."""
        if len(input_shape) != 5:
            raise ModelContractError("Encoder input shape must contain five dimensions.")
        parameter = next(self.parameters())
        was_training = self.training
        self.eval()
        try:
            output = self(torch.zeros(input_shape, dtype=parameter.dtype, device=parameter.device))
            return tuple(output.shape)
        finally:
            self.train(was_training)
