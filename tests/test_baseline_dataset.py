from __future__ import annotations

from pathlib import Path

import pytest
import torch

from acda3d.data.baseline_dataset import ClassificationOnlyMRIDataset
from acda3d.exceptions import DatasetContractError


def _row(path: Path, label: str = "MCI") -> dict[str, object]:
    return {
        "x_path": path,
        "label": label,
        "subject_id": "subject-01",
        "subject_hash": "hash-01",
        "cohort": "ADNI",
    }


def test_dataset_loads_direct_tensor_and_returns_classification_schema(tmp_path: Path) -> None:
    path = tmp_path / "scan.pt"
    torch.save(torch.ones(5, 6, 7), path)

    item = ClassificationOnlyMRIDataset([_row(path)])[0]

    assert set(item) == {"x", "y", "subject_id", "subject_hash", "cohort", "label_name"}
    assert item["x"].shape == (1, 5, 6, 7)
    assert item["x"].dtype == torch.float32
    assert item["y"].item() == 1
    assert item["label_name"] == "MCI"
    assert "c_target" not in item and "g_bar" not in item


@pytest.mark.parametrize("key", ["x", "image", "mri", "tensor", "volume"])
def test_dataset_loads_only_explicit_mapping_keys(tmp_path: Path, key: str) -> None:
    path = tmp_path / f"{key}.pt"
    torch.save({key: torch.zeros(1, 4, 4, 4)}, path)

    assert ClassificationOnlyMRIDataset([_row(path, "CN")])[0]["x"].shape == (1, 4, 4, 4)


@pytest.mark.parametrize(("label", "index"), [("CN", 0), ("MCI", 1), ("AD", 2)])
def test_dataset_uses_fixed_diagnostic_order(tmp_path: Path, label: str, index: int) -> None:
    path = tmp_path / f"{label}.pt"
    torch.save(torch.zeros(1, 3, 3, 3), path)

    assert ClassificationOnlyMRIDataset([_row(path, label)])[0]["y"].item() == index


def test_dataset_accepts_legacy_capital_label_column(tmp_path: Path) -> None:
    path = tmp_path / "scan.pt"
    torch.save(torch.zeros(1, 3, 3, 3), path)
    row = _row(path)
    row["Label"] = row.pop("label")

    assert ClassificationOnlyMRIDataset([row])[0]["label_name"] == "MCI"


@pytest.mark.parametrize(
    "payload",
    [
        {"unexpected": torch.zeros(1, 3, 3, 3)},
        torch.zeros(2, 3, 3, 3),
        torch.zeros(2, 3),
        torch.tensor([[[[float("nan")]]]]),
        torch.ones(1, 3, 3, 3, dtype=torch.int64),
    ],
)
def test_dataset_rejects_ambiguous_or_invalid_tensor_payloads(tmp_path: Path, payload: object) -> None:
    path = tmp_path / "invalid.pt"
    torch.save(payload, path)

    with pytest.raises(DatasetContractError):
        ClassificationOnlyMRIDataset([_row(path)])[0]


def test_dataset_rejects_missing_file_and_unknown_label(tmp_path: Path) -> None:
    with pytest.raises(DatasetContractError, match="does not exist"):
        ClassificationOnlyMRIDataset([_row(tmp_path / "missing.pt")])[0]

    path = tmp_path / "scan.pt"
    torch.save(torch.zeros(1, 3, 3, 3), path)
    with pytest.raises(DatasetContractError, match="Unsupported diagnostic label"):
        ClassificationOnlyMRIDataset([_row(path, "UNKNOWN")])


def test_dataset_is_deterministic_and_does_not_mutate_source_rows(tmp_path: Path) -> None:
    path = tmp_path / "scan.pt"
    torch.save(torch.arange(27, dtype=torch.float32).reshape(1, 3, 3, 3), path)
    row = _row(path)
    dataset = ClassificationOnlyMRIDataset([row])

    first = dataset[0]
    second = dataset[0]

    assert torch.equal(first["x"], second["x"])
    assert row["x_path"] == path
