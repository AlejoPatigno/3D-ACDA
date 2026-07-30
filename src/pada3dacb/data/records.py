"""Typed common subject records for all Phase 6 dataset roles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pada3dacb.exceptions import DatasetContractError

CLASS_ORDER = ("CN", "MCI", "AD")
CLASS_TO_INDEX = {label: index for index, label in enumerate(CLASS_ORDER)}
SUPPORTED_COHORTS = {"ADNI", "OASIS"}


@dataclass(frozen=True)
class ArtifactRequirements:
    derivative: bool = True
    label: bool = True
    concept: bool = False
    jacobian: bool = False


REQUIREMENT_PROFILES = {
    "classification_only": ArtifactRequirements(),
    "source_with_concepts": ArtifactRequirements(concept=True),
    "source_with_anatomy": ArtifactRequirements(jacobian=True),
    "source_full_artifacts": ArtifactRequirements(concept=True, jacobian=True),
    "target_adaptation": ArtifactRequirements(label=False),
    "target_evaluation": ArtifactRequirements(),
}


@dataclass(frozen=True)
class SubjectRecord:
    subject_hash: str
    cohort: str
    class_label: str
    label_index: int
    derivative_path: Path
    subject_id: str | None = None
    concept_path: Path | None = None
    jacobian_path: Path | None = None
    preprocessing_configuration_hash: str | None = None
    precompute_configuration_hash: str | None = None
    atlas_hash: str | None = None
    concept_status: str | None = None
    jacobian_status: str | None = None
    original_inventory_row: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return f"{self.cohort}:{self.subject_hash}"

    @property
    def public_subject(self) -> str:
        return self.subject_id or self.subject_hash

    def validate(self) -> None:
        if self.cohort not in SUPPORTED_COHORTS:
            raise DatasetContractError(f"Unsupported cohort: {self.cohort!r}.")
        if self.class_label not in CLASS_TO_INDEX:
            raise DatasetContractError(f"Unsupported diagnostic label: {self.class_label!r}.")
        expected = CLASS_TO_INDEX[self.class_label]
        if self.label_index != expected:
            raise DatasetContractError(
                f"Label/index mismatch for {self.identity}: {self.class_label} requires {expected}, got {self.label_index}."
            )
        if not self.subject_hash.strip():
            raise DatasetContractError("subject_hash cannot be empty.")
        if not self.derivative_path.is_absolute():
            raise DatasetContractError(f"Derivative path is not resolved: {self.derivative_path}.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("derivative_path", "concept_path", "jacobian_path"):
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SubjectRecord:
        data = dict(payload)
        for key in ("derivative_path", "concept_path", "jacobian_path"):
            if data.get(key) is not None:
                data[key] = Path(data[key])
        record = cls(**data)
        record.validate()
        return record


def requirement_profile(name: str) -> ArtifactRequirements:
    try:
        return REQUIREMENT_PROFILES[name]
    except KeyError as error:
        raise DatasetContractError(f"Unknown dataset requirement profile: {name!r}.") from error
