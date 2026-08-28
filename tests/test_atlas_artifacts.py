import nibabel as nib
import numpy as np
import pytest
import torch

from acda3d.artifacts.atlas import (
    AtlasConfig,
    AtlasROIManager,
    infer_label_values,
    load_label_atlas,
    validate_atlas_grid,
)
from acda3d.exceptions import ArtifactValidationError


def save_atlas(tmp_path, values):
    path = tmp_path / "atlas.nii.gz"
    nib.save(nib.Nifti1Image(np.asarray(values, dtype=np.float32), np.eye(4)), path)
    return path


def test_atlas_labels_masks_and_order(tmp_path):
    path = save_atlas(tmp_path, [[[0, 4], [2, 2]], [[4, 0], [2, 4]]])
    manager = AtlasROIManager(path, AtlasConfig(expected_num_rois=2))
    assert manager.label_values == [2, 4]
    assert manager.atlas_tensor.dtype == torch.float32
    assert tuple(manager.atlas_tensor.shape) == (2, 2, 2, 2)
    assert manager.roi_volumes.tolist() == [3, 3]
    assert infer_label_values(manager.atlas_np) == [2, 4]
    validate_atlas_grid(manager.shape, (2, 2, 2))
    with pytest.raises(ArtifactValidationError, match="does not match"):
        manager.get_binary_masks((3, 3, 3))


@pytest.mark.parametrize("values", [np.zeros((2, 2, 2)), np.full((2, 2, 2), np.nan), np.full((2, 2, 2), 1.5)])
def test_invalid_atlas(values, tmp_path):
    path = save_atlas(tmp_path, values)
    with pytest.raises(ArtifactValidationError):
        AtlasROIManager(path, AtlasConfig(expected_num_rois=None))


def test_load_preserves_integer_labels(tmp_path):
    _, atlas = load_label_atlas(save_atlas(tmp_path, np.arange(8).reshape(2, 2, 2)))
    assert atlas.dtype == np.int32
