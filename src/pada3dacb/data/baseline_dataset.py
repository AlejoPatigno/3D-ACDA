"""Classification-only MRI dataset for supervised architectural baselines."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

from pada3dacb.data.records import CLASS_TO_INDEX
from pada3dacb.exceptions import DatasetContractError

_TENSOR_KEYS = ("x", "image", "mri", "tensor", "volume")


def _records_from(value: Any) -> list[Mapping[str, object]]:
    if hasattr(value, "to_dict"):
        value = value.to_dict(orient="records")
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        raise DatasetContractError("Baseline inventory must be an iterable of records.")
    records = list(value)
    if not all(isinstance(record, Mapping) for record in records):
        raise DatasetContractError("Every baseline inventory row must be a mapping.")
    return records


def _load_tensor(path: Path) -> torch.Tensor:
    if not path.is_file():
        raise DatasetContractError(f"MRI tensor path does not exist: {path}.")
    try:
        value = torch.load(path, map_location="cpu", weights_only=True)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise DatasetContractError(f"Failed to load MRI tensor at {path}: {error}") from error
    if isinstance(value, Mapping):
        matches = [value[key] for key in _TENSOR_KEYS if key in value]
        if len(matches) != 1:
            raise DatasetContractError(
                f"MRI mapping at {path} must contain exactly one supported key: {_TENSOR_KEYS}."
            )
        value = matches[0]
    if not torch.is_tensor(value):
        raise DatasetContractError(f"MRI artifact at {path} must contain a tensor.")
    if value.ndim == 3:
        value = value.unsqueeze(0)
    if value.ndim != 4:
        raise DatasetContractError(f"MRI tensor at {path} must have rank 3 or 4, got {value.ndim}.")
    if value.shape[0] != 1:
        raise DatasetContractError(
            f"MRI tensor at {path} must have exactly one channel; silent channel truncation is prohibited."
        )
    if not value.dtype.is_floating_point:
        raise DatasetContractError(f"MRI tensor at {path} must use a floating dtype, got {value.dtype}.")
    value = value.to(device="cpu", dtype=torch.float32).contiguous()
    if not torch.isfinite(value).all():
        raise DatasetContractError(f"MRI tensor at {path} contains non-finite values.")
    return value


class ClassificationOnlyMRIDataset(Dataset):
    """Load model-ready MRI tensors without concept or adaptation artifacts."""

    def __init__(self, inventory: Any) -> None:
        self.records = _records_from(inventory)
        for index, record in enumerate(self.records):
            if "x_path" not in record:
                raise DatasetContractError(f"Baseline inventory row {index} is missing x_path.")
            label = record.get("label", record.get("Label"))
            if label not in CLASS_TO_INDEX:
                raise DatasetContractError(f"Unsupported diagnostic label: {label!r}.")

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        path = Path(record["x_path"])
        label_name = str(record.get("label", record.get("Label")))
        subject_id = str(record.get("subject_id") or path.stem)
        return {
            "x": _load_tensor(path),
            "y": torch.tensor(CLASS_TO_INDEX[label_name], dtype=torch.long),
            "subject_id": subject_id,
            "subject_hash": str(record.get("subject_hash") or subject_id),
            "cohort": str(record.get("cohort") or ""),
            "label_name": label_name,
        }
