"""Typed YAML configuration for PADA-3DACB."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pada3dacb.exceptions import ConfigurationError, UnsupportedExperimentError
from pada3dacb.paths import is_forbidden_hardcoded_path, resolve_path

PROPOSED_MODEL_NAME = "PADA-3DACB"
ALLOWED_METHODS = {"source_only", "coral", "mmd", "cdan", "prototype_pseudo", "baseline"}
ALLOWED_COHORTS = {"ADNI", "OASIS"}


def _as_mapping(value: Any, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"Configuration section '{section}' must be a mapping.")
    return value


def _clean_dict(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if dataclasses.is_dataclass(value):
        return _clean_dict(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): _clean_dict(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_clean_dict(v) for v in value]
    return value


@dataclass
class PathsConfig:
    input_root: Path | None = None
    output_root: Path | None = None
    temp_root: Path | None = None
    model_ready_data: Path | None = None
    precomputed_artifacts: Path | None = None
    runs_root: Path | None = None
    analysis_root: Path | None = None
    model_ready_output: Path | None = None
    missing_report_dir: Path | None = None
    precompute_run_dir: Path | None = None
    baseline_runs_root: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path | None) -> PathsConfig:
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: resolve_path(v, base_dir) for k, v in data.items() if k in fields})


@dataclass
class CohortConfig:
    root: Path | None = None
    metadata_csv: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path | None) -> CohortConfig:
        return cls(
            root=resolve_path(data.get("root"), base_dir),
            metadata_csv=resolve_path(data.get("metadata_csv"), base_dir),
        )


@dataclass
class DataConfig:
    adni: CohortConfig = field(default_factory=CohortConfig)
    oasis: CohortConfig = field(default_factory=CohortConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path | None) -> DataConfig:
        return cls(
            adni=CohortConfig.from_dict(_as_mapping(data.get("adni"), "data.adni"), base_dir),
            oasis=CohortConfig.from_dict(_as_mapping(data.get("oasis"), "data.oasis"), base_dir),
        )


@dataclass
class AtlasConfig:
    raw_path: Path | None = None
    prepared_path: Path | None = None
    output_dir: Path | None = None
    resampled_path: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path | None) -> AtlasConfig:
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: resolve_path(v, base_dir) for k, v in data.items() if k in fields})


@dataclass
class ModelConfig:
    name: str = PROPOSED_MODEL_NAME
    contextual_encoder: bool = False
    num_classes: int = 3
    num_rois: int = 102

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in dataclasses.fields(cls)}})


@dataclass
class TrainingConfig:
    warmup_epochs: int = 5
    full_epochs: int = 50
    early_stopping: bool = False
    batch_size: int = 16
    learning_rate: float = 0.0001
    weight_decay: float = 0.0001
    checkpoint_every: int = 5
    evaluate_source_every: int = 1
    evaluate_target_every: int = 1
    mixed_precision: bool = True
    resume: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainingConfig:
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in dataclasses.fields(cls)}})


@dataclass
class MonitoringConfig:
    source_metrics: bool = True
    target_metrics: bool = True
    target_metrics_label: str = "MONITORING ONLY - NOT A TRAINING LOSS"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MonitoringConfig:
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in dataclasses.fields(cls)}})


@dataclass
class ExperimentConfig:
    name: str = "pada3dacb_experiment"
    method: str = "prototype_pseudo"
    source_domain: str = "ADNI"
    target_domain: str = "OASIS"
    seed: int = 42
    fold: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in dataclasses.fields(cls)}})


@dataclass
class ProjectConfig:
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    data: DataConfig = field(default_factory=DataConfig)
    atlas: AtlasConfig = field(default_factory=AtlasConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    adaptation: dict[str, Any] = field(default_factory=dict)
    baseline: dict[str, Any] = field(default_factory=dict)
    config_path: Path | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        base_dir: Path | None = None,
        config_path: Path | None = None,
    ) -> ProjectConfig:
        return cls(
            experiment=ExperimentConfig.from_dict(_as_mapping(data.get("experiment"), "experiment")),
            paths=PathsConfig.from_dict(_as_mapping(data.get("paths"), "paths"), base_dir),
            data=DataConfig.from_dict(_as_mapping(data.get("data"), "data"), base_dir),
            atlas=AtlasConfig.from_dict(_as_mapping(data.get("atlas"), "atlas"), base_dir),
            model=ModelConfig.from_dict(_as_mapping(data.get("model"), "model")),
            training=TrainingConfig.from_dict(_as_mapping(data.get("training"), "training")),
            monitoring=MonitoringConfig.from_dict(_as_mapping(data.get("monitoring"), "monitoring")),
            adaptation=_as_mapping(data.get("adaptation"), "adaptation"),
            baseline=_as_mapping(data.get("baseline"), "baseline"),
            config_path=config_path,
        )

    def validate(self) -> None:
        method = self.experiment.method
        if method not in ALLOWED_METHODS:
            raise UnsupportedExperimentError(f"Unsupported experiment method: {method}")

        if self.experiment.source_domain not in ALLOWED_COHORTS:
            raise ConfigurationError(f"Unknown source cohort: {self.experiment.source_domain}")
        if self.experiment.target_domain not in ALLOWED_COHORTS:
            raise ConfigurationError(f"Unknown target cohort: {self.experiment.target_domain}")
        if self.experiment.source_domain == self.experiment.target_domain:
            raise ConfigurationError("Cross-domain experiments require different source and target domains.")

        if self.model.contextual_encoder:
            raise ConfigurationError(
                "The contextual ROI encoder belongs to the excluded architecture and cannot be enabled in PADA-3DACB."
            )
        if method != "baseline" and self.model.name != PROPOSED_MODEL_NAME:
            raise ConfigurationError(
                f"Proposed-model experiments must use model.name == {PROPOSED_MODEL_NAME!r}."
            )
        if method == "baseline" and self.model.name in {"PADA-3DACB-Lite", "PADA-3DACB-Full", "Lite", "Full"}:
            raise ConfigurationError(f"Invalid public model name: {self.model.name}")

        if self.training.early_stopping:
            raise ConfigurationError(
                "Early stopping is disabled. PADA-3DACB experiments use a fixed number of epochs."
            )
        if self.training.warmup_epochs < 0:
            raise ConfigurationError("training.warmup_epochs must be >= 0.")
        if self.training.full_epochs <= 0:
            raise ConfigurationError("training.full_epochs must be > 0.")
        if self.training.batch_size <= 0:
            raise ConfigurationError("training.batch_size must be > 0.")
        if self.training.checkpoint_every <= 0:
            raise ConfigurationError("training.checkpoint_every must be > 0.")
        if self.training.evaluate_source_every <= 0:
            raise ConfigurationError("training.evaluate_source_every must be > 0.")
        if self.training.evaluate_target_every <= 0:
            raise ConfigurationError("training.evaluate_target_every must be > 0.")

        for key, value in self.to_dict(include_none=True).items():
            if _contains_forbidden(value):
                raise ConfigurationError(f"Configuration contains a forbidden hard-coded path at {key}.")

    def to_dict(self, *, include_none: bool = False) -> dict[str, Any]:
        data = _clean_dict(
            {
                "experiment": self.experiment,
                "paths": self.paths,
                "data": self.data,
                "atlas": self.atlas,
                "model": self.model,
                "training": self.training,
                "monitoring": self.monitoring,
                "adaptation": self.adaptation,
                "baseline": self.baseline,
            }
        )
        if include_none:
            return data
        return _drop_none(data)

    def sha256(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def short_hash(self, length: int = 12) -> str:
        if length <= 0:
            raise ConfigurationError("Hash length must be positive.")
        return self.sha256()[:length]

    def save_resolved(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as stream:
            yaml.safe_dump(self.to_dict(), stream, sort_keys=True)
        return target


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _drop_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none(v) for v in value]
    return value


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_forbidden(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden(v) for v in value)
    return is_forbidden_hardcoded_path(value)


def load_config(path: str | Path, *, validate: bool = True) -> ProjectConfig:
    config_path = Path(path).expanduser().resolve(strict=False)
    with config_path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ConfigurationError("Top-level configuration must be a mapping.")
    config = ProjectConfig.from_dict(data, base_dir=config_path.parent, config_path=config_path)
    if validate:
        config.validate()
    return config
