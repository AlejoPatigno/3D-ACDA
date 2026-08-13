"""Tests for checkpoint and artifact discovery."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import torch
import yaml

from pada3dacb.evaluation.concepts.discovery import (
    DiscoveryConfig,
    discover_candidates,
    filter_pada_candidates,
    validate_candidate_hashes,
)
from pada3dacb.evaluation.concepts.schemas import (
    CheckpointPolicy,
    Direction,
    MethodId,
)


class TestDiscoveryConfig:
    def test_valid_config(self):
        config = DiscoveryConfig(
            runs_root=Path("/tmp/runs"),
            artifact_root=Path("/tmp/artifacts"),
            methods=frozenset([MethodId.SOURCE_ONLY, MethodId.CORAL]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0, 1, 2, 3, 4],
            expected_seeds=[42],
            expected_concept_normalizer_hash="a" * 64,
            expected_atlas_roi_order_hash="b" * 64,
            expected_atlas_hash="c" * 64,
        )
        assert config.methods == frozenset([MethodId.SOURCE_ONLY, MethodId.CORAL])


class TestDiscoverCandidates:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.runs_root = self.tmpdir / "runs"
        self.artifact_root = self.tmpdir / "artifacts"
        self.runs_root.mkdir(parents=True)
        self.artifact_root.mkdir(parents=True)

        # Create concept normalizer
        normalizer_data = {
            "mu": [0.0] * 5,
            "sigma": [1.0] * 5,
            "eps": 1e-6,
            "roi_labels": list(range(5)),
            "provenance": {"test": True},
        }
        (self.artifact_root / "concept_normalizer.json").write_text(json.dumps(normalizer_data))

        # Create concept targets for subjects
        for s in range(10):
            subject_id = f"subject_{s:03d}"
            c_target = torch.rand(5)
            g_bar = torch.rand(5)
            torch.save(c_target, self.artifact_root / f"{subject_id}_c_target.pt")
            torch.save(g_bar, self.artifact_root / f"{subject_id}_g_bar.pt")

        # Create checkpoint structure for one method/direction/seed/fold
        self._create_checkpoint(
            method=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            epoch=50,
        )

    def _create_checkpoint(self, method, direction, seed, fold, policy, epoch=50):
        dir_name = f"{method.value}__{direction.value}__seed_{seed}__fold_{fold}"
        checkpoint_dir = self.runs_root / "checkpoints" / dir_name
        policy_dir = checkpoint_dir / policy.value
        policy_dir.mkdir(parents=True, exist_ok=True)

        ckpt = {
            "experiment_hash": f"{method.value}{direction.value}{seed}{fold}exp",
            "model_hash": f"{method.value}{direction.value}{seed}{fold}mod",
            "training_hash": f"{method.value}{direction.value}{seed}{fold}trn",
            "epoch": epoch,
            "logical_checkpoint": policy.value,
            "model_state_dict": {},
            "atlas_hash": "atlas_sha256",
            "roi_order_hash": "roi_order_sha256",
            "concept_normalizer_hash": "normalizer_sha256",
            "config": {
                "method": method.value,
                "direction": direction.value,
                "seed": seed,
                "fold": fold,
                "checkpoint_policy": policy.value,
                "K": 5,
            },
        }
        # Use the naming pattern expected by discovery: best_source_f1_epoch_{epoch}.pt
        if policy == CheckpointPolicy.PRIMARY_BEST_SOURCE_F1:
            filename = f"best_source_f1_epoch_{epoch}.pt"
        else:
            filename = f"last_epoch_{epoch}.pt"
        torch.save(ckpt, policy_dir / filename)

        # Create manifest
        manifest_dir = self.runs_root / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "split_hashes": {
                "source_train": "split1",
                "source_val": "split2",
                "target_adaptation": "split3",
                "target_evaluation": "split4",
            }
        }
        (manifest_dir / f"{ckpt['experiment_hash']}.json").write_text(json.dumps(manifest))

        # Create concept artifacts directory
        artifact_dir = self.artifact_root / "concept_targets" / direction.value / f"seed_{seed}" / f"fold_{fold}"
        artifact_dir.mkdir(parents=True, exist_ok=True)

    def test_discover_single_candidate(self):
        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
            expected_concept_normalizer_hash="normalizer_sha256",
            expected_atlas_roi_order_hash="roi_order_sha256",
            expected_atlas_hash="atlas_sha256",
        )

        candidates, issues = discover_candidates(config)

        assert len(candidates) == 1
        assert len(issues) == 0
        candidate = candidates[0]
        assert candidate.method_id == MethodId.SOURCE_ONLY
        assert candidate.direction == Direction.ADNI_TO_OASIS
        assert candidate.seed == 42
        assert candidate.fold == 0
        assert candidate.checkpoint_policy == CheckpointPolicy.PRIMARY_BEST_SOURCE_F1
        assert candidate.logical_checkpoint == "best_source_f1"
        assert candidate.checkpoint_epoch == 50

    def test_discover_missing_checkpoint_dir(self):
        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0, 1],  # Fold 1 doesn't exist
            expected_seeds=[42],
        )

        candidates, issues = discover_candidates(config)

        assert len(candidates) == 1  # Only fold 0 found
        assert any("checkpoint_dir_not_found" in issue for issue in issues)

    def test_discover_missing_checkpoint_file(self):
        # Remove the checkpoint file but keep directory
        dir_name = f"{MethodId.SOURCE_ONLY.value}__{Direction.ADNI_TO_OASIS.value}__seed_42__fold_0"
        checkpoint_dir = self.runs_root / "checkpoints" / dir_name
        policy_dir = checkpoint_dir / CheckpointPolicy.PRIMARY_BEST_SOURCE_F1.value
        for f in policy_dir.glob("*.pt"):
            f.unlink()

        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
        )

        candidates, issues = discover_candidates(config)

        assert len(candidates) == 0
        assert any("checkpoint_not_found" in issue for issue in issues)

    def test_discover_multiple_checkpoints_raises_issue(self):
        # Add a second checkpoint file
        dir_name = f"{MethodId.SOURCE_ONLY.value}__{Direction.ADNI_TO_OASIS.value}__seed_42__fold_0"
        policy_dir = self.runs_root / "checkpoints" / dir_name / CheckpointPolicy.PRIMARY_BEST_SOURCE_F1.value
        ckpt2 = {
            "experiment_hash": "exp2",
            "model_hash": "mod2",
            "training_hash": "trn2",
            "epoch": 60,
            "logical_checkpoint": "best_source_f1",
            "model_state_dict": {},
        }
        torch.save(ckpt2, policy_dir / "best_source_f1_epoch_60.pt")

        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
        )

        candidates, issues = discover_candidates(config)

        assert len(candidates) == 0
        assert any("multiple_checkpoints_found" in issue for issue in issues)

    def test_discover_not_applicable_methods(self):
        # Create checkpoint for AAGN
        self._create_checkpoint(
            method=MethodId.AAGN,
            direction=Direction.ADNI_TO_OASIS,
            seed=42,
            fold=0,
            policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        )

        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.AAGN]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
        )

        candidates, issues = discover_candidates(config)

        assert len(candidates) == 0
        assert any("not_applicable" in issue for issue in issues)

    def test_reports_not_applicable_without_checkpoint(self):
        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.FASTER_SNN]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
        )

        candidates, issues = discover_candidates(config)

        assert candidates == []
        assert issues == [
            "not_applicable:faster_snn:not_applicable_no_pada3dacb_concept_head"
        ]

    def test_discover_hash_mismatch(self):
        config = DiscoveryConfig(
            runs_root=self.runs_root,
            artifact_root=self.artifact_root,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
            expected_concept_normalizer_hash="wrong_hash",
        )

        candidates, issues = discover_candidates(config)

        assert len(candidates) == 1  # Candidate retained for exclusion reporting.
        assert any("concept_normalizer_hash_mismatch" in issue for issue in issues)
        assert any("concept_normalizer_hash_mismatch" in issue for issue in candidates[0].issues)

    def test_filter_pada_candidates(self):
        from pada3dacb.evaluation.concepts.schemas import ConceptCandidate

        candidates = [
            ConceptCandidate(
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
                atlas_hash="atlas",
                roi_order_hash="roi",
                concept_normalizer_hash="norm",
                checkpoint_path=Path("ckpt1.pt"),
                concept_artifacts_root=Path("artifacts1"),
            ),
            ConceptCandidate(
                method_id=MethodId.AAGN,
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
                atlas_hash="atlas",
                roi_order_hash="roi",
                concept_normalizer_hash="norm",
                checkpoint_path=Path("ckpt2.pt"),
                concept_artifacts_root=Path("artifacts2"),
            ),
        ]

        filtered = filter_pada_candidates(candidates)
        assert len(filtered) == 1
        assert filtered[0].method_id == MethodId.SOURCE_ONLY

    def test_validate_candidate_hashes(self):
        from pada3dacb.evaluation.concepts.schemas import ConceptCandidate

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
            checkpoint_path=Path("ckpt1.pt"),
            concept_artifacts_root=Path("artifacts1"),
        )

        issues = validate_candidate_hashes(candidate, "norm2", "roi1", "atlas1")
        assert "concept_normalizer_mismatch" in issues[0]

        issues = validate_candidate_hashes(candidate, "norm1", "roi2", "atlas1")
        assert "roi_order_mismatch" in issues[0]

        issues = validate_candidate_hashes(candidate, "norm1", "roi1", "atlas2")
        assert "atlas_mismatch" in issues[0]

        issues = validate_candidate_hashes(candidate, "norm1", "roi1", "atlas1")
        assert len(issues) == 0

    def test_strict_config_rejects_invalid_selectors(self, tmp_path):
        config = DiscoveryConfig(
            runs_root=tmp_path,
            artifact_root=tmp_path,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[-1],
            expected_seeds=["42"],
            strict=True,
        )
        with pytest.raises(ValueError, match="fold|seed"):
            config.validate()

    def test_strict_config_requires_runtime_roi_identity_and_atlas_manager(self, tmp_path):
        config = DiscoveryConfig(
            runs_root=tmp_path,
            artifact_root=tmp_path,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
            strict=True,
            manifest_path=tmp_path / "manifest.json",
            runtime_roi_labels=None,
        )
        config.manifest_path.write_text("{}")
        with pytest.raises(ValueError, match="runtime ROI labels|atlas manager"):
            config.validate()

    def test_strict_config_rejects_mismatched_artifact_root(self, tmp_path):
        config = DiscoveryConfig(
            runs_root=tmp_path,
            artifact_root=tmp_path / "configured-artifacts",
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
            strict=True,
            manifest_path=tmp_path / "manifest.json",
            runtime_roi_labels=[2, 4],
        )
        config.manifest_path.write_text("{}")
        with pytest.raises(ValueError, match="atlas manager|manifest"):
            config.validate()

    def test_strict_config_rejects_invalid_gate_evidence_and_paths(self, tmp_path):
        payload = {
            "schema_version": "1.0", "protocol_version": "1.0", "class_order": {"CN": 0, "MCI": 1, "AD": 2},
            "methods": ["source_only"], "directions": ["adni_to_oasis"], "expected_folds": [0], "expected_seeds": [42],
            "checkpoint_policies": {"primary": "best_source_f1"}, "bootstrap": {"replicates": 1, "seed": 0, "ci_policy": "x", "stratification": "y"}, "top_k": [1], "device": "cpu",
            "real_evaluation_gate": {"authorized": False, "authorized_exports": {"resolved": True, "sha256": None}, "concept_normalizer": {"resolved": False, "sha256": None}, "atlas_hash": {"resolved": False, "sha256": None}, "protocol_approval": {"resolved": False, "sha256": None}},
        }
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        from pada3dacb.evaluation.concepts.schemas import (
            ConceptEvaluationConfig,
            ConfigurationError,
        )
        with pytest.raises(ConfigurationError, match="authorized_exports"):
            ConceptEvaluationConfig.from_yaml(path)

    def test_strict_config_rejects_real_path_types_and_input_output_overlap(self, tmp_path):
        from pada3dacb.evaluation.concepts.provenance import compute_sha256_file
        from pada3dacb.evaluation.concepts.schemas import (
            ConceptEvaluationConfig,
            ConfigurationError,
            canonical_roi_order_hash,
        )

        payload = {
            "schema_version": "1.0", "protocol_version": "1.0", "class_order": {"CN": 0, "MCI": 1, "AD": 2},
            "methods": ["source_only"], "directions": ["adni_to_oasis"], "expected_folds": [0], "expected_seeds": [42],
            "checkpoint_policies": {"primary": "best_source_f1"}, "bootstrap": {"replicates": 1, "seed": 0, "ci_policy": "x", "stratification": "y"}, "top_k": [1], "device": "cpu",
            "real_evaluation_gate": {"authorized": True, "authorized_exports": {"resolved": True, "sha256": "a" * 64}, "concept_normalizer": {"resolved": True, "sha256": "b" * 64}, "atlas_hash": {"resolved": True, "sha256": "c" * 64}, "protocol_approval": {"resolved": True, "sha256": "d" * 64}},
            "atlas": {"expected_roi_order_hash": canonical_roi_order_hash([2, 4]), "expected_atlas_hash": "c" * 64},
        }
        path = tmp_path / "config.yaml"
        payload.update({"manifest_path": 7, "atlas_path": "atlas.bin", "output_root": "out"})
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with pytest.raises(ConfigurationError, match="manifest_path"):
            ConceptEvaluationConfig.from_yaml(path)

        payload["manifest_path"] = "missing-manifest.json"
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with pytest.raises(ConfigurationError, match="does not exist"):
            ConceptEvaluationConfig.from_yaml(path)

        atlas = tmp_path / "atlas.bin"
        atlas.write_bytes(b"atlas")
        payload["atlas"]["expected_atlas_hash"] = compute_sha256_file(atlas)
        payload["real_evaluation_gate"]["atlas_hash"]["sha256"] = compute_sha256_file(atlas)
        payload.update({"manifest_path": "manifest.json", "atlas_path": "atlas.bin", "output_root": "out", "input_roots": ["out"]})
        (tmp_path / "manifest.json").write_text(json.dumps({"schema_version": "phase16-concept-provenance-v1", "roi_order": {"labels": [2, 4], "sha256": canonical_roi_order_hash([2, 4])}, "atlas": {"relative_path": "atlas.bin", "sha256": compute_sha256_file(atlas), "roi_order_sha256": canonical_roi_order_hash([2, 4])}, "candidates": []}), encoding="utf-8")
        (tmp_path / "out").mkdir()
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with pytest.raises(ConfigurationError, match="overlap"):
            ConceptEvaluationConfig.from_yaml(path)

    def test_strict_discovery_requires_manifest_assignment(self, tmp_path):
        config = DiscoveryConfig(
            runs_root=tmp_path,
            artifact_root=tmp_path,
            methods=frozenset([MethodId.SOURCE_ONLY]),
            directions=frozenset([Direction.ADNI_TO_OASIS]),
            checkpoint_policies=frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]),
            expected_folds=[0],
            expected_seeds=[42],
            strict=True,
            manifest_path=tmp_path / "missing-manifest.json",
        )
        candidates, issues = discover_candidates(config)
        assert candidates == []
        assert any("manifest" in issue for issue in issues)


    def test_strict_discovery_accepts_exact_manifest_assignment(self, tmp_path):
        from pada3dacb.evaluation.concepts.provenance import compute_sha256_file
        from pada3dacb.evaluation.concepts.schemas import canonical_roi_order_hash

        root = tmp_path
        atlas = root / "atlas.bin"
        normalizer = root / "normalizer.json"
        checkpoint = root / "runs" / "checkpoints" / "source_only__adni_to_oasis__seed_42__fold_0" / "primary_best_source_f1" / "best_source_f1_epoch_1.pt"
        checkpoint.parent.mkdir(parents=True)
        (root / "artifacts" / "concept_targets" / "adni_to_oasis" / "seed_42" / "fold_0").mkdir(parents=True)
        atlas.write_bytes(b"atlas")
        normalizer.write_text(json.dumps({"roi_labels": [2, 4]}), encoding="utf-8")
        roi_hash = canonical_roi_order_hash([2, 4])
        payload = {"experiment_hash": "e" * 64, "model_hash": "m" * 64, "training_hash": "t" * 64, "epoch": 1, "atlas_hash": compute_sha256_file(atlas), "roi_order_hash": roi_hash, "concept_normalizer_hash": compute_sha256_file(normalizer), "model_state_dict": {}}
        torch.save(payload, checkpoint)
        manifest = {"schema_version": "phase16-concept-provenance-v1", "roi_order": {"labels": [2, 4], "sha256": roi_hash}, "atlas": {"relative_path": "atlas.bin", "sha256": compute_sha256_file(atlas), "roi_order_sha256": roi_hash}, "candidates": [{"key": {"method_id": "source_only", "direction": "adni_to_oasis", "seed": 42, "fold": 0, "checkpoint_policy": "primary_best_source_f1"}, "checkpoint": {"relative_path": str(checkpoint.relative_to(root)).replace("\\", "/"), "sha256": compute_sha256_file(checkpoint), "roi_order_sha256": roi_hash}, "normalizer": {"relative_path": "normalizer.json", "sha256": compute_sha256_file(normalizer), "roi_order_sha256": roi_hash}, "concept_artifacts_root": "artifacts/concept_targets/adni_to_oasis/seed_42/fold_0"}]}
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        manager = type("Atlas", (), {"label_values": [2, 4], "atlas_hash": compute_sha256_file(atlas)})()
        config = DiscoveryConfig(root / "runs", root / "artifacts", frozenset([MethodId.SOURCE_ONLY]), frozenset([Direction.ADNI_TO_OASIS]), frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]), [0], [42], strict=True, manifest_path=manifest_path, runtime_roi_labels=[2, 4], atlas_manager=manager)

        candidates, issues = discover_candidates(config)
        assert len(candidates) == 1
        assert issues == []

        manifest["candidates"][0]["concept_artifacts_root"] = "artifacts"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        candidates, issues = discover_candidates(config)
        assert candidates == []
        assert any("artifact assignment" in issue for issue in issues)

        manifest["candidates"][0]["concept_artifacts_root"] = "artifacts/concept_targets/adni_to_oasis/seed_42/fold_0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        config = DiscoveryConfig(root / "runs", root / "artifacts", frozenset([MethodId.SOURCE_ONLY]), frozenset([Direction.ADNI_TO_OASIS]), frozenset([CheckpointPolicy.PRIMARY_BEST_SOURCE_F1]), [0], [42], strict=True, manifest_path=manifest_path, runtime_roi_labels=[4, 2], atlas_manager=manager)
        candidates, issues = discover_candidates(config)
        assert candidates == []
        assert any("runtime ROI labels" in issue for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])