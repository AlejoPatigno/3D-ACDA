import torch
from torch.nn import functional as functional

from pada3dacb.losses import PredictionConsistencyLoss


def test_asymmetric_kl_exact_parity_and_both_branch_gradients():
    latent = torch.randn(3, 3, requires_grad=True)
    concept = torch.randn(3, 3, requires_grad=True)
    actual = PredictionConsistencyLoss()(latent, concept)
    expected = functional.kl_div(
        functional.log_softmax(latent, -1), functional.softmax(concept, -1), reduction="batchmean"
    )
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    actual.backward()
    assert torch.isfinite(latent.grad).all()
    assert torch.isfinite(concept.grad).all()
