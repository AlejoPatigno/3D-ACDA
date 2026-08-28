from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from acda3d.evaluation.schemas import REQUIRED_PROVENANCE_FIELDS


def write_input(root: Path, relative_path: str = "fold/predictions.csv") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"subject_hash,prob_cn,prob_mci,prob_ad\nabc,0.2,0.3,0.5\n")
    return path


def provenance_values(**overrides: Any) -> dict[str, Any]:
    values = {field: f"value-{field}" for field in REQUIRED_PROVENANCE_FIELDS}
    values.update(
        method_id="mmd",
        direction="adni_to_oasis",
        source_cohort="ADNI",
        target_cohort="OASIS",
        seed=17,
        fold=2,
        logical_checkpoint="best_source_f1",
        checkpoint_epoch=8,
        class_order=("CN", "MCI", "AD"),
    )
    values.update(overrides)
    return values


def canonical_rows() -> list[dict[str, Any]]:
    return [
        {"subject_hash": "hash-a", "subject_id": "private-a", "true_label": 0, "probabilities": (0.8, 0.1, 0.1)},
        {"subject_hash": "hash-b", "subject_id": "private-b", "true_label": 1, "probabilities": (0.1, 0.8, 0.1)},
    ]


def write_shared_candidate(
    root: Path,
    *,
    method: str = "mmd",
    direction: str = "adni_to_oasis",
    seed: int = 17,
    fold: int = 2,
    checkpoint: str = "best_source_f1",
) -> Path:
    base = root / "shared" / method / direction / f"seed_{seed}" / f"fold_{fold}"
    fields = [
        "subject_hash", "true_label_index", "probability_CN", "probability_MCI", "probability_AD",
        "direction", "method", "fold", "seed", "checkpoint_name", "checkpoint_epoch", "experiment_hash",
    ]
    for directory in ("source_validation_predictions", "target_monitoring_predictions"):
        path = base / directory / f"{checkpoint}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in canonical_rows():
                writer.writerow(
                    {
                        "subject_hash": row["subject_hash"],
                        "true_label_index": row["true_label"],
                        "probability_CN": row["probabilities"][0],
                        "probability_MCI": row["probabilities"][1],
                        "probability_AD": row["probabilities"][2],
                        "direction": direction,
                        "method": method,
                        "fold": fold,
                        "seed": seed,
                        "checkpoint_name": checkpoint,
                        "checkpoint_epoch": 8,
                        "experiment_hash": "experiment-hash",
                    }
                )
    manifest = provenance_values(method_id=method, direction=direction, experiment_hash="experiment-hash")
    (base / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return base


def shared_discovery_config() -> dict[str, Any]:
    return {
        "shared_method": {
            "prediction_pattern": "shared/{method}/{direction}/seed_{seed}/fold_{fold}/{role_directory}/{logical_checkpoint}.csv",
            "companion_patterns": ["shared/{method}/{direction}/seed_{seed}/fold_{fold}/run_manifest.json"],
            "role_directories": {
                "source_oof": "source_validation_predictions",
                "target_evaluation": "target_monitoring_predictions",
            },
        },
        "baseline_combined": {
            "prediction_pattern": "baselines/{method}/{direction}/seed_{seed}/fold_{fold}/predictions.csv",
            "companion_patterns": [
                "baselines/{method}/{direction}/seed_{seed}/fold_{fold}/run_manifest.json",
                "baselines/{method}/{direction}/seed_{seed}/fold_{fold}/fold_result.json",
            ],
        },
    }


def add_identity_population_controls(config: dict[str, Any], root: Path) -> dict[str, Any]:
    identity = {}
    for cohort in ("ADNI", "OASIS"):
        relative = f"identity/{cohort}.csv"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "subject_id,subject_hash\nprivate-a,hash-a\nprivate-b,hash-b\n",
            encoding="utf-8",
        )
        identity[cohort] = {
            "relative_path": relative,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "raw_identifier_field": "subject_id",
            "subject_hash_field": "subject_hash",
            "approved": True,
        }
    populations = {}
    for direction in ("adni_to_oasis", "oasis_to_adni"):
        populations[direction] = {}
        for role in ("source_oof", "target_evaluation"):
            relative = f"populations/{direction}/{role}.csv"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("subject_hash\nhash-a\nhash-b\n", encoding="utf-8")
            populations[direction][role] = {
                "relative_path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    config["identity_companions"] = identity
    config["expected_population_companions"] = populations
    return config


def write_baseline_candidate(
    root: Path,
    *,
    method: str = "aagn",
    direction: str = "adni_to_oasis",
    seed: int = 17,
    fold: int = 2,
) -> Path:
    base = root / "baselines" / method / direction / f"seed_{seed}" / f"fold_{fold}"
    base.mkdir(parents=True, exist_ok=True)
    fields = [
        "subject_id", "subject_hash", "label", "prediction", "prob_cn", "prob_mci",
        "prob_ad", "split", "checkpoint", "method", "model",
    ]
    with (base / "predictions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for checkpoint in ("best_source_f1", "last"):
            for split in ("source_validation", "target_monitoring"):
                for row in canonical_rows():
                    writer.writerow(
                        {
                            "subject_id": row["subject_id"], "subject_hash": row["subject_hash"],
                            "label": row["true_label"], "prediction": row["true_label"],
                            "prob_cn": row["probabilities"][0], "prob_mci": row["probabilities"][1],
                            "prob_ad": row["probabilities"][2], "split": split,
                            "checkpoint": checkpoint, "method": "baseline", "model": method,
                        }
                    )
    manifest = provenance_values(method_id=method, direction=direction, experiment_hash="baseline-experiment")
    manifest["baseline_id"] = method
    (base / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (base / "fold_result.json").write_text(json.dumps({"status": "COMPLETED"}), encoding="utf-8")
    return base
