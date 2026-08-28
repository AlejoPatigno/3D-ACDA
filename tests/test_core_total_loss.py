import torch

from acda3d.losses import CoreACDA3DLoss, CoreLossWeights
from tests.phase8_helpers import TinyACDA3D


def test_core_total_is_exact_weighted_sum_without_adaptation_fields():
    model = TinyACDA3D()
    output = model(torch.randn(2, 1, 2, 2, 2), torch.ones(2, 1, 1, 1))
    result = CoreACDA3DLoss(2)(
        output, torch.tensor([0, 1]), torch.full((2, 2), 0.5), torch.full((2, 2), 0.4)
    )
    expected = (
        result.classification + result.concept_classification
        + 0.5 * result.concept_supervision + 0.2 * result.anatomical_consistency
        + 0.1 * result.prediction_consistency
    )
    torch.testing.assert_close(result.total, expected, rtol=0, atol=0)
    assert set(vars(result)) == {
        "total", "classification", "concept_classification", "concept_supervision",
        "anatomical_consistency", "prediction_consistency",
    }
    result.total.backward()
    assert all(parameter.grad is not None for parameter in model.parameters())


def test_warm_coefficients_and_zero_components_are_explicit():
    weights = CoreLossWeights(
        classification=0, concept_classification=0, prediction_consistency=0,
        concept_supervision=0, anatomical_consistency=0,
    )
    model = TinyACDA3D()
    output = model(torch.ones(1, 1, 2, 2, 2), torch.ones(2, 1, 1, 1))
    result = CoreACDA3DLoss(2, weights=weights)(
        output, torch.tensor([0]), torch.ones(1, 2), torch.ones(1, 2), stage="warm"
    )
    assert result.total.item() == 0


def test_canonical_warm_multipliers_produce_documented_effective_coefficients():
    weights = CoreLossWeights()
    assert weights.effective("warm") == {
        "classification": 0.1,
        "concept_classification": 1.0,
        "prediction_consistency": 0.0,
        "concept_supervision": 0.5,
        "anatomical_consistency": 0.2,
    }
