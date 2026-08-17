from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from pada3dacb.adaptation.cdan import conditional_outer_product, expected_conditional_dimension
from pada3dacb.adaptation.prototype import build_source_prototypes
from pada3dacb.adaptation.pseudo_label import pseudo_label_cross_entropy
from pada3dacb.binary import (
    BINARY_CLASS_ORDER,
    BINARY_CLASS_TO_INDEX,
    BINARY_MAPPING_CONTRACT,
    SPLIT_DISPOSITION,
    BinaryLabelError,
    BinarySubjectRecord,
    build_binary_identity,
    build_binary_target_partition,
    evaluate_binary_predictions,
    load_verified_oasis_metadata,
    map_adni_label,
    validate_binary_prediction,
    validate_target_adaptation_batch,
)
from pada3dacb.evaluation.concepts.class_profiles import compute_binary_class_profiles
from pada3dacb.exceptions import CheckpointMigrationError
from pada3dacb.models import build_pada3dacb
from pada3dacb.models.checkpoint_migration import load_binary_checkpoint

TEST_SUBJECT_HASH_KEY = b"phase18b-test-subject-hmac-key!!"


def test_binary_vocabulary_and_adni_mapping_preserve_original_label() -> None:
    assert BINARY_CLASS_ORDER == ("CN", "Impaired")
    assert BINARY_CLASS_TO_INDEX == {"CN": 0, "Impaired": 1}
    assert BINARY_MAPPING_CONTRACT == "phase-18b-binary-v1"
    assert map_adni_label("CN").to_dict()["binary_label"] == 0
    assert map_adni_label("MCI").to_dict()["binary_label_name"] == "Impaired"
    assert map_adni_label("AD").original_label_name == "AD"
    with pytest.raises(BinaryLabelError):
        map_adni_label("Impaired")
    with pytest.raises(BinaryLabelError):
        map_adni_label(None)


def test_binary_subject_record_requires_provenance_and_hashed_identity() -> None:
    record = BinarySubjectRecord.from_source(
        cohort="ADNI",
        subject_id="synthetic-subject-1",
        original_label="MCI",
        source_row="row-1",
        derivative_path=Path("derivatives/synthetic.pt").resolve(),
    )
    payload = record.to_dict()
    assert payload["original_label_name"] == "MCI"
    assert payload["binary_label_name"] == "Impaired"
    assert payload["subject_hash"] != "synthetic-subject-1"
    assert payload["mapping_contract"] == BINARY_MAPPING_CONTRACT
    assert "subject_id" not in payload
    with pytest.raises(BinaryLabelError):
        BinarySubjectRecord(
            subject_hash="a" * 64,
            cohort="ADNI",
            original_label_name=None,
            binary_label_name="CN",
            binary_label=0,
            source_row_hash="b" * 64,
            derivative_path=Path("x").resolve(),
            mapping_contract=BINARY_MAPPING_CONTRACT,
        )


def test_phrase_only_notebook_is_rejected(tmp_path: Path) -> None:
    csv_path = tmp_path / "oasis.csv"
    csv_path.write_text("ID,CDR\nsynthetic-visit-1,0\n", encoding="utf-8")
    notebook = tmp_path / "preprocess.ipynb"
    notebook.write_text("CDR == 0 -> CN; CDR > 0 -> Impaired; missing excluded", encoding="utf-8")
    with pytest.raises(BinaryLabelError, match="structural"):
        load_verified_oasis_metadata(
            csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
        )


def test_verified_oasis_metadata_uses_structural_notebook_semantics_without_raw_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "oasis.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["ID", "CDR"])
        writer.writeheader()
        writer.writerows([
            {"ID": "synthetic-visit-1", "CDR": "0"},
            {"ID": "synthetic-visit-2", "CDR": "0.5"},
            {"ID": "synthetic-visit-3", "CDR": "2"},
            {"ID": "synthetic-visit-4", "CDR": ""},
        ])
    notebook = tmp_path / "preprocess.ipynb"
    notebook.write_text(
        json.dumps({"cells": [{"cell_type": "code", "source": [
            "import pandas as pd\n",
            "metadata = pd.read_csv('metadata.csv')\n",
            "ids = metadata['ID']\n",
            "def map_cdr(value):\n",
            "    cdr = pd.to_numeric(value, errors='coerce')\n",
            "    if pd.isna(cdr) or cdr < 0:\n",
            "        return None\n",
            "    if cdr == 0:\n",
            "        return 'CN'\n",
            "    if cdr > 0:\n",
            "        return 'Impaired'\n",
            "    return None\n",
        ]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}),
        encoding="utf-8",
    )
    evidence = load_verified_oasis_metadata(
        csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    )
    assert evidence.semantics_approved is False
    assert evidence.evidence_verified is True
    assert evidence.accepted_count == 3
    assert evidence.excluded_count == 1
    assert evidence.exclusion_reasons == {"missing_or_invalid_cdr": 1}
    assert evidence.accepted_cdr_value_counts == {"0": 1, "0.5": 1, "2": 1}
    assert evidence.source_field_name == "CDR"
    assert evidence.mapping_contract == BINARY_MAPPING_CONTRACT
    assert {row["binary_label_name"] for row in evidence.records} == {"CN", "Impaired"}
    assert all("synthetic-visit" not in json.dumps(row) for row in evidence.records)
    assert evidence.cdr_values == (0.0, 0.5, 2.0)
    assert evidence.csv_sha256 == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert evidence.notebook_sha256 == hashlib.sha256(notebook.read_bytes()).hexdigest()


def test_structural_notebook_requires_explicit_positive_mapping_branch(tmp_path: Path) -> None:
    csv_path = tmp_path / "oasis.csv"
    csv_path.write_text("ID,CDR\nsynthetic-visit-1,0\n", encoding="utf-8")
    notebook = tmp_path / "preprocess.ipynb"
    notebook.write_text(json.dumps({"cells": [{"cell_type": "code", "source": [
        "import pandas as pd\n",
        "metadata = pd.read_csv('metadata.csv')\n",
        "ids = metadata['ID']\n",
        "cdr = pd.to_numeric(metadata['CDR'], errors='coerce')\n",
        "if pd.isna(cdr) or cdr < 0: cdr = None\n",
        "positive_label = 'Impaired'\n",
        "label = 'CN' if cdr == 0 else 'CN'\n",
    ]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}), encoding="utf-8")
    with pytest.raises(BinaryLabelError, match="positive"):
        load_verified_oasis_metadata(
            csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
        )


def test_target_partition_is_deterministic_and_disjoint() -> None:
    records = [
        BinarySubjectRecord.from_source(
            cohort="OASIS", subject_id=f"subject-{index}", original_label="CN" if index < 4 else "Impaired",
            source_row=f"row-{index}", derivative_path=Path(f"{index}.pt").resolve(),
            subject_hash_key=TEST_SUBJECT_HASH_KEY,
        )
        for index in range(8)
    ]
    first = build_binary_target_partition(records, seed=42, adaptation_fraction=0.5)
    second = build_binary_target_partition(records, seed=42, adaptation_fraction=0.5)
    assert first == second
    assert not set(first["target_adaptation"]) & set(first["target_evaluation"])
    assert first["disposition"] == SPLIT_DISPOSITION


def test_binary_prediction_tie_and_evaluation_undefined_policy() -> None:
    record = validate_binary_prediction({"prob_cn": 0.5, "prob_impaired": 0.5, "dtype": "float64"})
    assert record.predicted_label == 0
    with pytest.raises(BinaryLabelError):
        validate_binary_prediction({"prob_cn": 0.5, "prob_impaired": 0.5, "prob_ad": 0.0})
    result = evaluate_binary_predictions(
        [{"true_label": 0, "prob_cn": 0.5, "prob_impaired": 0.5, "dtype": "float64"}]
    )
    assert result.confusion_matrix == ((1, 0), (0, 0))
    assert result.metrics["recall_impaired"]["value"] is None
    assert result.metrics["recall_impaired"]["reason"] == "zero_support"


def test_binary_identities_reject_historical_three_class_collisions() -> None:
    identity = build_binary_identity("experiment", {"name": "synthetic"})
    assert identity["task"] == "CN_vs_Impaired"
    assert identity["class_order"] == ["CN", "Impaired"]
    assert identity["identity_hash"] != ""
    with pytest.raises(BinaryLabelError):
        build_binary_identity("split", {"task": "CN_vs_MCI_vs_AD"})


def test_binary_model_and_checkpoint_fail_closed() -> None:
    model = build_pada3dacb({"name": "PADA-3DACB", "num_classes": 2, "num_rois": 2,
                             "encoder": {"base_channels": 2, "output_channels": 4},
                             "tokenizer": {"feature_dim": 4, "token_dim": 4},
                             "concept_bottleneck": {"hidden_dim": 4}})
    assert model.cls_head.fc.out_features == 2
    assert model(torch.randn(1, 1, 16, 16, 16), torch.ones(2, 2, 2, 2)).latent_logits.shape == (1, 2)
    three_class = {"model_state_dict": {"cls_head.fc.weight": torch.zeros(3, 4)}}
    with pytest.raises(CheckpointMigrationError, match="two|2|cardinality"):
        load_binary_checkpoint(model, three_class)


def test_binary_cdan_and_binary_losses_use_two_classes() -> None:
    assert expected_conditional_dimension(128, 2) == 256
    assert expected_conditional_dimension(64, 2) == 128
    features = torch.randn(3, 4, requires_grad=True)
    probabilities = torch.softmax(torch.randn(3, 2, requires_grad=True), dim=-1)
    conditional_outer_product(features, probabilities).sum().backward()
    assert features.grad is not None and probabilities.grad_fn is not None
    source, valid = build_source_prototypes(torch.randn(3, 4), torch.tensor([0, 1, 1]), class_count=2)
    assert source.shape == (2, 4) and valid.tolist() == [True, True]
    loss = pseudo_label_cross_entropy(torch.tensor([[8.0, -8.0], [-8.0, 8.0]]), tau_p=0.99, class_count=2)
    assert loss.loss.ndim == 0 and set(loss.pseudo_labels.tolist()) == {0, 1}


def test_binary_class_profiles_reuse_existing_concept_artifacts() -> None:
    records = [
        SimpleNamespace(true_label=0, predicted_concepts=(0.1, 0.2), concept_targets=(0.0, 1.0), anatomical_targets=(0.2, 0.3)),
        SimpleNamespace(true_label=1, predicted_concepts=(0.8, 0.7), concept_targets=(1.0, 0.0), anatomical_targets=(0.6, 0.5)),
    ]
    profiles = compute_binary_class_profiles(records, bootstrap_replicates=8, bootstrap_seed=4)
    assert [profile.class_label for profile in profiles] == ["CN", "Impaired"]
    assert [profile.support for profile in profiles] == [1, 1]


def test_binary_target_firewall_rejects_every_label_alias() -> None:
    valid = {"x": "synthetic", "subject_id": "synthetic", "subject_hash": "a" * 64, "cohort": "OASIS"}
    validate_target_adaptation_batch(valid)
    for alias in ("y", "label", "labels", "binary_label", "binary_label_name", "original_label",
                  "original_label_name", "diagnosis", "c_target", "g_bar", "target_label", "true_label"):
        with pytest.raises(BinaryLabelError):
            validate_target_adaptation_batch({**valid, alias: 1})


def test_oasis_duplicate_and_conflicting_rows_are_excluded(tmp_path: Path) -> None:
    csv_path = tmp_path / "oasis.csv"
    csv_path.write_text("ID,CDR\nOAS1_0001_MR1,0\nOAS1_0001_MR1,0\nOAS1_0002_MR1,0\nOAS1_0002_MR1,1\n", encoding="utf-8")
    notebook = tmp_path / "preprocess.ipynb"
    notebook.write_text(json.dumps({"cells": [{"cell_type": "code", "source": [
        "import pandas as pd\n",
        "metadata = pd.read_csv('metadata.csv')\n",
        "ids = metadata['ID']\n",
        "cdr = pd.to_numeric(value, errors='coerce')\n",
        "if pd.isna(cdr) or cdr < 0: return None\n",
        "if cdr == 0: return 'CN'\n",
        "if cdr > 0: return 'Impaired'\n",
    ]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}), encoding="utf-8")
    evidence = load_verified_oasis_metadata(
        csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    )
    assert evidence.accepted_count == 1
    assert evidence.excluded_count == 3
    assert evidence.exclusion_reasons == {"conflicting_person_diagnosis": 2, "longitudinal_duplicate": 1}


def test_oasis_rejects_missing_negative_and_nonfinite_cdr_without_raw_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "oasis.csv"
    csv_path.write_text(
        "ID,CDR\n,0\nmissing-cdr,\nnegative,-1\nnan,nan\ninf,inf\nvalid,0.5\n",
        encoding="utf-8",
    )
    notebook = tmp_path / "preprocess.ipynb"
    notebook.write_text(json.dumps({"cells": [{"cell_type": "code", "source": [
        "import pandas as pd\n",
        "metadata = pd.read_csv('metadata.csv')\n",
        "ids = metadata['ID']\n",
        "cdr_values = pd.to_numeric(metadata['CDR'], errors='coerce')\n",
        "if pd.isna(cdr_values) or cdr_values < 0: return None\n",
        "if cdr_values == 0: return 'CN'\n",
        "if cdr_values > 0: return 'Impaired'\n",
    ]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}), encoding="utf-8")
    evidence = load_verified_oasis_metadata(
        csv_path, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    )
    assert evidence.accepted_count == 1
    assert evidence.exclusion_reasons == {
        "missing_or_invalid_cdr": 1,
        "missing_subject_id": 1,
        "negative_cdr": 1,
        "nonfinite_cdr": 2,
    }
    serialized_records = json.dumps(evidence.records)
    assert all(raw not in serialized_records for raw in ("missing-cdr", "negative", "nan", "inf", "valid"))


def test_oasis_row_content_hash_is_deterministic_and_covers_complete_row(tmp_path: Path) -> None:
    notebook = tmp_path / "preprocess.ipynb"
    notebook.write_text(json.dumps({"cells": [{"cell_type": "code", "source": [
        "import pandas as pd\n",
        "metadata = pd.read_csv('metadata.csv')\n",
        "ids = metadata['ID']\n",
        "cdr_values = pd.to_numeric(metadata['CDR'], errors='coerce')\n",
        "if pd.isna(cdr_values) or cdr_values < 0: return None\n",
        "if cdr_values == 0: return 'CN'\n",
        "if cdr_values > 0: return 'Impaired'\n",
    ]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}), encoding="utf-8")
    first = tmp_path / "first.csv"
    first.write_text("ID,CDR,SESSION\nsubject-a,0,one\n", encoding="utf-8")
    reordered = tmp_path / "reordered.csv"
    reordered.write_text("SESSION,CDR,ID\none,0,subject-a\n", encoding="utf-8")
    changed = tmp_path / "changed.csv"
    changed.write_text("ID,CDR,SESSION\nsubject-a,0,two\n", encoding="utf-8")
    first_evidence = load_verified_oasis_metadata(
        first, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    )
    reordered_evidence = load_verified_oasis_metadata(
        reordered, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    )
    changed_evidence = load_verified_oasis_metadata(
        changed, notebook, subject_hash_key=TEST_SUBJECT_HASH_KEY
    )
    assert first_evidence.records[0]["source_row_hash"] == reordered_evidence.records[0]["source_row_hash"]
    assert first_evidence.records[0]["source_row_hash"] != changed_evidence.records[0]["source_row_hash"]
    assert len(first_evidence.row_content_hashes) == 1
    assert first_evidence.row_content_hashes == (first_evidence.records[0]["source_row_hash"],)


def test_phase18b_config_is_task_source_and_model_contract() -> None:
    from pada3dacb.config import load_config

    config = load_config("configs/publication/phase18b_binary.yaml")
    assert config.task_id == "cn_vs_impaired"
    assert config.task_type == "binary_classification"
    assert config.model.num_classes == 2
    assert config.class_order == ("CN", "Impaired")
    assert config.class_ids == {"CN": 0, "Impaired": 1}


def test_binary_metrics_and_selection_ignore_target_metrics() -> None:
    from pada3dacb.binary import (
        BINARY_METRIC_NAMES,
        select_best_checkpoint_by_source_validation_macro_f1,
    )

    result = evaluate_binary_predictions([
        {"true_label": 0, "prob_cn": 0.9, "prob_impaired": 0.1},
        {"true_label": 1, "prob_cn": 0.2, "prob_impaired": 0.8},
    ])
    assert set(BINARY_METRIC_NAMES) <= set(result.metrics)
    selected = select_best_checkpoint_by_source_validation_macro_f1([
        {"metrics": {"source_validation_macro_f1": 0.7, "target_macro_f1": 0.99}, "name": "a"},
        {"metrics": {"source_validation_macro_f1": 0.8, "target_macro_f1": 0.01}, "name": "b"},
    ])
    assert selected["name"] == "b"


def test_binary_model_and_confusion_are_production_shapes() -> None:
    from pada3dacb.binary import build_binary_model
    from pada3dacb.evaluation.confusion_matrices import compute_binary_confusion

    model = build_binary_model("source_only", {"name": "PADA-3DACB", "num_rois": 2, "encoder": {"base_channels": 2, "output_channels": 4}, "tokenizer": {"feature_dim": 4, "token_dim": 4}, "concept_bottleneck": {"hidden_dim": 4}})
    output = model(torch.randn(2, 1, 16, 16, 16), torch.ones(2, 2, 2, 2))
    assert output.latent_logits.shape == (2, 2)
    assert output.concepts.shape == (2, 2)
    assert output.alpha.shape == (2, 2)
    assert compute_binary_confusion([
        {"true_label": 0, "prob_cn": 0.8, "prob_impaired": 0.2},
        {"true_label": 1, "prob_cn": 0.1, "prob_impaired": 0.9},
    ]) == ((1, 0), (0, 1))


def test_all_six_binary_ablations_are_declared() -> None:
    from pada3dacb.binary import BINARY_ABLATIONS, binary_experiment_matrix

    matrix = binary_experiment_matrix()
    assert tuple(matrix["ablations"]) == BINARY_ABLATIONS
    assert len(matrix["ablations"]) == 6
