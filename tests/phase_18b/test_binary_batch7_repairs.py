from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from torch import nn

import pada3dacb.binary as binary
from pada3dacb.binary import (
    BINARY_MAPPING_CONTRACT,
    OASIS_POLICY_HASH,
    OASIS_SEMANTIC_AUTHORITY_MARKER,
    OasisEvidence,
    oasis_evidence_hash,
    validate_oasis_semantic_approval,
)
from pada3dacb.data.records import SubjectRecord, binary_record_from_subject_record
from pada3dacb.exceptions import (
    CheckpointMigrationError,
    DatasetContractError,
    TrainingRuntimeError,
)
from pada3dacb.experiments.prediction_export import (
    binary_prediction_metrics,
    collect_binary_predictions,
    validate_task_scoped_binary_prediction_records,
)
from pada3dacb.label_space import BINARY_CLASS_ORDER, BinaryPrediction
from pada3dacb.models.checkpoint_migration import (
    load_binary_checkpoint as load_migrated_binary_checkpoint,
)
from pada3dacb.training.checkpointing import load_binary_training_checkpoint


class _BinaryModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.cls_head = nn.Linear(1, 2)

    def forward(self, x: torch.Tensor, roi_masks: torch.Tensor) -> SimpleNamespace:
        del roi_masks
        return SimpleNamespace(latent_probabilities=torch.softmax(x, dim=-1))


def test_valid_task_scoped_binary_record_uses_declared_fields() -> None:
    validate_task_scoped_binary_prediction_records([
        {
            "subject_hash": "subject-a",
            "cohort": "ADNI",
            "prob_cn": 0.75,
            "prob_impaired": 0.25,
            "predicted_label": 0,
        }
    ])


def test_binary_collection_retains_evaluation_labels_without_polluting_public_export() -> None:
    model = _BinaryModel()
    loader = [{
        "x": torch.tensor([[2.0, 0.0], [0.0, 2.0]]),
        "y": torch.tensor([0, 1]),
        "subject_hash": ["a", "b"],
        "cohort": ["ADNI", "OASIS"],
    }]
    frame = collect_binary_predictions(
        model,
        loader,
        torch.ones(1),
        torch.device("cpu"),
        direction="ADNI_to_OASIS",
        fold=0,
        seed=1,
        checkpoint_name="synthetic",
        checkpoint_epoch=0,
        split="evaluation",
        experiment_hash="hash",
    )
    assert {"true_label", "true_label_index", "predicted_label_index"} <= set(frame.columns)
    metrics = binary_prediction_metrics(frame)
    assert metrics["accuracy"]["value"] == 1.0
    assert "true_label" not in {"subject_hash", "cohort", "prob_cn", "prob_impaired", "predicted_label"}


def test_binary_metric_api_is_single_and_normative_with_nullable_undefined_support() -> None:
    source = inspect.getsource(binary)
    assert source.count("def evaluate_binary_predictions") == 1
    result = binary.evaluate_binary_predictions([
        {"true_label": 0, "prob_cn": 1.0, "prob_impaired": 0.0},
    ])
    required = {
        "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "sensitivity",
        "specificity", "mcc", "cohen_kappa", "roc_auc", "pr_auc", "log_loss",
        "brier_score", "source_validation_macro_f1",
    }
    assert required <= set(result.metrics)
    for name in ("balanced_accuracy", "macro_f1", "weighted_f1", "roc_auc", "pr_auc"):
        assert result.metrics[name]["value"] is None
        assert result.metrics[name]["reason"]


def test_all_public_binary_checkpoint_loaders_reject_metadata_free_two_logit_state(tmp_path: Path) -> None:
    model = _BinaryModel()
    state = model.state_dict()
    with pytest.raises(CheckpointMigrationError):
        binary.load_binary_checkpoint(model, state)
    with pytest.raises(CheckpointMigrationError):
        load_migrated_binary_checkpoint(model, state)
    path = tmp_path / "metadata-free.pt"
    torch.save({
        "model_state_dict": state,
        "optimizer_state_dict": {},
        "epoch": 0,
        "global_step": 0,
        "rng_state": {"python": None},
    }, path)
    with pytest.raises(TrainingRuntimeError):
        load_binary_training_checkpoint(path)


def _oasis_source(*, label: str, metadata: dict[str, object]) -> SubjectRecord:
    return SubjectRecord(
        subject_hash="a" * 64,
        cohort="OASIS",
        class_label=label,
        label_index=0 if label == "CN" else 1,
        derivative_path=Path("oasis.pt").resolve(),
        subject_id="OASIS-1",
        metadata=metadata,
    )


def _oasis_evidence(label: str = "CN") -> dict[str, object]:
    return {
        "csv_sha256": "c" * 64,
        "notebook_sha256": "d" * 64,
        "semantics_approved": True,
        "evidence_verified": True,
        "mapping_contract": "phase-18b-binary-v1",
        "records": [{"subject_hash": "a" * 64, "person_hash": "a" * 64, "binary_label_name": label, "original_metadata_value": "0", "source_row_hash": "e" * 64, "visit_hash": "f" * 64}],
    }


def test_oasis_adapter_requires_hash_bound_structured_evidence_and_preserves_adni() -> None:
    evidence = OasisEvidence(
        semantics_approved=True,
        scientific_review_status="PASS",
        accepted_count=1,
        excluded_count=0,
        cdr_values=(0.0,),
        records=({
            "subject_hash": "a" * 64,
            "person_hash": "a" * 64,
            "binary_label_name": "CN",
            "original_metadata_value": "0",
            "source_row_hash": "e" * 64,
            "visit_hash": "f" * 64,
        },),
        csv_sha256="c" * 64,
        notebook_sha256="d" * 64,
        mapping_contract=BINARY_MAPPING_CONTRACT,
        evidence_verified=True,
    )
    approval = validate_oasis_semantic_approval(evidence, {
        "csv_sha256": evidence.csv_sha256,
        "notebook_sha256": evidence.notebook_sha256,
        "mapping_contract": BINARY_MAPPING_CONTRACT,
        "mapping_contract_version": "v1",
        "policy_hash": OASIS_POLICY_HASH,
        "review_id": "review-18b-batch7",
        "authority_marker": OASIS_SEMANTIC_AUTHORITY_MARKER,
        "result": "PASS",
        "evidence_hash": oasis_evidence_hash(evidence),
    })
    adapted = binary_record_from_subject_record(
        _oasis_source(label="CN", metadata={}), oasis_evidence=evidence, oasis_approval=approval
    )
    assert adapted.binary_label_name == "CN"
    with pytest.raises(DatasetContractError, match="attestation|approval"):
        binary_record_from_subject_record(_oasis_source(label="CN", metadata={}), oasis_evidence=evidence)
    with pytest.raises(DatasetContractError, match="OasisEvidence"):
        binary_record_from_subject_record(
            _oasis_source(label="CN", metadata={}),
            oasis_evidence=evidence.to_dict(),
            oasis_approval=approval,
        )
    with pytest.raises(DatasetContractError, match="structured|evidence"):
        binary_record_from_subject_record(_oasis_source(label="CN", metadata={}), oasis_provenance_verified=True)

    adni = SubjectRecord(
        subject_hash="adni-hash",
        cohort="ADNI",
        class_label="MCI",
        label_index=1,
        derivative_path=Path("adni.pt").resolve(),
    )
    assert binary_record_from_subject_record(adni).binary_label_name == "Impaired"


def test_label_space_exports_explicit_stable_api() -> None:
    import pada3dacb.label_space as label_space

    assert label_space.__all__
    assert "BinaryPrediction" in label_space.__all__
    assert "ast" not in label_space.__all__
    assert all(not name.startswith("_") for name in label_space.__all__)
    assert BINARY_CLASS_ORDER == ("CN", "Impaired")
    assert BinaryPrediction.from_mapping({"prob_cn": 0.5, "prob_impaired": 0.5}).predicted_label == 0


def test_binary_concept_cli_requires_explicit_validate_only() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/evaluate_binary_concepts.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "validate-only" in completed.stderr
