"""Tests for concept evaluation schemas."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptNormalizerHash,
    ConceptSubjectRecord,
    Direction,
    MethodId,
    validate_alpha_sums_to_one,
    validate_concept_normalizer,
    validate_finite_array,
    validate_roi_order,
)
from pada3dacb.evaluation.schemas import ConfigurationError


def _make_record(**overrides: object) -> ConceptSubjectRecord:
    k = 5
    values: dict[str, object] = {
        "method_id": MethodId.SOURCE_ONLY,
        "model": "PADA-3DACB",
        "direction": Direction.ADNI_TO_OASIS,
        "source_domain": "ADNI",
        "target_domain": "OASIS",
        "seed": 42,
        "fold": 0,
        "logical_checkpoint": "best_source_f1",
        "checkpoint_epoch": 100,
        "checkpoint_policy": CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        "experiment_hash": "a" * 64,
        "subject_id": "sub-001",
        "subject_hash": "b" * 64,
        "cohort": "ADNI",
        "true_label": 0,
        "label_name": "CN",
        "predicted_concepts": (0.1, 0.2, 0.3, 0.4, 0.5),
        "concept_targets": (0.2, 0.3, 0.4, 0.5, 0.6),
        "anatomical_targets": (0.3, 0.4, 0.5, 0.6, 0.7),
        "attention_alpha": (0.1, 0.2, 0.3, 0.15, 0.25),
        "latent_probabilities": (0.8, 0.1, 0.1),
        "concept_probabilities": (0.7, 0.2, 0.1),
        "latent_prediction": 0,
        "concept_prediction": 0,
        "K": k,
        "roi_order_hash": "a" * 64,
        "normalizer_hash": "b" * 64,
        "concept_config_hash": "c" * 64,
    }
    values.update(overrides)
    return ConceptSubjectRecord(**values)  # type: ignore[arg-type]


class TestConceptSubjectRecord:
    def test_valid_record(self):
        K = 5
        record = ConceptSubjectRecord(
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=100,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            experiment_hash="a" * 64,
            subject_id="sub-001",
            subject_hash="b" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=tuple(np.linspace(0.1, 0.5, K)),
            concept_targets=tuple(np.linspace(0.1, 0.5, K)),
            anatomical_targets=tuple(np.linspace(0.1, 0.5, K)),
            attention_alpha=tuple(np.full(K, 1.0 / K)),
            latent_probabilities=(0.8, 0.1, 0.1),
            concept_probabilities=(0.7, 0.2, 0.1),
            latent_prediction=0,
            concept_prediction=0,
            model="PADA-3DACB",
            source_domain="ADNI",
            target_domain="OASIS",
            K=K,
            roi_order_hash="a" * 64,
            normalizer_hash="b" * 64,
            concept_config_hash="c" * 64,
        )
        assert record.K == K
        assert record.subject_key is not None

    def test_invalid_vector_length(self):
        K = 5
        with pytest.raises(ValueError, match="length 3 != K=5"):
            ConceptSubjectRecord(
                method_id=MethodId.SOURCE_ONLY,
                direction=Direction.ADNI_TO_OASIS,
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=100,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                experiment_hash="a" * 64,
                subject_id="sub-001",
                subject_hash="b" * 64,
                cohort="ADNI",
                true_label=0,
                label_name="CN",
                predicted_concepts=tuple(np.linspace(0.1, 0.3, 3)),  # Wrong length
                concept_targets=tuple(np.linspace(0.1, 0.5, K)),
                anatomical_targets=tuple(np.linspace(0.1, 0.5, K)),
                attention_alpha=tuple(np.full(K, 1.0 / K)),
                latent_probabilities=(0.8, 0.1, 0.1),
                concept_probabilities=(0.7, 0.2, 0.1),
                latent_prediction=0,
                concept_prediction=0,
                model="PADA-3DACB",
                source_domain="ADNI",
                target_domain="OASIS",
                K=K,
                roi_order_hash="a" * 64,
                normalizer_hash="b" * 64,
                concept_config_hash="c" * 64,
            )

    def test_invalid_prediction(self):
        K = 5
        with pytest.raises(ValueError, match="latent_prediction must be 0, 1, or 2"):
            ConceptSubjectRecord(
                method_id=MethodId.SOURCE_ONLY,
                direction=Direction.ADNI_TO_OASIS,
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=100,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                experiment_hash="a" * 64,
                subject_id="sub-001",
                subject_hash="b" * 64,
                cohort="ADNI",
                true_label=0,
                label_name="CN",
                predicted_concepts=tuple(np.linspace(0.1, 0.5, K)),
                concept_targets=tuple(np.linspace(0.1, 0.5, K)),
                anatomical_targets=tuple(np.linspace(0.1, 0.5, K)),
                attention_alpha=tuple(np.full(K, 1.0 / K)),
                latent_probabilities=(0.8, 0.1, 0.1),
                concept_probabilities=(0.7, 0.2, 0.1),
                latent_prediction=3,  # Invalid
                concept_prediction=0,
                model="PADA-3DACB",
                source_domain="ADNI",
                target_domain="OASIS",
                K=K,
                roi_order_hash="a" * 64,
                normalizer_hash="b" * 64,
                concept_config_hash="c" * 64,
            )

    @pytest.mark.parametrize(
        ("field_name", "invalid_values"),
        [
            ("predicted_concepts", (np.nan, 0.2, 0.3, 0.4, 0.5)),
            ("concept_targets", (0.1, np.inf, 0.3, 0.4, 0.5)),
            ("anatomical_targets", (0.1, 0.2, -np.inf, 0.4, 0.5)),
            ("attention_alpha", (0.1, 0.2, 0.3, np.nan, 0.4)),
            ("latent_probabilities", (0.8, np.nan, 0.2)),
            ("concept_probabilities", (np.inf, 0.0, 0.0)),
        ],
    )
    def test_rejects_non_finite_outputs(self, field_name, invalid_values):
        with pytest.raises(ValueError, match=rf"{field_name} contains non-finite values"):
            _make_record(**{field_name: invalid_values})

    def test_rejects_non_normalized_attention(self):
        with pytest.raises(ValueError, match="attention alpha sums to"):
            _make_record(attention_alpha=(0.1, 0.1, 0.1, 0.1, 0.1))

    @pytest.mark.parametrize(
        "field_name",
        ["predicted_concepts", "concept_targets", "anatomical_targets"],
    )
    def test_rejects_out_of_range_normalized_concepts(self, field_name):
        with pytest.raises(ValueError, match=rf"{field_name} must be in \[0, 1\]"):
            _make_record(**{field_name: (0.1, 0.2, 0.3, 0.4, 1.1)})

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"K": 0}, "K must be positive"),
            ({"seed": -1}, "seed must be nonnegative"),
            ({"fold": -1}, "fold must be nonnegative"),
            ({"checkpoint_epoch": -1}, "checkpoint_epoch must be nonnegative"),
            ({"true_label": 3}, "true_label must be 0, 1, or 2"),
            ({"label_name": "AD"}, "label_name does not match true_label"),
            ({"source_domain": "OASIS"}, "source_domain does not match direction"),
            ({"target_domain": "ADNI"}, "target_domain does not match direction"),
            ({"cohort": "OTHER"}, "cohort must match source or target domain"),
            ({"logical_checkpoint": "last"}, "logical checkpoint does not match policy"),
            ({"latent_probabilities": (-0.1, 0.5, 0.6)}, "latent_probabilities must be in"),
            ({"concept_probabilities": (0.2, 0.2, 0.2)}, "concept_probabilities must sum to one"),
            ({"latent_prediction": 1}, "latent_prediction must equal probability argmax"),
            ({"concept_prediction": 2}, "concept_prediction must equal probability argmax"),
            ({"attention_alpha": (-0.1, 0.2, 0.3, 0.3, 0.3)}, "attention_alpha must be nonnegative"),
        ],
    )
    def test_rejects_invalid_metadata_and_probability_contracts(self, overrides, message):
        with pytest.raises(ValueError, match=message):
            _make_record(**overrides)

    @pytest.mark.parametrize(
        "field_name",
        [
            "experiment_hash",
            "subject_hash",
            "roi_order_hash",
            "normalizer_hash",
            "concept_config_hash",
        ],
    )
    def test_rejects_non_sha256_metadata(self, field_name):
        with pytest.raises(ValueError, match=rf"{field_name} must be lowercase SHA-256"):
            _make_record(**{field_name: "not-a-sha256"})


class TestValidationUtilities:
    def test_validate_finite_array(self):
        arr = np.array([1.0, 2.0, 3.0])
        validate_finite_array(arr, "test")

    def test_validate_finite_array_nan(self):
        arr = np.array([1.0, np.nan, 3.0])
        with pytest.raises(ValueError, match="test contains non-finite values"):
            validate_finite_array(arr, "test")

    def test_validate_finite_array_inf(self):
        arr = np.array([1.0, np.inf, 3.0])
        with pytest.raises(ValueError, match="test contains non-finite values"):
            validate_finite_array(arr, "test")

    def test_validate_alpha_sums_to_one(self):
        alpha = np.array([[0.2, 0.3, 0.5], [0.1, 0.6, 0.3]])
        validate_alpha_sums_to_one(alpha, tol=1e-4)

    def test_validate_alpha_sums_to_one_fail(self):
        alpha = np.array([[0.2, 0.3, 0.5], [0.1, 0.6, 0.4]])  # Second row sums to 1.1
        with pytest.raises(ValueError, match="attention alpha sums to"):
            validate_alpha_sums_to_one(alpha, tol=1e-4)

    def test_validate_roi_order(self):
        validate_roi_order(5, AtlasROIOrderHash("a" * 64), AtlasROIOrderHash("a" * 64))

    def test_validate_roi_order_rejects_nonpositive_k(self):
        with pytest.raises(ConfigurationError, match="ROI count must be positive"):
            validate_roi_order(0, AtlasROIOrderHash("a" * 64), AtlasROIOrderHash("a" * 64))

    def test_validate_roi_order_mismatch(self):
        with pytest.raises(ConfigurationError, match="ROI order hash mismatch"):
            validate_roi_order(5, AtlasROIOrderHash("a" * 64), AtlasROIOrderHash("b" * 64))

    def test_validate_concept_normalizer(self):
        validate_concept_normalizer(
            ConceptNormalizerHash("a" * 64),
            ConceptNormalizerHash("a" * 64)
        )

    def test_validate_concept_normalizer_mismatch(self):
        with pytest.raises(ConfigurationError, match="Concept normalizer hash mismatch"):
            validate_concept_normalizer(
                ConceptNormalizerHash("a" * 64),
                ConceptNormalizerHash("b" * 64)
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])