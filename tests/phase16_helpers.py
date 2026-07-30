"""Test fixtures for Phase 16 concept evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import yaml

from pada3dacb.evaluation.concepts.schemas import (
    CheckpointPolicy,
    ConceptSubjectRecord,
    Direction,
    MethodId,
)


@dataclass
class FixtureConfig:
    K: int = 5  # Number of ROIs
    N_subjects: int = 20
    N_methods: int = 5
    methods: tuple = (
        MethodId.SOURCE_ONLY,
        MethodId.CORAL,
        MethodId.MMD,
        MethodId.CDAN,
        MethodId.PROTOTYPE_PSEUDO,
    )
    directions: tuple = (Direction.ADNI_TO_OASIS, Direction.OASIS_TO_ADNI)
    checkpoint_policies: tuple = (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,)


FIXTURE_CONFIG = FixtureConfig()


def write_matrix(
    tmp_path: Path,
    methods: tuple[MethodId, ...] | None = None,
    directions: tuple[Direction, ...] | None = None,
    K: int | None = None,
    N_subjects: int | None = None,
) -> tuple[Path, dict]:
    """
    Write synthetic concept evaluation inputs.

    Returns:
        (runs_root, config_dict)
    """
    methods = methods or FIXTURE_CONFIG.methods
    directions = directions or FIXTURE_CONFIG.directions
    K = K or FIXTURE_CONFIG.K
    N_subjects = N_subjects or FIXTURE_CONFIG.N_subjects
    rng = np.random.default_rng(1600)

    # Create directory structure
    runs_root = tmp_path / "runs"
    artifact_root = tmp_path / "artifacts"
    runs_root.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)

    # Write concept normalizer
    normalizer_data = {
        "mu": np.zeros(K, dtype=np.float32).tolist(),
        "sigma": np.ones(K, dtype=np.float32).tolist(),
        "eps": 1e-6,
        "roi_labels": list(range(K)),
        "provenance": {"test": True},
    }
    (artifact_root / "concept_normalizer.json").write_text(
        yaml.safe_dump(normalizer_data, sort_keys=False), encoding="utf-8"
    )

    # Write concept targets for each subject
    for s in range(N_subjects):
        subject_id = f"subject_{s:03d}"
        c_target = rng.uniform(0, 1, K).astype(np.float32)
        g_bar = rng.uniform(0, 1, K).astype(np.float32)
        torch.save(c_target, artifact_root / f"{subject_id}_c_target.pt")
        torch.save(g_bar, artifact_root / f"{subject_id}_g_bar.pt")

    # Write checkpoints and run manifests
    for method in methods:
        for direction in directions:
            for policy in (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, CheckpointPolicy.SENSITIVITY_LAST):
                for seed in [42]:
                    for fold in [0, 1, 2, 3, 4]:
                        dir_name = f"{method.value}__{direction.value}__seed_{seed}__fold_{fold}"
                        run_dir = runs_root / "checkpoints" / dir_name
                        policy_dir = run_dir / policy.value
                        policy_dir.mkdir(parents=True, exist_ok=True)

                        # Create checkpoint
                        ckpt = {
                            "experiment_hash": f"{method.value}{direction.value}{seed}{fold}exp",
                            "model_hash": f"{method.value}{direction.value}{seed}{fold}mod",
                            "training_hash": f"{method.value}{direction.value}{seed}{fold}trn",
                            "epoch": 50,
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
                                "K": K,
                            },
                        }
                        torch.save(ckpt, policy_dir / "checkpoint_epoch_50.pt")

    # Write config
    config = {
        "schema_version": "1.0",
        "protocol_version": "1.0",
        "class_order": {"CN": 0, "MCI": 1, "AD": 2},
        "methods": [m.value for m in methods],
        "directions": [d.value for d in directions],
        "expected_folds": [0, 1, 2, 3, 4],
        "expected_seeds": [42],
        "checkpoint_policies": ["best_source_f1", "last"],
        "primary_policy": "best_source_f1",
        "sensitivity_policy": "last",
        "bootstrap": {
            "replicates": 100,
            "seed": 12345,
            "ci_policy": "percentile_95_linear",
            "stratification": "diagnosis_class",
        },
        "top_k": [5, 10],
        "real_evaluation_gate": {
            "authorized": False,
            "authorized_exports": None,
            "concept_normalizer": None,
            "atlas_hash": None,
            "protocol_approval": None,
        },
        "concept_normalizer": {"expected_hash": None},
        "atlas": {"expected_roi_order_hash": None, "expected_atlas_hash": None},
        "device": "cpu",
    }

    config_path = tmp_path / "concepts_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    return runs_root, {"_config_path": str(config_path)}


def _subject_record(
    method: MethodId,
    direction: Direction,
    policy: CheckpointPolicy,
    seed: int,
    fold: int,
    subject_idx: int,
    K: int = 5,
) -> ConceptSubjectRecord:
    """Create a synthetic subject record."""
    return ConceptSubjectRecord(
        method_id=method,
        direction=direction,
        checkpoint_policy=policy.value,
        seed=seed,
        fold=fold,
        logical_checkpoint=policy.value,
        checkpoint_epoch=50,
        experiment_hash="test_exp_hash",
        subject_id=f"subject_{subject_idx:03d}",
        subject_hash=f"{subject_idx:064x}",
        cohort="ADNI",
        true_label=subject_idx % 3,
        label_name=["CN", "MCI", "AD"][subject_idx % 3],
        predicted_concepts=tuple(np.random.uniform(0, 1, K)),
        concept_targets=tuple(np.random.uniform(0, 1, K)),
        anatomical_targets=tuple(np.random.uniform(0, 1, K)),
        attention_alpha=tuple(np.ones(K) / K),
        latent_probabilities=tuple(np.ones(3) / 3),
        concept_probabilities=tuple(np.ones(3) / 3),
        latent_prediction=0,
        concept_prediction=0,
    )


def cli_module():
    """Import and return the CLI module."""
    import importlib
    return importlib.import_module("scripts.evaluate_concepts")


def matrix_argv(
    config: dict,
    runs_root: Path,
    *args,
    methods: tuple[MethodId, ...] | None = None,
    output: Path | None = None,
) -> list[str]:
    """Build CLI arguments for testing."""
    methods = methods or FIXTURE_CONFIG.methods
    argv = [
        "--config", config["_config_path"],
        "--runs-root", str(runs_root),
        "--both-directions",
    ]
    for m in methods:
        argv.extend(["--method", m.value])
    if output:
        argv.extend(["--output-root", str(output)])
    argv.extend(args)
    return argv