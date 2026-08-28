from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from acda3d.binary import (
    BINARY_MAPPING_CONTRACT,
    OASIS_POLICY_HASH,
    OASIS_SEMANTIC_AUTHORITY_MARKER,
    BinarySubjectRecord,
    load_verified_oasis_metadata,
    oasis_evidence_hash,
    validate_oasis_semantic_approval,
)
from acda3d.data.records import SubjectRecord, binary_record_from_subject_record
from acda3d.data.splits import (
    generate_binary_source_folds_for_records,
    generate_binary_target_partition_for_records,
    validate_binary_split_manifest,
)
from acda3d.exceptions import DatasetContractError

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


def _evidence(tmp_path: Path, rows: list[dict[str, str]]):
    csv_path = tmp_path / "oasis.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["ID", "CDR", "SESSION"])
        writer.writeheader()
        writer.writerows(rows)
    notebook = tmp_path / "preprocess.ipynb"
    _notebook(notebook)
    return load_verified_oasis_metadata(
        csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    ), csv_path, notebook


def test_oasis_groups_visits_by_person_and_selects_mr1(tmp_path: Path) -> None:
    evidence, _, _ = _evidence(
        tmp_path,
        [
            {"ID": "OAS1_0001_MR2", "CDR": "0", "SESSION": "later"},
            {"ID": "OAS1_0001_MR1", "CDR": "0", "SESSION": "baseline"},
            {"ID": "OAS1_0002_MR1", "CDR": "0.5", "SESSION": "baseline"},
        ],
    )
    assert evidence.accepted_count == 2
    assert evidence.excluded_count == 1
    assert evidence.exclusion_reasons == {"longitudinal_duplicate": 1}
    record = next(row for row in evidence.records if row["original_metadata_value"] == "0")
    assert record["visit_number"] == 1
    assert record["person_hash"] == record["subject_hash"]
    assert record["visit_hash"] != record["subject_hash"]
    assert "OAS1_0001" not in json.dumps(record)


def test_oasis_person_hashes_drive_disjoint_source_folds_and_target_partition(tmp_path: Path) -> None:
    records = [
        BinarySubjectRecord.from_source(
            cohort="OASIS",
            subject_id=f"OAS1_{index:04d}_MR{2 if index % 3 == 0 else 1}",
            original_label="CN" if index < 5 else "Impaired",
            source_row=f"row-{index}",
            derivative_path=(tmp_path / f"{index}.pt").resolve(),
            subject_hash_key=TEST_SUBJECT_HASH_KEY,
        )
        for index in range(10)
    ]
    assert records[0].subject_hash == BinarySubjectRecord.from_source(
        cohort="OASIS", subject_id="OAS1_0000_MR1", original_label="CN", source_row="other", derivative_path=(tmp_path / "other.pt").resolve(), subject_hash_key=TEST_SUBJECT_HASH_KEY
    ).subject_hash
    folds = generate_binary_source_folds_for_records(records)
    target = generate_binary_target_partition_for_records(records)
    validate_binary_split_manifest(folds, target)
    assert all(fold["identity_level"] == "person" and fold["person_disjoint"] for fold in folds)
    assert target["identity_level"] == "person" and target["person_disjoint"]


def test_oasis_conflicting_person_visits_exclude_all_valid_visits(tmp_path: Path) -> None:
    evidence, _, _ = _evidence(
        tmp_path,
        [
            {"ID": "OAS1_0001_MR1", "CDR": "0", "SESSION": "baseline"},
            {"ID": "OAS1_0001_MR2", "CDR": "0.5", "SESSION": "later"},
        ],
    )
    assert evidence.accepted_count == 0
    assert evidence.excluded_count == 2
    assert evidence.exclusion_reasons == {"conflicting_person_diagnosis": 2}


def test_oasis_rejects_closed_domain_violations_with_reasons(tmp_path: Path) -> None:
    evidence, _, _ = _evidence(
        tmp_path,
        [
            {"ID": "OAS1_0001_MR1", "CDR": "0.25", "SESSION": "bad"},
            {"ID": "OAS1_0002_MR1", "CDR": "99", "SESSION": "bad"},
            {"ID": "OAS1_0003_MR1", "CDR": "-1", "SESSION": "bad"},
            {"ID": "OAS1_0004_MR1", "CDR": "abc", "SESSION": "bad"},
            {"ID": "OAS1_0005_MR1", "CDR": "", "SESSION": "bad"},
        ],
    )
    assert evidence.accepted_count == 0
    assert evidence.exclusion_reasons == {
        "malformed_cdr": 1,
        "missing_or_invalid_cdr": 1,
        "negative_cdr": 1,
        "out_of_domain_cdr": 2,
    }


def test_oasis_admission_requires_approved_exact_evidence(tmp_path: Path) -> None:
    evidence, csv_path, notebook = _evidence(
        tmp_path, [{"ID": "OAS1_0001_MR1", "CDR": "0", "SESSION": "baseline"}]
    )
    evidence = replace(evidence, semantics_approved=True, scientific_review_status="PASS")
    source = SubjectRecord(
        subject_hash=evidence.records[0]["subject_hash"],
        cohort="OASIS",
        class_label="CN",
        label_index=0,
        derivative_path=(tmp_path / "x.pt").resolve(),
        subject_id="OAS1_0001",
        metadata={
            "oasis_evidence": {
                **evidence.to_dict(),
                "semantics_approved": True,
            },
            "oasis_input_hashes": {
                "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                "notebook_sha256": hashlib.sha256(notebook.read_bytes()).hexdigest(),
            },
        },
    )
    approval = validate_oasis_semantic_approval(evidence, {
        "csv_sha256": evidence.csv_sha256,
        "notebook_sha256": evidence.notebook_sha256,
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "mapping_contract_version": "v1",
        "policy_hash": OASIS_POLICY_HASH,
        "review_id": "review-18b-batch8",
        "authority_marker": OASIS_SEMANTIC_AUTHORITY_MARKER,
        "result": "PASS",
        "evidence_hash": oasis_evidence_hash(evidence),
    })
    adapted = binary_record_from_subject_record(
        source, oasis_evidence=evidence, oasis_approval=approval
    )
    assert adapted.original_metadata_value == "0"
    with pytest.raises(DatasetContractError, match="attestation|approval"):
        binary_record_from_subject_record(source, oasis_evidence=evidence)
    with pytest.raises(DatasetContractError, match="OasisEvidence"):
        binary_record_from_subject_record(
            source, oasis_evidence=evidence.to_dict(), oasis_approval=approval
        )
    with pytest.raises(DatasetContractError, match="attestation|approval"):
        binary_record_from_subject_record(source, oasis_evidence=evidence, oasis_approval=None)
    assert "OAS1_0001" not in json.dumps(adapted.to_dict())


def test_oasis_artifact_shape_is_person_level_without_raw_ids() -> None:
    provenance = json.loads(Path("specs/phase_18b_binary_label_space/oasis_binary_provenance.json").read_text())
    partition = json.loads(Path("specs/phase_18b_binary_label_space/oasis_target_partition.json").read_text())
    csv_hash = hashlib.sha256(Path("oasis_cross-sectional (1).csv").read_bytes()).hexdigest()
    notebook_hash = hashlib.sha256(Path("preprocess-adni-oasis.ipynb").read_bytes()).hexdigest()
    assert provenance["provenance"]["csv_sha256"] == csv_hash
    assert provenance["provenance"]["notebook_sha256"] == notebook_hash
    assert partition["provenance"]["csv_sha256"] == csv_hash
    assert partition["provenance"]["notebook_sha256"] == notebook_hash
    assert provenance["provenance"]["canonical_accepted_persons"] == 416
    assert provenance["provenance"]["longitudinal_duplicate_exclusions"] == 20
    assert partition["provenance"]["canonical_accepted_persons"] == 416
    assert partition["provenance"]["person_intersection_count"] == 0
    serialized = json.dumps((provenance, partition))
    assert "OAS1_" not in serialized
    assert "oasis_cross-sectional" not in serialized
