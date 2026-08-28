from __future__ import annotations

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from acda3d.models.baselines import build_baseline
from acda3d.models.baselines.faster_snn import FasterSNNBaseline, SpikeAct


class _NotebookSpikeFn(torch.autograd.Function):
    @staticmethod
    def forward(ctx: object, x: torch.Tensor) -> torch.Tensor:
        ctx.save_for_backward(x)  # type: ignore[attr-defined]
        return (x > 0).float()

    @staticmethod
    def backward(ctx: object, grad_output: torch.Tensor) -> torch.Tensor:
        (x,) = ctx.saved_tensors  # type: ignore[attr-defined]
        return grad_output * (1.0 / (1.0 + x.abs()).pow(2))


class _NotebookSpike(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return _NotebookSpikeFn.apply(x)


class _NotebookReference(nn.Module):
    """Direct transcription of the participating FasterSNN notebook definition."""

    def __init__(self, n_classes: int = 3, base_ch: int = 2) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv3d(1, base_ch, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch, affine=True),
            _NotebookSpike(),
            nn.Conv3d(base_ch, base_ch * 2, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch * 2, affine=True),
            _NotebookSpike(),
            nn.Conv3d(base_ch * 2, base_ch * 4, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch * 4, affine=True),
            _NotebookSpike(),
            nn.Conv3d(base_ch * 4, base_ch * 8, 3, 2, 1, bias=False),
            nn.InstanceNorm3d(base_ch * 8, affine=True),
            _NotebookSpike(),
        )
        self.cls = nn.Linear(base_ch * 8, n_classes)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        feature_map = self.features(x)
        features = F.adaptive_avg_pool3d(feature_map, 1).flatten(1)
        return {"logits": self.cls(features), "features": features}


def test_direct_notebook_transcription_parity_with_copied_weights() -> None:
    torch.manual_seed(19)
    model = FasterSNNBaseline(base_ch=2).eval()
    reference = _NotebookReference(base_ch=2).eval()
    reference.load_state_dict(model.state_dict())
    x = torch.randn(2, 1, 32, 32, 32)

    actual = model(x)
    expected = reference(x)

    assert actual.keys() == expected.keys()
    for key in actual:
        torch.testing.assert_close(actual[key], expected[key], rtol=0, atol=0)


def test_surrogate_spike_matches_notebook_forward_and_backward() -> None:
    x = torch.tensor([-2.0, 0.0, 3.0], requires_grad=True)
    output = SpikeAct()(x)

    torch.testing.assert_close(output, torch.tensor([0.0, 0.0, 1.0]))
    output.sum().backward()
    torch.testing.assert_close(x.grad, torch.tensor([1 / 9, 1.0, 1 / 16]))


def test_four_blocks_have_exact_intermediate_shapes_and_order() -> None:
    model = FasterSNNBaseline(base_ch=2).eval()
    observed: list[tuple[int, ...]] = []
    handles = [
        layer.register_forward_hook(lambda _m, _i, out: observed.append(tuple(out.shape)))
        for layer in model.features
        if isinstance(layer, SpikeAct)
    ]
    try:
        model(torch.randn(2, 1, 32, 48, 64))
    finally:
        for handle in handles:
            handle.remove()

    assert observed == [
        (2, 2, 16, 24, 32),
        (2, 4, 8, 12, 16),
        (2, 8, 4, 6, 8),
        (2, 16, 2, 3, 4),
    ]


def test_minimum_viable_spatial_shape_is_accepted() -> None:
    output = FasterSNNBaseline(base_ch=2).eval()(torch.randn(2, 1, 17, 17, 17))
    assert output["logits"].shape == (2, 3)
    assert output["features"].shape == (2, 16)


def test_registry_build_outputs_are_finite_deterministic_and_exactly_parameterized() -> None:
    model = build_baseline("faster_snn", {"base_ch": 2, "dropout": 0.25}).eval()
    assert next(model.parameters()).device.type == "cpu"
    x = torch.randn(2, 1, 32, 32, 32)

    first = model(x)
    second = model(x)

    assert first["logits"].shape == (2, 3)
    assert first["features"].shape == (2, 16)
    assert all(torch.isfinite(value).all() for value in first.values())
    for key in first:
        torch.testing.assert_close(first[key], second[key], rtol=0, atol=0)
    count = sum(parameter.numel() for parameter in model.parameters())
    assert count == 4_701
    assert model.baseline_metadata["total_parameters"] == count
    assert model.baseline_metadata["trainable_parameters"] == count


@pytest.mark.parametrize(
    ("x", "error", "message"),
    [
        (torch.randn(2, 32, 32, 32), ValueError, r"\[B, 1, D, H, W\]"),
        (torch.randn(2, 2, 32, 32, 32), ValueError, r"\[B, 1, D, H, W\]"),
        (torch.ones(1, 1, 32, 32, 32, dtype=torch.int64), TypeError, "floating-point"),
        (torch.full((1, 1, 32, 32, 32), float("nan")), ValueError, "finite"),
        (torch.randn(1, 1, 16, 32, 32), ValueError, "at least 17"),
    ],
)
def test_invalid_mri_input_fails(
    x: torch.Tensor, error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        FasterSNNBaseline(base_ch=2)(x)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_classes": 0}, "positive"),
        ({"base_ch": 0}, "positive"),
        ({"dropout": -0.1}, "between zero and one"),
    ],
)
def test_invalid_constructor_values_fail(kwargs: dict[str, int | float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        FasterSNNBaseline(**kwargs)
