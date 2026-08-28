import pytest
import torch

from acda3d.exceptions import ModelContractError
from acda3d.models import Encoder3D


def test_encoder_shape_finiteness_determinism_and_inference():
    model = Encoder3D(feature_dim=8, base_channels=4).eval()
    x = torch.randn(2, 1, 16, 16, 16)
    first = model(x)
    second = model(x)
    assert first.shape == (2, 8, 2, 2, 2)
    assert torch.isfinite(first).all()
    assert torch.equal(first, second)
    assert model.infer_output_shape((1, 1, 16, 16, 16)) == (1, 8, 2, 2, 2)


def test_encoder_rejects_bad_shape_and_propagates_gradients():
    model = Encoder3D(feature_dim=8, base_channels=4)
    with pytest.raises(ModelContractError):
        model(torch.randn(1, 2, 16, 16, 16))
    model(torch.randn(1, 1, 16, 16, 16)).sum().backward()
    assert all(parameter.grad is not None for parameter in model.parameters())
