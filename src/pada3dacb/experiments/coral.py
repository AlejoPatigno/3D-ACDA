"""Configuration and immutable run identity for PADA-3DACB + CORAL."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import torch
import yaml

from pada3dacb.adaptation import CORALAdaptationMethod
from pada3dacb.data.artifact_wiring import load_artifact_index, validate_subject_records
from pada3dacb.data.datasets import TargetAdaptationDataset
from pada3dacb.data.loaders import (
    DataLoaderConfig,
    build_source_train_loader,
    build_source_validation_loader,
    build_target_adaptation_loader,
    build_target_evaluation_loader,
)
from pada3dacb.data.records import requirement_profile
from pada3dacb.exceptions import (
    ConfigurationError,
    ExperimentValidationError,
    PhaseNotImplementedError,
)
from pada3dacb.experiments.fold_summary import write_fold_summary
from pada3dacb.experiments.prediction_export import (
    collect_predictions,
    export_predictions,
    prediction_metrics,
)
from pada3dacb.experiments.run_manifest import (
    atomic_json,
    create_run_manifest,
    stable_hash,
    update_run_manifest,
)
from pada3dacb.experiments.runner import (
    FoldExecutionResult,
    PreparedFold,
    SourceOnlyExperimentRunner,
    _frame_hash,
    _records_for_rows,
    prepare_fold_inputs,
)
from pada3dacb.experiments.source_only import (
    SourceOnlyExperimentConfig,
    load_source_only_config,
)
from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.training import UDATrainer
from pada3dacb.training.checkpointing import load_training_checkpoint
from pada3dacb.training.reproducibility import seed_everything
from pada3dacb.training.runtime import validate_nonempty_loader

CORAL_DISPLAY_NAME = "PADA-3DACB + CORAL"


@dataclass(frozen=True)
class CORALAdaptationConfig:
    name: str = "coral"
    feature: str = "z"
    weight: float | None = None
    active_during_warmup: bool = False
    covariance: dict[str, str] = field(
        default_factory=lambda: {
            "estimator": "unbiased",
            "normalization": "four_d_squared",
            "compute_dtype": "float32",
        }
    )

    def validate(self) -> None:
        if self.name != "coral":
            raise PhaseNotImplementedError(
                f"Adaptation method {self.name!r} is not implemented in Phase 10."
            )
        if self.feature != "z":
            raise ConfigurationError("CORAL feature must be the subject embedding 'z'.")
        if self.weight is None:
            raise ConfigurationError("CORAL requires an explicit adaptation.weight.")
        if not math.isfinite(self.weight) or self.weight < 0:
            raise ConfigurationError("CORAL adaptation.weight must be finite and non-negative.")
        if self.active_during_warmup is not False:
            raise ConfigurationError("CORAL must be inactive during warm-up.")
        expected = {
            "estimator": "unbiased",
            "normalization": "four_d_squared",
            "compute_dtype": "float32",
        }
        if self.covariance != expected:
            raise ConfigurationError(f"CORAL covariance configuration must be {expected}.")

    def resolved_dict(self) -> dict[str, Any]:
        return asdict(self)

    def sha256(self) -> str:
        return stable_hash(self.resolved_dict())


@dataclass
class CORALExperimentConfig(SourceOnlyExperimentConfig):
    adaptation: CORALAdaptationConfig = field(default_factory=CORALAdaptationConfig)

    def validate(self) -> None:
        if self.method != "coral":
            raise PhaseNotImplementedError(f"Method {self.method!r} is not implemented in Phase 10.")
        if self.display_name != CORAL_DISPLAY_NAME:
            raise ConfigurationError(f"CORAL display_name must be {CORAL_DISPLAY_NAME!r}.")
        self._validate_common()
        self.adaptation.validate()

    def resolved_dict(self) -> dict[str, Any]:
        payload = super().resolved_dict()
        payload["adaptation"] = self.adaptation.resolved_dict()
        return payload

    def run_dir(self, fold: int, seed: int) -> Path:
        assert self.paths.output_root is not None and self.adaptation.weight is not None
        return (
            self.paths.output_root
            / "coral"
            / self.direction
            / f"seed_{seed}"
            / stable_weight_directory(self.adaptation.weight)
            / f"fold_{fold}"
        )


def stable_weight_directory(weight: float) -> str:
    """Use the exact IEEE-754 representation to prevent directory collisions."""
    encoded = float(weight).hex().replace("-", "m").replace("+", "p").replace(".", "d")
    return f"weight_{encoded}"


def load_coral_config(
    path: str | Path,
    *,
    overrides: dict[str, Any] | None = None,
) -> CORALExperimentConfig:
    overrides = dict(overrides or {})
    coral_weight = overrides.pop("coral_weight", None)
    base = load_source_only_config(path, overrides=overrides, validate=False)
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    adaptation_payload = dict(payload.get("adaptation") or {})
    weight_value = coral_weight if coral_weight is not None else adaptation_payload.get("weight")
    adaptation = CORALAdaptationConfig(
        name=str(adaptation_payload.get("name", "coral")),
        feature=str(adaptation_payload.get("feature", "z")),
        weight=None if weight_value is None else float(weight_value),
        active_during_warmup=bool(adaptation_payload.get("active_during_warmup", False)),
        covariance=dict(adaptation_payload.get("covariance") or {}),
    )
    inherited = {
        item.name: getattr(base, item.name)
        for item in fields(SourceOnlyExperimentConfig)
    }
    config = CORALExperimentConfig(**inherited, adaptation=adaptation)
    config.validate()
    return config


@dataclass
class PreparedCORALFold:
    base: PreparedFold
    target_adaptation_dataset: TargetAdaptationDataset
    target_adaptation_assignment_hash: str
    target_evaluation_assignment_hash: str


def prepare_coral_fold_inputs(
    config: CORALExperimentConfig, fold: int
) -> PreparedCORALFold:
    base = prepare_fold_inputs(config, fold)
    assert config.paths.artifact_index
    result = load_artifact_index(
        config.paths.artifact_index,
        artifact_root=config.paths.artifact_root,
        profile="classification_only",
        check_files=True,
    )
    adaptation_rows = base.target_split[
        base.target_split["partition"] == "target_adaptation"
    ]
    evaluation_rows = base.target_split[
        base.target_split["partition"] == "target_evaluation"
    ]
    if adaptation_rows.empty:
        raise ExperimentValidationError("The immutable target_adaptation partition is empty.")
    overlap = set(adaptation_rows["subject_hash"]).intersection(evaluation_rows["subject_hash"])
    if overlap:
        raise ExperimentValidationError(
            "Target adaptation and target evaluation partitions are not disjoint."
        )
    records = _records_for_rows(adaptation_rows, result.records)
    errors = validate_subject_records(
        records, requirement_profile("target_adaptation"), check_files=True
    )
    if errors:
        raise ExperimentValidationError(
            "Target-adaptation artifact validation failed: " + " | ".join(errors)
        )
    dataset = TargetAdaptationDataset(
        records,
        expected_spatial_shape=base.input_shape,
        expected_num_rois=int(config.model["num_rois"]),
    )
    allowed = {"x", "subject_id", "subject_hash", "cohort"}
    observed = set(dataset[0])
    if observed != allowed:
        raise ExperimentValidationError(
            f"TargetAdaptationDataset fields must be {sorted(allowed)}, got {sorted(observed)}."
        )
    columns = ["cohort", "subject_hash", "class_label", "partition"]
    return PreparedCORALFold(
        base=base,
        target_adaptation_dataset=dataset,
        target_adaptation_assignment_hash=_frame_hash(adaptation_rows, columns),
        target_evaluation_assignment_hash=_frame_hash(evaluation_rows, columns),
    )


class CORALExperimentRunner(SourceOnlyExperimentRunner):
    """Sequential CORAL runner over immutable source and target partitions."""

    uses_target_adaptation = True
    method_name = "coral"
    display_name = CORAL_DISPLAY_NAME
    loss_name = "coral"

    def __init__(self, config: CORALExperimentConfig):
        config.validate()
        self.config = config

    def _prepare_fold(self, fold: int) -> PreparedCORALFold:
        return prepare_coral_fold_inputs(self.config, fold)

    def _build_adaptation_method(self):
        return CORALAdaptationMethod()

    def _loaders(self, prepared: PreparedCORALFold, seed: int):
        values = {
            key: value
            for key, value in self.config.data_loader.items()
            if key in DataLoaderConfig.__dataclass_fields__
        }
        loader_config = DataLoaderConfig(**values)
        if not loader_config.drop_last_train:
            raise ExperimentValidationError(
                f"{self.method_name.upper()} requires drop_last_train=True for training loaders."
            )
        base = prepared.base
        source_train = build_source_train_loader(
            base.source_train_dataset, loader_config, seed=seed
        )
        target_adaptation = build_target_adaptation_loader(
            prepared.target_adaptation_dataset, loader_config, seed=seed + 1
        )
        source_validation = build_source_validation_loader(
            base.source_validation_dataset, loader_config, seed=seed
        )
        target_evaluation = (
            build_target_evaluation_loader(
                base.target_evaluation_dataset, loader_config, seed=seed
            )
            if base.target_evaluation_dataset is not None
            else None
        )
        validate_nonempty_loader(source_train, "source_train_loader")
        validate_nonempty_loader(target_adaptation, "target_adaptation_loader")
        validate_nonempty_loader(source_validation, "source_validation_loader")
        if loader_config.batch_size < 2:
            raise ExperimentValidationError(
                f"{self.method_name.upper()} loaders require batch_size >= 2."
            )
        if target_evaluation is not None:
            validate_nonempty_loader(target_evaluation, "target_evaluation_loader")
        return source_train, target_adaptation, source_validation, target_evaluation

    def _manifest(
        self,
        prepared: PreparedCORALFold,
        fold: int,
        seed: int,
        model: torch.nn.Module,
        feature_shape: tuple[int, ...],
        mask_hash: str,
        source_steps: int,
        target_steps: int,
    ) -> dict[str, Any]:
        base = prepared.base
        assert self.config.adaptation.weight is not None
        return create_run_manifest(
            experiment_name=self.config.name,
            display_name=self.config.display_name,
            method="coral",
            source_domain=self.config.source_domain,
            target_domain=self.config.target_domain,
            direction=self.config.direction,
            fold=fold,
            seed=seed,
            source_split_assignment_hash=base.source_assignment_hash,
            target_split_assignment_hash=base.target_assignment_hash,
            split_assignment_hash=base.protocol["split_assignment_hash"],
            target_adaptation_assignment_hash=prepared.target_adaptation_assignment_hash,
            target_evaluation_assignment_hash=prepared.target_evaluation_assignment_hash,
            artifact_index_hash=base.artifact_index_hash,
            atlas_hash=base.atlas_hash,
            roi_order_hash=base.roi_order_hash,
            model_configuration_hash=stable_hash(self.config.model),
            training_configuration_hash=stable_hash(asdict(self.config.training)),
            roi_mask_preparation_hash=mask_hash,
            feature_shape=list(feature_shape),
            experiment_hash=self.config.sha256(),
            model_parameter_count=sum(parameter.numel() for parameter in model.parameters()),
            adaptation_method="coral",
            adaptation_feature="z",
            adaptation_weight=self.config.adaptation.weight,
            adaptation_configuration_hash=self.config.adaptation.sha256(),
            source_train_count=len(base.source_train_dataset),
            target_adaptation_count=len(prepared.target_adaptation_dataset),
            source_steps_per_epoch=source_steps,
            expected_target_cycles_per_epoch=(source_steps - 1) // target_steps,
            warmup_adaptation_active=False,
            full_adaptation_active=True,
            target_training_labels_available=False,
        )

    def _completed_reuse(
        self,
        run_dir: Path,
        experiment_hash: str,
        prepared: PreparedCORALFold,
    ) -> FoldExecutionResult | None:
        result = super()._completed_reuse(run_dir, experiment_hash)
        if result is None:
            return None
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "method": "coral",
            "adaptation_weight": self.config.adaptation.weight,
            "source_split_assignment_hash": prepared.base.source_assignment_hash,
            "target_adaptation_assignment_hash": prepared.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": prepared.target_evaluation_assignment_hash,
        }
        mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
        if mismatches:
            raise ExperimentValidationError(
                f"Completed CORAL fold has incompatible fields: {sorted(mismatches)}."
            )
        return result

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
        prepared = self._prepare_fold(fold)
        base = prepared.base
        run_dir = self.config.run_dir(fold, seed)
        experiment_hash = self.config.sha256()
        source_train, target_adaptation, source_validation, target_evaluation = (
            self._loaders(prepared, seed)
        )
        if not self.config.execution.overwrite:
            reused = self._completed_reuse(run_dir, experiment_hash, prepared)
            if reused is not None and self.config.execution.continue_completed_folds:
                return reused
            if (
                run_dir.exists()
                and any(run_dir.iterdir())
                and resume_from is None
                and not dry_run
                and not validate_only
            ):
                raise ExperimentValidationError(
                    f"{self.method_name.upper()} fold directory is incomplete; "
                    "provide --resume-from or --overwrite."
                )
        planned = {
            "planned_source_train": len(base.source_train_dataset),
            "planned_source_validation": len(base.source_validation_dataset),
            "planned_target_adaptation": len(prepared.target_adaptation_dataset),
            "planned_target_evaluation": len(base.target_evaluation_dataset or []),
            "source_steps_per_epoch": len(source_train),
            "target_steps_per_cycle": len(target_adaptation),
            "expected_target_cycles_per_epoch": (len(source_train) - 1)
            // len(target_adaptation),
            "target_training_labels_available": False,
            "intended_run_dir": str(run_dir),
        }
        if dry_run:
            return FoldExecutionResult(
                self.config.direction,
                seed,
                fold,
                "PENDING",
                run_dir,
                experiment_hash,
                planned,
            )
        seed_everything(seed)
        model, feature_masks, feature_shape, mask_hash = self._model_and_masks(base)
        loss_fn = CorePADA3DACBLoss(
            int(self.config.model["num_rois"]),
            weights=self.config.loss_weights,
            label_smoothing=self.config.label_smoothing,
        )
        adaptation_method = self._build_adaptation_method()
        if validate_only:
            source_batch = next(iter(source_train))
            target_batch = next(iter(target_adaptation))
            UDATrainer._validate_target_batch(target_batch)
            before = {key: value.detach().clone() for key, value in model.state_dict().items()}
            with torch.no_grad():
                source_output = model(source_batch["x"], feature_masks)
                target_output = model(target_batch["x"], feature_masks)
                core = loss_fn(
                    source_output,
                    source_batch["y"],
                    source_batch["c_target"],
                    source_batch["g_bar"],
                    stage="full",
                )
                adaptation = adaptation_method.compute(source_output, target_output, "full")
                combined = core.total + float(self.config.adaptation.weight) * adaptation.total
            if not torch.isfinite(combined):
                raise ExperimentValidationError(
                    f"Validate-only combined {self.method_name.upper()} loss is non-finite."
                )
            if any(not torch.equal(before[key], value) for key, value in model.state_dict().items()):
                raise ExperimentValidationError("Validate-only modified model parameters.")
            return FoldExecutionResult(
                self.config.direction,
                seed,
                fold,
                "PENDING",
                run_dir,
                experiment_hash,
                {
                    **planned,
                    "validated": True,
                    f"{self.loss_name}_loss": float(adaptation.total),
                },
            )
        run_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(
            run_dir / "input_validation.json",
            {
                **planned,
                "valid": True,
                "atlas_hash": base.atlas_hash,
                "roi_order_hash": base.roi_order_hash,
                "feature_shape": list(feature_shape),
                "target_adaptation_fields": sorted(prepared.target_adaptation_dataset[0]),
            },
        )
        (run_dir / "config_resolved.yaml").write_text(
            yaml.safe_dump(self.config.resolved_dict(), sort_keys=True), encoding="utf-8"
        )
        manifest_path = run_dir / "run_manifest.json"
        if resume_from is not None and manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("experiment_hash") != experiment_hash:
                raise ExperimentValidationError(
                    f"Resume manifest has an incompatible {self.method_name.upper()} hash."
                )
        else:
            manifest = self._manifest(
                prepared,
                fold,
                seed,
                model,
                feature_shape,
                mask_hash,
                len(source_train),
                len(target_adaptation),
            )
        update_run_manifest(manifest_path, manifest, "PENDING")
        from dataclasses import replace

        training_config = replace(
            self.config.training,
            device=self._device(),
            seed=seed,
            target_monitoring_enabled=self.config.evaluation.target_monitoring,
        )
        trainer = UDATrainer(
            model,
            loss_fn,
            feature_masks,
            run_dir,
            config=training_config,
            split_assignment_hash=base.protocol["split_assignment_hash"],
            atlas_hash=base.atlas_hash,
            roi_order_hash=base.roi_order_hash,
            adaptation_method=adaptation_method,
            adaptation_weight=float(self.config.adaptation.weight),
            adaptation_configuration=self.config.adaptation.resolved_dict(),
            source_split_assignment_hash=base.source_assignment_hash,
            target_adaptation_assignment_hash=prepared.target_adaptation_assignment_hash,
            target_evaluation_assignment_hash=prepared.target_evaluation_assignment_hash,
        )
        update_run_manifest(manifest_path, manifest, "RUNNING")
        try:
            history = trainer.fit(
                source_train,
                source_validation,
                target_evaluation,
                target_adaptation_loader=target_adaptation,
                resume_from=resume_from,
                interrupt_after_epoch=interrupt_after_epoch,
            )
            if trainer.completed_epoch < training_config.total_epochs:
                update_run_manifest(manifest_path, manifest, "INTERRUPTED")
                return FoldExecutionResult(
                    self.config.direction,
                    seed,
                    fold,
                    "INTERRUPTED",
                    run_dir,
                    experiment_hash,
                    {"last_epoch": trainer.completed_epoch},
                )
            metrics = self._export_results(
                prepared,
                trainer,
                source_validation,
                target_evaluation,
                fold,
                seed,
                experiment_hash,
                history.rows,
            )
            atomic_json(run_dir / "fold_metrics.json", metrics)
            (run_dir / "log.txt").write_text(
                f"{self.display_name} completed. Target labels did not enter training; "
                "target metrics are monitoring only.\n",
                encoding="utf-8",
            )
            checkpoint_paths = {
                "best_source_f1": run_dir / "checkpoint_best_source_f1.pt",
                "last": run_dir / "checkpoint_last.pt",
            }
            update_run_manifest(
                manifest_path,
                manifest,
                "COMPLETED",
                checkpoint_paths={key: str(value) for key, value in checkpoint_paths.items()},
            )
            return FoldExecutionResult(
                self.config.direction,
                seed,
                fold,
                "COMPLETED",
                run_dir,
                experiment_hash,
                metrics,
            )
        except Exception as error:
            update_run_manifest(manifest_path, manifest, "FAILED", error=str(error))
            raise

    def _export_results(
        self,
        prepared: PreparedCORALFold,
        trainer: UDATrainer,
        source_validation: Any,
        target_evaluation: Any | None,
        fold: int,
        seed: int,
        experiment_hash: str,
        history_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        run_dir = self.config.run_dir(fold, seed)
        checkpoint_paths = {
            "best_source_f1": run_dir / "checkpoint_best_source_f1.pt",
            "last": run_dir / "checkpoint_last.pt",
        }
        checkpoint_results: dict[str, Any] = {}
        for checkpoint_name in self.config.evaluation.export_checkpoints:
            checkpoint_path = checkpoint_paths[checkpoint_name]
            checkpoint = load_training_checkpoint(checkpoint_path)
            trainer.model.load_state_dict(checkpoint["model_state_dict"], strict=True)
            common = {
                "direction": self.config.direction,
                "fold": fold,
                "seed": seed,
                "checkpoint_name": checkpoint_name,
                "checkpoint_epoch": int(checkpoint["epoch"]),
                "experiment_hash": experiment_hash,
                "method": self.method_name,
                "model_name": self.display_name,
            }
            source_frame = collect_predictions(
                trainer.model,
                source_validation,
                trainer.roi_masks,
                trainer.device,
                split="source_validation",
                **common,
            )
            source_path = run_dir / "source_validation_predictions" / f"{checkpoint_name}.csv"
            export_predictions(source_frame, source_path)
            item: dict[str, Any] = {
                "epoch": int(checkpoint["epoch"]),
                "source_validation": prediction_metrics(source_frame),
                "checkpoint_path": str(checkpoint_path),
                "source_predictions": str(source_path),
            }
            if target_evaluation is not None:
                target_frame = collect_predictions(
                    trainer.model,
                    target_evaluation,
                    trainer.roi_masks,
                    trainer.device,
                    split="target_monitoring",
                    **common,
                )
                target_path = run_dir / "target_monitoring_predictions" / f"{checkpoint_name}.csv"
                export_predictions(target_frame, target_path)
                item["target_monitoring"] = {
                    **prediction_metrics(target_frame),
                    "label": self.config.evaluation.target_monitoring_label,
                }
                item["target_predictions"] = str(target_path)
            checkpoint_results[checkpoint_name] = item
        best = checkpoint_results["best_source_f1"]
        last = checkpoint_results["last"]
        return {
            **self._adaptation_summary(history_rows),
            "best_source_epoch": best["epoch"],
            "best_source_macro_f1": best["source_validation"]["macro_f1"],
            "last_epoch": last["epoch"],
            "last_source_macro_f1": last["source_validation"]["macro_f1"],
            "best_source_target_monitoring_macro_f1": best.get(
                "target_monitoring", {}
            ).get("macro_f1"),
            "last_target_monitoring_macro_f1": last.get(
                "target_monitoring", {}
            ).get("macro_f1"),
            "checkpoint_best_source_f1": str(checkpoint_paths["best_source_f1"]),
            "checkpoint_last": str(checkpoint_paths["last"]),
            "checkpoint_results": checkpoint_results,
        }

    def _adaptation_summary(self, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
        full_rows = [row for row in history_rows if row["stage"] == "full"]
        final = history_rows[-1]
        return {
            "adaptation_method": "coral",
            "adaptation_weight": self.config.adaptation.weight,
            "final_train_coral_loss": final["train/coral_loss"],
            "final_weighted_coral_loss": final["train/weighted_coral_loss"],
            "mean_train_coral_loss_full_stage": sum(
                row["train/coral_loss"] for row in full_rows
            )
            / len(full_rows),
            "target_batch_cycles": sum(
                row["train/target_batch_cycles"] for row in full_rows
            ),
        }

    def _experiment_manifest_fields(self) -> dict[str, Any]:
        return {"attempted_weights": [self.config.adaptation.weight]}

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
                            fold,
                            seed,
                            dry_run=dry_run,
                            validate_only=validate_only,
                            resume_from=resume_from,
                        )
                    )
                except Exception as error:
                    results.append(
                        FoldExecutionResult(
                            self.config.direction,
                            seed,
                            fold,
                            "FAILED",
                            self.config.run_dir(fold, seed),
                            self.config.sha256(),
                            {},
                            error=str(error),
                        )
                    )
                    if self.config.execution.fail_fast:
                        raise
        if not dry_run and not validate_only:
            assert self.config.paths.output_root is not None
            direction_dir = (
                self.config.paths.output_root / self.method_name / self.config.direction
            )
            write_fold_summary([result.summary_row() for result in results], direction_dir)
            atomic_json(
                direction_dir / "experiment_manifest.json",
                {
                    "experiment_hash": self.config.sha256(),
                    "direction": self.config.direction,
                    "method": self.method_name,
                    **self._experiment_manifest_fields(),
                    "runs": [result.summary_row() for result in results],
                },
            )
        return results


def run_coral_both_directions(
    config: CORALExperimentConfig,
    *,
    dry_run: bool = False,
    validate_only: bool = False,
) -> dict[str, list[FoldExecutionResult]]:
    outputs: dict[str, list[FoldExecutionResult]] = {}
    for source, target in (("ADNI", "OASIS"), ("OASIS", "ADNI")):
        direction_config = copy.deepcopy(config)
        direction_config.source_domain = source
        direction_config.target_domain = target
        direction_config.validate()
        outputs[direction_config.direction] = CORALExperimentRunner(
            direction_config
        ).run(dry_run=dry_run, validate_only=validate_only)
    return outputs
