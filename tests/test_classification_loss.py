import pytest
import torch
from torch.nn import functional as functional

from acda3d.exceptions import LossContractError
from acda3d.losses import ClassificationLoss


def test_classification_matches_cross_entropy_and_has_finite_gradient():
    logits = torch.tensor([[1.0, 0.0, -1.0], [0.0, 2.0, 1.0]], requires_grad=True)
    labels = torch.tensor([0, 2])
    actual = ClassificationLoss(label_smoothing=0.1)(logits, labels)
    expected = functional.cross_entropy(logits, labels, label_smoothing=0.1)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    actual.backward()
    assert torch.isfinite(logits.grad).all()


def test_classification_rejects_dtype_and_class_index():
    loss = ClassificationLoss()
    with pytest.raises(LossContractError, match="long"):
        loss(torch.randn(2, 3), torch.tensor([0.0, 1.0]))
    with pytest.raises(LossContractError, match="class index"):
        loss(torch.randn(2, 3), torch.tensor([0, 3]))
