"""Source-only orchestration and shared immutable-fold preparation primitives."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd
import torch
import yaml

from acda3d.data.artifact_wiring import load_artifact_index, validate_subject_records
from acda3d.data.datasets import LabeledSourceDataset, LabeledTargetDataset
from acda3d.data.loaders import (
    DataLoaderConfig,
    build_source_train_loader,
    build_source_validation_loader,
    build_target_evaluation_loader,
)
from acda3d.data.records import SubjectRecord, requirement_profile
from acda3d.data.splits import assignment_hash, validate_split_assignments
from acda3d.exceptions import ExperimentValidationError
from acda3d.experiments.fold_summary import write_fold_summary
from acda3d.experiments.prediction_export import (
    collect_predictions,
    export_predictions,
    prediction_metrics,
)
from acda3d.experiments.run_manifest import (
    atomic_json,
    create_run_manifest,
    stable_hash,
    update_run_manifest,
)
from acda3d.experiments.source_only import SourceOnlyExperimentConfig
from acda3d.losses import CoreACDA3DLoss
from acda3d.models import (
    ROIMaskPreparationConfig,
    build_acda3d,
    prepare_feature_grid_roi_masks,
)
from acda3d.training import SourceOnlyTrainer
from acda3d.training.checkpointing import load_training_checkpoint
from acda3d.training.reproducibility import seed_everything
from acda3d.training.runtime import validate_nonempty_loader


@dataclass
class FoldExecutionResult:
    direction: str
    seed: int
    fold: int
    status: str
    run_dir: Path
    experiment_hash: str
    metrics: dict[str, Any]
    reused: bool = False
    error: str | None = None

    def summary_row(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "seed": self.seed,
            "fold": self.fold,
            "status": self.status,
            "reused": self.reused,
            "experiment_hash": self.experiment_hash,
            "error": self.error,
            **self.metrics,
        }


@dataclass
class PreparedFold:
    source_train_dataset: LabeledSourceDataset
    source_validation_dataset: LabeledSourceDataset
    target_evaluation_dataset: LabeledTargetDataset | None
    source_folds: pd.DataFrame
    target_split: pd.DataFrame
    protocol: dict[str, Any]
    artifact_index_hash: str
    source_assignment_hash: str
    target_assignment_hash: str
    atlas_hash: str
    roi_order_hash: str
    roi_masks: torch.Tensor
    input_shape: tuple[int, int, int]


def _frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    rows = frame[columns].sort_values(columns).to_dict("records")
    return stable_hash(rows)


def _records_for_rows(rows: pd.DataFrame, records: list[SubjectRecord]) -> list[SubjectRecord]:
    mapping = {record.identity: record for record in records}
    selected = []
    for _, row in rows.iterrows():
        identity = f"{row['cohort']}:{row['subject_hash']}"
        if identity not in mapping:
            raise ExperimentValidationError(f"Split subject is absent from artifact index: {identity}.")
        selected.append(mapping[identity])
    return selected


def _load_roi_contract(config: SourceOnlyExperimentConfig) -> tuple[torch.Tensor, str, str]:
    assert config.paths.atlas_metadata and config.paths.roi_masks
    if not config.paths.atlas_metadata.is_file() or not config.paths.roi_masks.is_file():
        raise ExperimentValidationError("Atlas metadata and ROI-mask tensor must exist.")
    metadata = json.loads(config.paths.atlas_metadata.read_text(encoding="utf-8"))
    payload = torch.load(config.paths.roi_masks, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or "roi_masks" not in payload:
        raise ExperimentValidationError("ROI mask file must contain the Phase 5 roi_masks payload.")
    masks = payload["roi_masks"]
    labels = [int(value) for value in payload.get("label_values", metadata.get("label_values", []))]
    atlas_hash = str(metadata.get("atlas_hash", ""))
    if payload.get("atlas_hash") != atlas_hash:
        raise ExperimentValidationError("ROI-mask atlas hash differs from atlas metadata.")
    if labels != [int(value) for value in metadata.get("label_values", [])]:
        raise ExperimentValidationError("ROI label ordering differs from atlas metadata.")
    if masks.ndim != 4 or masks.shape[0] != int(config.model["num_rois"]):
        raise ExperimentValidationError("ROI masks do not match configured num_rois.")
    return masks.float(), atlas_hash, stable_hash(labels)


def prepare_fold_inputs(config: SourceOnlyExperimentConfig, fold: int) -> PreparedFold:
    config.validate()
    assert config.paths.artifact_index and config.paths.split_root
    result = load_artifact_index(
        config.paths.artifact_index,
        artifact_root=config.paths.artifact_root,
        profile="classification_only",
        check_files=True,
    )
    split_dir = config.paths.split_root / config.direction
    paths = {
        "source": split_dir / "source_folds.csv",
        "target": split_dir / "target_split.csv",
        "protocol": split_dir / "protocol.json",
    }
    if not all(path.is_file() for path in paths.values()):
        raise ExperimentValidationError(f"Immutable split manifests are incomplete: {split_dir}.")
    source_folds = pd.read_csv(paths["source"])
    target_split = pd.read_csv(paths["target"])
    protocol = json.loads(paths["protocol"].read_text(encoding="utf-8"))
    if protocol.get("source_cohort") != config.source_domain or protocol.get("target_cohort") != config.target_domain:
        raise ExperimentValidationError("Split direction does not match experiment direction.")
    validate_split_assignments(source_folds, target_split, 5)
    if assignment_hash(source_folds, target_split) != protocol.get("split_assignment_hash"):
        raise ExperimentValidationError("Split assignment hash is invalid.")
    if result.report.index_hash != protocol.get("input_artifact_index_hash"):
        raise ExperimentValidationError("Artifact index hash differs from the immutable split protocol.")
    selected = source_folds[source_folds["fold"] == fold]
    train_rows = selected[selected["partition"] == "source_train"]
    validation_rows = selected[selected["partition"] == "source_validation"]
    target_rows = target_split[target_split["partition"] == "target_evaluation"]
    if train_rows.empty or validation_rows.empty or (config.evaluation.target_monitoring and target_rows.empty):
        raise ExperimentValidationError("A required source or target-evaluation partition is empty.")
    source_train_records = _records_for_rows(train_rows, result.records)
    source_validation_records = _records_for_rows(validation_rows, result.records)
    target_records = _records_for_rows(target_rows, result.records)
    errors = validate_subject_records(
        [*source_train_records, *source_validation_records],
        requirement_profile("source_full_artifacts"),
        check_files=True,
    )
    if errors:
        raise ExperimentValidationError("Source artifact validation failed: " + " | ".join(errors))
    masks, atlas_hash, roi_order_hash = _load_roi_contract(config)
    record_hashes = {record.atlas_hash for record in result.records if record.atlas_hash}
    if record_hashes and record_hashes != {atlas_hash}:
        raise ExperimentValidationError(
            f"Artifact atlas hashes {sorted(record_hashes)} do not match {atlas_hash}."
        )
    record_roi_hashes = {
        str(record.metadata["roi_order_hash"])
        for record in result.records
        if record.metadata.get("roi_order_hash")
    }
    if record_roi_hashes and record_roi_hashes != {roi_order_hash}:
        raise ExperimentValidationError("Artifact ROI-order hashes differ from atlas metadata.")
    first_tensor = torch.load(source_train_records[0].derivative_path, map_location="cpu", weights_only=True)
    if isinstance(first_tensor, dict):
        first_tensor = next(value for value in first_tensor.values() if torch.is_tensor(value))
    if not torch.is_tensor(first_tensor) or first_tensor.ndim != 4 or first_tensor.shape[0] != 1:
        raise ExperimentValidationError("Model-ready derivative must have shape (1,H,W,D).")
    input_shape = tuple(int(value) for value in first_tensor.shape[1:])
    num_rois = int(config.model["num_rois"])
    dataset_kwargs = {"expected_spatial_shape": input_shape, "expected_num_rois": num_rois}
    source_train = LabeledSourceDataset(source_train_records, **dataset_kwargs)
    source_validation = LabeledSourceDataset(source_validation_records, **dataset_kwargs)
    target_evaluation = (
        LabeledTargetDataset(target_records, **dataset_kwargs)
        if config.evaluation.target_monitoring
        else None
    )
    source_hash = _frame_hash(
        source_folds, ["cohort", "subject_hash", "class_label", "fold", "partition"]
    )
    target_hash = _frame_hash(
        target_split, ["cohort", "subject_hash", "class_label", "partition"]
    )
    return PreparedFold(
        source_train,
        source_validation,
        target_evaluation,
        source_folds,
        target_split,
        protocol,
        result.report.index_hash,
        source_hash,
        target_hash,
        atlas_hash,
        roi_order_hash,
        masks,
        input_shape,
    )


class SourceOnlyExperimentRunner:
    """Sequential source-only runner; never constructs a target-adaptation loader."""

    uses_target_adaptation = False

    def __init__(self, config: SourceOnlyExperimentConfig):
        config.validate()
        self.config = config

    def _device(self) -> str:
        requested = self.config.execution.device
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return requested

    def _loaders(self, prepared: PreparedFold, seed: int):
        loader_values = {
            key: value
            for key, value in self.config.data_loader.items()
            if key in DataLoaderConfig.__dataclass_fields__
        }
        loader_config = DataLoaderConfig(**loader_values)
        source_train_loader = build_source_train_loader(
            prepared.source_train_dataset, loader_config, seed=seed
        )
        source_validation_loader = build_source_validation_loader(
            prepared.source_validation_dataset, loader_config, seed=seed
        )
        target_evaluation_loader = (
            build_target_evaluation_loader(
                prepared.target_evaluation_dataset, loader_config, seed=seed
            )
            if prepared.target_evaluation_dataset is not None
            else None
        )
        validate_nonempty_loader(source_train_loader, "source_train_loader")
        validate_nonempty_loader(source_validation_loader, "source_validation_loader")
        if target_evaluation_loader is not None:
            validate_nonempty_loader(target_evaluation_loader, "target_evaluation_loader")
        return source_train_loader, source_validation_loader, target_evaluation_loader

    def _model_and_masks(self, prepared: PreparedFold):
        model = build_acda3d(self.config.model)
        feature_shape = model.encoder.infer_output_shape((1, 1, *prepared.input_shape))[2:]
        mask_config = ROIMaskPreparationConfig(
            mode=str(self.config.roi_mask_preparation.get("mode", "nearest")),
            normalize=True,
            epsilon=float(self.config.roi_mask_preparation.get("epsilon", 1e-8)),
            expected_num_rois=int(self.config.model["num_rois"]),
        )
        feature_masks = prepare_feature_grid_roi_masks(
            prepared.roi_masks, feature_shape, mask_config
        )
        return model, feature_masks, feature_shape, mask_config.sha256()

    def _manifest(self, prepared: PreparedFold, fold: int, seed: int, model: torch.nn.Module, feature_shape: tuple[int, ...], mask_hash: str) -> dict[str, Any]:
        experiment_hash = self.config.sha256()
        return create_run_manifest(
            experiment_name=self.config.name,
            display_name=self.config.display_name,
            method="source_only",
            source_domain=self.config.source_domain,
            target_domain=self.config.target_domain,
            direction=self.config.direction,
            fold=fold,
            seed=seed,
            source_split_assignment_hash=prepared.source_assignment_hash,
            target_split_assignment_hash=prepared.target_assignment_hash,
            split_assignment_hash=prepared.protocol["split_assignment_hash"],
            artifact_index_hash=prepared.artifact_index_hash,
            atlas_hash=prepared.atlas_hash,
            roi_order_hash=prepared.roi_order_hash,
            model_configuration_hash=stable_hash(self.config.model),
            training_configuration_hash=stable_hash(asdict(self.config.training)),
            roi_mask_preparation_hash=mask_hash,
            feature_shape=list(feature_shape),
            experiment_hash=experiment_hash,
            model_parameter_count=sum(parameter.numel() for parameter in model.parameters()),
        )

    def _completed_reuse(self, run_dir: Path, experiment_hash: str) -> FoldExecutionResult | None:
        manifest_path = run_dir / "run_manifest.json"
        if not manifest_path.is_file():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "COMPLETED":
            return None
        required = [
            run_dir / "checkpoint_last.pt",
            run_dir / "checkpoint_best_source_f1.pt",
            run_dir / "fold_metrics.json",
            run_dir / "training_history.csv",
        ]
        if manifest.get("experiment_hash") != experiment_hash or not all(path.is_file() for path in required):
            raise ExperimentValidationError("Completed fold is incompatible or incomplete; use --overwrite.")
        metrics = json.loads((run_dir / "fold_metrics.json").read_text(encoding="utf-8"))
        return FoldExecutionResult(
            manifest["direction"], int(manifest["seed"]), int(manifest["fold"]),
            "COMPLETED", run_dir, experiment_hash, metrics, reused=True,
        )

    def run_fold(
        self,
        fold: int,
        seed: int,
        *,
        dry_run: bool = False,
        validate_only: bool = False,
        resume_from: str | Path | None = None,
        interrupt_after_epoch: int | None = None,
    ) -> FoldExecutionResult:
        prepared = prepare_fold_inputs(self.config, fold)
        run_dir = self.config.run_dir(fold, seed)
        experiment_hash = self.config.sha256()
        if not self.config.execution.overwrite:
            reused = self._completed_reuse(run_dir, experiment_hash)
            if reused is not None and self.config.execution.continue_completed_folds:
                return reused
            if run_dir.exists() and any(run_dir.iterdir()) and resume_from is None and not dry_run and not validate_only:
                raise ExperimentValidationError(
                    "Fold directory already contains an incomplete run; provide --resume-from or --overwrite."
                )
        if dry_run:
            return FoldExecutionResult(
                self.config.direction, seed, fold, "PENDING", run_dir, experiment_hash,
                {"planned_source_train": len(prepared.source_train_dataset),
                 "planned_source_validation": len(prepared.source_validation_dataset),
                 "planned_target_evaluation": len(prepared.target_evaluation_dataset or [])},
            )
        seed_everything(seed)
        model, feature_masks, feature_shape, mask_hash = self._model_and_masks(prepared)
        source_train_loader, source_validation_loader, target_evaluation_loader = self._loaders(
            prepared, seed
        )
        if validate_only:
            raw_batch = next(iter(source_train_loader))
            with torch.no_grad():
                output = model(raw_batch["x"], feature_masks)
            if output.concepts.shape[1] != int(self.config.model["num_rois"]):
                raise ExperimentValidationError("Validate-only forward produced an invalid ROI count.")
            return FoldExecutionResult(
                self.config.direction, seed, fold, "PENDING", run_dir, experiment_hash,
                {"validated": True, "feature_shape": list(feature_shape)},
            )
        run_dir.mkdir(parents=True, exist_ok=True)
        validation_payload = {
            "valid": True,
            "source_train_subjects": len(prepared.source_train_dataset),
            "source_validation_subjects": len(prepared.source_validation_dataset),
            "target_evaluation_subjects": len(prepared.target_evaluation_dataset or []),
            "source_train_batches": len(source_train_loader),
            "source_validation_batches": len(source_validation_loader),
            "target_evaluation_batches": len(target_evaluation_loader) if target_evaluation_loader else 0,
            "atlas_hash": prepared.atlas_hash,
            "roi_order_hash": prepared.roi_order_hash,
            "feature_shape": list(feature_shape),
            "target_adaptation_loader_constructed": False,
        }
        atomic_json(run_dir / "input_validation.json", validation_payload)
        (run_dir / "config_resolved.yaml").write_text(
            yaml.safe_dump(self.config.resolved_dict(), sort_keys=True), encoding="utf-8"
        )
        manifest_path = run_dir / "run_manifest.json"
        if resume_from is not None and manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("experiment_hash") != experiment_hash:
                raise ExperimentValidationError("Resume manifest has an incompatible experiment hash.")
        else:
            manifest = self._manifest(prepared, fold, seed, model, feature_shape, mask_hash)
        update_run_manifest(manifest_path, manifest, "PENDING")
        training_config = replace(
            self.config.training,
            device=self._device(),
            seed=seed,
            target_monitoring_enabled=self.config.evaluation.target_monitoring,
        )
        loss_fn = CoreACDA3DLoss(
            int(self.config.model["num_rois"]),
            weights=self.config.loss_weights,
            label_smoothing=self.config.label_smoothing,
        )
        trainer = SourceOnlyTrainer(
            model,
            loss_fn,
            feature_masks,
            run_dir,
            config=training_config,
            split_assignment_hash=prepared.protocol["split_assignment_hash"],
            atlas_hash=prepared.atlas_hash,
            roi_order_hash=prepared.roi_order_hash,
        )
        update_run_manifest(manifest_path, manifest, "RUNNING")
        try:
            trainer.fit(
                source_train_loader,
                source_validation_loader,
                target_evaluation_loader,
                resume_from=resume_from,
                interrupt_after_epoch=interrupt_after_epoch,
            )
            if trainer.completed_epoch < training_config.total_epochs:
                update_run_manifest(manifest_path, manifest, "INTERRUPTED")
                return FoldExecutionResult(
                    self.config.direction, seed, fold, "INTERRUPTED", run_dir,
                    experiment_hash, {"last_epoch": trainer.completed_epoch},
                )
            checkpoint_results: dict[str, Any] = {}
            checkpoint_paths = {
                "best_source_f1": run_dir / "checkpoint_best_source_f1.pt",
                "last": run_dir / "checkpoint_last.pt",
            }
            for checkpoint_name in self.config.evaluation.export_checkpoints:
                checkpoint_path = checkpoint_paths[checkpoint_name]
                checkpoint = load_training_checkpoint(checkpoint_path)
                model.load_state_dict(checkpoint["model_state_dict"], strict=True)
                source_frame = collect_predictions(
                    model, source_validation_loader, trainer.roi_masks, trainer.device,
                    direction=self.config.direction, fold=fold, seed=seed,
                    checkpoint_name=checkpoint_name, checkpoint_epoch=int(checkpoint["epoch"]),
                    split="source_validation", experiment_hash=experiment_hash,
                )
                source_path = run_dir / "source_validation_predictions" / f"{checkpoint_name}.csv"
                export_predictions(source_frame, source_path)
                result_metrics: dict[str, Any] = {
                    "epoch": int(checkpoint["epoch"]),
                    "source_validation": prediction_metrics(source_frame),
                    "checkpoint_path": str(checkpoint_path),
                    "source_predictions": str(source_path),
                }
                if target_evaluation_loader is not None:
                    target_frame = collect_predictions(
                        model, target_evaluation_loader, trainer.roi_masks, trainer.device,
                        direction=self.config.direction, fold=fold, seed=seed,
                        checkpoint_name=checkpoint_name, checkpoint_epoch=int(checkpoint["epoch"]),
                        split="target_monitoring", experiment_hash=experiment_hash,
                    )
                    target_path = run_dir / "target_monitoring_predictions" / f"{checkpoint_name}.csv"
                    export_predictions(target_frame, target_path)
                    result_metrics["target_monitoring"] = {
                        **prediction_metrics(target_frame),
                        "label": "MONITORING ONLY — NOT A TRAINING LOSS",
                    }
                    result_metrics["target_predictions"] = str(target_path)
                checkpoint_results[checkpoint_name] = result_metrics
            best = checkpoint_results["best_source_f1"]
            last = checkpoint_results["last"]
            runtime_path = run_dir / "runtime.json"
            runtime = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path.is_file() else {}
            metrics = {
                "best_source_epoch": best["epoch"],
                "best_source_macro_f1": best["source_validation"]["macro_f1"],
                "best_source_validation_accuracy": best["source_validation"]["accuracy"],
                "last_epoch": last["epoch"],
                "last_source_macro_f1": last["source_validation"]["macro_f1"],
                "last_source_validation_accuracy": last["source_validation"]["accuracy"],
                "best_target_monitoring_macro_f1": best.get("target_monitoring", {}).get("macro_f1"),
                "last_target_monitoring_macro_f1": last.get("target_monitoring", {}).get("macro_f1"),
                "checkpoint_best_source_f1": str(checkpoint_paths["best_source_f1"]),
                "checkpoint_last": str(checkpoint_paths["last"]),
                "checkpoint_results": checkpoint_results,
                "runtime_seconds": float(runtime.get("total_train_seconds", 0.0)),
            }
            atomic_json(run_dir / "fold_metrics.json", metrics)
            (run_dir / "log.txt").write_text(
                "3D-ACDA Source-Only completed. Target metrics are monitoring only.\n",
                encoding="utf-8",
            )
            update_run_manifest(
                manifest_path,
                manifest,
                "COMPLETED",
                checkpoint_paths={key: str(value) for key, value in checkpoint_paths.items()},
            )
            return FoldExecutionResult(
                self.config.direction, seed, fold, "COMPLETED", run_dir,
                experiment_hash, metrics,
            )
        except Exception as error:
            update_run_manifest(manifest_path, manifest, "FAILED", error=str(error))
            raise

    def run(
        self,
        *,
        dry_run: bool = False,
        validate_only: bool = False,
        resume_from: str | Path | None = None,
    ) -> list[FoldExecutionResult]:
        results: list[FoldExecutionResult] = []
        for seed in self.config.seeds:
            for fold in self.config.folds:
                try:
                    results.append(
                        self.run_fold(
                            fold, seed, dry_run=dry_run, validate_only=validate_only,
                            resume_from=resume_from,
                        )
                    )
                except Exception as error:
                    results.append(
                        FoldExecutionResult(
                            self.config.direction, seed, fold, "FAILED",
                            self.config.run_dir(fold, seed), self.config.sha256(), {},
                            error=str(error),
                        )
                    )
                    if self.config.execution.fail_fast:
                        raise
        if not dry_run and not validate_only:
            assert self.config.paths.output_root is not None
            direction_dir = self.config.paths.output_root / "source_only" / self.config.direction
            write_fold_summary([result.summary_row() for result in results], direction_dir)
            atomic_json(
                direction_dir / "experiment_manifest.json",
                {
                    "experiment_hash": self.config.sha256(),
                    "direction": self.config.direction,
                    "method": "source_only",
                    "runs": [result.summary_row() for result in results],
                },
            )
        return results


def run_both_directions(
    config: SourceOnlyExperimentConfig,
    *,
    dry_run: bool = False,
    validate_only: bool = False,
) -> dict[str, list[FoldExecutionResult]]:
    outputs = {}
    for source, target in (("ADNI", "OASIS"), ("OASIS", "ADNI")):
        direction_config = copy.deepcopy(config)
        direction_config.source_domain = source
        direction_config.target_domain = target
        direction_config.validate()
        outputs[direction_config.direction] = SourceOnlyExperimentRunner(direction_config).run(
            dry_run=dry_run, validate_only=validate_only
        )
    return outputs
