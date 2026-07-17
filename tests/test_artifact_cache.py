import json

import nibabel as nib
import numpy as np
import pandas as pd
import torch

from pada3dacb.artifacts.cache import PrecomputeRunConfig, ensure_artifact_cache


def setup_case(tmp_path):
    atlas = np.zeros((2, 2, 2), np.float32)
    atlas[0] = 1
    atlas[1] = 2
    atlas_path = tmp_path / "atlas.nii.gz"
    nib.save(nib.Nifti1Image(atlas, np.eye(4)), atlas_path)
    rows = []
    for subject, label, value in [("s1", "CN", 1.0), ("s2", "AD", 2.0)]:
        path = tmp_path / f"{subject}.pt"
        tensor = torch.arange(1, 9, dtype=torch.float32).reshape(1, 2, 2, 2) * value
        torch.save(tensor, path)
        rows.append({"subject_id": subject, "cohort": "ADNI", "class_label": label, "derivative_path": path})
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    cfg = PrecomputeRunConfig()
    cfg.paths.manifest, cfg.paths.atlas, cfg.paths.artifact_root = manifest, atlas_path, tmp_path / "artifacts"
    cfg.precompute.expected_spatial_shape = (2, 2, 2)
    cfg.precompute.expected_num_rois = 2
    cfg.precompute.compute_jacobians = False
    return cfg


def test_cache_compute_resume_and_corruption(tmp_path):
    cfg = setup_case(tmp_path)
    first = ensure_artifact_cache(cfg)
    assert set(first.concept_status) == {"COMPUTED"}
    second = ensure_artifact_cache(cfg)
    assert set(second.concept_status) == {"SKIPPED_VALID"}
    artifact = cfg.paths.artifact_root / first.iloc[0].concept_path
    artifact.write_bytes(b"corrupt")
    third = ensure_artifact_cache(cfg)
    assert third.iloc[0].concept_status == "INVALID_EXISTING_corrupt"
    cfg.precompute.overwrite = True
    repaired = ensure_artifact_cache(cfg)
    assert repaired.iloc[0].concept_status == "COMPUTED"
    assert not list(cfg.paths.artifact_root.rglob("*.tmp"))


def test_dry_run_creates_only_reports(tmp_path):
    cfg = setup_case(tmp_path)
    cfg.precompute.dry_run = True
    result = ensure_artifact_cache(cfg)
    assert set(result.concept_status) == {"PLANNED"}
    assert (cfg.paths.artifact_root / "dry_run_plan.csv").exists()
    assert not (cfg.paths.artifact_root / "concepts").exists()
    assert json.loads((cfg.paths.artifact_root / "artifact_summary.json").read_text())["dry_run"] is True


def test_failure_isolation_and_branch_specific_hash(tmp_path, monkeypatch):
    cfg = setup_case(tmp_path)
    frame = pd.read_csv(cfg.paths.manifest)
    frame.loc[len(frame)] = {
        "subject_id": "missing",
        "cohort": "ADNI",
        "class_label": "AD",
        "derivative_path": tmp_path / "missing.pt",
    }
    frame.to_csv(cfg.paths.manifest, index=False)
    concept_only = ensure_artifact_cache(cfg)
    assert concept_only.loc[concept_only.subject_id == "s1", "concept_status"].item() == "COMPUTED"
    assert "missing" in (cfg.paths.artifact_root / "failures.csv").read_text(encoding="utf-8")

    cfg.precompute.compute_jacobians = True
    cfg.paths.template = tmp_path / "s1.pt"

    def fake_g_bar(*args, **kwargs):
        return torch.tensor([0.25, 0.75], dtype=torch.float32)

    monkeypatch.setattr("pada3dacb.artifacts.cache.compute_g_bar_from_template_and_subject", fake_g_bar)
    combined = ensure_artifact_cache(cfg)
    valid = combined[combined.subject_id.isin(["s1", "s2"])]
    assert set(valid.concept_status) == {"SKIPPED_VALID"}
    assert set(valid.jacobian_status) == {"COMPUTED"}
