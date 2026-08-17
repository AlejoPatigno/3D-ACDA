from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.aggregation import aggregate_binary_concept_records
from pada3dacb.evaluation.concepts.inference import validate_binary_concept_inference_shapes
from pada3dacb.evaluation.concepts.provenance import validate_binary_concept_compatibility
from pada3dacb.evaluation.concepts.report import evaluate_binary_concept_records
from pada3dacb.evaluation.concepts.schemas import BINARY_CONCEPT_CLASS_ORDER

HASHES = {name: f"{index:064x}" for index, name in enumerate(("atlas", "normalizer", "targets", "anatomy"), 1)}


def _records():
    return [
        SimpleNamespace(
            subject_hash="cn-1", true_label=0, label_name="CN", K=2,
            predicted_concepts=(0.1, 0.2), concept_targets=(0.0, 0.25),
            anatomical_targets=(0.15, 0.3), roi_order_hash=HASHES["atlas"],
            normalizer_hash=HASHES["normalizer"],
        ),
        SimpleNamespace(
            subject_hash="mci-1", true_label=1, label_name="MCI", K=2,
            predicted_concepts=(0.7, 0.8), concept_targets=(0.75, 0.85),
            anatomical_targets=(0.65, 0.9), roi_order_hash=HASHES["atlas"],
            normalizer_hash=HASHES["normalizer"],
        ),
        SimpleNamespace(
            subject_hash="ad-1", true_label=2, label_name="AD", K=2,
            predicted_concepts=(0.9, 0.95), concept_targets=(0.88, 0.9),
            anatomical_targets=(0.8, 0.92), roi_order_hash=HASHES["atlas"],
            normalizer_hash=HASHES["normalizer"],
        ),
    ]


def test_binary_profiles_have_only_active_cn_and_impaired_axes():
    result = evaluate_binary_concept_records(
        _records(), task_id="cn_vs_impaired", task_hash="binary-task",
        expected_task_hash="binary-task", expected_k=2,
        expected_artifact_hashes=HASHES, artifact_hashes=HASHES,
        expected_roi_order_hash=HASHES["atlas"], roi_order_hash=HASHES["atlas"],
        expected_atlas_hash=HASHES["atlas"], atlas_hash=HASHES["atlas"],
        expected_mask_hash=HASHES["anatomy"], mask_hash=HASHES["anatomy"],
    )
    assert result["class_order"] == BINARY_CONCEPT_CLASS_ORDER
    assert [profile.class_label for profile in result["profiles"]] == ["CN", "Impaired"]
    assert not {profile.class_label for profile in result["profiles"]} & {"MCI", "AD"}
    assert result["provenance"]["source_label_support"] == {"CN": 1, "MCI": 1, "AD": 1}


def test_binary_evaluation_reuses_targets_for_fidelity_and_anatomy():
    records = _records()
    result = evaluate_binary_concept_records(records, task_id="cn_vs_impaired")
    predicted = np.asarray([r.predicted_concepts for r in records])
    c_target = np.asarray([r.concept_targets for r in records])
    g_bar = np.asarray([r.anatomical_targets for r in records])
    assert result["fidelity"]["global"].mae == pytest.approx(np.abs(predicted - c_target).mean())
    assert result["anatomy"]["global"].mae == pytest.approx(np.abs(predicted - g_bar).mean())
    assert result["provenance"]["targets_reused"] is True


def test_binary_compatibility_rejects_changed_k_roi_or_hashes():
    kwargs = {
        "task_id": "cn_vs_impaired",
        "artifact_hashes": HASHES,
        "expected_artifact_hashes": HASHES,
        "k": 2,
        "expected_k": 2,
        "roi_order_hash": HASHES["atlas"],
        "expected_roi_order_hash": HASHES["atlas"],
        "atlas_hash": HASHES["atlas"],
        "expected_atlas_hash": HASHES["atlas"],
        "mask_hash": HASHES["anatomy"],
        "expected_mask_hash": HASHES["anatomy"],
    }
    validate_binary_concept_compatibility(**kwargs)
    for field, value in (("k", 3), ("roi_order_hash", "f" * 64), ("atlas_hash", "e" * 64)):
        with pytest.raises(ValueError):
            validate_binary_concept_compatibility(**{**kwargs, field: value})


def test_binary_compatibility_rejects_refit_or_regeneration():
    kwargs = {"task_id": "cn_vs_impaired", "k": 2, "expected_k": 2}
    with pytest.raises(ValueError, match="refit"):
        validate_binary_concept_compatibility(**kwargs, refit=True)
    with pytest.raises(ValueError, match="regenerat"):
        validate_binary_concept_compatibility(**kwargs, regenerate=True)


def test_binary_task_and_hash_collisions_are_rejected():
    with pytest.raises(ValueError, match="task_id"):
        evaluate_binary_concept_records(_records(), task_id="cn_vs_mci_vs_ad")
    with pytest.raises(ValueError, match="hash"):
        evaluate_binary_concept_records(_records(), task_id="cn_vs_impaired", task_hash="new", expected_task_hash="old")


def test_binary_inference_shapes_preserve_concepts_alpha_and_two_logits():
    result = validate_binary_concept_inference_shapes(
        np.zeros((3, 4)), np.zeros((3, 4)), np.zeros((3, 2)), np.zeros((3, 2)),
        task_id="cn_vs_impaired",
    )
    assert result == {"batch": 3, "K": 4, "logit_classes": 2}
    with pytest.raises(ValueError):
        validate_binary_concept_inference_shapes(
            np.zeros((3, 4)), np.zeros((3, 4)), np.zeros((3, 3)), np.zeros((3, 2)),
            task_id="cn_vs_impaired",
        )


def test_binary_aggregation_routes_historical_mci_and_ad_without_averaging_targets():
    records = _records()
    aggregated = aggregate_binary_concept_records(records, task_id="cn_vs_impaired")
    assert [record.subject_hash for record in aggregated.records] == [record.subject_hash for record in records]
    assert aggregated.source_label_support == {"CN": 1, "MCI": 1, "AD": 1}
    assert aggregated.records[1].concept_targets == records[1].concept_targets
    assert aggregated.records[2].anatomical_targets == records[2].anatomical_targets
