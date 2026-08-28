import pytest
import torch

from acda3d.adaptation.cdan import conditional_outer_product, expected_conditional_dimension
from acda3d.exceptions import LossContractError


def test_conditional_outer_product_uses_row_major_feature_by_class_flattening_without_detach():
    features = torch.tensor([[1.0, 2.0]], requires_grad=True)
    probabilities = torch.tensor([[0.25, 0.5, 0.25]], requires_grad=True)

    conditional = conditional_outer_product(features, probabilities)

    assert conditional.shape == (1, 6)
    assert torch.equal(conditional, torch.tensor([[0.25, 0.5, 0.25, 0.5, 1.0, 0.5]]))
    conditional.sum().backward()
    assert features.grad is not None
    assert probabilities.grad is not None


def test_conditional_outer_product_is_deterministic_for_multiple_samples():
    features = torch.tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
    probabilities = torch.tensor([[0.2, 0.3, 0.5], [0.1, 0.6, 0.3]], requires_grad=True)

    first = conditional_outer_product(features, probabilities)
    second = conditional_outer_product(features, probabilities)

    expected = torch.tensor(
        [
            [0.2, 0.3, 0.5, 0.4, 0.6, 1.0],
            [0.3, 1.8, 0.9, 0.4, 2.4, 1.2],
        ]
    )
    torch.testing.assert_close(first, expected)
    torch.testing.assert_close(second, expected)


def test_conditional_dimension_is_inferred_from_embedding_and_class_count():
    assert expected_conditional_dimension(embedding_dimension=128, class_count=3) == 384
    assert expected_conditional_dimension(embedding_dimension=5, class_count=3) == 15


@pytest.mark.parametrize(
    ("features", "probabilities"),
    [
        (torch.ones(2, 4), torch.full((2, 3), 0.5)),
        (torch.ones(2, 4), torch.ones(2, 2)),
        (torch.ones(2, 4), torch.ones(3, 3) / 3),
        (torch.ones(2, 4), torch.tensor([[1.0, 0.0, float("nan")], [0.0, 1.0, 0.0]])),
    ],
)
def test_conditional_outer_product_rejects_invalid_probability_inputs(features, probabilities):
    with pytest.raises(LossContractError):
        conditional_outer_product(features, probabilities)
