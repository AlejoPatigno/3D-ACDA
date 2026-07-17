import nibabel as nib
import numpy as np
import pytest
import torch

from pada3dacb.artifacts.atlas import AtlasConfig, AtlasROIManager
from pada3dacb.artifacts.concepts import (
    ConceptNormalizer,
    ConceptTargetConfig,
    build_subject_concept_target,
    extract_tissue_loss_proxy,
)


def manager(tmp_path):
    atlas = np.zeros((2, 2, 2), dtype=np.float32)
    atlas[0] = 1
    atlas[1] = 2
    path = tmp_path / "atlas.nii.gz"
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), path)
    return AtlasROIManager(path, AtlasConfig(expected_num_rois=2))


def test_proxy_notebook_parity(tmp_path):
    volume = torch.tensor([[[[1.0, 2.0], [3.0, 4.0]], [[10.0, 10.0], [10.0, 10.0]]]])
    reference_q = np.percentile(volume.numpy()[volume.numpy() > 0], 20.0)
    reference = np.array([(volume.numpy()[0, 0] <= reference_q).mean(), (volume.numpy()[0, 1] <= reference_q).mean()], dtype=np.float32)
    assert np.array_equal(extract_tissue_loss_proxy(volume, manager(tmp_path)), reference)
    normalizer = ConceptNormalizer(np.zeros(2, np.float32), np.ones(2, np.float32), roi_labels=[1, 2])
    target = build_subject_concept_target(volume, manager(tmp_path), normalizer)
    assert target.shape == (2,) and torch.isfinite(target).all()


def test_proxy_rejects_empty_and_nonfinite(tmp_path):
    with pytest.raises(ValueError, match="Empty brain"):
        extract_tissue_loss_proxy(torch.zeros(1, 2, 2, 2), manager(tmp_path))
    bad = torch.ones(1, 2, 2, 2)
    bad[0, 0, 0, 0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        extract_tissue_loss_proxy(bad, manager(tmp_path), ConceptTargetConfig())
