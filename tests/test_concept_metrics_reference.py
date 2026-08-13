"""Independent mathematical and read-only boundary checks for Phase 16 WU-07."""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest
import torch

from pada3dacb.evaluation.concepts.aggregation import aggregate_target_evaluation
from pada3dacb.evaluation.concepts.agreement import compute_js_divergence
from pada3dacb.evaluation.concepts.anatomy import compute_weighted_anatomy_score
from pada3dacb.evaluation.concepts.fidelity import (
    compute_global_fidelity,
    compute_per_roi_fidelity,
)
from pada3dacb.evaluation.concepts.inference import run_subject_inference
from pada3dacb.evaluation.concepts.schemas import (
    CheckpointPolicy,
    ConceptSubjectRecord,
    Direction,
    MethodId,
)
from pada3dacb.evaluation.concepts.statistics import adjust_holm, bootstrap_metric
from pada3dacb.evaluation.schemas import ValueStatus


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    centered_x = x - x.mean()
    centered_y = y - y.mean()
    return float(np.sum(centered_x * centered_y) / np.sqrt(
        np.sum(centered_x**2) * np.sum(centered_y**2)
    ))


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    x_rank = np.argsort(np.argsort(x)).astype(float)
    y_rank = np.argsort(np.argsort(y)).astype(float)
    return _pearson(x_rank, y_rank)


def test_fidelity_equations_match_independent_matrix_reference() -> None:
    predicted = np.array([[0.0, 1.0], [1.0, 4.0], [3.0, 2.0], [4.0, 7.0]])
    target = np.array([[0.0, 2.0], [2.0, 3.0], [4.0, 1.0], [6.0, 8.0]])
    diff = predicted - target

    global_result = compute_global_fidelity(predicted, target)
    assert global_result.mae == pytest.approx(np.mean(np.abs(diff)))
    assert global_result.rmse == pytest.approx(np.sqrt(np.mean(diff**2)))
    assert global_result.bias == pytest.approx(np.mean(diff))

    per_roi = compute_per_roi_fidelity(predicted, target)
    for index, row in enumerate(per_roi):
        roi_diff = diff[:, index]
        assert row.mae == pytest.approx(np.mean(np.abs(roi_diff)))
        assert row.rmse == pytest.approx(np.sqrt(np.mean(roi_diff**2)))
        assert row.bias == pytest.approx(np.mean(roi_diff))
        assert row.pearson == pytest.approx(_pearson(predicted[:, index], target[:, index]))
        assert row.spearman == pytest.approx(_spearman(predicted[:, index], target[:, index]))
        assert row.status is ValueStatus.AVAILABLE


def test_anatomy_weighting_matches_weighted_roi_equations() -> None:
    predicted = np.array([[0.0, 2.0, 5.0], [2.0, 4.0, 2.0]])
    target = np.array([[1.0, 0.0, 1.0], [1.0, 1.0, 4.0]])
    weights = np.array([0.2, 0.3, 0.5])
    diff = predicted - target
    expected_mae = float(np.sum(weights * np.mean(np.abs(diff), axis=0)))
    expected_rmse = float(np.sqrt(np.sum(weights * np.mean(diff**2, axis=0))))
    expected_bias = float(np.sum(weights * np.mean(diff, axis=0)))

    result = compute_weighted_anatomy_score(predicted, target, weights)

    assert result.status is ValueStatus.AVAILABLE
    assert result.weighted_mae == pytest.approx(expected_mae)
    assert result.weighted_rmse == pytest.approx(expected_rmse)
    assert result.weighted_bias == pytest.approx(expected_bias)


def test_js_divergence_matches_direct_kl_to_mixture_reference() -> None:
    latent = np.array([[0.5, 0.3, 0.2], [0.6, 0.1, 0.3]])
    concept = np.array([[0.2, 0.5, 0.3], [0.2, 0.5, 0.3]])
    expected = []
    for p, q in zip(latent, concept, strict=True):
        mixture = (p + q) / 2.0
        expected.append(0.5 * np.sum(p * np.log(p / mixture)))
        expected[-1] += 0.5 * np.sum(q * np.log(q / mixture))

    assert compute_js_divergence(latent, concept) == pytest.approx(np.mean(expected))


def _record(seed: int, fold: int, offset: float) -> ConceptSubjectRecord:
    return ConceptSubjectRecord(
        method_id=MethodId.SOURCE_ONLY,
        model="PADA-3DACB",
        direction=Direction.ADNI_TO_OASIS,
        source_domain="ADNI",
        target_domain="OASIS",
        seed=seed,
        fold=fold,
        logical_checkpoint="best_source_f1",
        checkpoint_epoch=10,
        checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        experiment_hash=f"{seed:064x}",
        subject_id="subject-a",
        subject_hash="a" * 64,
        cohort="OASIS",
        true_label=1,
        label_name="MCI",
        predicted_concepts=(0.2 + offset, 0.6 + offset),
        concept_targets=(0.25, 0.75),
        anatomical_targets=(0.3, 0.7),
        attention_alpha=(0.4, 0.6),
        latent_probabilities=(0.2, 0.6, 0.2),
        concept_probabilities=(0.3, 0.5, 0.2),
        latent_prediction=1,
        concept_prediction=1,
        K=2,
        roi_order_hash="a" * 64,
        normalizer_hash="b" * 64,
        concept_config_hash="c" * 64,
    )


def test_aggregation_reference_is_fold_then_seed() -> None:
    records = [
        _record(42, 0, 0.0), _record(42, 1, 0.2),
        _record(99, 0, 0.1), _record(99, 1, 0.3),
    ]
    fold_ensembles, seed_ensembles = aggregate_target_evaluation(
        records, expected_folds=(0, 1), expected_seeds=(42, 99)
    )

    assert fold_ensembles["a" * 64, 42].predicted_concepts == pytest.approx((0.3, 0.7))
    assert fold_ensembles["a" * 64, 99].predicted_concepts == pytest.approx((0.4, 0.8))
    assert seed_ensembles is not None
    assert seed_ensembles["a" * 64].predicted_concepts == pytest.approx((0.35, 0.75))
    assert seed_ensembles["a" * 64].concept_targets == (0.25, 0.75)


def test_bootstrap_reference_resamples_subjects_within_class() -> None:
    values = np.array([0.0, 0.0, 10.0, 10.0, 20.0, 20.0])
    labels = np.array([0, 0, 1, 1, 2, 2])
    result = bootstrap_metric(values, labels=labels, metric="concept_mae", n_replicates=100, seed=17)

    assert result.point_estimate == pytest.approx(10.0)
    assert (result.ci_low, result.ci_high) == pytest.approx((10.0, 10.0))
    assert (result.requested, result.successful, result.invalid) == (100, 100, 0)


def test_holm_reference_preserves_canonical_four_slot_family() -> None:
    rows = adjust_holm([0.001, 0.02, 0.02, 0.9], metric="anatomy_mae")

    assert [row.holm_rank for row in rows] == [1, 2, 3, 4]
    assert [row.adjusted_p_value for row in rows] == pytest.approx([0.004, 0.06, 0.06, 0.9])
    assert [row.family_size for row in rows] == [4] * 4


class _InferenceProbe(torch.nn.Module):
    weight: torch.nn.Parameter

    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([[0.2, 0.8]]))

    def forward(
        self,
        inputs: torch.Tensor,
        roi_masks: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        assert inputs.shape[0] == 2
        assert roi_masks.shape == (2, 1, 1, 1)
        self.seen_batch_size = inputs.shape[0]
        self.seen_roi_masks = roi_masks.detach().clone()
        batch_size = inputs.shape[0]
        concepts = self.weight.expand(batch_size, -1)
        logits = torch.tensor([[2.0, 1.0, 0.0]], dtype=inputs.dtype).expand(batch_size, -1)
        alpha = torch.tensor([[0.25, 0.75]], dtype=inputs.dtype).expand(batch_size, -1)
        return {"concepts": concepts, "latent_logits": logits, "concept_logits": logits, "alpha": alpha}


def test_synthetic_inference_is_no_grad_and_does_not_regenerate_targets() -> None:
    model = _InferenceProbe()
    before = model.weight.detach().clone()
    batch = {
        "x": torch.ones((2, 2)),
        "subject_id": ["subject-a", "subject-b"],
        "subject_hash": ["a" * 64, "b" * 64],
        "cohort": ["OASIS", "OASIS"],
        "label": torch.tensor([1, 0]),
        "label_name": ["MCI", "CN"],
        "concept_targets": torch.tensor([[0.1, 0.9], [0.2, 0.8]]),
        "anatomical_targets": torch.tensor([[0.3, 0.7], [0.4, 0.6]]),
        "roi_masks": torch.ones((2, 1, 1, 1)),
    }
    atlas = type(
        "Atlas",
        (),
        {"K": 2, "get_binary_masks": lambda self: torch.ones((2, 1, 1, 1))},
    )()
    records = run_subject_inference(
        model=model,
        dataloader=[batch],
        concept_normalizer=object(),
        device="cpu",
        atlas_mgr=atlas,
        method_id=MethodId.SOURCE_ONLY,
        direction=Direction.ADNI_TO_OASIS,
        source_domain="ADNI",
        target_domain="OASIS",
        seed=42,
        fold=0,
        logical_checkpoint="best_source_f1",
        checkpoint_epoch=10,
        checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        experiment_hash="d" * 64,
        roi_order_hash="a" * 64,
        normalizer_hash="b" * 64,
        concept_config_hash="c" * 64,
    )

    assert len(records) == 2
    assert records[0].concept_targets == pytest.approx((0.1, 0.9))
    assert records[1].concept_targets == pytest.approx((0.2, 0.8))
    assert model.seen_batch_size > 1
    assert model.seen_roi_masks.shape == (2, 1, 1, 1)
    assert torch.equal(model.weight, before)
    assert model.weight.grad is None
    source = Path("src/pada3dacb/evaluation/concepts/inference.py").read_text(encoding="utf-8")
    assert "@torch.no_grad()" in source
    assert "build_subject_concept_target" not in source
    assert "optimizer" not in inspect.getsource(run_subject_inference)
    assert "backward(" not in inspect.getsource(run_subject_inference)
    assert ".step(" not in inspect.getsource(run_subject_inference)
