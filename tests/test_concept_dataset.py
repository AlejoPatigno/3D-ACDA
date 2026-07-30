"""Tests for concept evaluation dataset."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from pada3dacb.evaluation.concepts.dataset import (
    ConceptEvaluationDataset,
    ConceptEvaluationSample,
    aggregate_folds,
    aggregate_seeds,
    build_concept_evaluation_dataset,
)
from pada3dacb.evaluation.concepts.schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptNormalizerHash,
    ConfigurationError,
    Direction,
    MethodId,
    SubjectConceptRecord,
    validate_alpha_sums_to_one,
    validate_finite_array,
)


class TestConceptEvaluationSample:
    def test_valid_sample(self):
        K = 5
        sample = ConceptEvaluationSample(
            subject_id="sub-001",
            subject_hash="a" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=torch.rand(K),
            concept_targets=torch.rand(K),
            anatomical_targets=torch.rand(K),
            attention_alpha=torch.tensor([0.2, 0.2, 0.2, 0.2, 0.2]),
            latent_probabilities=torch.tensor([0.8, 0.1, 0.1]),
            concept_probabilities=torch.tensor([0.7, 0.2, 0.1]),
            latent_prediction=0,
            concept_prediction=0,
            experiment_hash="exp123",
            direction="adni_to_oasis",
            checkpoint_policy="best_source_f1",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
        )
        assert sample.predicted_concepts.shape == (K,)
        assert sample.attention_alpha.sum().item() == pytest.approx(1.0, abs=1e-4)

    def test_invalid_alpha_sum(self):
        K = 5
        with pytest.raises(ValueError, match="attention alpha sums to"):
            ConceptEvaluationSample(
                subject_id="sub-001",
                subject_hash="a" * 64,
                cohort="ADNI",
                true_label=0,
                label_name="CN",
                predicted_concepts=torch.rand(K),
                concept_targets=torch.rand(K),
                anatomical_targets=torch.rand(K),
                attention_alpha=torch.tensor([0.3, 0.3, 0.3, 0.3, 0.3]),  # Sum = 1.5
                latent_probabilities=torch.tensor([0.8, 0.1, 0.1]),
                concept_probabilities=torch.tensor([0.7, 0.2, 0.1]),
                latent_prediction=0,
                concept_prediction=0,
                experiment_hash="exp123",
                direction="adni_to_oasis",
                checkpoint_policy="best_source_f1",
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=50,
            )


class TestConceptEvaluationDataset:
    def setup_method(self):
        self.K = 5
        self.roi_order_hash = AtlasROIOrderHash("a" * 64)
        self.normalizer_hash = ConceptNormalizerHash("b" * 64)

    def _make_sample(self, subject_id="sub-001", true_label=0):
        return ConceptEvaluationSample(
            subject_id=subject_id,
            subject_hash=f"{hash(subject_id):064x}",
            cohort="ADNI",
            true_label=true_label,
            label_name=["CN", "MCI", "AD"][true_label],
            predicted_concepts=torch.rand(self.K),
            concept_targets=torch.rand(self.K),
            anatomical_targets=torch.rand(self.K),
            attention_alpha=torch.tensor([1.0 / self.K] * self.K),
            latent_probabilities=torch.tensor([0.8, 0.1, 0.1]),
            concept_probabilities=torch.tensor([0.7, 0.2, 0.1]),
            latent_prediction=0,
            concept_prediction=0,
            experiment_hash="exp123",
            direction="adni_to_oasis",
            checkpoint_policy="best_source_f1",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
        )

    def test_valid_dataset(self):
        samples = [self._make_sample(f"sub-{i:03d}", i % 3) for i in range(10)]
        ds = ConceptEvaluationDataset(samples, self.roi_order_hash, self.normalizer_hash)
        assert len(ds) == 10
        assert ds.k == self.K
        assert ds.roi_order_hash == self.roi_order_hash
        assert ds.concept_normalizer_hash == self.normalizer_hash

    def test_empty_dataset_raises(self):
        with pytest.raises(ConfigurationError, match="requires at least one sample"):
            ConceptEvaluationDataset([], self.roi_order_hash, self.normalizer_hash)

    def test_shape_mismatch_raises(self):
        samples = [self._make_sample()]
        # Create sample with wrong K
        bad_sample = ConceptEvaluationSample(
            subject_id="sub-002",
            subject_hash="b" * 64,
            cohort="ADNI",
            true_label=1,
            label_name="MCI",
            predicted_concepts=torch.rand(self.K + 1),  # Wrong K
            concept_targets=torch.rand(self.K + 1),
            anatomical_targets=torch.rand(self.K + 1),
            attention_alpha=torch.tensor([1.0 / (self.K + 1)] * (self.K + 1)),
            latent_probabilities=torch.tensor([0.8, 0.1, 0.1]),
            concept_probabilities=torch.tensor([0.7, 0.2, 0.1]),
            latent_prediction=0,
            concept_prediction=0,
            experiment_hash="exp123",
            direction="adni_to_oasis",
            checkpoint_policy="best_source_f1",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
        )
        with pytest.raises(ConfigurationError, match="shape mismatch"):
            ConceptEvaluationDataset([samples[0], bad_sample], self.roi_order_hash, self.normalizer_hash)

    def test_getitem(self):
        samples = [self._make_sample(f"sub-{i:03d}", i % 3) for i in range(5)]
        ds = ConceptEvaluationDataset(samples, self.roi_order_hash, self.normalizer_hash)
        sample = ds[2]
        assert sample.subject_id == "sub-002"
        assert sample.true_label == 2

    def test_filter_by_label(self):
        samples = [self._make_sample(f"sub-{i:03d}", i % 3) for i in range(9)]
        ds = ConceptEvaluationDataset(samples, self.roi_order_hash, self.normalizer_hash)
        cn_ds = ds.filter_by_label(0)
        assert len(cn_ds) == 3
        assert all(s.true_label == 0 for s in cn_ds)

    def test_filter_by_cohort(self):
        samples = [
            self._make_sample("sub-001", 0),
            self._make_sample("sub-002", 1),
        ]
        # Manually set different cohorts
        samples[0] = ConceptEvaluationSample(
            subject_id="sub-001",
            subject_hash="a" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=torch.rand(self.K),
            concept_targets=torch.rand(self.K),
            anatomical_targets=torch.rand(self.K),
            attention_alpha=torch.tensor([1.0 / self.K] * self.K),
            latent_probabilities=torch.tensor([0.8, 0.1, 0.1]),
            concept_probabilities=torch.tensor([0.7, 0.2, 0.1]),
            latent_prediction=0,
            concept_prediction=0,
            experiment_hash="exp123",
            direction="adni_to_oasis",
            checkpoint_policy="best_source_f1",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
        )
        samples[1] = ConceptEvaluationSample(
            subject_id="sub-002",
            subject_hash="b" * 64,
            cohort="OASIS",
            true_label=1,
            label_name="MCI",
            predicted_concepts=torch.rand(self.K),
            concept_targets=torch.rand(self.K),
            anatomical_targets=torch.rand(self.K),
            attention_alpha=torch.tensor([1.0 / self.K] * self.K),
            latent_probabilities=torch.tensor([0.8, 0.1, 0.1]),
            concept_probabilities=torch.tensor([0.7, 0.2, 0.1]),
            latent_prediction=0,
            concept_prediction=0,
            experiment_hash="exp123",
            direction="adni_to_oasis",
            checkpoint_policy="best_source_f1",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
        )
        ds = ConceptEvaluationDataset(samples, self.roi_order_hash, self.normalizer_hash)
        adni_ds = ds.filter_by_cohort("ADNI")
        assert len(adni_ds) == 1
        assert adni_ds[0].cohort == "ADNI"

    def test_to_arrays(self):
        samples = [self._make_sample(f"sub-{i:03d}", i % 3) for i in range(6)]
        ds = ConceptEvaluationDataset(samples, self.roi_order_hash, self.normalizer_hash)
        arrays = ds.to_arrays()
        assert arrays["predicted_concepts"].shape == (6, self.K)
        assert arrays["concept_targets"].shape == (6, self.K)
        assert arrays["anatomical_targets"].shape == (6, self.K)
        assert arrays["attention_alpha"].shape == (6, self.K)
        assert arrays["latent_probabilities"].shape == (6, 3)
        assert arrays["concept_probabilities"].shape == (6, 3)
        assert arrays["latent_predictions"].shape == (6,)
        assert arrays["concept_predictions"].shape == (6,)
        assert arrays["true_labels"].shape == (6,)
        assert arrays["subject_hashes"].shape == (6,)


class TestFoldEnsemble:
    def setup_method(self):
        self.K = 5
        self.roi_order_hash = AtlasROIOrderHash("a" * 64)
        self.normalizer_hash = ConceptNormalizerHash("b" * 64)

    def _make_subject_record(self, fold: int, seed: int = 42) -> SubjectConceptRecord:
        return SubjectConceptRecord(
            method_id=MethodId.SOURCE_ONLY,
            model="PADA-3DACB",
            direction=Direction.ADNI_TO_OASIS,
            source_domain="ADNI",
            target_domain="OASIS",
            seed=seed,
            fold=fold,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            experiment_hash="a" * 64,
            subject_id="sub-001",
            subject_hash="a" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=tuple(np.random.rand(self.K)),
            concept_targets=tuple(np.random.rand(self.K)),
            anatomical_targets=tuple(np.random.rand(self.K)),
            attention_alpha=tuple(np.ones(self.K) / self.K),
            latent_probabilities=(0.8, 0.1, 0.1),
            concept_probabilities=(0.7, 0.2, 0.1),
            latent_prediction=0,
            concept_prediction=0,
            K=self.K,
            roi_order_hash=self.roi_order_hash,
            normalizer_hash=self.normalizer_hash,
            concept_config_hash="c" * 64,
        )

    def test_aggregate_folds_valid(self):
        fold_records = [self._make_subject_record(fold=f) for f in range(5)]
        expected_folds = [0, 1, 2, 3, 4]
        ensemble = aggregate_folds(fold_records, expected_folds)

        assert ensemble.fold_count == 5
        assert ensemble.subject_id == "sub-001"
        assert ensemble.subject_hash == "a" * 64
        assert ensemble.predicted_concepts.shape == (self.K,)
        assert ensemble.latent_probabilities.shape == (3,)
        assert ensemble.concept_probabilities.shape == (3,)
        assert ensemble.attention_alpha.shape == (self.K,)

    def test_aggregate_folds_missing_fold_raises(self):
        fold_records = [self._make_subject_record(fold=f) for f in range(4)]  # Missing fold 4
        expected_folds = [0, 1, 2, 3, 4]
        with pytest.raises(ValueError, match="Missing or extra folds"):
            aggregate_folds(fold_records, expected_folds)

    def test_aggregate_folds_wrong_subject_raises(self):
        fold_records = [self._make_subject_record(fold=f) for f in range(2)]
        fold_records[1] = SubjectConceptRecord(
            method_id=MethodId.SOURCE_ONLY,
            model="PADA-3DACB",
            direction=Direction.ADNI_TO_OASIS,
            source_domain="ADNI",
            target_domain="OASIS",
            seed=42,
            fold=1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            experiment_hash="a" * 64,
            subject_id="sub-002",
            subject_hash="b" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=tuple(np.random.rand(self.K)),
            concept_targets=tuple(np.random.rand(self.K)),
            anatomical_targets=tuple(np.random.rand(self.K)),
            attention_alpha=tuple(np.ones(self.K) / self.K),
            latent_probabilities=(0.8, 0.1, 0.1),
            concept_probabilities=(0.7, 0.2, 0.1),
            latent_prediction=0,
            concept_prediction=0,
            K=self.K,
            roi_order_hash=self.roi_order_hash,
            normalizer_hash=self.normalizer_hash,
            concept_config_hash="c" * 64,
        )
        expected_folds = [0, 1]
        with pytest.raises(ValueError, match="inconsistent subject hashes"):
            aggregate_folds(fold_records, expected_folds)

    def test_aggregate_seeds(self):
        fold_ensembles = []
        for seed in [42, 123]:
            fold_records = [self._make_subject_record(fold=f, seed=seed) for f in range(5)]
            ensemble = aggregate_folds(fold_records, [0, 1, 2, 3, 4])
            fold_ensembles.append(ensemble)

        mean_concepts, mean_alpha, mean_latent, mean_concept = aggregate_seeds(fold_ensembles)

        assert mean_concepts.shape == (self.K,)
        assert mean_alpha.shape == (self.K,)
        assert mean_latent.shape == (3,)
        assert mean_concept.shape == (3,)

    def test_aggregate_seeds_empty_raises(self):
        with pytest.raises(ValueError, match="No seed ensembles to aggregate"):
            aggregate_seeds([])


class TestBuildConceptEvaluationDataset:
    def test_build_from_subject_records(self):
        K = 5
        roi_order_hash = AtlasROIOrderHash("a" * 64)
        normalizer_hash = ConceptNormalizerHash("b" * 64)

        subject_records = [
            SubjectConceptRecord(
                method_id=MethodId.SOURCE_ONLY,
                model="PADA-3DACB",
                direction=Direction.ADNI_TO_OASIS,
                source_domain="ADNI",
                target_domain="OASIS",
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=50,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                experiment_hash="a" * 64,
                subject_id=f"sub-{i:03d}",
                subject_hash=f"{i:064x}",
                cohort="ADNI",
                true_label=i % 3,
                label_name=["CN", "MCI", "AD"][i % 3],
                predicted_concepts=tuple(np.random.rand(K)),
                concept_targets=tuple(np.random.rand(K)),
                anatomical_targets=tuple(np.random.rand(K)),
                attention_alpha=tuple(np.ones(K) / K),
                latent_probabilities=(0.8, 0.1, 0.1),
                concept_probabilities=(0.7, 0.2, 0.1),
                latent_prediction=0,
                concept_prediction=0,
                K=K,
                roi_order_hash=roi_order_hash,
                normalizer_hash=normalizer_hash,
                concept_config_hash="c" * 64,
            )
            for i in range(10)
        ]

        ds = build_concept_evaluation_dataset(subject_records, roi_order_hash, normalizer_hash)
        assert len(ds) == 10
        assert ds.k == K


class TestValidationUtilities:
    def test_validate_finite_array(self):
        arr = np.array([1.0, 2.0, 3.0])
        validate_finite_array(arr, "test")

    def test_validate_finite_array_nan(self):
        arr = np.array([1.0, np.nan, 3.0])
        with pytest.raises(ValueError, match="contains non-finite values"):
            validate_finite_array(arr, "test")

    def test_validate_finite_array_inf(self):
        arr = np.array([1.0, np.inf, 3.0])
        with pytest.raises(ValueError, match="contains non-finite values"):
            validate_finite_array(arr, "test")

    def test_validate_alpha_sums_to_one(self):
        alpha = np.array([[0.2, 0.3, 0.5], [0.1, 0.6, 0.3]])
        validate_alpha_sums_to_one(alpha, tol=1e-4)

    def test_validate_alpha_sums_to_one_fail(self):
        alpha = np.array([[0.2, 0.3, 0.5], [0.1, 0.6, 0.4]])  # Second row sums to 1.1
        with pytest.raises(ValueError, match="attention alpha sums to"):
            validate_alpha_sums_to_one(alpha, tol=1e-4)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])