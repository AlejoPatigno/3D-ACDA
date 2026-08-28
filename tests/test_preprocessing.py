import json
import time

import nibabel as nib
import numpy as np
import pytest
import torch
import torch.nn.functional as F

from acda3d.data.inventories import SelectedScan
from acda3d.data.preprocessing import (
    PreprocessingRunConfig,
    apply_mri_transforms,
    center_crop_or_pad_3d,
    load_mri_tensor,
    process_scan,
    resize_3d_tensor,
    robust_intensity_normalization,
)


def ref_normalization(x, pmin=1.0, pmax=99.0):
    vals = x[x > 0]
    if vals.numel() == 0:
        return x
    lo = torch.quantile(vals, pmin / 100.0)
    hi = torch.quantile(vals, pmax / 100.0)
    x = torch.clamp(x, lo, hi)
    mean = vals.mean()
    std = vals.std().clamp_min(1e-6)
    return (x - mean) / std


def ref_resize(x, target_shape):
    x5 = x.unsqueeze(0)
    x5 = x5.permute(0, 1, 4, 2, 3)
    x5 = F.interpolate(x5, size=(target_shape[2], target_shape[0], target_shape[1]), mode="trilinear", align_corners=False)
    x5 = x5.permute(0, 1, 3, 4, 2)
    return x5.squeeze(0)


def test_normalization_parity_cases():
    cases = [
        torch.arange(1, 28, dtype=torch.float32).reshape(1, 3, 3, 3),
        torch.zeros(1, 3, 3, 3),
        torch.ones(1, 3, 3, 3),
        torch.tensor([0.0, 1.0, 2.0, 1000.0]).reshape(1, 1, 2, 2),
        torch.tensor([float("nan"), float("inf"), -float("inf"), 1.0]).reshape(1, 1, 2, 2),
    ]
    for case in cases:
        clean = torch.nan_to_num(case.float(), nan=0.0, posinf=0.0, neginf=0.0)
        assert torch.allclose(robust_intensity_normalization(clean), ref_normalization(clean), equal_nan=True)


@pytest.mark.parametrize("shape", [(2, 2, 2), (6, 6, 6), (3, 7, 5), (4, 4, 4)])
def test_resize_crop_pad_parity(shape):
    x = torch.arange(np.prod(shape), dtype=torch.float32).reshape(1, *shape)
    target = (4, 4, 4)
    assert torch.allclose(resize_3d_tensor(x, target), ref_resize(x, target))
    out = center_crop_or_pad_3d(x, target)
    assert out.shape == (1, 4, 4, 4)


def test_complete_transform_parity():
    x = torch.arange(27, dtype=torch.float32).reshape(1, 3, 3, 3)
    target = (4, 4, 4)
    expected = center_crop_or_pad_3d(ref_resize(ref_normalization(x), target), target)
    actual = apply_mri_transforms(x, target)
    assert actual.shape == (1, 4, 4, 4)
    assert torch.allclose(actual, expected)
    assert torch.isfinite(actual).all()


def test_loading_formats(tmp_path):
    arr = np.ones((3, 3, 3), dtype=np.float32)
    npy = tmp_path / "a.npy"
    npz = tmp_path / "a.npz"
    pt = tmp_path / "a.pt"
    ptd = tmp_path / "d.pt"
    nii = tmp_path / "a.nii.gz"
    np.save(npy, arr)
    np.savez(npz, array=arr)
    torch.save(torch.ones(1, 3, 3, 3), pt)
    torch.save({"image": torch.ones(3, 3, 3)}, ptd)
    nib.save(nib.Nifti1Image(arr, np.eye(4)), str(nii))
    for path in [npy, npz, pt, ptd, nii]:
        loaded = load_mri_tensor(path)
        assert loaded.tensor.shape == (1, 3, 3, 3)
    bad = tmp_path / "bad.pt"
    torch.save({"unknown": torch.ones(3, 3, 3)}, bad)
    with pytest.raises(ValueError):
        load_mri_tensor(bad)


def test_serialization_sidecar_resume_and_overwrite(tmp_path):
    source = tmp_path / "002_S_0619.npy"
    np.save(source, np.ones((3, 3, 3), dtype=np.float32))
    cfg = PreprocessingRunConfig()
    cfg.data.output_root = tmp_path / "out"
    cfg.preprocessing.target_shape = (4, 4, 4)
    scan = SelectedScan("002_S_0619", "ADNI", "CN", source, [source], "test")
    record = process_scan(scan, cfg)
    output = tmp_path / "out" / "CN" / "002_S_0619_MRI.pt"
    assert record.status == "PROCESSED"
    assert output.exists()
    assert not list(output.parent.glob("*.tmp"))
    assert output.with_suffix(".pt.json").exists()
    sidecar = json.loads(output.with_suffix(".pt.json").read_text(encoding="utf-8"))
    assert sidecar["configuration_hash"] == cfg.sha256()
    before = output.stat().st_mtime
    time.sleep(0.01)
    record = process_scan(scan, cfg)
    assert record.status == "SKIPPED_VALID"
    assert output.stat().st_mtime == before
    cfg.preprocessing.overwrite = True
    record = process_scan(scan, cfg)
    assert record.status == "PROCESSED"


def test_dry_run_writes_no_tensor(tmp_path):
    source = tmp_path / "002_S_0619.npy"
    np.save(source, np.ones((3, 3, 3), dtype=np.float32))
    cfg = PreprocessingRunConfig()
    cfg.data.output_root = tmp_path / "out"
    cfg.preprocessing.dry_run = True
    scan = SelectedScan("002_S_0619", "ADNI", "CN", source, [source], "test")
    record = process_scan(scan, cfg)
    assert record.status == "DRY_RUN"
    assert not (tmp_path / "out" / "CN" / "002_S_0619_MRI.pt").exists()
