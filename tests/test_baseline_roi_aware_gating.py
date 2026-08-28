from __future__ import annotations

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from acda3d.models.baselines import build_baseline
from acda3d.models.baselines.roi_aware_gating import ROIAwareGatingBaseline


class _Conv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel: int = 3, stride: int = 1) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, kernel, stride, kernel // 2, bias=False),
            nn.InstanceNorm3d(out_ch, affine=True),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class _Residual(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, stride: int = 1) -> None:
        super().__init__()
        self.conv1 = _Conv(in_ch, out_ch, stride=stride)
        self.conv2 = nn.Sequential(
            nn.Conv3d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.InstanceNorm3d(out_ch, affine=True),
        )
        self.act = nn.GELU()
        self.skip = (
            nn.Sequential(
                nn.Conv3d(in_ch, out_ch, 1, stride=stride, bias=False),
                nn.InstanceNorm3d(out_ch, affine=True),
            )
            if in_ch != out_ch or stride != 1
            else None
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x if self.skip is None else self.skip(x)
        return self.act(self.conv2(self.conv1(x)) + identity)


class _NotebookBackbone(nn.Module):
    def __init__(self, base_ch: int, embed_dim: int) -> None:
        super().__init__()
        self.stem = _Conv(1, base_ch, 5, 2)
        self.layer1 = nn.Sequential(_Residual(base_ch, base_ch), _Residual(base_ch, base_ch))
        self.layer2 = nn.Sequential(
            _Residual(base_ch, base_ch * 2, 2), _Residual(base_ch * 2, base_ch * 2)
        )
        self.layer3 = nn.Sequential(
            _Residual(base_ch * 2, base_ch * 4, 2), _Residual(base_ch * 4, base_ch * 4)
        )
        self.layer4 = nn.Sequential(
            _Residual(base_ch * 4, embed_dim, 2), _Residual(embed_dim, embed_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.layer3(self.layer2(self.layer1(self.stem(x))))
        return self.layer4(x)


class _NotebookReference(nn.Module):
    """Direct transcription of the participating notebook AAGN definition."""

    def __init__(self, masks: torch.Tensor, base_ch: int, embed_dim: int) -> None:
        super().__init__()
        self.backbone = _NotebookBackbone(base_ch, embed_dim)
        self.register_buffer("roi_masks", masks.float())
        self.gate = nn.Sequential(nn.Linear(embed_dim, embed_dim), nn.GELU(), nn.Linear(embed_dim, 1))
        self.cls = nn.Linear(embed_dim, 3)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        feat = self.backbone(x)
        masks = self.roi_masks.unsqueeze(1)
        masks = F.interpolate(masks, feat.shape[-3:], mode="trilinear", align_corners=False)[:, 0]
        denom = masks.flatten(1).sum(-1, keepdim=True).clamp_min(1e-6)
        masks = masks / denom.view(-1, 1, 1, 1)
        roi_features = torch.einsum("bcv,kv->bkc", feat.flatten(2), masks.flatten(1))
        alpha = torch.softmax(self.gate(roi_features).squeeze(-1), dim=-1)
        features = torch.einsum("bk,bkc->bc", alpha, roi_features)
        return {"logits": self.cls(features), "features": features, "alpha": alpha}


def _masks() -> torch.Tensor:
    masks = torch.zeros(3, 32, 32, 32)
    masks[0, :16] = 1
    masks[1, 16:] = 1
    masks[2, 8:24, 8:24, 8:24] = 1
    return masks


def test_direct_notebook_transcription_parity_with_copied_weights() -> None:
    torch.manual_seed(7)
    model = ROIAwareGatingBaseline(_masks(), base_ch=2, embed_dim=8).eval()
    reference = _NotebookReference(_masks(), base_ch=2, embed_dim=8).eval()
    reference.load_state_dict(model.state_dict())
    x = torch.randn(2, 1, 32, 32, 32)

    actual = model(x)
    expected = reference(x)

    assert actual.keys() == expected.keys()
    for key in actual:
        torch.testing.assert_close(actual[key], expected[key], rtol=0, atol=0)


def test_roi_order_controls_alpha_and_normalized_pooling() -> None:
    model = ROIAwareGatingBaseline(_masks(), base_ch=2, embed_dim=8).eval()
    reordered = ROIAwareGatingBaseline(_masks()[[2, 0, 1]], base_ch=2, embed_dim=8).eval()
    reordered.load_state_dict({k: v for k, v in model.state_dict().items() if k != "roi_masks"}, strict=False)
    x = torch.randn(1, 1, 32, 32, 32)

    output = model(x)
    changed = reordered(x)

    torch.testing.assert_close(changed["alpha"], output["alpha"][:, [2, 0, 1]])
    torch.testing.assert_close(changed["features"], output["features"])
    torch.testing.assert_close(changed["logits"], output["logits"])
    torch.testing.assert_close(output["alpha"].sum(dim=1), torch.ones(1))


@pytest.mark.parametrize(
    ("masks", "message"),
    [
        (None, "roi_masks"),
        (torch.ones(2, 8, 8), "four dimensions"),
        (torch.empty(0, 8, 8, 8), "at least one"),
        (torch.full((2, 8, 8, 8), float("nan")), "finite"),
    ],
)
def test_missing_and_invalid_masks_fail(masks: torch.Tensor | None, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        ROIAwareGatingBaseline(masks, base_ch=2, embed_dim=8)  # type: ignore[arg-type]


@pytest.mark.parametrize("shape", [(2, 32, 32, 32), (2, 2, 32, 32, 32)])
def test_invalid_mri_rank_or_channel_fails(shape: tuple[int, ...]) -> None:
    model = ROIAwareGatingBaseline(_masks(), base_ch=2, embed_dim=8)
    with pytest.raises(ValueError, match=r"\[B, 1, D, H, W\]"):
        model(torch.randn(shape))


def test_outputs_are_finite_three_class_deterministic_and_parameterized() -> None:
    model = build_baseline("aagn", {"roi_masks": _masks(), "base_ch": 2, "embed_dim": 8})
    assert next(model.parameters()).device.type == "cpu"
    model.eval()
    x = torch.randn(2, 1, 32, 32, 32)

    first = model(x)
    second = model(x)

    assert first["logits"].shape == (2, 3)
    assert first["features"].shape == (2, 8)
    assert first["alpha"].shape == (2, 3)
    assert all(torch.isfinite(value).all() for value in first.values())
    for key in first:
        torch.testing.assert_close(first[key], second[key])
    count = sum(parameter.numel() for parameter in model.parameters())
    assert count == 15_586
    assert model.baseline_metadata["total_parameters"] == count
    assert model.baseline_metadata["trainable_parameters"] == count
