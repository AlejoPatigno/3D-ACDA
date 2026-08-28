"""Explicit Phase 6 dataset roles backed by immutable subject records."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import Dataset

from acda3d.artifacts.cache import load_model_ready_tensor
from acda3d.binary import BinarySubjectRecord
from acda3d.data.artifact_wiring import validate_subject_records
from acda3d.data.records import SubjectRecord, requirement_profile
from acda3d.exceptions import DatasetContractError


def load_artifact_vector(path: Path, expected_num_rois: int, name: str) -> torch.Tensor:
    value = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(value, dict):
        aliases = (name, "c_target", "concept_target", "g_bar")
        matches = [value[key] for key in aliases if key in value]
        if not matches:
            raise DatasetContractError(f"Unsupported {name} dictionary at {path}.")
        value = matches[0]
    if not torch.is_tensor(value):
        raise DatasetContractError(f"Expected a tensor at {path}, got {type(value).__name__}.")
    if value.device.type != "cpu" or value.dtype != torch.float32 or tuple(value.shape) != (expected_num_rois,) or not torch.isfinite(value).all():
        raise DatasetContractError(
            f"{name} at {path} must be finite CPU float32 with shape {(expected_num_rois,)}, got {value.device}, {value.dtype}, {tuple(value.shape)}."
        )
    return value.contiguous()


class _RecordDataset(Dataset):
    profile = "classification_only"

    def __init__(self, records: Iterable[SubjectRecord], expected_spatial_shape: tuple[int, int, int] = (128, 128, 128), expected_num_rois: int = 102, validate_on_initialization: bool = True, include_debug_paths: bool = False):
        self.records = list(records)
        self.expected_spatial_shape = tuple(expected_spatial_shape)
        self.expected_num_rois = int(expected_num_rois)
        self.include_debug_paths = include_debug_paths
        if validate_on_initialization:
            requirements = requirement_profile(self.profile)
            errors = validate_subject_records(self.records, requirements, check_files=True)
            if errors:
                raise DatasetContractError("Dataset initialization failed: " + " | ".join(errors))
            for record in self.records:
                load_model_ready_tensor(record.derivative_path, self.expected_spatial_shape)
                if requirements.concept and record.concept_path is not None:
                    load_artifact_vector(record.concept_path, self.expected_num_rois, "c_target")
                if requirements.jacobian and record.jacobian_path is not None:
                    load_artifact_vector(record.jacobian_path, self.expected_num_rois, "g_bar")

    def __len__(self) -> int:
        return len(self.records)

    def _base(self, record: SubjectRecord) -> dict[str, object]:
        item: dict[str, object] = {
            "x": load_model_ready_tensor(record.derivative_path, self.expected_spatial_shape),
            "subject_id": record.public_subject,
            "subject_hash": record.subject_hash,
            "cohort": record.cohort,
        }
        if self.include_debug_paths:
            item["derivative_path"] = str(record.derivative_path)
        return item

    @staticmethod
    def _label(record: SubjectRecord) -> dict[str, object]:
        return {"y": torch.tensor(record.label_index, dtype=torch.long), "label_name": record.class_label}

    def _artifacts(self, record: SubjectRecord, *, concept: bool, jacobian: bool) -> dict[str, torch.Tensor]:
        item: dict[str, torch.Tensor] = {}
        if concept:
            if record.concept_path is None:
                raise DatasetContractError(f"Missing concept path for {record.identity}.")
            item["c_target"] = load_artifact_vector(record.concept_path, self.expected_num_rois, "c_target")
        if jacobian:
            if record.jacobian_path is None:
                raise DatasetContractError(f"Missing Jacobian path for {record.identity}.")
            item["g_bar"] = load_artifact_vector(record.jacobian_path, self.expected_num_rois, "g_bar")
        return item


class LabeledSourceDataset(_RecordDataset):
    profile = "source_full_artifacts"

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        return {**self._base(record), **self._label(record), **self._artifacts(record, concept=True, jacobian=True)}


class TargetAdaptationDataset(_RecordDataset):
    profile = "target_adaptation"

    def __getitem__(self, index: int) -> dict[str, object]:
        return self._base(self.records[index])


class LabeledTargetDataset(_RecordDataset):
    profile = "target_evaluation"

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        return {**self._base(record), **self._label(record)}


class SupervisedMRIDataset(_RecordDataset):
    def __init__(self, records: Iterable[SubjectRecord], *, profile: str = "classification_only", **kwargs: object):
        self.profile = profile
        self.requirements = requirement_profile(profile)
        super().__init__(records, **kwargs)

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        return {
            **self._base(record),
            **self._label(record),
            **self._artifacts(record, concept=self.requirements.concept, jacobian=self.requirements.jacobian),
        }


def _record_map(records: Iterable[SubjectRecord]) -> dict[str, SubjectRecord]:
    return {record.identity: record for record in records}


def _records_for_manifest(frame: pd.DataFrame, records: Iterable[SubjectRecord]) -> list[SubjectRecord]:
    mapping = _record_map(records)
    selected = []
    for _, row in frame.iterrows():
        identity = f"{row['cohort']}:{row['subject_hash']}"
        if identity not in mapping:
            raise DatasetContractError(f"Split row does not resolve to a subject record: {identity}.")
        selected.append(mapping[identity])
    return selected


def build_source_datasets_for_fold(source_folds_manifest: str | Path, fold: int, records: Iterable[SubjectRecord], **kwargs: object) -> tuple[LabeledSourceDataset, LabeledSourceDataset]:
    frame = pd.read_csv(source_folds_manifest)
    selected = frame[frame["fold"] == int(fold)]
    train = _records_for_manifest(selected[selected["partition"] == "source_train"], records)
    validation = _records_for_manifest(selected[selected["partition"] == "source_validation"], records)
    return LabeledSourceDataset(train, **kwargs), LabeledSourceDataset(validation, **kwargs)


def build_target_datasets(target_split_manifest: str | Path, records: Iterable[SubjectRecord], **kwargs: object) -> tuple[TargetAdaptationDataset, LabeledTargetDataset]:
    frame = pd.read_csv(target_split_manifest)
    adaptation = _records_for_manifest(frame[frame["partition"] == "target_adaptation"], records)
    evaluation = _records_for_manifest(frame[frame["partition"] == "target_evaluation"], records)
    return TargetAdaptationDataset(adaptation, **kwargs), LabeledTargetDataset(evaluation, **kwargs)


def build_supervised_datasets_for_fold(source_folds_manifest: str | Path, fold: int, records: Iterable[SubjectRecord], *, profile: str = "classification_only", **kwargs: object) -> tuple[SupervisedMRIDataset, SupervisedMRIDataset]:
    frame = pd.read_csv(source_folds_manifest)
    selected = frame[frame["fold"] == int(fold)]
    train = _records_for_manifest(selected[selected["partition"] == "source_train"], records)
    validation = _records_for_manifest(selected[selected["partition"] == "source_validation"], records)
    return SupervisedMRIDataset(train, profile=profile, **kwargs), SupervisedMRIDataset(validation, profile=profile, **kwargs)


class _BinaryRecordDataset(Dataset):
    """Dataset adapter for the task-scoped binary spine."""

    def __init__(self, records: Iterable[BinarySubjectRecord], expected_spatial_shape: tuple[int, int, int] = (128, 128, 128), *, validate_on_initialization: bool = True) -> None:
        self.records = list(records)
        self.expected_spatial_shape = tuple(expected_spatial_shape)
        if not self.records:
            raise DatasetContractError("Binary dataset cannot be empty")
        for record in self.records:
            if not isinstance(record, BinarySubjectRecord):
                raise DatasetContractError("Binary dataset accepts only BinarySubjectRecord values")
            if record.binary_label not in (0, 1):
                raise DatasetContractError("Binary dataset labels must be 0 or 1")
            if validate_on_initialization and not record.derivative_path.is_file():
                raise DatasetContractError(f"Binary derivative file does not exist: {record.derivative_path}")

    def __len__(self) -> int:
        return len(self.records)

    def _base(self, record: BinarySubjectRecord) -> dict[str, object]:
        return {"x": load_model_ready_tensor(record.derivative_path, self.expected_spatial_shape), "subject_id": record.subject_hash, "subject_hash": record.subject_hash, "cohort": record.cohort}


class BinaryLabeledSourceDataset(_BinaryRecordDataset):
    """Labeled source dataset; provenance is available only on the source side."""

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        return {**self._base(record), "y": torch.tensor(record.binary_label, dtype=torch.long), "binary_label_name": record.binary_label_name, "original_label_name": record.original_label_name, "mapping_contract": record.mapping_contract}


class BinaryTargetAdaptationDataset(_BinaryRecordDataset):
    """Unlabeled target adapter with the exact four-key firewall contract."""

    def __getitem__(self, index: int) -> dict[str, object]:
        return self._base(self.records[index])


class BinaryLabeledTargetDataset(_BinaryRecordDataset):
    """Read-only target evaluation adapter; never use for adaptation loaders."""

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        return {**self._base(record), "y": torch.tensor(record.binary_label, dtype=torch.long), "binary_label_name": record.binary_label_name, "original_label_name": record.original_label_name, "mapping_contract": record.mapping_contract}


def _binary_record_map(records: Iterable[BinarySubjectRecord]) -> dict[str, BinarySubjectRecord]:
    return {f"{record.cohort}:{record.subject_hash}": record for record in records}


def _binary_records_for_manifest(frame: pd.DataFrame, records: Iterable[BinarySubjectRecord]) -> list[BinarySubjectRecord]:
    mapping = _binary_record_map(records)
    selected: list[BinarySubjectRecord] = []
    for _, row in frame.iterrows():
        identity = f"{row['cohort']}:{row['subject_hash']}"
        if identity not in mapping:
            raise DatasetContractError(f"Binary split row does not resolve to a subject record: {identity}.")
        selected.append(mapping[identity])
    return selected


def build_binary_source_datasets_for_fold(source_folds_manifest: str | Path, fold: int, records: Iterable[BinarySubjectRecord], **kwargs: object) -> tuple[BinaryLabeledSourceDataset, BinaryLabeledSourceDataset]:
    frame = pd.read_csv(source_folds_manifest)
    if {"class_label", "label_index"}.intersection(frame.columns):
        raise DatasetContractError("Historical three-class split columns are not valid for binary datasets")
    selected = frame[frame["fold"] == int(fold)]
    train = _binary_records_for_manifest(selected[selected["partition"] == "source_train"], records)
    validation = _binary_records_for_manifest(selected[selected["partition"] == "source_validation"], records)
    return BinaryLabeledSourceDataset(train, **kwargs), BinaryLabeledSourceDataset(validation, **kwargs)


def build_binary_target_datasets(target_split_manifest: str | Path, records: Iterable[BinarySubjectRecord], **kwargs: object) -> tuple[BinaryTargetAdaptationDataset, BinaryLabeledTargetDataset]:
    frame = pd.read_csv(target_split_manifest)
    if {"class_label", "label_index"}.intersection(frame.columns):
        raise DatasetContractError("Historical three-class split columns are not valid for binary datasets")
    adaptation = _binary_records_for_manifest(frame[frame["partition"] == "target_adaptation"], records)
    evaluation = _binary_records_for_manifest(frame[frame["partition"] == "target_evaluation"], records)
    if {record.subject_hash for record in adaptation} & {record.subject_hash for record in evaluation}:
        raise DatasetContractError("Binary target adaptation and evaluation assignments overlap")
    return BinaryTargetAdaptationDataset(adaptation, **kwargs), BinaryLabeledTargetDataset(evaluation, **kwargs)
