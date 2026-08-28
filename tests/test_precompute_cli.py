import subprocess
import sys

import nibabel as nib
import numpy as np
import pandas as pd
import torch


def test_cli_concept_jacobian_and_combined_modes(tmp_path):
    atlas = np.zeros((4, 4, 4), np.float32)
    atlas[:2] = 1
    atlas[2:] = 2
    atlas_path = tmp_path / "atlas.nii.gz"
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), atlas_path)
    derivative = tmp_path / "s1.pt"
    torch.save(torch.arange(1, 65, dtype=torch.float32).reshape(1, 4, 4, 4), derivative)
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{"subject_id": "s1", "cohort": "ADNI", "class_label": "CN", "derivative_path": derivative}]).to_csv(manifest, index=False)
    config = tmp_path / "config.yaml"
    config.write_text("precompute:\n  expected_spatial_shape: [4, 4, 4]\n  expected_num_rois: 2\natlas:\n  expected_num_rois: 2\nconcepts:\n  normal_class_name: CN\njacobians:\n  n_iterations: 1\nexecution:\n  number_of_workers: 1\n", encoding="utf-8")
    concept_root = tmp_path / "concept"
    base = [sys.executable, "scripts/precompute_artifacts.py", "--config", str(config), "--manifest", str(manifest), "--atlas", str(atlas_path), "--template", str(derivative)]
    completed = subprocess.run([*base, "--artifact-root", str(concept_root), "--no-jacobians"], text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert (concept_root / "artifact_index.csv").exists()
    for switches, name in [(["--no-concepts", "--compute-jacobians"], "jacobian"), (["--compute-concepts", "--compute-jacobians"], "combined")]:
        root = tmp_path / name
        result = subprocess.run([*base, "--artifact-root", str(root), *switches], text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stderr
        assert (root / "artifact_index.csv").exists()
        assert (root / "jacobians" / "subjects" / "s1.pt").exists()


def test_no_forbidden_phase_six_symbols():
    from pathlib import Path

    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/acda3d/artifacts").glob("*.py"))
    for forbidden in ("ContextualROIEncoder", "CORAL", "MMD", "CDAN", "pseudo-label"):
        assert forbidden not in text
