import torch

from pada3dacb.adaptation import MMDAdaptationMethod, mmd_loss
from tests.phase8_helpers import TinyPADA3DACB


def test_mmd_gradients_reach_both_features_and_shared_encoder_under_autocast():
    source = torch.randn(3, 4, requires_grad=True)
    target = torch.randn(2, 4, requires_grad=True)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        loss = mmd_loss(source, target, [0.5, 1.0, 2.0])
    assert loss.dtype == torch.float32
    loss.backward()
    assert torch.isfinite(source.grad).all() and torch.isfinite(target.grad).all()

    model = TinyPADA3DACB()
    masks = torch.ones(2, 1, 1, 1)
    output = MMDAdaptationMethod([0.5, 1.0, 2.0]).compute(
        model(torch.rand(3, 1, 2, 2, 2), masks),
        model(torch.rand(2, 1, 2, 2, 2), masks),
        "full",
    )
    output.total.backward()
    assert model.encoder.weight.grad is not None
    assert torch.isfinite(model.encoder.weight.grad).all()
