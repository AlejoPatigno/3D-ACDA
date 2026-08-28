import pytest
import torch
from torch.nn import functional as functional

from acda3d.exceptions import ModelContractError
from acda3d.models import (
    ROIMaskPreparationConfig,
    prepare_feature_grid_roi_masks,
    roi_mask_cache_key,
)


def test_nearest_then_normalize_exact_notebook_parity_and_immutability():
    source = torch.zeros(2, 4, 4, 4)
    source[0, :2] = 1
    source[1, 2:] = 1
    original = source.clone()
    expected = functional.interpolate(source.unsqueeze(1), size=(2, 2, 2), mode="nearest").squeeze(1)
    expected = (expected.flatten(1) / expected.flatten(1).sum(1, keepdim=True).clamp_min(1e-8)).view_as(expected)
    actual = prepare_feature_grid_roi_masks(
        source, (2, 2, 2), ROIMaskPreparationConfig(expected_num_rois=2)
    )
    assert torch.equal(source, original)
    assert torch.equal(actual, expected)
    assert torch.equal(actual.sum((1, 2, 3)), torch.ones(2))
    assert actual.shape == (2, 2, 2, 2)
    assert torch.equal(actual, prepare_feature_grid_roi_masks(source, (2, 2, 2)))


def test_roi_order_and_bool_contract_are_preserved():
    masks = torch.zeros(2, 2, 2, 2, dtype=torch.bool)
    masks[0, 0] = True
    masks[1, 1] = True
    output = prepare_feature_grid_roi_masks(masks, (2, 2, 2))
    assert output[0, 0].sum() > 0 and output[0, 1].sum() == 0
    assert output[1, 1].sum() > 0 and output[1, 0].sum() == 0


def test_empty_after_resize_and_invalid_inputs_fail():
    masks = torch.zeros(2, 4, 4, 4)
    masks[0, 0, 0, 0] = 1
    masks[1, 3, 3, 3] = 1
    with pytest.raises(ModelContractError, match="became empty"):
        prepare_feature_grid_roi_masks(masks, (1, 1, 1))
    with pytest.raises(ModelContractError, match="Expected 3"):
        prepare_feature_grid_roi_masks(
            torch.ones(2, 2, 2, 2), (1, 1, 1), ROIMaskPreparationConfig(expected_num_rois=3)
        )
    masks[0, 0, 0, 0] = float("nan")
    with pytest.raises(ModelContractError, match="finite"):
        prepare_feature_grid_roi_masks(masks, (2, 2, 2))


def test_cache_key_is_deterministic_and_provenance_sensitive():
    config = ROIMaskPreparationConfig(expected_num_rois=2)
    first = roi_mask_cache_key("atlas", (2, 2, 2), config)
    assert first == roi_mask_cache_key("atlas", (2, 2, 2), config)
    assert first != roi_mask_cache_key("other", (2, 2, 2), config)
