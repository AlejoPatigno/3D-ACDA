"""Tests for concept inference pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from pada3dacb.evaluation.concepts.inference import (
    CheckpointBundle,
    load_checkpoint,
    load_concept_normalizer_from_checkpoint,
    run_inference_on_candidates,
    run_subject_inference,
)
from pada3dacb.evaluation.concepts.schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptCandidate,
    ConceptNormalizerHash,
    Direction,
    MethodId,
    SubjectConceptRecord,
)
from pada3dacb.exceptions import ConfigurationError
from pada3dacb.models.pada3dacb import PADA3DACB


class TestCheckpointBundle:
    def test_bundle_creation(self):
        model = MagicMock(spec=PADA3DACB)
        bundle = CheckpointBundle(
            model=model,
            experiment_hash="exp123",
            model_hash="mod123",
            training_hash="trn123",
            epoch=50,
            logical_checkpoint="best_source_f1",
            config_dict={"K": 84},
            concept_normalizer=None,
        )
        assert bundle.model == model
        assert bundle.experiment_hash == "exp123"
        assert bundle.epoch == 50


class TestLoadCheckpoint:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.checkpoint_path = self.tmpdir / "checkpoint.pt"

    def test_load_checkpoint_success(self):
        ckpt = {
            "model_state_dict": {},
            "experiment_hash": "exp123",
            "model_hash": "mod123",
            "training_hash": "trn123",
            "epoch": 50,
            "logical_checkpoint": "best_source_f1",
            "config": {"num_rois": 5, "feature_dim": 256, "token_dim": 128},
        }
        torch.save(ckpt, self.checkpoint_path)

        with patch("pada3dacb.evaluation.concepts.inference.PADA3DACB") as mock_pada3dacb_class:
            mock_model = MagicMock(spec=PADA3DACB)
            mock_pada3dacb_class.return_value = mock_model
            mock_model.load_state_dict = MagicMock()
            mock_model.to = MagicMock(return_value=mock_model)
            mock_model.eval = MagicMock()

            bundle = load_checkpoint(self.checkpoint_path, "cpu")

            assert bundle.experiment_hash == "exp123"
            assert bundle.model_hash == "mod123"
            assert bundle.training_hash == "trn123"
            assert bundle.epoch == 50
            assert bundle.logical_checkpoint == "best_source_f1"
            mock_pada3dacb_class.assert_called_once()
            mock_model.load_state_dict.assert_called_once()

    def test_load_checkpoint_missing_hashes(self):
        ckpt = {"model_state_dict": {}, "epoch": 50}
        torch.save(ckpt, self.checkpoint_path)

        with pytest.raises(ConfigurationError, match="Checkpoint missing required hashes"):
            load_checkpoint(self.checkpoint_path, "cpu")

    def test_load_checkpoint_failure(self):
        # Corrupted file - write invalid pickle data
        self.checkpoint_path.write_bytes(b"not a valid checkpoint")

        with pytest.raises(ConfigurationError, match="Failed to load checkpoint"):
            load_checkpoint(self.checkpoint_path, "cpu")


class TestLoadConceptNormalizerFromCheckpoint:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def test_load_from_artifacts_root(self):
        artifacts_root = self.tmpdir / "artifacts"
        artifacts_root.mkdir()

        normalizer_data = {
            "mu": [0.0] * 5,
            "sigma": [1.0] * 5,
            "eps": 1e-6,
            "roi_labels": list(range(5)),
        }
        (artifacts_root / "concept_normalizer.json").write_text(json.dumps(normalizer_data))

        checkpoint_path = self.tmpdir / "checkpoints" / "method__dir__seed_42__fold_0" / "best_source_f1" / "checkpoint.pt"
        checkpoint_path.parent.mkdir(parents=True)
        torch.save({}, checkpoint_path)

        with patch("pada3dacb.evaluation.concepts.inference.ConceptNormalizer.load") as mock_load:
            mock_normalizer = MagicMock()
            mock_load.return_value = mock_normalizer

            result = load_concept_normalizer_from_checkpoint(checkpoint_path, artifacts_root)

            mock_load.assert_called_once_with(artifacts_root / "concept_normalizer.json")
            assert result == mock_normalizer

    def test_load_from_checkpoint_dir(self):
        checkpoint_dir = self.tmpdir / "checkpoints" / "method__dir__seed_42__fold_0" / "best_source_f1"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_path = checkpoint_dir / "checkpoint.pt"
        torch.save({}, checkpoint_path)

        normalizer_data = {
            "mu": [0.0] * 5,
            "sigma": [1.0] * 5,
            "eps": 1e-6,
            "roi_labels": list(range(5)),
        }
        (checkpoint_dir.parent / "concept_normalizer.json").write_text(json.dumps(normalizer_data))

        artifacts_root = self.tmpdir / "artifacts"
        artifacts_root.mkdir()

        with patch("pada3dacb.evaluation.concepts.inference.ConceptNormalizer.load") as mock_load:
            mock_normalizer = MagicMock()
            mock_load.return_value = mock_normalizer

            result = load_concept_normalizer_from_checkpoint(checkpoint_path, artifacts_root)

            mock_load.assert_called_once_with(checkpoint_dir.parent / "concept_normalizer.json")
            assert result == mock_normalizer

    def test_load_not_found(self):
        checkpoint_path = self.tmpdir / "checkpoint.pt"
        torch.save({}, checkpoint_path)

        artifacts_root = self.tmpdir / "artifacts"
        artifacts_root.mkdir()

        result = load_concept_normalizer_from_checkpoint(checkpoint_path, artifacts_root)
        assert result is None


class TestRunSubjectInference:
    def setup_method(self):
        self.K = 5
        self.device = "cpu"

        # Mock model
        self.model = MagicMock(spec=PADA3DACB)
        self.model.eval = MagicMock()

        # Mock normalizer
        self.normalizer = MagicMock()
        self.normalizer.atlas_mgr = MagicMock()
        self.normalizer.atlas_mgr.K = self.K

        # Mock dataloader
        self.dataloader = MagicMock()
        self.batch = {
            "x": torch.randn(2, 1, 64, 64, 64),
            "subject_id": ["sub-001", "sub-002"],
            "subject_hash": ["1" * 64, "2" * 64],
            "cohort": ["ADNI", "ADNI"],
            "label": torch.tensor([0, 1]),
            "label_name": ["CN", "MCI"],
            "concept_targets": torch.tensor([
                [0.1, 0.2, 0.3, 0.4, 0.5],
                [0.2, 0.3, 0.4, 0.5, 0.6],
            ]),
            "anatomical_targets": torch.tensor([
                [0.6, 0.5, 0.4, 0.3, 0.2],
                [0.7, 0.6, 0.5, 0.4, 0.3],
            ]),
            "metadata": {},
        }
        self.dataloader.__iter__ = MagicMock(return_value=iter([self.batch]))

        # Mock model forward
        concepts = torch.randn(2, self.K)
        latent_logits = torch.randn(2, 3)
        concept_logits = torch.randn(2, 3)
        alpha = torch.softmax(torch.randn(2, self.K), dim=1)

        mock_outputs = {
            "concepts": concepts,
            "latent_logits": latent_logits,
            "concept_logits": concept_logits,
            "alpha": alpha,
        }
        self.model.return_value = mock_outputs

        # Mock build_subject_concept_target
        self.concept_config = MagicMock()

    def test_run_subject_inference_uses_precomputed_targets(self):
        records = run_subject_inference(
            model=self.model,
            dataloader=self.dataloader,
            concept_normalizer=self.normalizer,
            device=self.device,
            atlas_mgr=self.normalizer.atlas_mgr,
            concept_config=self.concept_config,
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            source_domain="ADNI",
            target_domain="OASIS",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            experiment_hash="d" * 64,
            roi_order_hash=AtlasROIOrderHash("a" * 64),
            normalizer_hash=ConceptNormalizerHash("b" * 64),
            concept_config_hash="c" * 64,
        )

        assert len(records) == 2
        assert records[0].concept_targets == pytest.approx((0.1, 0.2, 0.3, 0.4, 0.5))
        assert records[0].anatomical_targets == pytest.approx((0.6, 0.5, 0.4, 0.3, 0.2))
        for record in records:
            assert isinstance(record, SubjectConceptRecord)
            assert len(record.predicted_concepts) == self.K
            assert len(record.concept_targets) == self.K
            assert len(record.anatomical_targets) == self.K
            assert len(record.attention_alpha) == self.K
            assert len(record.latent_probabilities) == 3
            assert len(record.concept_probabilities) == 3
            assert 0 <= record.latent_prediction <= 2
            assert 0 <= record.concept_prediction <= 2
            assert record.K == self.K

    def test_run_subject_inference_missing_outputs(self):
        # Model missing required outputs
        mock_outputs = {
            "concepts": torch.randn(2, self.K),
            "latent_logits": torch.randn(2, 3),
            # missing concept_logits and alpha
        }
        self.model.return_value = mock_outputs

        with pytest.raises(RuntimeError, match="Model output missing required keys"):
            run_subject_inference(
                model=self.model,
                dataloader=self.dataloader,
                concept_normalizer=self.normalizer,
                device=self.device,
                atlas_mgr=self.normalizer.atlas_mgr,
                concept_config=self.concept_config,
                method_id=MethodId.SOURCE_ONLY,
                direction=Direction.ADNI_TO_OASIS,
                source_domain="ADNI",
                target_domain="OASIS",
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=50,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                experiment_hash="d" * 64,
                roi_order_hash=AtlasROIOrderHash("a" * 64),
                normalizer_hash=ConceptNormalizerHash("b" * 64),
                concept_config_hash="c" * 64,
            )

    def test_run_subject_inference_rejects_atlas_k_mismatch(self):
        self.normalizer.atlas_mgr.K = self.K - 1
        with pytest.raises(RuntimeError, match="atlas K does not match model concepts"):
            run_subject_inference(
                model=self.model,
                dataloader=self.dataloader,
                concept_normalizer=self.normalizer,
                device=self.device,
                atlas_mgr=self.normalizer.atlas_mgr,
                method_id=MethodId.SOURCE_ONLY,
                direction=Direction.ADNI_TO_OASIS,
                source_domain="ADNI",
                target_domain="OASIS",
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=50,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                experiment_hash="d" * 64,
                roi_order_hash=AtlasROIOrderHash("a" * 64),
                normalizer_hash=ConceptNormalizerHash("b" * 64),
                concept_config_hash="c" * 64,
            )

    def test_run_subject_inference_requires_precomputed_targets(self):
        self.batch.pop("anatomical_targets")
        with pytest.raises(RuntimeError, match="precomputed concept and anatomical targets"):
            run_subject_inference(
                model=self.model,
                dataloader=self.dataloader,
                concept_normalizer=self.normalizer,
                device=self.device,
                atlas_mgr=self.normalizer.atlas_mgr,
                method_id=MethodId.SOURCE_ONLY,
                direction=Direction.ADNI_TO_OASIS,
                source_domain="ADNI",
                target_domain="OASIS",
                seed=42,
                fold=0,
                logical_checkpoint="best_source_f1",
                checkpoint_epoch=50,
                checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
                experiment_hash="d" * 64,
                roi_order_hash=AtlasROIOrderHash("a" * 64),
                normalizer_hash=ConceptNormalizerHash("b" * 64),
                concept_config_hash="c" * 64,
            )


class TestRunInferenceOnCandidates:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.device = "cpu"
        self.K = 5

        # Create mock normalizer
        self.normalizer = MagicMock()
        self.normalizer.atlas_mgr = MagicMock()

        # Create mock atlas_mgr
        self.atlas_mgr = MagicMock()

        # Create candidate
        self.candidate = ConceptCandidate(
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            experiment_hash="d" * 64,
            model_hash="e" * 64,
            training_hash="f" * 64,
            split_hashes={},
            atlas_hash="9" * 64,
            roi_order_hash="a" * 64,
            concept_normalizer_hash="b" * 64,
            checkpoint_path=self.tmpdir / "checkpoint.pt",
            concept_artifacts_root=self.tmpdir / "artifacts",
        )

    @patch("pada3dacb.evaluation.concepts.inference.load_checkpoint")
    @patch("pada3dacb.evaluation.concepts.inference.run_subject_inference")
    def test_run_inference_on_candidates(self, mock_run_inference, mock_load_checkpoint):
        # Mock checkpoint loading
        mock_model = MagicMock(spec=PADA3DACB)
        mock_bundle = CheckpointBundle(
            model=mock_model,
            experiment_hash="exp123",
            model_hash="mod123",
            training_hash="trn123",
            epoch=50,
            logical_checkpoint="best_source_f1",
            config_dict={"atlas_mgr": self.atlas_mgr},
            concept_normalizer=self.normalizer,
        )
        mock_load_checkpoint.return_value = mock_bundle

        # Mock inference results
        subject_record = SubjectConceptRecord(
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
            experiment_hash="d" * 64,
            subject_id="sub-001",
            subject_hash="1" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=(0.1, 0.2, 0.3, 0.4, 0.5),
            concept_targets=(0.2, 0.3, 0.4, 0.5, 0.6),
            anatomical_targets=(0.6, 0.5, 0.4, 0.3, 0.2),
            attention_alpha=tuple(np.ones(self.K) / self.K),
            latent_probabilities=(0.8, 0.1, 0.1),
            concept_probabilities=(0.7, 0.2, 0.1),
            latent_prediction=0,
            concept_prediction=0,
            K=self.K,
            roi_order_hash=AtlasROIOrderHash("a" * 64),
            normalizer_hash=ConceptNormalizerHash("b" * 64),
            concept_config_hash="c" * 64,
        )
        mock_run_inference.return_value = [subject_record]

        # Mock dataloader factory
        def dataloader_factory(candidate):
            return MagicMock()

        results = run_inference_on_candidates(
            candidates=[self.candidate],
            dataloader_factory=dataloader_factory,
            device=self.device,
            concept_normalizer=self.normalizer,
            atlas_mgr=self.atlas_mgr,
        )

        key = (
            self.candidate.method_id,
            self.candidate.direction,
            self.candidate.seed,
            self.candidate.fold,
            self.candidate.checkpoint_policy,
        )
        assert key in results
        assert len(results[key]) == 1

        record = results[key][0]
        assert isinstance(record, SubjectConceptRecord)
        call = mock_run_inference.call_args
        assert call.kwargs["method_id"] is MethodId.SOURCE_ONLY
        assert call.kwargs["direction"] is Direction.ADNI_TO_OASIS
        assert call.kwargs["experiment_hash"] == "d" * 64
        assert call.kwargs["roi_order_hash"] == AtlasROIOrderHash("a" * 64)
        assert call.kwargs["normalizer_hash"] == ConceptNormalizerHash("b" * 64)
        assert len(call.kwargs["concept_config_hash"]) == 64

    @patch("pada3dacb.evaluation.concepts.inference.load_checkpoint")
    def test_run_inference_rejects_candidate_with_provenance_issues(self, mock_load_checkpoint):
        self.candidate.issues.append("roi_order_hash_mismatch")

        with pytest.raises(ConfigurationError, match="provenance validation issues"):
            run_inference_on_candidates(
                candidates=[self.candidate],
                dataloader_factory=lambda candidate: MagicMock(),
                device=self.device,
                concept_normalizer=self.normalizer,
                atlas_mgr=self.atlas_mgr,
            )
        mock_load_checkpoint.assert_not_called()

    @patch("pada3dacb.evaluation.concepts.inference.load_checkpoint")
    @patch("pada3dacb.evaluation.concepts.inference.run_subject_inference")
    def test_run_inference_multiple_candidates(self, mock_run_inference, mock_load_checkpoint):
        mock_model = MagicMock(spec=PADA3DACB)
        mock_bundle = CheckpointBundle(
            model=mock_model,
            experiment_hash="exp123",
            model_hash="mod123",
            training_hash="trn123",
            epoch=50,
            logical_checkpoint="best_source_f1",
            config_dict={"atlas_mgr": self.atlas_mgr},
            concept_normalizer=self.normalizer,
        )
        mock_load_checkpoint.return_value = mock_bundle

        subject_record = SubjectConceptRecord(
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
            experiment_hash="d" * 64,
            subject_id="sub-001",
            subject_hash="1" * 64,
            cohort="ADNI",
            true_label=0,
            label_name="CN",
            predicted_concepts=(0.1, 0.2, 0.3, 0.4, 0.5),
            concept_targets=(0.2, 0.3, 0.4, 0.5, 0.6),
            anatomical_targets=(0.6, 0.5, 0.4, 0.3, 0.2),
            attention_alpha=tuple(np.ones(self.K) / self.K),
            latent_probabilities=(0.8, 0.1, 0.1),
            concept_probabilities=(0.7, 0.2, 0.1),
            latent_prediction=0,
            concept_prediction=0,
            K=self.K,
            roi_order_hash=AtlasROIOrderHash("a" * 64),
            normalizer_hash=ConceptNormalizerHash("b" * 64),
            concept_config_hash="c" * 64,
        )
        mock_run_inference.return_value = [subject_record]

        def dataloader_factory(candidate):
            return MagicMock()

        candidate2 = ConceptCandidate(
            method_id=MethodId.CORAL,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            experiment_hash="6" * 64,
            model_hash="7" * 64,
            training_hash="8" * 64,
            split_hashes={},
            atlas_hash="9" * 64,
            roi_order_hash="a" * 64,
            concept_normalizer_hash="b" * 64,
            checkpoint_path=self.tmpdir / "checkpoint2.pt",
            concept_artifacts_root=self.tmpdir / "artifacts2",
        )

        results = run_inference_on_candidates(
            candidates=[self.candidate, candidate2],
            dataloader_factory=dataloader_factory,
            device=self.device,
            concept_normalizer=self.normalizer,
            atlas_mgr=self.atlas_mgr,
        )

        assert len(results) == 2
        key1 = (
            MethodId.SOURCE_ONLY, Direction.ADNI_TO_OASIS, 42, 0,
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1
        )
        key2 = (
            MethodId.CORAL, Direction.ADNI_TO_OASIS, 42, 0,
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1
        )
        assert key1 in results
        assert key2 in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])