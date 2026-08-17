from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch import nn

from pada3dacb.binary import BINARY_MAPPING_CONTRACT, BinarySubjectRecord
from pada3dacb.data.datasets import (
    BinaryLabeledSourceDataset,
    BinaryTargetAdaptationDataset,
)
from pada3dacb.data.records import SubjectRecord, binary_record_from_subject_record
from pada3dacb.data.splits import (
    generate_binary_source_folds_for_records,
    generate_binary_target_partition_for_records,
    validate_binary_split_manifest,
)
from pada3dacb.exceptions import DatasetContractError, SplitValidationError, TrainingRuntimeError
from pada3dacb.models.checkpoint_migration import load_binary_checkpoint
from pada3dacb.training.checkpointing import validate_binary_checkpoint_metadata
from pada3dacb.training.uda_trainer import UDATrainer

TEST_SUBJECT_HASH_KEY = b"phase18b-test-subject-hmac-key!!"


def _binary_records(cohort: str = "ADNI") -> list[BinarySubjectRecord]:
    return [
        BinarySubjectRecord.from_source(
            cohort=cohort,
            subject_id=f"subject-{i}",
            original_label="CN" if i % 2 == 0 else ("MCI" if cohort == "ADNI" else "Impaired"),
            source_row=f"row-{i}",
            derivative_path=Path(f"{cohort}-{i}.pt").resolve(),
            subject_hash_key=TEST_SUBJECT_HASH_KEY if cohort == "OASIS" else None,
        )
        for i in range(10)
    ]


def test_binary_record_adapter_preserves_historical_subject_record_and_oasis_requires_provenance(tmp_path: Path) -> None:
    source = SubjectRecord(
        subject_hash="historical-hash",
        cohort="ADNI",
        class_label="MCI",
        label_index=1,
        derivative_path=(tmp_path / "x.pt").resolve(),
        subject_id="ADNI-1",
        original_inventory_row=7,
    )
    record = binary_record_from_subject_record(source)
    assert source.class_label == "MCI"
    assert record.original_label_name == "MCI"
    assert record.binary_label_name == "Impaired"
    assert record.binary_label == 1

    oasis = SubjectRecord(
        subject_hash="oasis-hash",
        cohort="OASIS",
        class_label="CN",
        label_index=0,
        derivative_path=(tmp_path / "oasis.pt").resolve(),
        subject_id="OASIS-1",
    )
    with pytest.raises(DatasetContractError, match="provenance|Evidence|approval"):
        binary_record_from_subject_record(oasis)


def test_binary_dataset_adapters_keep_target_batch_exactly_unlabeled(tmp_path: Path) -> None:
    derivative = tmp_path / "x.pt"
    torch.save(torch.zeros(1, 4, 4, 4), derivative)
    records = [
        BinarySubjectRecord.from_source(
            cohort="ADNI", subject_id="s0", original_label="CN", source_row="r0", derivative_path=derivative
        ),
        BinarySubjectRecord.from_source(
            cohort="ADNI", subject_id="s1", original_label="AD", source_row="r1", derivative_path=derivative
        ),
    ]
    source = BinaryLabeledSourceDataset(records, expected_spatial_shape=(4, 4, 4))
    assert source[0]["y"].item() in {0, 1}
    assert source[1]["original_label_name"] == "AD"
    target = BinaryTargetAdaptationDataset(records, expected_spatial_shape=(4, 4, 4))
    assert set(target[0]) == {"x", "subject_id", "subject_hash", "cohort"}


def test_binary_split_manifest_is_task_bound_deterministic_and_disjoint() -> None:
    source = _binary_records()
    folds = generate_binary_source_folds_for_records(source)
    target = generate_binary_target_partition_for_records(_binary_records("OASIS"))
    assert folds == generate_binary_source_folds_for_records(source)
    assert target == generate_binary_target_partition_for_records(_binary_records("OASIS"))
    validate_binary_split_manifest(folds, target)
    assert all(fold["split_identity"] for fold in folds)
    assert target["split_identity"]
    assert not set(target["target_adaptation"]) & set(target["target_evaluation"])
    with pytest.raises(SplitValidationError, match="historical|three-class"):
        validate_binary_split_manifest(
            [{**fold, "class_order": ["CN", "MCI", "AD"]} for fold in folds], target
        )


def test_binary_target_firewall_is_exact_before_forward() -> None:
    valid = {"x": torch.ones(2, 1), "subject_id": ["a", "b"], "subject_hash": ["a", "b"], "cohort": ["OASIS", "OASIS"]}
    UDATrainer._validate_target_batch(valid, strict=True)
    for invalid in (
        {key: value for key, value in valid.items() if key != "cohort"},
        {**valid, "diagnosis": ["CN", "AD"]},
        {**valid, "extra": 1},
    ):
        with pytest.raises(TrainingRuntimeError):
            UDATrainer._validate_target_batch(invalid, strict=True)


def test_binary_checkpoint_metadata_is_complete_and_tamper_evident() -> None:
    configuration = {"task_id": "cn_vs_impaired", "num_classes": 2, "seed": 42}
    metadata = {
        "task_id": "cn_vs_impaired",
        "class_order": ["CN", "Impaired"],
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "split_identity": "a" * 64,
        "split_assignment_hash": "b" * 64,
        "configuration_payload": configuration,
        "configuration_payload_hash": __import__("pada3dacb.training.checkpointing", fromlist=["configuration_hash"]).configuration_hash(configuration),
        "binary_classifier_cardinality": 2,
    }
    validate_binary_checkpoint_metadata(metadata)
    with pytest.raises(TrainingRuntimeError, match="metadata|tamper"):
        validate_binary_checkpoint_metadata({**metadata, "configuration_payload_hash": "c" * 64})
    with pytest.raises(TrainingRuntimeError, match="metadata"):
        validate_binary_checkpoint_metadata({key: value for key, value in metadata.items() if key != "mapping_contract"})


def test_binary_checkpoint_rejects_historical_or_partial_state() -> None:
    class BinaryModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.cls_head = nn.Linear(4, 2)

    model = BinaryModel()
    metadata = {
        "task_id": "cn_vs_impaired",
        "class_order": ["CN", "Impaired"],
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "split_identity": "a" * 64,
        "split_assignment_hash": "b" * 64,
        "configuration_payload": {"task_id": "cn_vs_impaired"},
        "configuration_payload_hash": __import__("pada3dacb.training.checkpointing", fromlist=["configuration_hash"]).configuration_hash({"task_id": "cn_vs_impaired"}),
        "binary_classifier_cardinality": 2,
    }
    with pytest.raises(Exception, match="historical|cardinality|metadata"):
        load_binary_checkpoint(model, {**metadata, "class_order": ["CN", "MCI", "AD"], "model_state_dict": model.state_dict()})
    with pytest.raises(Exception, match="partial|classifier|metadata"):
        load_binary_checkpoint(model, {**metadata, "model_state_dict": {"cls_head.weight": model.cls_head.weight}})
