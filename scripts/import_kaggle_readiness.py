#!/usr/bin/env python3
"""Validate a de-identified Kaggle Phase 18D readiness bundle.

The importer never reads raw cohort files and never writes into the supplied
bundle. Hashes are recomputed only for files present in the bundle. Hashes of
external Kaggle inputs are accepted only as attested provenance fields.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_URL = "https://www.kaggle.com/datasets/sanjukaggling/adnidataset"
EXPECTED_DATASET_NAME = "ADNI_dataset"
EXPECTED_TASK = "cn_vs_impaired"
EXPECTED_CLASS_ORDER = ["CN", "Impaired"]
EXPECTED_OASIS = {
    "visits": 436,
    "canonical_persons": 416,
    "repeated_visits_excluded": 20,
    "CN": 316,
    "Impaired": 100,
}
REQUIRED_FILES = (
    "source_provenance.json",
    "metadata_manifest.json",
    "subject_artifacts.jsonl",
    "cohort_manifest.json",
    "splits_manifest.json",
    "privacy_report.json",
    "concept_anatomy_reuse.json",
    "readiness_state.json",
)
_HEX = frozenset("0123456789abcdef")


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def load_jsonl(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL line {line_number} is not an object")
            rows.append(value)
    return rows


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _errors_for_hash(value: Any, field: str) -> list[str]:
    return [] if is_sha256(value) else [f"{field} must be a lowercase SHA-256 digest"]


def _safe_bundle_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if root.resolve() not in candidate.parents:
        raise ValueError(f"Bundle path escapes evidence root: {relative}")
    return candidate


def validate_source_provenance(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "source_provenance.json")
        if data.get("source_url") != EXPECTED_SOURCE_URL:
            errors.append("Unexpected ADNI source URL")
        if data.get("observed_dataset_name") != EXPECTED_DATASET_NAME:
            errors.append("Unexpected Kaggle dataset identity")
        for field in ("discovery_timestamp", "notebook_identity", "metadata_attestation"):
            if field not in data:
                errors.append(f"Missing source provenance field: {field}")
        attestation = data.get("metadata_attestation", {})
        errors.extend(_errors_for_hash(attestation.get("sha256"), "metadata_attestation.sha256"))
        if not isinstance(attestation.get("byte_size"), int) or attestation["byte_size"] <= 0:
            errors.append("metadata_attestation.byte_size must be positive")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid source_provenance.json: {exc}")
    return not errors, errors


def validate_metadata_manifest(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "metadata_manifest.json")
        for field in ("relative_path", "sha256", "byte_size", "row_count", "columns", "required_fields", "label_counts"):
            if field not in data:
                errors.append(f"Missing metadata field: {field}")
        errors.extend(_errors_for_hash(data.get("sha256"), "metadata_manifest.sha256"))
        if not isinstance(data.get("byte_size"), int) or data["byte_size"] <= 0:
            errors.append("metadata_manifest.byte_size must be positive")
        if not isinstance(data.get("row_count"), int) or data["row_count"] <= 0:
            errors.append("metadata_manifest.row_count must be positive")
        required = data.get("required_fields", {})
        if not isinstance(required, dict) or not required or not all(required.values()):
            errors.append("All required metadata fields must be present")
        labels = data.get("label_counts", {})
        if not isinstance(labels, dict) or set(labels) - {"CN", "MCI", "AD"}:
            errors.append("Metadata labels must be restricted to CN, MCI, and AD")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid metadata_manifest.json: {exc}")
    return not errors, errors


def validate_subject_artifacts(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    bundle = Path(root).resolve()
    try:
        rows = load_jsonl(bundle / "subject_artifacts.jsonl")
        tokens: set[str] = set()
        for index, row in enumerate(rows):
            prefix = f"subject_artifacts.jsonl[{index}]"
            token = row.get("subject_hash") or row.get("subject_token")
            if not is_sha256(token):
                errors.append(f"{prefix}.subject_hash must be HMAC token digest")
            elif token in tokens:
                errors.append(f"Duplicate subject hash: {token}")
            else:
                tokens.add(token)
            if row.get("hmac_algorithm") != "HMAC-SHA256":
                errors.append(f"{prefix} has invalid HMAC algorithm")
            if row.get("status") not in {"pending", "running", "completed", "failed"}:
                errors.append(f"{prefix}.status is invalid")
            artifact_hash = row.get("model_ready_sha256") or row.get("artifact_sha256")
            if row.get("status") == "completed":
                errors.extend(_errors_for_hash(artifact_hash, f"{prefix}.model_ready_sha256"))
                relative = row.get("model_ready_relative_path") or row.get("artifact_path")
                if not isinstance(relative, str) or not relative:
                    errors.append(f"{prefix} is completed without an artifact path")
                else:
                    try:
                        artifact = _safe_bundle_path(bundle, relative)
                        if not artifact.is_file():
                            errors.append(f"Missing bundle artifact: {relative}")
                        elif sha256_file(artifact) != artifact_hash:
                            errors.append(f"Artifact hash mismatch: {relative}")
                    except ValueError as exc:
                        errors.append(str(exc))
        if not rows:
            errors.append("subject_artifacts.jsonl must not be empty")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid subject_artifacts.jsonl: {exc}")
    return not errors, errors


def _manifest_hash(data: dict[str, Any], field: str = "manifest_sha256") -> str:
    copy = dict(data)
    copy.pop(field, None)
    encoded = json.dumps(copy, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(encoded)


def validate_cohort_manifest(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "cohort_manifest.json")
        if data.get("task_id") != EXPECTED_TASK:
            errors.append("cohort_manifest.task_id must be cn_vs_impaired")
        if data.get("class_order") != EXPECTED_CLASS_ORDER:
            errors.append("cohort_manifest.class_order must be [CN, Impaired]")
        persons = data.get("persons")
        if not isinstance(persons, list) or not persons:
            errors.append("cohort_manifest.persons must be non-empty")
        else:
            seen: set[str] = set()
            for index, person in enumerate(persons):
                token = person.get("subject_hash") if isinstance(person, dict) else None
                if not is_sha256(token):
                    errors.append(f"Invalid cohort person hash at index {index}")
                elif token in seen:
                    errors.append(f"Duplicate cohort person hash: {token}")
                else:
                    seen.add(token)
                if isinstance(person, dict) and person.get("binary_label") not in (0, 1):
                    errors.append(f"Invalid binary label at index {index}")
        if not is_sha256(data.get("manifest_sha256")):
            errors.append("cohort_manifest.manifest_sha256 is invalid")
        elif _manifest_hash(data) != data["manifest_sha256"]:
            errors.append("cohort_manifest.manifest_sha256 does not match content")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid cohort_manifest.json: {exc}")
    return not errors, errors


def validate_splits_manifest(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "splits_manifest.json")
        folds = data.get("source_folds", data.get("source_fold_membership"))
        if not isinstance(folds, dict) or set(folds) != {f"fold_{i}" for i in range(5)}:
            errors.append("Exactly fold_0 through fold_4 are required")
        target_a = set(data.get("target_adaptation", data.get("target_adaptation_membership", [])))
        target_e = set(data.get("target_evaluation", data.get("target_evaluation_membership", [])))
        if not target_a or not target_e:
            errors.append("Target adaptation/evaluation partitions must be non-empty")
        overlap = target_a & target_e
        if overlap:
            errors.append(f"Target adaptation/evaluation overlap: {len(overlap)}")
        if not ((isinstance(data.get("target_firewall"), dict) and data["target_firewall"].get("status") == "pass") or data.get("target_firewall") == "pass" or data.get("target_firewall_result") == "pass"):
            errors.append("Target firewall did not pass")
        if not is_sha256(data.get("manifest_sha256")):
            errors.append("splits_manifest.manifest_sha256 is invalid")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid splits_manifest.json: {exc}")
    return not errors, errors


def validate_privacy_report(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "privacy_report.json")
        if data.get("hmac_algorithm") != "HMAC-SHA256":
            errors.append("privacy_report must declare HMAC-SHA256")
        if data.get("raw_ids_emitted") is not False or data.get("secrets_emitted") is not False:
            errors.append("Raw IDs and secrets must both be false")
        if data.get("key_stored_in_repository") is not False:
            errors.append("HMAC key must not be stored in repository")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid privacy_report.json: {exc}")
    return not errors, errors


def validate_concept_anatomy_reuse(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "concept_anatomy_reuse.json")
        if data.get("refit") is True or data.get("regenerated") is True:
            errors.append("Concept/anatomy artifacts must be reused without refit/regeneration")
        artifacts = data.get("artifacts", {})
        if not isinstance(artifacts, dict) or not artifacts:
            errors.append("Concept/anatomy artifact identities are missing")
        for name, record in artifacts.items():
            digest = record.get("sha256") if isinstance(record, dict) else record
            errors.extend(_errors_for_hash(digest, f"concept_anatomy.{name}.sha256"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid concept_anatomy_reuse.json: {exc}")
    return not errors, errors


def validate_oasis_cohort(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "oasis_verification.json")
        observed = data.get("counts", {})
        for field, expected in EXPECTED_OASIS.items():
            if observed.get(field) != expected:
                errors.append(f"BLOCKED_COHORT_MISMATCH: OASIS {field} expected {expected}, got {observed.get(field)}")
        if data.get("mapping") != {"0": "CN", "0.5": "Impaired", "1": "Impaired", "2": "Impaired"}:
            errors.append("BLOCKED_COHORT_MISMATCH: OASIS mapping is not approved")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid oasis_verification.json: {exc}")
    return not errors, errors


def validate_readiness_state(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = load_json(Path(root) / "readiness_state.json")
        if data.get("state") != "KAGGLE_READINESS_EVIDENCE_PRODUCED":
            errors.append("Importer accepts only KAGGLE_READINESS_EVIDENCE_PRODUCED")
        flags = data.get("authorization_flags", {})
        expected = {"authorized": False, "real_execution_authorized": False, "freeze_approved": False, "publication_authorized": False, "phase_19_forbidden": True}
        for key, value in expected.items():
            if flags.get(key) is not value:
                errors.append(f"Authorization flag {key} must be {value}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid readiness_state.json: {exc}")
    return not errors, errors


def validate_bundle_hashes(root: str | os.PathLike[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    path = Path(root) / "bundle_hashes.json"
    if not path.exists():
        return False, ["Missing bundle_hashes.json"]
    try:
        data = load_json(path)
        for relative, expected in data.get("bundle_files", {}).items():
            errors.extend(_errors_for_hash(expected, f"bundle_files.{relative}"))
            try:
                actual = sha256_file(_safe_bundle_path(Path(root), relative))
                if actual != expected:
                    errors.append(f"Bundle hash mismatch: {relative}")
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        for field in ("external_source_hashes",):
            for name, expected in data.get(field, {}).items():
                errors.extend(_errors_for_hash(expected, f"{field}.{name}"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid bundle_hashes.json: {exc}")
    return not errors, errors


def validate_bundle(root: str | os.PathLike[str]) -> dict[str, Any]:
    evidence_root = Path(root).resolve()
    errors: list[str] = []
    for filename in REQUIRED_FILES + ("oasis_verification.json", "bundle_hashes.json"):
        if not (evidence_root / filename).is_file():
            errors.append(f"Missing required evidence file: {filename}")
    validators = (
        validate_source_provenance,
        validate_metadata_manifest,
        validate_subject_artifacts,
        validate_cohort_manifest,
        validate_splits_manifest,
        validate_privacy_report,
        validate_concept_anatomy_reuse,
        validate_oasis_cohort,
        validate_readiness_state,
        validate_bundle_hashes,
    )
    if not errors:
        for validator in validators:
            passed, validator_errors = validator(evidence_root)
            if not passed:
                errors.extend(validator_errors)
    return {"valid": not errors, "evidence_root": str(evidence_root), "errors": errors}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = validate_bundle(args.evidence_root)
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    elif result["valid"]:
        print("KAGGLE_READINESS_EVIDENCE_IMPORTED: validation PASS")
    else:
        print("KAGGLE_READINESS_EVIDENCE_IMPORTED: validation BLOCKED", file=sys.stderr)
        for error in result["errors"]:
            print(f"- {error}", file=sys.stderr)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
