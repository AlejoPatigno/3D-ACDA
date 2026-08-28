from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from import_kaggle_readiness import (  # noqa: E402
    EXPECTED_OASIS,
    main,
    sha256_file,
    validate_bundle,
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(root: Path, name: str, value: dict) -> None:
    (root / name).write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def create_bundle(root: Path) -> None:
    artifact = root / "artifacts" / "person.pt"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"synthetic model-ready artifact")
    artifact_hash = sha256_file(artifact)
    subject_hash = "a" * 64
    metadata_hash = "b" * 64

    write_json(root, "source_provenance.json", {
        "source_url": "https://www.kaggle.com/datasets/sanjukaggling/adnidataset",
        "observed_dataset_name": "ADNI_dataset",
        "discovery_timestamp": "2026-01-01T00:00:00Z",
        "notebook_identity": "00_kaggle_input_binding.ipynb",
        "metadata_attestation": {"sha256": metadata_hash, "byte_size": 123},
    })
    write_json(root, "metadata_manifest.json", {
        "relative_path": "ad_new_2_19_2026.csv",
        "sha256": metadata_hash,
        "byte_size": 123,
        "row_count": 10,
        "columns": ["subject_id", "diagnosis", "scan_id"],
        "required_fields": {"subject_id": True, "diagnosis": True, "scan_id": True},
        "label_counts": {"CN": 5, "MCI": 3, "AD": 2},
    })
    (root / "subject_artifacts.jsonl").write_text(json.dumps({
        "subject_hash": subject_hash,
        "hmac_algorithm": "HMAC-SHA256",
        "hmac_key_id": "acda3d-subject-id",
        "hmac_key_version": "v1",
        "model_ready_relative_path": "artifacts/person.pt",
        "model_ready_sha256": artifact_hash,
        "status": "completed",
    }) + "\n", encoding="utf-8")

    cohort = {
        "task_id": "cn_vs_impaired",
        "class_order": ["CN", "Impaired"],
        "persons": [{"subject_hash": subject_hash, "binary_label": 0}],
    }
    cohort["manifest_sha256"] = digest(json.dumps(cohort, sort_keys=True, separators=(",", ":")).encode())
    write_json(root, "cohort_manifest.json", cohort)

    write_json(root, "splits_manifest.json", {
        "source_folds": {f"fold_{i}": [subject_hash] for i in range(5)},
        "target_adaptation": [subject_hash],
        "target_evaluation": ["c" * 64],
        "target_firewall": {"status": "pass", "fields": ["subject_hash", "cohort"]},
        "manifest_sha256": "d" * 64,
    })
    write_json(root, "privacy_report.json", {
        "hmac_algorithm": "HMAC-SHA256",
        "hmac_key_id": "acda3d-subject-id",
        "hmac_key_version": "v1",
        "raw_ids_emitted": False,
        "secrets_emitted": False,
        "key_stored_in_repository": False,
    })
    write_json(root, "concept_anatomy_reuse.json", {
        "refit": False,
        "regenerated": False,
        "artifacts": {name: {"sha256": (str(index) * 64)[:64]} for index, name in enumerate(
            ["c_target", "g_bar", "normalizer", "roi_order", "atlas", "masks", "jacobian"], 1
        )},
    })
    write_json(root, "oasis_verification.json", {
        "counts": EXPECTED_OASIS,
        "mapping": {"0": "CN", "0.5": "Impaired", "1": "Impaired", "2": "Impaired"},
    })
    bundle_files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "bundle_hashes.json":
            bundle_files[str(path.relative_to(root)).replace("\\", "/")] = sha256_file(path)
    write_json(root, "bundle_hashes.json", {
        "bundle_files": bundle_files,
        "external_source_hashes": {"adni_metadata_csv": metadata_hash},
    })
    write_json(root, "readiness_state.json", {
        "state": "KAGGLE_READINESS_EVIDENCE_PRODUCED",
        "authorization_flags": {
            "authorized": False,
            "real_execution_authorized": False,
            "freeze_approved": False,
            "publication_authorized": False,
            "phase_19_forbidden": True,
        },
    })
    # State hash is intentionally added after bundle hash creation and excluded from
    # the bundle hash fixture to keep the test focused on validation behavior.


def test_valid_bundle_passes() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        create_bundle(root)
        result = validate_bundle(root)
        assert result["valid"], result["errors"]


def test_missing_bundle_file_fails_closed(tmp_path: Path) -> None:
    create_bundle(tmp_path)
    (tmp_path / "metadata_manifest.json").unlink()
    result = validate_bundle(tmp_path)
    assert not result["valid"]
    assert any("metadata_manifest.json" in error for error in result["errors"])


def test_target_overlap_fails_closed(tmp_path: Path) -> None:
    create_bundle(tmp_path)
    splits_path = tmp_path / "splits_manifest.json"
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    splits["target_evaluation"] = splits["target_adaptation"]
    splits_path.write_text(json.dumps(splits), encoding="utf-8")
    result = validate_bundle(tmp_path)
    assert not result["valid"]
    assert any("overlap" in error for error in result["errors"])


def test_oasis_count_mismatch_fails_closed(tmp_path: Path) -> None:
    create_bundle(tmp_path)
    oasis_path = tmp_path / "oasis_verification.json"
    oasis = json.loads(oasis_path.read_text(encoding="utf-8"))
    oasis["counts"]["CN"] = 315
    oasis_path.write_text(json.dumps(oasis), encoding="utf-8")
    result = validate_bundle(tmp_path)
    assert not result["valid"]
    assert any("BLOCKED_COHORT_MISMATCH" in error for error in result["errors"])


def test_cli_json_result_fails_for_missing_root(tmp_path: Path) -> None:
    assert main(["--evidence-root", str(tmp_path / "missing"), "--json"]) == 1
