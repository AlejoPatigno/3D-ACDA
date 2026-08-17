"""Load the Phase 5 artifact index into validated common subject records."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pandas as pd

from pada3dacb.binary import BinarySubjectRecord
from pada3dacb.data.records import (
    CLASS_TO_INDEX,
    ArtifactRequirements,
    SubjectRecord,
    requirement_profile,
)
from pada3dacb.exceptions import DatasetContractError

VALID_ARTIFACT_STATUSES = {"COMPUTED", "SKIPPED_VALID"}


@dataclass
class ArtifactValidationReport:
    index_path: str
    index_hash: str
    total_rows: int
    valid_records: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    remappings: list[dict[str, str]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


@dataclass
class ArtifactIndexResult:
    records: list[SubjectRecord]
    report: ArtifactValidationReport


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_value(
    value: Any,
    root: Path,
    *,
    old_prefix: Path | None,
    new_prefix: Path | None,
    report: ArtifactValidationReport,
) -> Path | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    path = Path(str(value))
    if old_prefix is not None and new_prefix is not None:
        try:
            relative = path.relative_to(old_prefix)
        except ValueError:
            pass
        else:
            remapped = (new_prefix / relative).resolve()
            report.remappings.append({"old": str(path), "new": str(remapped)})
            return remapped
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def build_subject_records(
    frame: pd.DataFrame,
    artifact_root: Path,
    report: ArtifactValidationReport,
    *,
    old_prefix: Path | None = None,
    new_prefix: Path | None = None,
) -> list[SubjectRecord]:
    records: list[SubjectRecord] = []
    for row_number, row in frame.iterrows():
        label = str(row.get("class_label", ""))
        raw_index = row.get("label_index")
        label_index = CLASS_TO_INDEX.get(label, -1) if pd.isna(raw_index) or raw_index is None else int(raw_index)
        metadata = {key: value for key, value in row.to_dict().items() if key not in {
            "subject_id", "subject_hash", "cohort", "class_label", "label_index",
            "derivative_path", "concept_path", "jacobian_path",
        }}
        record = SubjectRecord(
            subject_id=None if pd.isna(row.get("subject_id")) else str(row.get("subject_id")),
            subject_hash=str(row.get("subject_hash", "")),
            cohort=str(row.get("cohort", "")),
            class_label=label,
            label_index=label_index,
            derivative_path=_path_value(row.get("derivative_path"), artifact_root, old_prefix=old_prefix, new_prefix=new_prefix, report=report) or Path(),
            concept_path=_path_value(row.get("concept_path"), artifact_root, old_prefix=old_prefix, new_prefix=new_prefix, report=report),
            jacobian_path=_path_value(row.get("jacobian_path"), artifact_root, old_prefix=old_prefix, new_prefix=new_prefix, report=report),
            preprocessing_configuration_hash=_optional_text(row.get("preprocessing_configuration_hash")),
            precompute_configuration_hash=_optional_text(row.get("precompute_configuration_hash")),
            atlas_hash=_optional_text(row.get("atlas_configuration_hash", row.get("atlas_hash"))),
            concept_status=_optional_text(row.get("concept_status")),
            jacobian_status=_optional_text(row.get("jacobian_status")),
            original_inventory_row=int(row.get("inventory_row", row_number)),
            metadata=metadata,
        )
        records.append(record)
    return records


def _optional_text(value: Any) -> str | None:
    return None if value is None or pd.isna(value) or str(value).strip() == "" else str(value)


def validate_subject_records(
    records: Iterable[SubjectRecord],
    requirements: ArtifactRequirements,
    *,
    check_files: bool = True,
) -> list[str]:
    records = list(records)
    errors: list[str] = []
    identities: set[str] = set()
    derivatives: set[Path] = set()
    for record in records:
        try:
            record.validate()
        except DatasetContractError as error:
            errors.append(str(error))
            continue
        if record.identity in identities:
            errors.append(f"Duplicate subject identity: {record.identity}.")
        identities.add(record.identity)
        if record.derivative_path in derivatives:
            errors.append(f"Duplicate derivative path: {record.derivative_path}.")
        derivatives.add(record.derivative_path)
        required_paths = [("derivative", record.derivative_path, True)]
        required_paths.extend([
            ("concept", record.concept_path, requirements.concept),
            ("jacobian", record.jacobian_path, requirements.jacobian),
        ])
        for name, path, required in required_paths:
            if required and path is None:
                errors.append(f"{record.identity} is missing required {name} path.")
            elif required and check_files and path is not None and not path.is_file():
                errors.append(f"{record.identity} required {name} file does not exist: {path}.")
        if requirements.concept and record.concept_status not in VALID_ARTIFACT_STATUSES:
            errors.append(f"{record.identity} has invalid concept status: {record.concept_status!r}.")
        if requirements.jacobian and record.jacobian_status not in VALID_ARTIFACT_STATUSES:
            errors.append(f"{record.identity} has invalid Jacobian status: {record.jacobian_status!r}.")
    return errors


def load_artifact_index(
    index_path: str | Path,
    *,
    artifact_root: str | Path | None = None,
    profile: str = "classification_only",
    old_prefix: str | Path | None = None,
    new_prefix: str | Path | None = None,
    check_files: bool = True,
) -> ArtifactIndexResult:
    path = Path(index_path).resolve()
    if not path.is_file():
        raise DatasetContractError(f"Artifact index does not exist: {path}.")
    frame = pd.read_csv(path)
    required = {"subject_hash", "cohort", "class_label", "derivative_path"}
    missing = required.difference(frame.columns)
    if missing:
        raise DatasetContractError(f"Artifact index is missing columns: {sorted(missing)}.")
    report = ArtifactValidationReport(str(path), _file_hash(path), len(frame))
    root = Path(artifact_root).resolve() if artifact_root else path.parent
    records = build_subject_records(
        frame,
        root,
        report,
        old_prefix=Path(old_prefix) if old_prefix else None,
        new_prefix=Path(new_prefix) if new_prefix else None,
    )
    records.sort(key=lambda record: (record.cohort, record.subject_hash))
    report.errors.extend(validate_subject_records(records, requirement_profile(profile), check_files=check_files))
    report.valid_records = len(records) if report.valid else 0
    if report.errors:
        raise DatasetContractError("Artifact-index validation failed: " + " | ".join(report.errors))
    return ArtifactIndexResult(records, report)


def remap_artifact_root(records: Iterable[SubjectRecord], old_prefix: str | Path, new_prefix: str | Path) -> tuple[list[SubjectRecord], list[dict[str, str]]]:
    report = ArtifactValidationReport("", "", 0)
    frame = pd.DataFrame([record.to_dict() for record in records])
    remapped = build_subject_records(frame, Path(new_prefix), report, old_prefix=Path(old_prefix), new_prefix=Path(new_prefix))
    return remapped, report.remappings


def summarize_record_coverage(records: Iterable[SubjectRecord]) -> pd.DataFrame:
    rows = [{"cohort": record.cohort, "class_label": record.class_label, "has_concept": record.concept_path is not None, "has_jacobian": record.jacobian_path is not None} for record in records]
    return pd.DataFrame(rows).groupby(["cohort", "class_label"], as_index=False).agg(subjects=("class_label", "size"), concepts=("has_concept", "sum"), jacobians=("has_jacobian", "sum"))


def build_binary_subject_records(frame: pd.DataFrame, artifact_root: Path, *, oasis_provenance_verified: bool = False, check_files: bool = True) -> list[BinarySubjectRecord]:
    """Build task-scoped binary records without changing historical index semantics."""
    required = {"subject_hash", "cohort", "derivative_path"}
    missing = required.difference(frame.columns)
    if missing:
        raise DatasetContractError(f"Binary artifact index is missing columns: {sorted(missing)}")
    records: list[BinarySubjectRecord] = []
    for row_number, row in frame.iterrows():
        cohort = str(row.get("cohort", "")).upper()
        subject_id = row.get("subject_id", row.get("subject_hash"))
        original = row.get("original_label_name", row.get("binary_label_name", row.get("class_label")))
        verified = oasis_provenance_verified or row.get("verified_binary_provenance") is True
        if cohort == "OASIS" and not verified:
            raise DatasetContractError("OASIS binary artifact rows require verified binary provenance")
        if cohort == "OASIS" and row.get("mapping_contract", "phase-18b-binary-v1") != "phase-18b-binary-v1":
            raise DatasetContractError("OASIS binary mapping contract is incompatible")
        report = ArtifactValidationReport("", "", 0)
        derivative = _path_value(row.get("derivative_path"), artifact_root, old_prefix=None, new_prefix=None, report=report)
        if derivative is None:
            raise DatasetContractError(f"Binary row {row_number} is missing derivative_path")
        if check_files and not derivative.is_file():
            raise DatasetContractError(f"Binary derivative file does not exist: {derivative}")
        try:
            adapted = BinarySubjectRecord.from_source(
                cohort=cohort, subject_id=subject_id, original_label=original, source_row=row_number,
                derivative_path=derivative, visit_id=row.get("visit_id"),
                source_file_hash=_optional_text(row.get("source_file_hash")),
                metadata_only=bool(row.get("metadata_only", False)),
            )
            provided_hash = str(row.get("subject_hash", ""))
            if len(provided_hash) == 64 and all(char in "0123456789abcdef" for char in provided_hash):
                adapted = replace(adapted, subject_hash=provided_hash)
            provided_row_hash = _optional_text(row.get("source_row_hash"))
            if provided_row_hash and len(provided_row_hash) == 64 and all(char in "0123456789abcdef" for char in provided_row_hash):
                adapted = replace(adapted, source_row_hash=provided_row_hash)
            records.append(adapted)
        except (TypeError, ValueError) as error:
            raise DatasetContractError(f"Invalid binary artifact row {row_number}: {error}") from error
    if not records:
        raise DatasetContractError("Binary artifact index cannot be empty")
    if len({record.subject_hash for record in records}) != len(records):
        raise DatasetContractError("Binary artifact index contains duplicate subject hashes")
    if {record.binary_label for record in records} != {0, 1}:
        raise DatasetContractError("Binary artifact index must contain CN and Impaired")
    return records


def load_binary_artifact_index(index_path: str | Path, *, artifact_root: str | Path | None = None, oasis_provenance_verified: bool = False, check_files: bool = True) -> list[BinarySubjectRecord]:
    path = Path(index_path).resolve()
    if not path.is_file():
        raise DatasetContractError(f"Binary artifact index does not exist: {path}")
    root = Path(artifact_root).resolve() if artifact_root else path.parent
    return build_binary_subject_records(pd.read_csv(path), root, oasis_provenance_verified=oasis_provenance_verified, check_files=check_files)
