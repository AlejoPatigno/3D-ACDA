from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import torch
from torch import nn

import pada3dacb.binary as binary
from pada3dacb.binary import (
    BINARY_MAPPING_CONTRACT,
    OASIS_POLICY_HASH,
    BinarySubjectRecord,
    OasisApprovalAttestation,
    load_verified_oasis_metadata,
    oasis_evidence_hash,
    validate_oasis_semantic_approval,
)
from pada3dacb.data.records import SubjectRecord, binary_record_from_subject_record
from pada3dacb.data.splits import (
    generate_binary_source_folds_for_records,
    generate_binary_target_partition_for_records,
    validate_binary_split_manifest,
)
from pada3dacb.exceptions import (
    CheckpointMigrationError,
    DatasetContractError,
    SplitValidationError,
)

TEST_SUBJECT_HASH_KEY = b"phase18b-test-subject-hmac-key!!"


def _notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "source": [
                            "import pandas as pd\n",
                            "metadata = pd.read_csv('metadata.csv')\n",
                            "ids = metadata['ID']\n",
                            "cdr_values = pd.to_numeric(metadata['CDR'], errors='coerce')\n",
                            "if pd.isna(cdr_values) or cdr_values < 0: return None\n",
                            "if cdr_values == 0: return 'CN'\n",
                            "if cdr_values > 0: return 'Impaired'\n",
                        ],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def test_oasis_hash_loading_requires_explicit_or_documented_external_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "oasis.csv"
    csv_path.write_text("ID,CDR\nsynthetic-visit-1,0\n", encoding="utf-8")
    notebook = tmp_path / "preprocess.ipynb"
    _notebook(notebook)
    monkeypatch.delenv("PADA3DACB_OASIS_SUBJECT_HASH_KEY_FILE", raising=False)
    with pytest.raises(binary.BinaryLabelError, match="subject hash key"):
        load_verified_oasis_metadata(csv_path, notebook)
    evidence = load_verified_oasis_metadata(csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY)
    assert evidence.records[0]["subject_hash"] != binary._hash_value("subject:OASIS", "synthetic-visit-1")
    assert evidence.subject_hash_key_id == hashlib.sha256(TEST_SUBJECT_HASH_KEY).hexdigest()
    assert evidence.subject_hash_key_version == "oasis-subject-hmac-v1"
    assert "synthetic-visit-1" not in json.dumps(evidence.to_dict())


def test_oasis_semantic_admission_requires_validator_bound_attestation(tmp_path: Path) -> None:
    csv_path = tmp_path / "oasis.csv"
    csv_path.write_text("ID,CDR\nOAS1_0001_MR1,0\n", encoding="utf-8")
    notebook = tmp_path / "preprocess.ipynb"
    _notebook(notebook)
    evidence = load_verified_oasis_metadata(csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY)
    evidence = replace(evidence, semantics_approved=True, scientific_review_status="PASS")
    attestation_payload = {
        "csv_sha256": evidence.csv_sha256,
        "notebook_sha256": evidence.notebook_sha256,
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "mapping_contract_version": "v1",
        "policy_hash": OASIS_POLICY_HASH,
        "review_id": "review-18b-batch9",
        "authority_marker": binary.OASIS_SEMANTIC_AUTHORITY_MARKER,
        "result": "PASS",
        "evidence_hash": oasis_evidence_hash(evidence),
    }
    approval = validate_oasis_semantic_approval(evidence, attestation_payload)
    assert isinstance(approval, OasisApprovalAttestation)
    source = SubjectRecord(
        subject_hash=evidence.records[0]["subject_hash"],
        cohort="OASIS",
        class_label="CN",
        label_index=0,
        derivative_path=(tmp_path / "x.pt").resolve(),
        subject_id="OAS1_0001",
    )
    adapted = binary_record_from_subject_record(source, oasis_evidence=evidence, oasis_approval=approval)
    assert adapted.binary_label_name == "CN"
    with pytest.raises(DatasetContractError, match="attestation|approval"):
        binary_record_from_subject_record(source, oasis_evidence=evidence)
    with pytest.raises(DatasetContractError, match="OasisEvidence|attestation"):
        binary_record_from_subject_record(source, oasis_evidence=evidence.to_dict(), oasis_approval=approval)


def _split_manifests(tmp_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    records = [
        BinarySubjectRecord.from_source(
            cohort="OASIS",
            subject_id=f"subject-{index}",
            original_label="CN" if index < 5 else "Impaired",
            source_row=f"row-{index}",
            derivative_path=(tmp_path / f"{index}.pt").resolve(),
            subject_hash_key=TEST_SUBJECT_HASH_KEY,
        )
        for index in range(10)
    ]
    return generate_binary_source_folds_for_records(records), generate_binary_target_partition_for_records(records)


def test_binary_split_manifest_rejects_duplicate_person_hashes(tmp_path: Path) -> None:
    folds, target = _split_manifests(tmp_path)
    duplicated_train = copy.deepcopy(folds)
    duplicated_train[0]["source_train"] = [duplicated_train[0]["source_train"][0]] * 2
    with pytest.raises(SplitValidationError, match="duplicate"):
        validate_binary_split_manifest(duplicated_train, target)
    duplicated_target = copy.deepcopy(target)
    duplicated_target["target_adaptation"] = [duplicated_target["target_adaptation"][0]] * 2
    with pytest.raises(SplitValidationError, match="duplicate"):
        validate_binary_split_manifest(folds, duplicated_target)


def test_binary_split_manifest_can_bind_approved_person_universe(tmp_path: Path) -> None:
    folds, target = _split_manifests(tmp_path)
    universe = set(target["target_adaptation"]) | set(target["target_evaluation"])
    validate_binary_split_manifest(folds, target, approved_person_universe=universe)
    with pytest.raises(SplitValidationError, match="approved person"):
        validate_binary_split_manifest(folds, target, approved_person_universe=universe - {next(iter(universe))})


def test_binary_checkpoint_path_loading_is_weights_only_before_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_load(path: object, **kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(torch, "load", fake_load)
    with pytest.raises(CheckpointMigrationError):
        binary.load_binary_checkpoint(nn.Linear(2, 2), tmp_path / "checkpoint.pt")
    assert calls == [{"weights_only": True, "map_location": "cpu"}]
