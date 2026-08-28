"""Notebook-faithful AAGN-style ROI-aware gating classifier."""

from __future__ import annotations

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from acda3d.models.baselines.common import validate_baseline_output, validate_mri_input


class _ConvNormAct3D(nn.Module):
    def __init__(
        self, in_ch: int, out_ch: int, kernel: int = 3, stride: int = 1
    ) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv3d(
                in_ch,
                out_ch,
                kernel_size=kernel,
                stride=stride,
                padding=kernel // 2,
                bias=False,
            ),
            nn.InstanceNorm3d(out_ch, affine=True),
            nn.GELU(),
        )

    def forward(self, x: Tensor) -> Tensor:
        return self.block(x)


class _ResidualBlock3D(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, stride: int = 1) -> None:
        super().__init__()
        self.conv1 = _ConvNormAct3D(in_ch, out_ch, stride=stride)
        self.conv2 = nn.Sequential(
            nn.Conv3d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm3d(out_ch, affine=True),
        )
        self.act = nn.GELU()
        self.skip = (
            nn.Sequential(
                nn.Conv3d(in_ch, out_ch, kernel_size=1, stride=stride, bias=False),
                nn.InstanceNorm3d(out_ch, affine=True),
            )
            if in_ch != out_ch or stride != 1
            else None
        )

    def forward(self, x: Tensor) -> Tensor:
        identity = x if self.skip is None else self.skip(x)
        return self.act(self.conv2(self.conv1(x)) + identity)


class _Small3DBackbone(nn.Module):
    """Participating notebook Small3DBackbone, specialized to one input channel."""

    def __init__(self, base_ch: int, out_ch: int) -> None:
        super().__init__()
        self.stem = _ConvNormAct3D(1, base_ch, kernel=5, stride=2)
        self.layer1 = nn.Sequential(
            _ResidualBlock3D(base_ch, base_ch),
            _ResidualBlock3D(base_ch, base_ch),
        )
        self.layer2 = nn.Sequential(
            _ResidualBlock3D(base_ch, base_ch * 2, 2),
            _ResidualBlock3D(base_ch * 2, base_ch * 2),
        )
        self.layer3 = nn.Sequential(
            _ResidualBlock3D(base_ch * 2, base_ch * 4, 2),
            _ResidualBlock3D(base_ch * 4, base_ch * 4),
        )
        self.layer4 = nn.Sequential(
            _ResidualBlock3D(base_ch * 4, out_ch, 2),
            _ResidualBlock3D(out_ch, out_ch),
        )

    def forward(self, x: Tensor) -> Tensor:
        x = self.layer3(self.layer2(self.layer1(self.stem(x))))
        return self.layer4(x)


def _resize_roi_masks(roi_masks: Tensor, target_shape: tuple[int, int, int]) -> Tensor:
    masks = roi_masks.unsqueeze(1).float()
    if tuple(masks.shape[-3:]) != target_shape:
        masks = F.interpolate(
            masks,
            size=target_shape,
            mode="trilinear",
            align_corners=False,
        )
    masks = masks[:, 0]
    denominator = masks.flatten(1).sum(-1, keepdim=True).clamp_min(1e-6)
    return masks / denominator.view(-1, 1, 1, 1)


class ROIAwareGatingBaseline(nn.Module):
    """AAGN-style normalized ROI pooling and learned ROI gating."""

    def __init__(
        self,
        roi_masks: Tensor,
        n_classes: int = 3,
        base_ch: int = 32,
        embed_dim: int = 128,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if not isinstance(roi_masks, Tensor):
            raise TypeError("roi_masks must be a tensor")
        if roi_masks.ndim != 4:
            raise ValueError("roi_masks must have four dimensions [K, D, H, W]")
        if roi_masks.shape[0] == 0:
            raise ValueError("roi_masks must contain at least one ROI")
        if not torch.isfinite(roi_masks).all():
            raise ValueError("roi_masks must contain only finite values")
        if n_classes <= 0 or base_ch <= 0 or embed_dim <= 0:
            raise ValueError("class and channel counts must be positive")
        if not 0.0 <= dropout <= 1.0:
            raise ValueError("dropout must be between zero and one")

        self.backbone = _Small3DBackbone(base_ch, embed_dim)
        self.register_buffer("roi_masks", roi_masks.detach().float().clone())
        self.K = roi_masks.shape[0]
        self.gate = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, 1),
        )
        self.cls = nn.Linear(embed_dim, n_classes)
        self.n_classes = n_classes

    def forward(self, x: Tensor) -> dict[str, Tensor]:
        x = validate_mri_input(x)
        feature_map = self.backbone(x)
        masks = _resize_roi_masks(self.roi_masks.to(feature_map.device), feature_map.shape[-3:])
        roi_features = torch.einsum(
            "bcv,kv->bkc",
            feature_map.flatten(2),
            masks.flatten(1).to(feature_map.dtype),
        )
        alpha = torch.softmax(self.gate(roi_features).squeeze(-1), dim=-1)
        features = torch.einsum("bk,bkc->bc", alpha, roi_features)
        output = {"logits": self.cls(features), "features": features, "alpha": alpha}
        validate_baseline_output(output, batch_size=x.shape[0], output_classes=self.n_classes)
        return output
