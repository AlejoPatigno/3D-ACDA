import pytest
import torch

from acda3d.exceptions import ModelContractError
from acda3d.models import ROITokenizer


def test_roi_tokenizer_preserves_order_and_gradients():
    tokenizer = ROITokenizer(num_rois=2, feature_dim=2, token_dim=2)
    with torch.no_grad():
        tokenizer.proj.weight.copy_(torch.eye(2))
        tokenizer.proj.bias.zero_()
        tokenizer.roi_emb.weight.zero_()
    features = torch.tensor([1.0, 2.0, 3.0, 4.0]).reshape(1, 2, 1, 1, 2).requires_grad_()
    masks = torch.tensor([[[[1.0, 0.0]]], [[[0.0, 1.0]]]])
    tokens = tokenizer(features, masks)
    assert tokens.shape == (1, 2, 2)
    assert torch.equal(tokens, torch.tensor([[[1.0, 3.0], [2.0, 4.0]]]))
    tokens.sum().backward()
    assert features.grad is not None
    assert tokenizer.proj.weight.grad is not None


def test_roi_tokenizer_rejects_empty_and_mismatched_masks():
    tokenizer = ROITokenizer(2, 4, 3)
    features = torch.randn(1, 4, 2, 2, 2)
    with pytest.raises(ModelContractError, match="non-empty"):
        tokenizer(features, torch.zeros(2, 2, 2, 2))
    with pytest.raises(ModelContractError, match="feature grid"):
        tokenizer(features, torch.ones(2, 4, 4, 4))


def test_bool_masks_are_supported_without_resizing():
    tokenizer = ROITokenizer(2, 4, 3)
    masks = torch.ones(2, 2, 2, 2, dtype=torch.bool)
    output = tokenizer(torch.randn(2, 4, 2, 2, 2), masks)
    assert output.shape == (2, 2, 3)
    assert torch.isfinite(output).all()
