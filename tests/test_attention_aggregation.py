import torch

from acda3d.models import AttentionAggregator, ClassificationHead


def test_attention_contract_determinism_and_gradient_flow():
    module = AttentionAggregator(6).eval()
    tokens = torch.randn(2, 4, 6, requires_grad=True)
    z, alpha = module(tokens)
    z_again, alpha_again = module(tokens)
    assert z.shape == (2, 6)
    assert alpha.shape == (2, 4)
    assert torch.isfinite(z).all() and torch.isfinite(alpha).all()
    assert torch.allclose(alpha.sum(dim=1), torch.ones(2))
    assert torch.equal(z, z_again) and torch.equal(alpha, alpha_again)
    z.sum().backward()
    assert tokens.grad is not None


def test_classification_head_probabilities_and_class_order_shape():
    logits = ClassificationHead(6, 3)(torch.randn(4, 6))
    probabilities = torch.softmax(logits, dim=-1)
    assert logits.shape == (4, 3)
    assert torch.allclose(probabilities.sum(dim=-1), torch.ones(4))
