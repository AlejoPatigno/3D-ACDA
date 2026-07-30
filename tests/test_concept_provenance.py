"""Tests for provenance validation and hashing."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

from pada3dacb.evaluation.concepts.provenance import (
    ArtifactHashes,
    build_provenance_report,
    compute_artifact_hashes,
    compute_sha256_array,
    compute_sha256_dict,
    compute_sha256_torch,
    load_normalizer_hash,
    validate_normalizer_hash,
    validate_roi_order_hash,
)
from pada3dacb.evaluation.concepts.schemas import (
    AtlasROIOrderHash,
    CheckpointPolicy,
    ConceptCandidate,
    ConceptNormalizerHash,
    Direction,
    MethodId,
    compute_sha256_file,
)


class TestHashComputation:
    def test_compute_sha256_dict(self):
        data = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        hash1 = compute_sha256_dict(data)
        hash2 = compute_sha256_dict(data)
        assert hash1 == hash2
        assert len(hash1) == 64
        # Verify it's deterministic
        assert hash1 == hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def test_compute_sha256_dict_order_invariant(self):
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        assert compute_sha256_dict(data1) == compute_sha256_dict(data2)

    def test_compute_sha256_array(self):
        arr = np.array([[1, 2], [3, 4]], dtype=np.float32)
        hash1 = compute_sha256_array(arr)
        hash2 = compute_sha256_array(arr.copy())
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_sha256_torch(self):
        tensor = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        hash1 = compute_sha256_torch(tensor)
        hash2 = compute_sha256_torch(tensor.clone())
        assert hash1 == hash2
        assert len(hash1) == 64


class TestNormalizerHashValidation:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        normalizer_data = {
            "mu": [0.0] * 5,
            "sigma": [1.0] * 5,
            "eps": 1e-6,
            "roi_labels": list(range(5)),
        }
        self.normalizer_path = self.tmpdir / "concept_normalizer.json"
        self.normalizer_path.write_text(json.dumps(normalizer_data, sort_keys=True))

    def test_load_normalizer_hash(self):
        hash_obj = load_normalizer_hash(self.normalizer_path)
        assert isinstance(hash_obj, ConceptNormalizerHash)
        assert len(hash_obj) == 64
        # Verify it matches direct computation
        expected = compute_sha256_file(self.normalizer_path)
        assert str(hash_obj) == expected

    def test_validate_normalizer_hash_match(self):
        actual = load_normalizer_hash(self.normalizer_path)
        issues = validate_normalizer_hash(actual, actual)
        assert len(issues) == 0

    def test_validate_normalizer_hash_mismatch(self):
        actual = load_normalizer_hash(self.normalizer_path)
        expected = ConceptNormalizerHash("a" * 64)
        issues = validate_normalizer_hash(actual, expected)
        assert len(issues) == 1
        assert "normalizer_hash_mismatch" in issues[0]

    def test_validate_normalizer_hash_none_expected(self):
        actual = load_normalizer_hash(self.normalizer_path)
        issues = validate_normalizer_hash(actual, None)
        assert len(issues) == 0

    def test_validate_roi_order_hash_match(self):
        actual = AtlasROIOrderHash("a" * 64)
        issues = validate_roi_order_hash(actual, "a" * 64)
        assert len(issues) == 0

    def test_validate_roi_order_hash_mismatch(self):
        actual = AtlasROIOrderHash("a" * 64)
        issues = validate_roi_order_hash(actual, "b" * 64)
        assert len(issues) == 1
        assert "roi_order_hash_mismatch" in issues[0]

    def test_validate_roi_order_hash_none_expected(self):
        actual = AtlasROIOrderHash("a" * 64)
        issues = validate_roi_order_hash(actual, None)
        assert len(issues) == 0


class TestArtifactHashes:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.artifact_root = self.tmpdir / "artifacts"
        self.artifact_root.mkdir(parents=True)

        # Create concept normalizer
        normalizer_data = {
            "mu": [0.0] * 5,
            "sigma": [1.0] * 5,
            "eps": 1e-6,
            "roi_labels": list(range(5)),
        }
        (self.artifact_root / "concept_normalizer.json").write_text(json.dumps(normalizer_data, sort_keys=True))

        # Create concept targets
        for s in range(5):
            subject_id = f"subject_{s:03d}"
            values = torch.linspace(float(s), float(s + 1), steps=5)
            torch.save(values, self.artifact_root / f"{subject_id}_c_target.pt")
            torch.save(values + 1.0, self.artifact_root / f"{subject_id}_g_bar.pt")

        # Create checkpoint
        self.checkpoint_path = self.tmpdir / "checkpoint.pt"
        torch.save({"model_state_dict": {}}, self.checkpoint_path)

    def test_compute_artifact_hashes(self):
        candidate = ConceptCandidate(
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
            roi_order_hash=hashlib.sha256(json.dumps(list(range(5))).encode()).hexdigest(),
            concept_normalizer_hash=compute_sha256_file(
                self.artifact_root / "concept_normalizer.json"
            ),
            checkpoint_path=self.checkpoint_path,
            concept_artifacts_root=self.artifact_root,
        )

        artifacts_roots = {
            (candidate.method_id, candidate.direction, candidate.seed, candidate.fold, candidate.checkpoint_policy):
                self.artifact_root
        }

        hashes = compute_artifact_hashes([candidate], artifacts_roots)

        assert isinstance(hashes, ArtifactHashes)
        assert len(hashes.checkpoint_hashes) == 1
        key = (MethodId.SOURCE_ONLY, Direction.ADNI_TO_OASIS, 42, 0, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1)
        assert key in hashes.checkpoint_hashes

        # Check concept target hashes
        assert len(hashes.concept_target_hashes) == 5
        assert len(hashes.anatomical_target_hashes) == 5

        # Check normalizer hash
        assert hashes.normalizer_hash != ConceptNormalizerHash("unknown")

        # Check ROI order hash
        assert hashes.roi_order_hash != AtlasROIOrderHash("unknown")
        assert hashes.atlas_hash == "9" * 64

    def test_compute_artifact_hashes_fails_closed_on_missing_normalizer(self):
        (self.artifact_root / "concept_normalizer.json").unlink()
        candidate = ConceptCandidate(
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
            checkpoint_path=self.checkpoint_path,
            concept_artifacts_root=self.artifact_root,
        )

        with pytest.raises(ValueError, match="concept normalizer is missing"):
            compute_artifact_hashes([candidate], {candidate.candidate_key: self.artifact_root})


class TestProvenanceReport:
    def test_build_provenance_report_included(self):
        candidate = ConceptCandidate(
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            experiment_hash="exp1",
            model_hash="mod1",
            training_hash="trn1",
            split_hashes={"source_train": "split1"},
            atlas_hash="atlas1",
            roi_order_hash="roi1",
            concept_normalizer_hash="norm1",
            checkpoint_path=Path("ckpt.pt"),
            concept_artifacts_root=Path("artifacts"),
        )

        validation_issues = {
            (MethodId.SOURCE_ONLY, Direction.ADNI_TO_OASIS, 42, 0, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1): []
        }

        report = build_provenance_report([candidate], validation_issues)

        assert len(report["candidates"]) == 1
        assert len(report["excluded"]) == 0
        assert report["candidates"][0]["status"] == "included"
        assert report["candidates"][0]["method_id"] == "source_only"
        assert "issues" not in report["candidates"][0]

        candidate.issues.append("checkpoint_hash_mismatch")
        excluded = build_provenance_report([candidate], validation_issues)
        assert excluded["candidates"] == []
        assert excluded["excluded"][0]["issues"] == ["checkpoint_hash_mismatch"]

    def test_build_provenance_report_excluded(self):
        candidate = ConceptCandidate(
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            experiment_hash="exp1",
            model_hash="mod1",
            training_hash="trn1",
            split_hashes={},
            atlas_hash="atlas1",
            roi_order_hash="roi1",
            concept_normalizer_hash="norm1",
            checkpoint_path=Path("ckpt.pt"),
            concept_artifacts_root=Path("artifacts"),
        )

        validation_issues = {
            (MethodId.SOURCE_ONLY, Direction.ADNI_TO_OASIS, 42, 0, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1):
                ["missing_hashes_in_checkpoint"]
        }

        report = build_provenance_report([candidate], validation_issues)

        assert len(report["candidates"]) == 0
        assert len(report["excluded"]) == 1
        assert report["excluded"][0]["status"] == "excluded"
        assert "issues" in report["excluded"][0]
        assert "missing_hashes_in_checkpoint" in report["excluded"][0]["issues"]

    def test_build_provenance_report_mixed(self):
        candidate1 = ConceptCandidate(
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            experiment_hash="exp1",
            model_hash="mod1",
            training_hash="trn1",
            split_hashes={},
            atlas_hash="atlas1",
            roi_order_hash="roi1",
            concept_normalizer_hash="norm1",
            checkpoint_path=Path("ckpt1.pt"),
            concept_artifacts_root=Path("artifacts1"),
        )

        candidate2 = ConceptCandidate(
            method_id=MethodId.CORAL,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=50,
            experiment_hash="exp2",
            model_hash="mod2",
            training_hash="trn2",
            split_hashes={},
            atlas_hash="atlas2",
            roi_order_hash="roi2",
            concept_normalizer_hash="norm2",
            checkpoint_path=Path("ckpt2.pt"),
            concept_artifacts_root=Path("artifacts2"),
        )

        validation_issues = {
            (MethodId.SOURCE_ONLY, Direction.ADNI_TO_OASIS, 42, 0, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1): [],
            (MethodId.CORAL, Direction.ADNI_TO_OASIS, 42, 0, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1):
                ["roi_order_hash_mismatch"],
        }

        report = build_provenance_report([candidate1, candidate2], validation_issues)

        assert len(report["candidates"]) == 1
        assert len(report["excluded"]) == 1
        assert report["candidates"][0]["method_id"] == "source_only"
        assert report["excluded"][0]["method_id"] == "coral"
        assert "roi_order_hash_mismatch" in report["excluded"][0]["issues"]

        # Check validation_issues section
        assert len(report["validation_issues"]) == 1
        assert report["validation_issues"][0]["issues"] == ["roi_order_hash_mismatch"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])