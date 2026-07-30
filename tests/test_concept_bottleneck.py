import torch

from pada3dacb.models import ConceptBottleneck


def test_active_per_roi_concept_mlp_contract_and_gradients():
    module = ConceptBottleneck(3, 6, 3, hidden_dim=4, dropout=0.0)
    tokens = torch.randn(2, 3, 6, requires_grad=True)
    concepts, logits = module(tokens)
    assert len(module.concept_mlps) == 3
    assert concepts.shape == (2, 3)
    assert logits.shape == (2, 3)
    assert torch.isfinite(concepts).all() and torch.isfinite(logits).all()
    assert ((concepts >= 0) & (concepts <= 1)).all()
    (concepts.sum() + logits.sum()).backward()
    assert tokens.grad is not None
    assert all(parameter.grad is not None for parameter in module.parameters())


def test_each_concept_uses_only_its_matching_roi_token():
    module = ConceptBottleneck(2, 4, hidden_dim=3, dropout=0.0).eval()
    original = torch.randn(1, 2, 4)
    changed = original.clone()
    changed[:, 1] += 10
    first, _ = module(original)
    second, _ = module(changed)
    assert torch.equal(first[:, 0], second[:, 0])
