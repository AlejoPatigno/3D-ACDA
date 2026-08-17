"""Typed YAML configuration for PADA-3DACB."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pada3dacb.binary import BINARY_CLASS_ORDER, BINARY_CLASS_TO_INDEX, BINARY_MAPPING_CONTRACT
from pada3dacb.exceptions import ConfigurationError, UnsupportedExperimentError
from pada3dacb.paths import is_forbidden_hardcoded_path, resolve_path

PROPOSED_MODEL_NAME = "PADA-3DACB"
ALLOWED_METHODS = {"source_only", "coral", "mmd", "cdan", "prototype_pseudo", "baseline", "ablation"}
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
    if isinstance(value, (list, tuple)):
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
    input_channels: int = 1
    encoder: dict[str, Any] = field(default_factory=dict)
    tokenizer: dict[str, Any] = field(default_factory=dict)
    token_processing: dict[str, Any] = field(default_factory=dict)
    aggregator: dict[str, Any] = field(default_factory=dict)
    classification_head: dict[str, Any] = field(default_factory=dict)
    concept_bottleneck: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in dataclasses.fields(cls)}})


@dataclass
class TrainingConfig:
    warmup_epochs: int = 20
    full_epochs: int = 30
    early_stopping: bool = False
    batch_size: int = 16
    learning_rate: float = 0.0003
    weight_decay: float = 0.0001
    checkpoint_every: int = 5
    evaluate_source_every: int = 1
    evaluate_target_every: int = 1
    mixed_precision: bool = False
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
    task_id: str | None = None
    task_type: str | None = None
    class_order: tuple[str, ...] | None = None
    class_ids: dict[str, int] | None = None
    mapping_contract: str | None = None
    split_disposition: str | None = None
    methods: tuple[str, ...] = ()
    ablations: tuple[str, ...] = ()
    authorization: dict[str, Any] = field(default_factory=dict)
    historical_supersession_marker: str | None = None
    config_path: Path | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        base_dir: Path | None = None,
        config_path: Path | None = None,
    ) -> ProjectConfig:
        task_value = data.get("task_id", data.get("task"))
        task_id = None if task_value is None else str(task_value).strip().lower()
        if task_id in {"cn_vs_impaired", "cn_vs_impaired_task"}:
            task_id = "cn_vs_impaired"
        task_type = data.get("task_type")
        if task_id == "cn_vs_impaired" and task_type is None:
            task_type = "binary_classification"
        raw_model = _as_mapping(data.get("model"), "model")
        if task_id == "cn_vs_impaired" and "num_classes" not in raw_model:
            raw_model = {**raw_model, "num_classes": 2}
        raw_order = data.get("class_order")
        raw_ids = data.get("class_ids")
        return cls(
            experiment=ExperimentConfig.from_dict(_as_mapping(data.get("experiment"), "experiment")),
            paths=PathsConfig.from_dict(_as_mapping(data.get("paths"), "paths"), base_dir),
            data=DataConfig.from_dict(_as_mapping(data.get("data"), "data"), base_dir),
            atlas=AtlasConfig.from_dict(_as_mapping(data.get("atlas"), "atlas"), base_dir),
            model=ModelConfig.from_dict(raw_model),
            training=TrainingConfig.from_dict(_as_mapping(data.get("training"), "training")),
            monitoring=MonitoringConfig.from_dict(_as_mapping(data.get("monitoring"), "monitoring")),
            adaptation=_as_mapping(data.get("adaptation"), "adaptation"),
            baseline=_as_mapping(data.get("baseline"), "baseline"),
            task_id=task_id,
            task_type=None if task_type is None else str(task_type),
            class_order=None if raw_order is None else tuple(str(item) for item in raw_order),
            class_ids=None if raw_ids is None else {str(key): int(value) for key, value in raw_ids.items()},
            mapping_contract=data.get("mapping_contract"),
            split_disposition=data.get("split_disposition"),
            methods=tuple(str(item) for item in data.get("methods", ())),
            ablations=tuple(str(item) for item in data.get("ablations", ())),
            authorization=dict(_as_mapping(data.get("authorization"), "authorization")),
            historical_supersession_marker=data.get("historical_supersession_marker"),
            config_path=config_path,
        )

    def validate(self) -> None:
        method = self.experiment.method
        if method not in ALLOWED_METHODS:
            raise UnsupportedExperimentError(f"Unsupported experiment method: {method}")

        if self.task_id == "cn_vs_impaired":
            if self.task_type != "binary_classification":
                raise ConfigurationError("CN_vs_Impaired requires task_type='binary_classification'.")
            if self.class_order != BINARY_CLASS_ORDER or self.class_ids != BINARY_CLASS_TO_INDEX:
                raise ConfigurationError("CN_vs_Impaired requires the fixed CN=0, Impaired=1 class order.")
            if self.mapping_contract != BINARY_MAPPING_CONTRACT:
                raise ConfigurationError("CN_vs_Impaired requires the Phase 18B mapping contract.")
            if self.model.num_classes != len(BINARY_CLASS_ORDER):
                raise ConfigurationError("CN_vs_Impaired model configuration must derive num_classes=2 from the task.")
            if self.split_disposition != "REGENERATE_BINARY_SPLITS_REQUIRED":
                raise ConfigurationError("Binary publication configuration must require binary split regeneration.")
            if (
                self.authorization.get("freeze_approved") is not False
                or self.authorization.get("real_execution_authorized") is not False
                or self.authorization.get("publication_authorized") is not False
                or self.authorization.get("phase_19_forbidden") is not True
            ):
                raise ConfigurationError("Phase 18B authorization flags must remain fail-closed.")

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
                "task_id": self.task_id,
                "task_type": self.task_type,
                "class_order": self.class_order,
                "class_ids": self.class_ids,
                "mapping_contract": self.mapping_contract,
                "split_disposition": self.split_disposition,
                "methods": self.methods,
                "ablations": self.ablations,
                "authorization": self.authorization,
                "historical_supersession_marker": self.historical_supersession_marker,
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
