from __future__ import annotations

import subprocess
import sys

import nibabel as nib
import numpy as np
import pandas as pd
import torch

from pada3dacb.data.derivative_verification import (
    VerificationConfig,
    VerificationStatus,
    extract_image_metadata,
    numerical_summary,
    status_aggregate,
    validate_atlas,
    verify_inventory,
)


def test_numerical_corruption_statuses():
    cfg = VerificationConfig()
    for array in [
        np.array([1.0, np.nan]),
        np.array([1.0, np.inf]),
        np.array([1.0, -np.inf]),
    ]:
        _, status = numerical_summary(array, cfg)
        assert status == VerificationStatus.FAILED
    _, zero_status = numerical_summary(np.zeros((3, 3, 3)), cfg)
    assert zero_status == VerificationStatus.WARNING
    _, constant_status = numerical_summary(np.ones((3, 3, 3)), cfg)
    assert constant_status == VerificationStatus.WARNING


def test_plain_pt_tensor_has_insufficient_physical_metadata(tmp_path):
    tensor_path = tmp_path / "subject.pt"
    atlas_path = tmp_path / "atlas.nii.gz"
    torch.save(torch.ones(1, 4, 4, 4), tensor_path)
    nib.save(nib.Nifti1Image(np.ones((4, 4, 4), dtype=np.int16), np.eye(4)), str(atlas_path))
    cfg = VerificationConfig(expected_num_rois=1)
    meta, _ = extract_image_metadata(tensor_path, cfg)
    atlas_meta, _ = validate_atlas(atlas_path, cfg)
    from pada3dacb.data.derivative_verification import compare_geometry

    comp = compare_geometry(meta, atlas_meta, cfg)
    assert meta.tensor_contract_status == VerificationStatus.PASSED
    assert comp.array_grid_status == VerificationStatus.PASSED
    assert comp.physical_geometry_status == VerificationStatus.INSUFFICIENT_METADATA


def test_pt_dictionary_supported_and_unsupported_keys(tmp_path):
    cfg = VerificationConfig()
    good = tmp_path / "good.pt"
    bad = tmp_path / "bad.pt"
    torch.save({"image": torch.ones(4, 4, 4)}, good)
    torch.save({"unknown": torch.ones(4, 4, 4)}, bad)
    assert extract_image_metadata(good, cfg)[0].tensor_contract_status == VerificationStatus.PASSED
    assert extract_image_metadata(bad, cfg)[0].tensor_contract_status == VerificationStatus.FAILED


def test_status_aggregation_order():
    assert status_aggregate([VerificationStatus.PASSED, VerificationStatus.WARNING]) == VerificationStatus.WARNING
    assert status_aggregate([VerificationStatus.WARNING, VerificationStatus.FAILED]) == VerificationStatus.FAILED
    assert (
        status_aggregate([VerificationStatus.PASSED, VerificationStatus.INSUFFICIENT_METADATA])
        == VerificationStatus.INSUFFICIENT_METADATA
    )


def test_verify_inventory_outputs_and_cli(tmp_path):
    atlas_path = tmp_path / "atlas.nii.gz"
    mri_path = tmp_path / "mri.nii.gz"
    affine = np.eye(4)
    nib.save(nib.Nifti1Image(np.ones((4, 4, 4), dtype=np.float32), affine), str(mri_path))
    nib.save(nib.Nifti1Image(np.ones((4, 4, 4), dtype=np.int16), affine), str(atlas_path))
    inventory = tmp_path / "inventory.csv"
    pd.DataFrame(
        [{"subject_id": "s1", "cohort": "ADNI", "class_label": "CN", "derivative_path": str(mri_path)}]
    ).to_csv(inventory, index=False)
    output = tmp_path / "out"
    cfg = VerificationConfig(expected_num_rois=1, overlay_sample_size=1)
    results, _ = verify_inventory(inventory, atlas_path, output, cfg)
    assert results[0].overall_status in {VerificationStatus.PASSED, VerificationStatus.WARNING}
    for name in [
        "subjects.csv",
        "summary.json",
        "summary.md",
        "failures.csv",
        "warnings.csv",
        "insufficient_metadata.csv",
        "atlas_report.json",
        "overlay_sample.csv",
        "configuration_resolved.yaml",
        "verification_metadata.json",
    ]:
        assert (output / name).exists()

    cli_output = tmp_path / "cli_out"
    command = [
        sys.executable,
        "scripts/verify_derivatives.py",
        "--config",
        "configs/verification/derivatives.yaml",
        "--inventory",
        str(inventory),
        "--atlas",
        str(atlas_path),
        "--output-dir",
        str(cli_output),
        "--sample-size",
        "1",
        "--overwrite",
    ]
    completed = subprocess.run(command, cwd=".", text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert (cli_output / "subjects.csv").exists()
