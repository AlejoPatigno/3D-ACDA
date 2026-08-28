"""Typed configuration and fold planning for 3D-ACDA Source-Only."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from acda3d.exceptions import ConfigurationError, PhaseNotImplementedError
from acda3d.experiments.run_manifest import stable_hash
from acda3d.losses import CoreLossWeights
from acda3d.training import FixedEpochTrainingConfig

DISPLAY_NAME = "3D-ACDA Source-Only"
SUPPORTED_DOMAINS = {"ADNI", "OASIS"}


@dataclass
class SourceOnlyPaths:
    artifact_index: Path | None = None
    artifact_root: Path | None = None
    split_root: Path | None = None
    atlas_metadata: Path | None = None
    roi_masks: Path | None = None
    output_root: Path | None = None


@dataclass
class SourceOnlyEvaluation:
    source_validation: bool = True
    target_monitoring: bool = True
    target_monitoring_label: str = "MONITORING ONLY — NOT A TRAINING LOSS"
    export_checkpoints: tuple[str, ...] = ("best_source_f1", "last")


@dataclass
class SourceOnlyExecution:
    overwrite: bool = False
    continue_completed_folds: bool = True
    fail_fast: bool = False
    device: str = "auto"


@dataclass
class SourceOnlyExperimentConfig:
    name: str = "acda3d_source_only"
    display_name: str = DISPLAY_NAME
    method: str = "source_only"
    source_domain: str = "ADNI"
    target_domain: str = "OASIS"
    folds: list[int] = field(default_factory=lambda: list(range(5)))
    seeds: list[int] = field(default_factory=lambda: [42])
    paths: SourceOnlyPaths = field(default_factory=SourceOnlyPaths)
    model: dict[str, Any] = field(default_factory=dict)
    training: FixedEpochTrainingConfig = field(default_factory=FixedEpochTrainingConfig)
    loss_weights: CoreLossWeights = field(default_factory=CoreLossWeights)
    label_smoothing: float = 0.1
    roi_mask_preparation: dict[str, Any] = field(default_factory=dict)
    data_loader: dict[str, Any] = field(default_factory=dict)
    evaluation: SourceOnlyEvaluation = field(default_factory=SourceOnlyEvaluation)
    execution: SourceOnlyExecution = field(default_factory=SourceOnlyExecution)
    config_path: Path | None = field(default=None, repr=False)

    def validate(self) -> None:
        if self.method != "source_only":
            raise PhaseNotImplementedError(f"Method {self.method!r} is not implemented in Phase 9.")
        if self.display_name != DISPLAY_NAME:
            raise ConfigurationError(f"Source-only display_name must be {DISPLAY_NAME!r}.")
        self._validate_common()

    def _validate_common(self) -> None:
        if self.source_domain not in SUPPORTED_DOMAINS or self.target_domain not in SUPPORTED_DOMAINS:
            raise ConfigurationError("Source and target must be ADNI or OASIS.")
        if self.source_domain == self.target_domain:
            raise ConfigurationError("Source and target domains must differ.")
        if not self.folds or any(fold not in range(5) for fold in self.folds):
            raise ConfigurationError("Source-only folds must be a non-empty subset of 0..4.")
        if len(set(self.folds)) != len(self.folds) or not self.seeds:
            raise ConfigurationError("Folds must be unique and at least one seed is required.")
        if self.model.get("name") != "3D-ACDA" or self.model.get("contextual_encoder") is not False:
            raise ConfigurationError("Source-only requires explicit non-contextual 3D-ACDA.")
        if int(self.model.get("num_classes", 0)) != 3 or int(self.model.get("num_rois", 0)) <= 0:
            raise ConfigurationError("Source-only requires three classes and a positive ROI count.")
        self.training.validate()
        self.loss_weights.validate()
        if self.loss_weights.effective("warm") != {
            "classification": 0.1,
            "concept_classification": 1.0,
            "prediction_consistency": 0.0,
            "concept_supervision": 0.5,
            "anatomical_consistency": 0.2,
        }:
            raise ConfigurationError("Resolved warm-up coefficients do not match the canonical execution.")
        if self.evaluation.target_monitoring_label != "MONITORING ONLY — NOT A TRAINING LOSS":
            raise ConfigurationError("Target monitoring label does not match the approved contract.")
        required = ("artifact_index", "split_root", "atlas_metadata", "roi_masks", "output_root")
        if any(getattr(self.paths, name) is None for name in required):
            raise ConfigurationError(f"Source-only paths are required: {required}.")

    @property
    def direction(self) -> str:
        return f"{self.source_domain}_to_{self.target_domain}"

    def resolved_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("config_path", None)
        return _serializable(payload)

    def sha256(self) -> str:
        return stable_hash(self.resolved_dict())

    def run_dir(self, fold: int, seed: int) -> Path:
        assert self.paths.output_root is not None
        return (
            self.paths.output_root / "source_only" / self.direction / f"seed_{seed}" / f"fold_{fold}"
        )


def _reference_path(value: str | Path, config_path: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, config_path.parent / path, config_path.parents[1] / path]
    return next((candidate.resolve() for candidate in candidates if candidate.exists()), candidates[0].resolve())


def _serializable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


def _data_path(value: Any, config_path: Path) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()


def load_source_only_config(
    path: str | Path,
    *,
    overrides: dict[str, Any] | None = None,
    validate: bool = True,
) -> SourceOnlyExperimentConfig:
    config_path = Path(path).resolve()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    experiment = dict(payload.get("experiment") or {})
    paths_payload = dict(payload.get("paths") or {})
    model_section = dict(payload.get("model") or {})
    training_section = dict(payload.get("training") or {})
    model_reference = model_section.pop("config", None)
    training_reference = training_section.pop("config", None)
    model_payload: dict[str, Any] = {}
    if model_reference:
        model_payload.update(
            (yaml.safe_load(_reference_path(model_reference, config_path).read_text(encoding="utf-8")) or {}).get("model", {})
        )
    model_payload.update(model_section)
    approved_training: dict[str, Any] = {}
    approved_losses: dict[str, Any] = {}
    approved_masks: dict[str, Any] = {}
    if training_reference:
        referenced = yaml.safe_load(
            _reference_path(training_reference, config_path).read_text(encoding="utf-8")
        ) or {}
        approved_training = dict(referenced.get("training") or {})
        approved_losses = dict(referenced.get("losses") or {})
        approved_masks = dict(referenced.get("roi_mask_preparation") or {})
    if training_section.get("early_stopping") is True:
        raise ConfigurationError("Early stopping is forbidden for source-only experiments.")
    optimizer = dict(approved_training.get("optimizer") or {})
    gradient = dict(approved_training.get("gradient") or {})
    checkpoint = dict(approved_training.get("checkpoint") or {})
    evaluation_training = dict(approved_training.get("evaluation") or {})
    resolved_training = FixedEpochTrainingConfig(
        warmup_epochs=int(approved_training.get("warmup_epochs", 20)),
        full_epochs=int(approved_training.get("full_epochs", 30)),
        learning_rate=float(optimizer.get("learning_rate", 3e-4)),
        weight_decay=float(optimizer.get("weight_decay", 1e-4)),
        gradient_clip_norm=float(gradient.get("clipping_value", 5.0)),
        mixed_precision=bool(approved_training.get("mixed_precision", False)),
        fail_on_nonfinite_loss=bool(gradient.get("fail_on_nonfinite_loss", True)),
        checkpoint_every=int(checkpoint.get("every_epochs", 5)),
        source_evaluation_every=int(evaluation_training.get("source_every_epochs", 1)),
        target_monitoring_every=int(evaluation_training.get("target_monitoring_every_epochs", 1)),
        target_monitoring_enabled=bool(evaluation_training.get("target_monitoring_enabled", True)),
        save_last=bool(checkpoint.get("save_last", True)),
        save_best_source_f1=bool(checkpoint.get("save_best_source_f1", True)),
        device=str((payload.get("execution") or {}).get("device", "auto")),
        seed=int((experiment.get("seeds") or [experiment.get("seed", 42)])[0]),
    )
    loss_weights = CoreLossWeights(
        classification=float(approved_losses.get("classification_weight", 1.0)),
        concept_classification=float(approved_losses.get("concept_classification_weight", 1.0)),
        prediction_consistency=float(approved_losses.get("prediction_consistency_weight", 0.1)),
        concept_supervision=float(approved_losses.get("concept_supervision_weight", 0.5)),
        anatomical_consistency=float(approved_losses.get("anatomical_consistency_weight", 0.2)),
        warm_classification=float(approved_losses.get("warm_classification_multiplier", 0.1)),
        warm_concept_classification=float(approved_losses.get("warm_concept_classification_multiplier", 1.0)),
        warm_prediction_consistency=float(approved_losses.get("warm_prediction_consistency_multiplier", 0.0)),
        warm_concept_supervision=float(approved_losses.get("warm_concept_supervision_multiplier", 1.0)),
        warm_anatomical_consistency=float(approved_losses.get("warm_anatomical_consistency_multiplier", 1.0)),
    )
    evaluation = dict(payload.get("evaluation") or {})
    execution = dict(payload.get("execution") or {})
    config = SourceOnlyExperimentConfig(
        name=str(experiment.get("name", "acda3d_source_only")),
        display_name=str(experiment.get("display_name", DISPLAY_NAME)),
        method=str(experiment.get("method", "source_only")),
        source_domain=str(experiment.get("source_domain", "ADNI")).upper(),
        target_domain=str(experiment.get("target_domain", "OASIS")).upper(),
        folds=[int(value) for value in experiment.get("folds", [0, 1, 2, 3, 4])],
        seeds=[int(value) for value in experiment.get("seeds", [42])],
        paths=SourceOnlyPaths(**{key: _data_path(value, config_path) for key, value in paths_payload.items() if key in SourceOnlyPaths.__dataclass_fields__}),
        model=model_payload,
        training=resolved_training,
        loss_weights=loss_weights,
        label_smoothing=float(approved_losses.get("label_smoothing", 0.1)),
        roi_mask_preparation=approved_masks,
        data_loader=dict(payload.get("data_loader") or {}),
        evaluation=SourceOnlyEvaluation(
            source_validation=bool(evaluation.get("source_validation", True)),
            target_monitoring=bool(evaluation.get("target_monitoring", True)),
            target_monitoring_label=str(evaluation.get("target_monitoring_label", "MONITORING ONLY — NOT A TRAINING LOSS")),
            export_checkpoints=tuple(evaluation.get("export_checkpoints", ["best_source_f1", "last"])),
        ),
        execution=SourceOnlyExecution(**{key: value for key, value in execution.items() if key in SourceOnlyExecution.__dataclass_fields__}),
        config_path=config_path,
    )
    if overrides:
        for key, value in overrides.items():
            if value is None:
                continue
            if hasattr(config.paths, key):
                setattr(config.paths, key, Path(value).resolve())
            elif hasattr(config.execution, key):
                setattr(config.execution, key, value)
            elif hasattr(config, key):
                setattr(config, key, value)
    if validate:
        config.validate()
    return config
