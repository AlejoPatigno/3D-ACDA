"""Tests for concept inference pipeline."""

from __future__ import annotations

import dataclasses
import hashlib
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
    run_real_evaluation,
    run_subject_inference,
)
from pada3dacb.evaluation.concepts.provenance import VerifiedEvaluationInputs
from pada3dacb.evaluation.concepts.schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptCandidate,
    ConceptNormalizerHash,
    Direction,
    FileIdentity,
    MethodId,
    RealEvaluationCapability,
    SubjectConceptRecord,
    VerifiedFixtureManifest,
    issue_real_evaluation_capability,
    verify_fixture_manifest,
)
from pada3dacb.evaluation.schemas import AnalysisMode, AuthorizationGateError
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
            mock_model.load_state_dict.assert_called_once_with({}, strict=True)

    def test_load_checkpoint_uses_safe_weights_only_loader(self, monkeypatch):
        ckpt = {
            "model_state_dict": {},
            "experiment_hash": "exp123",
            "model_hash": "mod123",
            "training_hash": "trn123",
            "config": {},
        }
        torch.save(ckpt, self.checkpoint_path)
        calls = []
        original_load = torch.load

        def traced_load(*args, **kwargs):
            calls.append(kwargs.get("weights_only"))
            return original_load(*args, **kwargs)

        monkeypatch.setattr(torch, "load", traced_load)
        with patch("pada3dacb.evaluation.concepts.inference.PADA3DACB") as model_class:
            model = MagicMock(spec=PADA3DACB)
            model_class.return_value = model
            load_checkpoint(self.checkpoint_path, "cpu")

        assert calls == [True]

    def test_unsupported_checkpoint_never_retries_with_unsafe_loader(self, monkeypatch):
        torch.save({"unsupported": object()}, self.checkpoint_path)
        calls = []
        original_load = torch.load

        def traced_load(*args, **kwargs):
            calls.append(kwargs.get("weights_only"))
            return original_load(*args, **kwargs)

        monkeypatch.setattr(torch, "load", traced_load)
        with pytest.raises(ConfigurationError, match="unsupported or unsafe checkpoint format"):
            load_checkpoint(self.checkpoint_path, "cpu")
        assert calls == [True]

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

    def test_load_checkpoint_requires_training_hash(self):
        ckpt = {
            "model_state_dict": {},
            "experiment_hash": "exp123",
            "model_hash": "mod123",
            "epoch": 50,
        }
        torch.save(ckpt, self.checkpoint_path)

        with pytest.raises(ConfigurationError, match="Checkpoint missing required hashes"):
            load_checkpoint(self.checkpoint_path, "cpu")


    def test_load_checkpoint_rejects_incompatible_state_dict(self):
        ckpt = {
            "model_state_dict": {"unexpected": torch.tensor(1.0)},
            "experiment_hash": "exp123",
            "model_hash": "mod123",
            "training_hash": "trn123",
            "config": {"num_rois": 5},
        }
        torch.save(ckpt, self.checkpoint_path)

        with patch("pada3dacb.evaluation.concepts.inference.PADA3DACB") as mock_pada3dacb_class:
            mock_model = MagicMock(spec=PADA3DACB)
            mock_pada3dacb_class.return_value = mock_model
            mock_model.load_state_dict.side_effect = RuntimeError("missing keys")

            with pytest.raises(ConfigurationError, match="incompatible model state"):
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
            "roi_masks": torch.ones(self.K, 8, 8, 8),
            "metadata": {},
        }
        self.normalizer.atlas_mgr.get_binary_masks.return_value = self.batch["roi_masks"]
        self.dataloader.__iter__ = MagicMock(return_value=iter([self.batch]))

        # Mock model forward
        concepts = torch.sigmoid(torch.randn(2, self.K))
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

    def test_run_subject_inference_requires_roi_masks(self):
        self.batch.pop("roi_masks")
        with pytest.raises(RuntimeError, match="roi_masks"):
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

    def test_run_subject_inference_rejects_malformed_roi_masks(self):
        self.batch["roi_masks"] = torch.ones(1, self.K, 8, 8, 8)
        with pytest.raises(RuntimeError, match="B dimension must match x"):
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

    def test_run_subject_inference_collapses_equivalent_batched_roi_masks(self):
        canonical = torch.arange(self.K * 8 * 8 * 8, dtype=torch.float32).reshape(self.K, 8, 8, 8)
        self.normalizer.atlas_mgr.get_binary_masks.return_value = canonical
        self.batch["roi_masks"] = canonical.unsqueeze(0).expand(2, -1, -1, -1, -1).clone()

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
        torch.testing.assert_close(self.model.call_args.args[1], canonical)

    def test_run_subject_inference_rejects_inconsistent_batched_roi_masks(self):
        self.batch["roi_masks"] = torch.ones(2, self.K, 8, 8, 8)
        self.batch["roi_masks"][1, 0, 0, 0, 0] = 2.0
        with pytest.raises(RuntimeError, match="identical across subjects"):
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

    def test_run_subject_inference_rejects_reordered_canonical_roi_masks(self):
        canonical = torch.arange(self.K * 8 * 8 * 8, dtype=torch.float32).reshape(
            self.K, 8, 8, 8
        ) + 1.0
        self.normalizer.atlas_mgr.get_binary_masks.return_value = canonical
        self.batch["roi_masks"] = canonical.flip(0)
        with pytest.raises(RuntimeError, match="canonical atlas ROI masks"):
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

    def test_run_subject_inference_rejects_wrong_declared_roi_order_hash(self):
        labels = list(range(1, self.K + 1))
        self.normalizer.atlas_mgr.label_values = labels
        self.batch["roi_masks"] = torch.ones(self.K, 8, 8, 8)
        with pytest.raises(RuntimeError, match="ROI order hash"):
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
                roi_order_hash=AtlasROIOrderHash("0" * 64),
                normalizer_hash=ConceptNormalizerHash("b" * 64),
                concept_config_hash="c" * 64,
            )

    def test_run_subject_inference_accepts_matching_roi_order_hash(self):
        labels = list(range(1, self.K + 1))
        self.normalizer.atlas_mgr.label_values = labels
        self.batch["roi_masks"] = torch.ones(self.K, 8, 8, 8)
        expected_hash = hashlib.sha256(json.dumps(labels).encode()).hexdigest()
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
            roi_order_hash=AtlasROIOrderHash(expected_hash),
            normalizer_hash=ConceptNormalizerHash("b" * 64),
            concept_config_hash="c" * 64,
        )
        assert len(records) == 2

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
        self.candidate.checkpoint_path.write_bytes(b"fixture-checkpoint")
        self.fixture_manifest = self._write_fixture_manifest([self.candidate.checkpoint_path])

    def _write_fixture_manifest(self, paths):
        payload = {
            "schema_version": "phase16-concept-fixture-manifest-v1",
            "fixture_marker": "phase16-synthetic-fixture",
            "fixture_only": True,
            "files": [
                {
                    "relative_path": path.relative_to(self.tmpdir).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in paths
            ],
        }
        return self._write_manifest_payload(payload)

    def _write_manifest_payload(self, payload, expected_sha256=None):
        manifest_path = self.tmpdir / "fixture-manifest.json"
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        manifest_path.write_bytes(raw)
        return verify_fixture_manifest(
            manifest_path,
            expected_sha256 or hashlib.sha256(raw).hexdigest(),
            self.tmpdir,
        )

    @patch("pada3dacb.evaluation.concepts.inference.load_checkpoint")
    def test_fixture_boolean_without_verified_manifest_fails_before_checkpoint_load(self, mock_load_checkpoint):
        with pytest.raises(AuthorizationGateError, match="verified fixture manifest"):
            run_inference_on_candidates(
                candidates=[self.candidate],
                dataloader_factory=lambda candidate: MagicMock(),
                device=self.device,
                concept_normalizer=self.normalizer,
                atlas_mgr=self.atlas_mgr,
                fixture_only=True,
            )
        mock_load_checkpoint.assert_not_called()

    @pytest.mark.parametrize("normalizer_hash", [None, "not-a-sha256"])
    def test_fixture_normalizer_hash_is_preflighted_before_checkpoint_load(self, normalizer_hash):
        candidate = dataclasses.replace(
            self.candidate, concept_normalizer_hash=normalizer_hash
        )
        dataloader_factory = MagicMock()
        with patch(
            "pada3dacb.evaluation.concepts.inference.load_checkpoint"
        ) as load_checkpoint, pytest.raises(ConfigurationError, match="normalizer hash"):
            run_inference_on_candidates(
                candidates=[candidate],
                dataloader_factory=dataloader_factory,
                device=self.device,
                concept_normalizer=self.normalizer,
                atlas_mgr=self.atlas_mgr,
                fixture_only=True,
                fixture_manifest=self.fixture_manifest,
            )
        load_checkpoint.assert_not_called()
        dataloader_factory.assert_not_called()

    def test_forged_fixture_manifest_value_object_fails_before_checkpoint_load(self):
        forged = VerifiedFixtureManifest(
            self.fixture_manifest.manifest_path,
            self.fixture_manifest.manifest_sha256,
            self.fixture_manifest.allowed_root,
            self.fixture_manifest.files,
        )
        with (
            patch("pada3dacb.evaluation.concepts.inference.load_checkpoint") as load,
            pytest.raises(AuthorizationGateError, match="verified fixture manifest"),
        ):
            run_inference_on_candidates(
                    candidates=[self.candidate],
                    dataloader_factory=lambda candidate: MagicMock(),
                    device=self.device,
                    concept_normalizer=self.normalizer,
                    atlas_mgr=self.atlas_mgr,
                    fixture_only=True,
                    fixture_manifest=forged,
                )
        load.assert_not_called()

    def test_fixture_manifest_rejects_missing_forged_marker_escape_and_file_hash(self):
        missing = self.tmpdir / "missing.json"
        with pytest.raises(ValueError, match="fixture manifest"):
            verify_fixture_manifest(missing, "0" * 64, self.tmpdir)

        payload = {
            "schema_version": "phase16-concept-fixture-manifest-v1",
            "fixture_marker": "wrong-marker",
            "fixture_only": True,
            "files": [{"relative_path": "checkpoint.pt", "sha256": "0" * 64}],
        }
        with pytest.raises(ValueError, match="fixture marker"):
            self._write_manifest_payload(payload)

        payload["fixture_marker"] = "phase16-synthetic-fixture"
        payload["files"][0]["relative_path"] = "../checkpoint.pt"
        with pytest.raises(ValueError, match="safe POSIX|escapes"):
            self._write_manifest_payload(payload)

        payload["files"][0]["relative_path"] = "checkpoint.pt"
        with pytest.raises(ValueError, match="hash"):
            self._write_manifest_payload(payload)

        valid = self._write_fixture_manifest([self.candidate.checkpoint_path])
        self.candidate.checkpoint_path.write_bytes(b"stale-fixture")
        with (
            patch("pada3dacb.evaluation.concepts.inference.load_checkpoint") as load,
            pytest.raises(ConfigurationError, match="stale|hash"),
        ):
            run_inference_on_candidates(
                    candidates=[self.candidate],
                    dataloader_factory=lambda candidate: MagicMock(),
                    device=self.device,
                    concept_normalizer=self.normalizer,
                    atlas_mgr=self.atlas_mgr,
                    fixture_only=True,
                    fixture_manifest=valid,
                )
        load.assert_not_called()

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
            fixture_only=True,
            fixture_manifest=self.fixture_manifest,
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
    def test_direct_real_candidate_inference_requires_capability_before_load(self, mock_load_checkpoint):
        with pytest.raises(AuthorizationGateError, match="capability"):
            run_inference_on_candidates(
                candidates=[self.candidate],
                dataloader_factory=lambda candidate: MagicMock(),
                device=self.device,
                concept_normalizer=self.normalizer,
                atlas_mgr=self.atlas_mgr,
                analysis_mode=AnalysisMode.REAL,
                capability=None,
                verified_inputs=None,
            )
        mock_load_checkpoint.assert_not_called()

    @patch("pada3dacb.evaluation.concepts.inference.load_checkpoint")
    def test_real_mode_cannot_opt_into_fixture_boundary(self, mock_load_checkpoint):
        with pytest.raises(AuthorizationGateError, match="capability"):
            run_inference_on_candidates(
                candidates=[self.candidate],
                dataloader_factory=lambda candidate: MagicMock(),
                device=self.device,
                concept_normalizer=self.normalizer,
                atlas_mgr=self.atlas_mgr,
                analysis_mode=AnalysisMode.REAL,
                fixture_only=True,
            )
        mock_load_checkpoint.assert_not_called()

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
                fixture_only=True,
                fixture_manifest=self.fixture_manifest,
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
        candidate2.checkpoint_path.write_bytes(b"fixture-checkpoint-2")
        fixture_manifest = self._write_fixture_manifest(
            [self.candidate.checkpoint_path, candidate2.checkpoint_path]
        )

        results = run_inference_on_candidates(
            candidates=[self.candidate, candidate2],
            dataloader_factory=dataloader_factory,
            device=self.device,
            concept_normalizer=self.normalizer,
            atlas_mgr=self.atlas_mgr,
            fixture_only=True,
            fixture_manifest=fixture_manifest,
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


class TestRealEvaluationBoundary:
    @staticmethod
    def _evidence():
        return {
            "authorized": True,
            "authorized_exports": {"resolved": True, "sha256": "1" * 64},
            "concept_normalizer": {"resolved": True, "sha256": "2" * 64},
            "atlas_hash": {"resolved": True, "sha256": "3" * 64},
            "protocol_approval": {"resolved": True, "sha256": "4" * 64},
        }

    @staticmethod
    def _candidate_fixture(tmp_path, method=MethodId.SOURCE_ONLY):
        atlas_path = tmp_path / "atlas.bin"
        atlas_path.write_bytes(b"atlas")
        normalizer_path = tmp_path / f"normalizer-{method.value}.json"
        normalizer_path.write_text("{}", encoding="utf-8")
        checkpoint_path = tmp_path / f"checkpoint-{method.value}.pt"
        payload = {
            "model_state_dict": {},
            "experiment_hash": "d" * 64,
            "model_hash": "e" * 64,
            "training_hash": "f" * 64,
            "atlas_hash": hashlib.sha256(b"atlas").hexdigest(),
            "concept_normalizer_hash": hashlib.sha256(b"{}").hexdigest(),
            "roi_order_hash": hashlib.sha256(json.dumps([1]).encode()).hexdigest(),
            "epoch": 1,
            "logical_checkpoint": "best_source_f1",
            "config": {},
        }
        torch.save(payload, checkpoint_path)
        candidate = ConceptCandidate(
            method_id=method,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=1,
            experiment_hash="d" * 64,
            model_hash="e" * 64,
            training_hash="f" * 64,
            split_hashes={},
            atlas_hash=hashlib.sha256(b"atlas").hexdigest(),
            roi_order_hash=hashlib.sha256(json.dumps([1]).encode()).hexdigest(),
            concept_normalizer_hash=hashlib.sha256(b"{}").hexdigest(),
            checkpoint_path=checkpoint_path,
            concept_artifacts_root=tmp_path,
        )
        key = tuple(item.value if hasattr(item, "value") else item for item in candidate.candidate_key)
        return candidate, VerifiedEvaluationInputs(
            manifest_sha256="a" * 64,
            roi_labels=(1,),
            roi_order_hash=AtlasROIOrderHash(candidate.roi_order_hash),
            atlas=FileIdentity(atlas_path, hashlib.sha256(b"atlas").hexdigest(), 5),
            normalizers={key: FileIdentity(normalizer_path, hashlib.sha256(b"{}").hexdigest(), 2)},
            checkpoints={key: FileIdentity(checkpoint_path, hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(), checkpoint_path.stat().st_size)},
            checkpoint_metadata={key: payload},
        )

    def test_missing_capability_fails_before_any_side_effect(self):
        events = []

        with pytest.raises(AuthorizationGateError, match="capability"):
            run_real_evaluation(
                candidates=[],
                dataloader_factory=None,
                device="cpu",
                concept_normalizer=None,
                atlas_mgr=None,
                capability=None,
                verified_inputs=None,
                authorization_evidence={},
                statistics_callback=None,
                publish_callback=None,
                event_hook=events.append,
            )

        assert events == []

    @pytest.mark.parametrize("forged", [True, "capability"])
    def test_forged_capability_fails_before_any_side_effect(self, forged):
        with pytest.raises(AuthorizationGateError, match="capability"):
            run_real_evaluation(
                candidates=[],
                dataloader_factory=None,
                device="cpu",
                concept_normalizer=None,
                atlas_mgr=None,
                capability=forged,
                verified_inputs=None,
                authorization_evidence=self._evidence(),
                statistics_callback=None,
                publish_callback=None,
            )

    def test_stale_manifest_capability_is_rejected(self, tmp_path):
        candidate, verified = self._candidate_fixture(tmp_path)
        evidence = self._evidence()
        capability = issue_real_evaluation_capability(evidence, "b" * 64, issuer="trusted-programmatic")
        with pytest.raises(AuthorizationGateError, match="stale"):
            run_real_evaluation(
                [candidate], lambda item: object(), "cpu", MagicMock(), MagicMock(),
                capability=capability, verified_inputs=verified,
                authorization_evidence=evidence,
                statistics_callback=lambda records: records,
                publish_callback=lambda statistics, records: statistics,
            )

    def test_visible_capability_fields_without_issuer_token_are_rejected(self):
        forged = RealEvaluationCapability(
            "phase16-real-evaluation-capability-v1",
            "a" * 64,
            "b" * 64,
            "trusted-programmatic",
        )
        with pytest.raises(AuthorizationGateError, match="capability"):
            run_real_evaluation(
                candidates=[], dataloader_factory=None, device="cpu",
                concept_normalizer=None, atlas_mgr=None, capability=forged,
                verified_inputs=None, authorization_evidence=self._evidence(),
                statistics_callback=None, publish_callback=None,
            )


    @pytest.mark.parametrize(
        ("normalizer_hash", "message"),
        [(None, "missing concept normalizer hash"), ("0" * 64, "conflicts")],
    )
    def test_candidate_normalizer_hash_is_verified_before_model_or_dataloader(
        self, tmp_path, normalizer_hash, message
    ):
        candidate, verified = self._candidate_fixture(tmp_path)
        candidate = dataclasses.replace(candidate, concept_normalizer_hash=normalizer_hash)
        evidence = self._evidence()
        capability = issue_real_evaluation_capability(
            evidence, verified.manifest_sha256, issuer="trusted-programmatic"
        )
        events = []
        dataloader_factory = MagicMock()

        with (
            patch("pada3dacb.evaluation.concepts.inference.PADA3DACB") as model_class,
            pytest.raises(ConfigurationError, match=message),
        ):
            run_real_evaluation(
                [candidate], dataloader_factory, "cpu", MagicMock(), MagicMock(),
                capability=capability,
                verified_inputs=verified,
                authorization_evidence=evidence,
                statistics_callback=lambda records: records,
                publish_callback=lambda statistics, records: statistics,
                event_hook=events.append,
            )

        model_class.assert_not_called()
        dataloader_factory.assert_not_called()
        assert events == ["authorize"]

    def test_real_event_order_is_authorize_then_identity_then_execution(self, tmp_path):
        candidate, verified = self._candidate_fixture(tmp_path)
        evidence = self._evidence()
        capability = issue_real_evaluation_capability(evidence, verified.manifest_sha256, issuer="trusted-programmatic")
        events = []

        def fake_inference(**kwargs):
            kwargs["_event_hook"]("forward")
            return []

        with patch("pada3dacb.evaluation.concepts.inference.PADA3DACB") as model_class:
            model_class.return_value = MagicMock()
            with patch(
                "pada3dacb.evaluation.concepts.inference.run_subject_inference",
                side_effect=fake_inference,
            ):
                result = run_real_evaluation(
                    [candidate], lambda item: object(), "cpu", MagicMock(), MagicMock(),
                    capability=capability,
                    verified_inputs=verified,
                    authorization_evidence=evidence,
                    statistics_callback=lambda records: {"records": records},
                    publish_callback=lambda statistics, records: "published",
                    event_hook=events.append,
                )

        assert result == "published"
        assert events == [
            "authorize", "artifact_hash", "checkpoint_hash", "safe_load",
            "model_ctor", "forward", "statistics", "publish",
        ]

    def test_all_candidate_checkpoints_are_safe_loaded_before_model_construction(self, tmp_path):
        first, first_inputs = self._candidate_fixture(tmp_path)
        second, second_inputs = self._candidate_fixture(tmp_path, MethodId.CORAL)
        verified = VerifiedEvaluationInputs(
            first_inputs.manifest_sha256,
            first_inputs.roi_labels,
            first_inputs.roi_order_hash,
            first_inputs.atlas,
            {**first_inputs.normalizers, **second_inputs.normalizers},
            {**first_inputs.checkpoints, **second_inputs.checkpoints},
            {**first_inputs.checkpoint_metadata, **second_inputs.checkpoint_metadata},
        )
        evidence = self._evidence()
        capability = issue_real_evaluation_capability(evidence, verified.manifest_sha256, issuer="trusted-programmatic")
        events = []

        with patch("pada3dacb.evaluation.concepts.inference.PADA3DACB") as model_class:
            model_class.return_value = MagicMock()
            with patch(
                "pada3dacb.evaluation.concepts.inference.run_subject_inference",
                return_value=[],
            ):
                run_real_evaluation(
                    [first, second], lambda item: object(), "cpu", MagicMock(), MagicMock(),
                    capability=capability,
                    verified_inputs=verified,
                    authorization_evidence=evidence,
                    statistics_callback=lambda records: records,
                    publish_callback=lambda statistics, records: statistics,
                    event_hook=events.append,
                )

        assert events.index("safe_load") < events.index("model_ctor")
        assert events.count("model_ctor") == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])