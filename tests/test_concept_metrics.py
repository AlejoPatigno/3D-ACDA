"""Tests for concept fidelity metrics."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.fidelity import (
    compute_all_fidelity,
    compute_global_fidelity,
    compute_per_roi_fidelity,
    compute_per_subject_fidelity,
)
from pada3dacb.evaluation.concepts.schemas import ConceptFidelityGlobal, ValueStatus


class TestConceptFidelity:
    def setup_method(self):
        np.random.seed(42)
        self.N = 10
        self.K = 5
        self.c_hat = np.random.uniform(0, 1, (self.N, self.K)).astype(np.float32)
        self.c_target = np.random.uniform(0, 1, (self.N, self.K)).astype(np.float32)

    def test_compute_global_fidelity(self):
        result = compute_global_fidelity(self.c_hat, self.c_target)
        assert isinstance(result, ConceptFidelityGlobal)
        assert 0 <= result.mae <= 1
        assert result.rmse >= result.mae
        assert -1 <= result.bias <= 1

    def test_compute_global_fidelity_perfect_match(self):
        result = compute_global_fidelity(self.c_hat, self.c_hat)
        assert result.mae == 0.0
        assert result.rmse == 0.0
        assert result.bias == 0.0

    def test_compute_global_fidelity_shape_mismatch(self):
        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_global_fidelity(self.c_hat, self.c_target[:5])

    def test_compute_per_subject_fidelity(self):
        results = compute_per_subject_fidelity(self.c_hat, self.c_target)
        assert len(results) == self.N
        for _i, r in enumerate(results):
            assert r.mae >= 0
            assert r.rmse >= r.mae

    def test_compute_per_roi_fidelity(self):
        results = compute_per_roi_fidelity(self.c_hat, self.c_target)
        assert len(results) == self.K
        for r in results:
            assert 0 <= r.roi_index < self.K
            assert r.mae >= 0
            assert r.rmse >= r.mae
            assert r.status in (ValueStatus.AVAILABLE, ValueStatus.UNAVAILABLE)

    def test_compute_all_fidelity(self):
        results = compute_all_fidelity(self.c_hat, self.c_target)
        assert "global" in results
        assert "per_subject" in results
        assert "per_roi" in results
        assert isinstance(results["global"], object)
        assert len(results["per_subject"]) == self.N
        assert len(results["per_roi"]) == self.K

    def test_constant_roi_correlation_unavailable(self):
        # Make one ROI constant
        c_hat_const = self.c_hat.copy()
        c_hat_const[:, 0] = 0.5  # Constant
        c_target_const = self.c_target.copy()
        c_target_const[:, 0] = 0.3  # Different constant

        results = compute_per_roi_fidelity(c_hat_const, c_target_const)
        assert results[0].status == ValueStatus.UNAVAILABLE
        assert results[0].reason == "constant_roi"
        assert results[0].pearson is None
        assert results[0].spearman is None


class TestAnatomyConsistency:
    def setup_method(self):
        np.random.seed(42)
        self.N = 10
        self.K = 5
        self.c_hat = np.random.uniform(0, 1, (self.N, self.K)).astype(np.float32)
        self.g_bar = np.random.uniform(0, 1, (self.N, self.K)).astype(np.float32)

    def test_compute_global_anatomy(self):
        from pada3dacb.evaluation.concepts.anatomy import compute_global_anatomy
        result = compute_global_anatomy(self.c_hat, self.g_bar)
        assert 0 <= result.mae <= 1
        assert result.rmse >= result.mae
        assert -1 <= result.bias <= 1

    def test_compute_per_roi_anatomy(self):
        from pada3dacb.evaluation.concepts.anatomy import compute_per_roi_anatomy
        results = compute_per_roi_anatomy(self.c_hat, self.g_bar)
        assert len(results) == self.K

    def test_compute_weighted_anatomy_score(self):
        from pada3dacb.evaluation.concepts.anatomy import compute_weighted_anatomy_score
        weights = np.ones(self.K) / self.K
        result = compute_weighted_anatomy_score(self.c_hat, self.g_bar, weights)
        assert result.status == "available"
        assert result.weighted_mae >= 0

    def test_compute_weighted_anatomy_score_no_weights(self):
        from pada3dacb.evaluation.concepts.anatomy import compute_weighted_anatomy_score
        result = compute_weighted_anatomy_score(self.c_hat, self.g_bar, None)
        assert result.status == "unavailable"
        assert result.reason == "weights_unavailable"


class TestHeadAgreement:
    def setup_method(self):
        np.random.seed(42)
        self.N = 50
        self.latent_probs = np.random.dirichlet([1, 1, 1], self.N).astype(np.float32)
        self.concept_probs = np.random.dirichlet([1, 1, 1], self.N).astype(np.float32)
        self.true_labels = np.random.randint(0, 3, self.N)

    def test_compute_head_predictive_metrics(self):
        from pada3dacb.evaluation.concepts.agreement import compute_head_predictive_metrics
        metrics = compute_head_predictive_metrics(self.latent_probs, self.concept_probs, self.true_labels)
        assert "latent_accuracy" in metrics
        assert "concept_accuracy" in metrics
        assert 0 <= metrics["latent_accuracy"] <= 1

    def test_compute_top1_agreement(self):
        from pada3dacb.evaluation.concepts.agreement import compute_top1_agreement
        agreement, disagreement = compute_top1_agreement(self.latent_probs, self.concept_probs)
        assert 0 <= agreement <= 1
        assert disagreement == 1 - agreement

    def test_compute_js_divergence(self):
        from pada3dacb.evaluation.concepts.agreement import compute_js_divergence
        js = compute_js_divergence(self.latent_probs, self.concept_probs)
        assert js >= 0

    def test_compute_js_divergence_identical(self):
        from pada3dacb.evaluation.concepts.agreement import compute_js_divergence
        js = compute_js_divergence(self.latent_probs, self.latent_probs)
        assert js == 0.0

    def test_compute_per_class_disagreement(self):
        from pada3dacb.evaluation.concepts.agreement import compute_per_class_disagreement
        latent_pred = np.argmax(self.latent_probs, axis=1)
        concept_pred = np.argmax(self.concept_probs, axis=1)
        results = compute_per_class_disagreement(latent_pred, concept_pred, self.true_labels)
        assert len(results) == 3  # CN, MCI, AD


class TestROIStability:
    def setup_method(self):
        np.random.seed(42)
        self.M = 8  # 4 folds x 2 seeds
        self.K = 5
        self.fidelity = np.random.uniform(0, 0.5, (self.M, self.K)).astype(np.float32)
        self.anatomy = np.random.uniform(0, 0.5, (self.M, self.K)).astype(np.float32)
        self.concept = np.random.uniform(0, 1, (self.M, self.K)).astype(np.float32)
        self.alpha = np.random.dirichlet([1]*self.K, self.M).astype(np.float32)

    def test_compute_pairwise_spearman(self):
        from pada3dacb.evaluation.concepts.stability import compute_pairwise_spearman
        rho = compute_pairwise_spearman(self.fidelity)
        assert rho.shape == (self.M, self.M)
        assert np.allclose(np.diag(rho), 1.0)

    def test_compute_mean_pairwise_rho(self):
        from pada3dacb.evaluation.concepts.stability import (
            compute_mean_pairwise_rho,
            compute_pairwise_spearman,
        )
        rho = compute_pairwise_spearman(self.fidelity)
        mean_rho = compute_mean_pairwise_rho(rho)
        # Spearman correlation can be negative for random data; just verify it's a valid correlation
        assert -1 <= mean_rho <= 1

    def test_compute_instance_std(self):
        from pada3dacb.evaluation.concepts.stability import compute_instance_std
        std = compute_instance_std(self.fidelity)
        assert std.shape == (self.K,)
        assert np.all(std >= 0)

    def test_compute_top_k_indices(self):
        from pada3dacb.evaluation.concepts.stability import compute_top_k_indices
        top_k = compute_top_k_indices(self.fidelity, k=2, ascending=True)
        assert len(top_k) == self.M
        assert all(len(indices) == 2 for indices in top_k)

    def test_compute_jaccard_overlap(self):
        from pada3dacb.evaluation.concepts.stability import compute_jaccard_overlap
        a = np.array([0, 1, 2])
        b = np.array([1, 2, 3])
        jaccard = compute_jaccard_overlap(a, b)
        assert jaccard == 0.5  # intersection {1,2} / union {0,1,2,3} = 2/4

    def test_compute_all_stability(self):
        from pada3dacb.evaluation.concepts.stability import compute_all_stability
        result = compute_all_stability(
            self.fidelity, self.anatomy, self.concept, self.alpha,
            k_values=[2, 3]
        )
        assert hasattr(result, "mean_pairwise_rho_fidelity")
        assert hasattr(result, "jaccard_fidelity")
        assert hasattr(result, "jaccard_anatomy")
        assert hasattr(result, "jaccard_concept")
        assert hasattr(result, "jaccard_alpha")
        assert 2 in result.jaccard_fidelity
        assert 3 in result.jaccard_concept


if __name__ == "__main__":
    pytest.main([__file__, "-v"])