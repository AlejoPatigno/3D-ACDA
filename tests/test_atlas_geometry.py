import nibabel as nib
import numpy as np

from pada3dacb.data.derivative_verification import (
    VerificationConfig,
    VerificationStatus,
    affine_diagnostics,
    compare_geometry,
    extract_image_metadata,
    validate_atlas,
)


def _save_nifti(path, data, affine):
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine), str(path))
    return path


def test_matching_nifti_geometry(tmp_path):
    affine = np.diag([1.0, 1.0, 1.0, 1.0])
    mri = _save_nifti(tmp_path / "mri.nii.gz", np.ones((4, 5, 6)), affine)
    atlas = _save_nifti(tmp_path / "atlas.nii.gz", np.ones((4, 5, 6)), affine)
    cfg = VerificationConfig(expected_num_rois=1)
    image_meta, _ = extract_image_metadata(mri, cfg)
    atlas_meta, _ = validate_atlas(atlas, cfg)
    comp = compare_geometry(image_meta, atlas_meta, cfg)
    assert comp.physical_geometry_status == VerificationStatus.PASSED
    assert comp.array_grid_status == VerificationStatus.PASSED


def test_shape_mismatch_fails_array_grid(tmp_path):
    affine = np.eye(4)
    mri = _save_nifti(tmp_path / "mri.nii.gz", np.ones((4, 5, 6)), affine)
    atlas = _save_nifti(tmp_path / "atlas.nii.gz", np.ones((4, 5, 7)), affine)
    cfg = VerificationConfig(expected_num_rois=1)
    image_meta, _ = extract_image_metadata(mri, cfg)
    atlas_meta, _ = validate_atlas(atlas, cfg)
    comp = compare_geometry(image_meta, atlas_meta, cfg)
    assert comp.array_grid_status == VerificationStatus.FAILED


def test_affine_spacing_and_orientation_mismatches_fail(tmp_path):
    cfg = VerificationConfig(expected_num_rois=1)
    atlas = _save_nifti(tmp_path / "atlas.nii.gz", np.ones((4, 4, 4)), np.eye(4))

    shifted = np.eye(4)
    shifted[0, 3] = 5
    mri_affine = _save_nifti(tmp_path / "mri_affine.nii.gz", np.ones((4, 4, 4)), shifted)
    image_meta, _ = extract_image_metadata(mri_affine, cfg)
    atlas_meta, _ = validate_atlas(atlas, cfg)
    assert compare_geometry(image_meta, atlas_meta, cfg).physical_geometry_status == VerificationStatus.FAILED

    spacing = np.diag([2.0, 1.0, 1.0, 1.0])
    mri_spacing = _save_nifti(tmp_path / "mri_spacing.nii.gz", np.ones((4, 4, 4)), spacing)
    image_meta, _ = extract_image_metadata(mri_spacing, cfg)
    assert compare_geometry(image_meta, atlas_meta, cfg).physical_geometry_status == VerificationStatus.FAILED

    flipped = np.diag([-1.0, 1.0, 1.0, 1.0])
    mri_orient = _save_nifti(tmp_path / "mri_orient.nii.gz", np.ones((4, 4, 4)), flipped)
    image_meta, _ = extract_image_metadata(mri_orient, cfg)
    assert compare_geometry(image_meta, atlas_meta, cfg).physical_geometry_status == VerificationStatus.FAILED


def test_invalid_affines_fail(tmp_path):
    for affine in [
        np.array([[np.nan, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float),
        np.diag([0.0, 1.0, 1.0, 1.0]),
        np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 2]], dtype=float),
    ]:
        status, messages, _ = affine_diagnostics(affine)
        assert status == VerificationStatus.FAILED
        assert messages


def test_atlas_integrity_cases(tmp_path):
    cfg = VerificationConfig(expected_num_rois=2)
    valid = _save_nifti(tmp_path / "valid.nii.gz", np.array([[[0, 1], [2, 2]]]), np.eye(4))
    assert validate_atlas(valid, cfg)[0].atlas_integrity_status == VerificationStatus.PASSED

    non_integer = _save_nifti(tmp_path / "float.nii.gz", np.array([[[0.2, 1.3]]]), np.eye(4))
    assert validate_atlas(non_integer, cfg)[0].atlas_integrity_status == VerificationStatus.FAILED

    background = _save_nifti(tmp_path / "background.nii.gz", np.zeros((2, 2, 2)), np.eye(4))
    assert validate_atlas(background, cfg)[0].atlas_integrity_status == VerificationStatus.FAILED

    nan_atlas = _save_nifti(tmp_path / "nan.nii.gz", np.array([[[0, np.nan]]]), np.eye(4))
    assert validate_atlas(nan_atlas, cfg)[0].atlas_integrity_status == VerificationStatus.FAILED
