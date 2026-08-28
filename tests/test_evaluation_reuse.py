from __future__ import annotations

from pathlib import Path

import pytest

from acda3d.evaluation.report import (
    ReportState,
    build_artifact_index,
    build_completion_manifest,
    build_output_plan,
    commit_output,
    verify_reuse,
)
from acda3d.evaluation.schemas import (
    AnalysisMode,
    CheckpointPolicy,
    Direction,
    MethodId,
    ReuseVerificationError,
)

IDENTITY_INPUTS = {
    "configuration_sha256": "b" * 64,
    "authorization_sha256": "c" * 64,
    "ordered_input_sha256s": ["d" * 64],
}
LIBRARIES = {"numpy": "2.3.2", "scipy": "1.17.0"}
EXPECTED_COMPLETION = {
    "expected_bootstrap": {
        "replicates": 10_000, "seed": 0, "ci_policy": "percentile_95_linear"
    },
    "expected_gate_states": {
        "authorized_exports": False, "D-14-001": False,
        "D-14-002": False, "protocol_approval": False,
    },
    "expected_disposition": "completed",
}


def _plan():
    return build_output_plan(
        "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY,
        (MethodId.MMD,), (Direction.ADNI_TO_OASIS,),
        (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.MMD,),
    )


def _completed_output(root: Path) -> tuple[object, dict[str, bytes]]:
    plan = _plan()
    artifacts = {
        path: f"payload:{path}\n".encode()
        for path in plan.intended_relative_paths
        if path != "evaluation_manifest.json"
    }
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, artifacts,
        identity_inputs=IDENTITY_INPUTS,
        library_versions=LIBRARIES,
    )
    commit_output(root, plan, artifacts)
    return plan, artifacts


def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*") if path.is_file()
    }


def test_exact_completed_reuse_is_read_only_and_returns_reused_state(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    before = _snapshot(output)
    outcome = verify_reuse(
        output, plan,
        expected_identity_inputs=IDENTITY_INPUTS,
        expected_library_versions=LIBRARIES,
    )
    assert outcome.state is ReportState.REUSED
    assert outcome.bundle is None
    assert _snapshot(output) == before


def test_reuse_rejects_tampered_expected_completion_metadata(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    manifest = output / "evaluation_manifest.json"
    payload = __import__("json").loads(manifest.read_text(encoding="utf-8"))
    payload["bootstrap"]["seed"] = 999
    manifest.write_text(__import__("json").dumps(payload), encoding="utf-8")
    with pytest.raises(ReuseVerificationError, match="bootstrap"):
        verify_reuse(
            output, plan, expected_identity_inputs=IDENTITY_INPUTS,
            expected_library_versions=LIBRARIES, **EXPECTED_COMPLETION,
        )


def test_reuse_requires_completion_manifest(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    (output / "evaluation_manifest.json").unlink()
    with pytest.raises(ReuseVerificationError, match="manifest"):
        verify_reuse(
            output, plan,
            expected_identity_inputs=IDENTITY_INPUTS,
            expected_library_versions=LIBRARIES,
        )


@pytest.mark.parametrize(
    ("identity_inputs", "libraries", "expected"),
    [
        ({**IDENTITY_INPUTS, "configuration_sha256": "e" * 64}, LIBRARIES, "identity"),
        (IDENTITY_INPUTS, {**LIBRARIES, "numpy": "0.0.0"}, "library"),
    ],
)
def test_reuse_rejects_identity_or_library_mismatch(
    tmp_path: Path,
    identity_inputs: dict[str, object],
    libraries: dict[str, str],
    expected: str,
) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    with pytest.raises(ReuseVerificationError, match=expected):
        verify_reuse(
            output, plan,
            expected_identity_inputs=identity_inputs,
            expected_library_versions=libraries,
        )


def test_reuse_rejects_required_file_hash_mismatch(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    (output / "method_status.csv").write_bytes(b"tampered")
    with pytest.raises(ReuseVerificationError, match="hash"):
        verify_reuse(
            output, plan,
            expected_identity_inputs=IDENTITY_INPUTS,
            expected_library_versions=LIBRARIES,
        )


def test_reuse_accepts_valid_artifact_index_and_rejects_legacy_alias(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    required = {
        path.relative_to(output).as_posix(): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file() and path.name != "evaluation_manifest.json"
    }
    (output / "artifact_index.json").write_bytes(build_artifact_index(required))
    assert verify_reuse(
        output, plan,
        expected_identity_inputs=IDENTITY_INPUTS,
        expected_library_versions=LIBRARIES,
    ).state is ReportState.REUSED
    (output / "artifact_index.json").unlink()
    (output / "evaluation_index.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ReuseVerificationError, match="file set"):
        verify_reuse(
            output, plan,
            expected_identity_inputs=IDENTITY_INPUTS,
            expected_library_versions=LIBRARIES,
        )


def test_reuse_rejects_index_hash_mismatch_and_missing_manifest_field(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    plan, _ = _completed_output(output)
    (output / "artifact_index.json").write_bytes(build_artifact_index({"wrong.csv": b"wrong"}))
    with pytest.raises(ReuseVerificationError, match="index"):
        verify_reuse(
            output, plan,
            expected_identity_inputs=IDENTITY_INPUTS,
            expected_library_versions=LIBRARIES,
        )
    (output / "artifact_index.json").unlink()
    manifest = output / "evaluation_manifest.json"
    payload = __import__("json").loads(manifest.read_text(encoding="utf-8"))
    payload.pop("class_order")
    manifest.write_text(__import__("json").dumps(payload), encoding="utf-8")
    with pytest.raises(ReuseVerificationError, match="class_order"):
        verify_reuse(
            output, plan,
            expected_identity_inputs=IDENTITY_INPUTS,
            expected_library_versions=LIBRARIES,
        )
