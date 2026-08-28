from __future__ import annotations

import numpy as np

from acda3d.data.derivative_verification import (
    GeometryComparison,
    ImageMetadata,
    VerificationResult,
    VerificationStatus,
    select_overlay_sample,
)
from acda3d.data.quality_control import generate_subject_overlays


def _result(subject_hash="abc", cohort="ADNI", label="CN"):
    return VerificationResult(
        row_number=1,
        subject_hash=subject_hash,
        cohort=cohort,
        class_label=label,
        derivative_path="x.pt",
        metadata=ImageMetadata(path="x.pt", file_format=".pt"),
        geometry=GeometryComparison(
            array_grid_status=VerificationStatus.PASSED,
            physical_geometry_status=VerificationStatus.INSUFFICIENT_METADATA,
        ),
        atlas_integrity_status=VerificationStatus.PASSED,
    )


def test_overlay_generation_and_safe_filename(tmp_path):
    result = _result("safehash")
    status = generate_subject_overlays(
        image_array=np.ones((4, 4, 4)),
        atlas_array=np.ones((4, 4, 4)),
        result=result,
        output_dir=tmp_path,
        slices_per_axis=1,
    )
    assert status == VerificationStatus.PASSED
    assert (tmp_path / "safehash_axial.png").exists()
    assert (tmp_path / "safehash_coronal.png").exists()
    assert (tmp_path / "safehash_sagittal.png").exists()


def test_overlay_not_generated_for_incompatible_grid(tmp_path):
    result = _result("safehash")
    status = generate_subject_overlays(
        image_array=np.ones((4, 4, 4)),
        atlas_array=np.ones((5, 4, 4)),
        result=result,
        output_dir=tmp_path,
    )
    assert status == VerificationStatus.FAILED
    assert not list(tmp_path.glob("*.png"))


def test_deterministic_sampling():
    results = [_result(str(i), cohort="ADNI" if i % 2 else "OASIS", label="CN") for i in range(8)]
    first = [r.subject_hash for r in select_overlay_sample(results, 4, 123)]
    second = [r.subject_hash for r in select_overlay_sample(results, 4, 123)]
    assert first == second
