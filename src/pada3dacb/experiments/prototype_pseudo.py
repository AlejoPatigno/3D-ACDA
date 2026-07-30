"""Configuration and orchestration for canonical PADA-3DACB prototype/pseudo-label adaptation."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any

import torch
import yaml

from pada3dacb.data.loaders import (
    DataLoaderConfig,
    build_source_train_loader,
    build_source_validation_loader,
    build_target_adaptation_loader,
    build_target_evaluation_loader,
)
from pada3dacb.exceptions import (
    ConfigurationError,
    ExperimentValidationError,
    PhaseNotImplementedError,
)
from pada3dacb.experiments.coral import (
    CORALExperimentRunner,
    PreparedCORALFold,
    prepare_coral_fold_inputs,
)
from pada3dacb.experiments.run_manifest import create_run_manifest, stable_hash
from pada3dacb.experiments.runner import FoldExecutionResult
from pada3dacb.experiments.source_only import SourceOnlyExperimentConfig, load_source_only_config
from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.training import UDATrainer
from pada3dacb.training.runtime import validate_nonempty_loader
from pada3dacb.training.uda_trainer import ProposedPrototypePseudoAdaptationMethod

PROTOTYPE_PSEUDO_DISPLAY_NAME = "PADA-3DACB"
_ALLOWED_TOP_LEVEL_KEYS = {
    "experiment",
    "paths",
    "model",
    "training",
    "adaptation",
    "data_loader",
    "evaluation",
    "execution",
}
_ALLOWED_ADAPTATION_KEYS = {"name", "feature", "active_during_warmup", "prototype", "pseudo_label"}
_CANONICAL_TRAINING = {
    "warmup_epochs": 5,
    "full_epochs": 50,
    "learning_rate": 1e-4,
    "weight_decay": 1e-4,
    "seed": 42,
}


def _finite_float(value: Any, field_name: str) -> float:
    if value is None:
        raise ConfigurationError(f"Prototype-pseudo {field_name} must be explicitly resolved for real runs.")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Prototype-pseudo {field_name} must be a finite number.") from exc
    if not math.isfinite(parsed):
        raise ConfigurationError(f"Prototype-pseudo {field_name} must be finite.")
    return parsed


@dataclass(frozen=True)
class PrototypePseudoAdaptationExperimentConfig:
    name: str = "prototype_pseudo"
    feature: str = "z_and_concept_logits"
    active_during_warmup: bool = False
    prototype: dict[str, float] = field(default_factory=dict)
    pseudo_label: dict[str, float | str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.name != "prototype_pseudo":
            raise PhaseNotImplementedError(f"Adaptation method {self.name!r} is not implemented in Phase 13.")
        if self.feature != "z_and_concept_logits":
            raise ConfigurationError("Prototype-pseudo adaptation must use z_and_concept_logits.")
        if self.active_during_warmup:
            raise ConfigurationError("Prototype-pseudo adaptation must be inactive during warm-up.")
        required_proto = {"lambda_proto", "proto_margin", "lambda_sep"}
        required_pl = {"lambda_pl", "tau_p", "probability_source"}
        if set(self.prototype) != required_proto:
            raise ConfigurationError(f"Prototype config fields must be {sorted(required_proto)}.")
        if set(self.pseudo_label) != required_pl:
            raise ConfigurationError(f"Pseudo-label config fields must be {sorted(required_pl)}.")
        for key in required_proto:
            value = _finite_float(self.prototype[key], f"prototype.{key}")
            if value < 0:
                raise ConfigurationError(f"prototype.{key} must be non-negative.")
        for key in ("lambda_pl", "tau_p"):
            value = _finite_float(self.pseudo_label[key], f"pseudo_label.{key}")
            if value < 0:
                raise ConfigurationError(f"pseudo_label.{key} must be non-negative.")
        tau = float(self.pseudo_label["tau_p"])
        if tau > 1:
            raise ConfigurationError("pseudo_label.tau_p must be in [0, 1].")
        if self.pseudo_label["probability_source"] != "concept_logits":
            raise ConfigurationError("Pseudo-labels must be created from concept_logits.")

    @property
    def lambda_proto(self) -> float:
        return float(self.prototype["lambda_proto"])

    @property
    def lambda_pl(self) -> float:
        return float(self.pseudo_label["lambda_pl"])

    @property
    def tau_p(self) -> float:
        return float(self.pseudo_label["tau_p"])

    @property
    def proto_margin(self) -> float:
        return float(self.prototype["proto_margin"])

    @property
    def lambda_sep(self) -> float:
        return float(self.prototype["lambda_sep"])

    def resolved_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "feature": self.feature,
            "active_during_warmup": self.active_during_warmup,
            "prototype": dict(self.prototype),
            "pseudo_label": dict(self.pseudo_label),
            "stateful_adaptation": "none",
        }

    def method_kwargs(self, num_classes: int) -> dict[str, float | int]:
        return {
            "lambda_proto": self.lambda_proto,
            "lambda_pl": self.lambda_pl,
            "tau_p": self.tau_p,
            "proto_margin": self.proto_margin,
            "lambda_sep": self.lambda_sep,
            "num_classes": int(num_classes),
        }

    def sha256(self) -> str:
        return stable_hash(self.resolved_dict())


@dataclass
class PrototypePseudoExperimentConfig(SourceOnlyExperimentConfig):
    adaptation: PrototypePseudoAdaptationExperimentConfig = field(default_factory=PrototypePseudoAdaptationExperimentConfig)

    def validate(self) -> None:
        if self.method != "prototype_pseudo":
            raise PhaseNotImplementedError(f"Method {self.method!r} is not implemented in Phase 13.")
        if self.display_name != PROTOTYPE_PSEUDO_DISPLAY_NAME:
            raise ConfigurationError(f"Prototype-pseudo display_name must be {PROTOTYPE_PSEUDO_DISPLAY_NAME!r}.")
        self._validate_common()
        self.adaptation.validate()
        if self.training.warmup_epochs != 5 or self.training.full_epochs != 50:
            raise ConfigurationError("Prototype-pseudo requires n_epochs_warm=5 and n_epochs_full=50.")
        if self.training.learning_rate != 1e-4 or self.training.weight_decay != 1e-4:
            raise ConfigurationError("Prototype-pseudo requires lr=1e-4 and weight_decay=1e-4.")
        if int(self.data_loader.get("batch_size", 0)) != 16:
            raise ConfigurationError("Prototype-pseudo requires batch_size=16.")

    def resolved_dict(self) -> dict[str, Any]:
        value = super().resolved_dict()
        value["adaptation"] = self.adaptation.resolved_dict()
        return value

    def run_dir(self, fold: int, seed: int) -> Path:
        assert self.paths.output_root is not None
        return (
            self.paths.output_root
            / "prototype_pseudo"
            / self.direction
            / f"seed_{seed}"
            / f"prototype_pseudo_{self.adaptation.sha256()[:16]}"
            / f"fold_{fold}"
        )


def load_prototype_pseudo_config(path: str | Path, *, overrides: dict[str, Any] | None = None) -> PrototypePseudoExperimentConfig:
    overrides = dict(overrides or {})
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    unsupported_top = sorted(set(payload) - _ALLOWED_TOP_LEVEL_KEYS)
    if unsupported_top:
        raise ConfigurationError(f"Unsupported Phase 13 configuration sections: {unsupported_top}.")
    base = load_source_only_config(path, overrides=overrides, validate=False)
    raw = dict(payload.get("adaptation") or {})
    unsupported = sorted(set(raw) - _ALLOWED_ADAPTATION_KEYS)
    if unsupported:
        raise ConfigurationError(f"Unsupported prototype-pseudo adaptation fields: {unsupported}.")
    prototype = dict(raw.get("prototype") or {})
    pseudo_label = dict(raw.get("pseudo_label") or {})
    adaptation = PrototypePseudoAdaptationExperimentConfig(
        name=str(raw.get("name", "prototype_pseudo")),
        feature=str(raw.get("feature", "z_and_concept_logits")),
        active_during_warmup=bool(raw.get("active_during_warmup", False)),
        prototype={
            "lambda_proto": _finite_float(prototype.get("lambda_proto"), "prototype.lambda_proto"),
            "proto_margin": _finite_float(prototype.get("proto_margin"), "prototype.proto_margin"),
            "lambda_sep": _finite_float(prototype.get("lambda_sep"), "prototype.lambda_sep"),
        },
        pseudo_label={
            "lambda_pl": _finite_float(pseudo_label.get("lambda_pl"), "pseudo_label.lambda_pl"),
            "tau_p": _finite_float(pseudo_label.get("tau_p"), "pseudo_label.tau_p"),
            "probability_source": str(pseudo_label.get("probability_source", "concept_logits")),
        },
    )
    inherited = {item.name: getattr(base, item.name) for item in fields(SourceOnlyExperimentConfig)}
    inherited["training"] = replace(
        base.training,
        warmup_epochs=_CANONICAL_TRAINING["warmup_epochs"],
        full_epochs=_CANONICAL_TRAINING["full_epochs"],
        learning_rate=_CANONICAL_TRAINING["learning_rate"],
        weight_decay=_CANONICAL_TRAINING["weight_decay"],
        seed=_CANONICAL_TRAINING["seed"],
    )
    inherited["data_loader"] = {**base.data_loader, "batch_size": 16}
    config = PrototypePseudoExperimentConfig(**inherited, adaptation=adaptation)
    config.validate()
    return config


class PrototypePseudoExperimentRunner(CORALExperimentRunner):
    method_name = "prototype_pseudo"
    display_name = PROTOTYPE_PSEUDO_DISPLAY_NAME
    loss_name = "prototype_pseudo"

    def __init__(self, config: PrototypePseudoExperimentConfig):
        config.validate()
        self.config = config

    def _prepare_fold(self, fold: int) -> PreparedCORALFold:
        return prepare_coral_fold_inputs(self.config, fold)

    def _build_adaptation_method(self):
        return ProposedPrototypePseudoAdaptationMethod(
            **self.config.adaptation.method_kwargs(int(self.config.model.get("num_classes", 3)))
        )

    def _loaders(self, prepared: PreparedCORALFold, seed: int):
        values = {
            key: value
            for key, value in self.config.data_loader.items()
            if key in DataLoaderConfig.__dataclass_fields__
        }
        smallest_train_partition = min(
            len(prepared.base.source_train_dataset), len(prepared.target_adaptation_dataset)
        )
        if smallest_train_partition < int(values.get("batch_size", 1)):
            values["batch_size"] = max(2, smallest_train_partition)
        loader_config = DataLoaderConfig(**values)
        base = prepared.base
        source_train = build_source_train_loader(base.source_train_dataset, loader_config, seed=seed)
        target_adaptation = build_target_adaptation_loader(prepared.target_adaptation_dataset, loader_config, seed=seed + 1)
        source_validation = build_source_validation_loader(base.source_validation_dataset, loader_config, seed=seed)
        target_evaluation = (
            build_target_evaluation_loader(base.target_evaluation_dataset, loader_config, seed=seed)
            if base.target_evaluation_dataset is not None
            else None
        )
        validate_nonempty_loader(source_train, "source_train_loader")
        validate_nonempty_loader(target_adaptation, "target_adaptation_loader")
        validate_nonempty_loader(source_validation, "source_validation_loader")
        if loader_config.batch_size < 2:
            raise ExperimentValidationError("Prototype-pseudo loaders require batch_size >= 2.")
        if target_evaluation is not None:
            validate_nonempty_loader(target_evaluation, "target_evaluation_loader")
        return source_train, target_adaptation, source_validation, target_evaluation

    def _manifest(self, prepared: PreparedCORALFold, fold: int, seed: int, model: torch.nn.Module, feature_shape: tuple[int, ...], mask_hash: str, source_steps: int, target_steps: int) -> dict[str, Any]:
        base = prepared.base
        adaptation = self.config.adaptation
        return create_run_manifest(
            experiment_name=self.config.name, display_name=self.config.display_name, method="prototype_pseudo",
            source_domain=self.config.source_domain, target_domain=self.config.target_domain, direction=self.config.direction, fold=fold, seed=seed,
            source_split_assignment_hash=base.source_assignment_hash, target_split_assignment_hash=base.target_assignment_hash, split_assignment_hash=base.protocol["split_assignment_hash"],
            target_adaptation_assignment_hash=prepared.target_adaptation_assignment_hash, target_evaluation_assignment_hash=prepared.target_evaluation_assignment_hash,
            artifact_index_hash=base.artifact_index_hash, atlas_hash=base.atlas_hash, roi_order_hash=base.roi_order_hash,
            model_configuration_hash=stable_hash(self.config.model), training_configuration_hash=stable_hash(asdict(self.config.training)), roi_mask_preparation_hash=mask_hash,
            feature_shape=list(feature_shape), experiment_hash=self.config.sha256(), model_parameter_count=sum(p.numel() for p in model.parameters()),
            adaptation_method="prototype_pseudo", adaptation_feature="z_and_concept_logits", adaptation_configuration_hash=adaptation.sha256(),
            lambda_proto=adaptation.lambda_proto, lambda_pl=adaptation.lambda_pl, tau_p=adaptation.tau_p, proto_margin=adaptation.proto_margin, lambda_sep=adaptation.lambda_sep,
            source_train_count=len(base.source_train_dataset), target_adaptation_count=len(prepared.target_adaptation_dataset), source_steps_per_epoch=source_steps,
            expected_target_cycles_per_epoch=(source_steps - 1) // target_steps, warmup_adaptation_active=False, full_adaptation_active=True,
            target_training_labels_available=False, target_concept_or_anatomy_used_for_adaptation=False, stateful_adaptation="none",
        )

    def _completed_reuse(self, run_dir: Path, experiment_hash: str, prepared: PreparedCORALFold):
        from pada3dacb.experiments.runner import SourceOnlyExperimentRunner

        result = SourceOnlyExperimentRunner._completed_reuse(self, run_dir, experiment_hash)
        if result is None:
            return None
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "method": "prototype_pseudo",
            "adaptation_method": "prototype_pseudo",
            "source_split_assignment_hash": prepared.base.source_assignment_hash,
            "target_adaptation_assignment_hash": prepared.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": prepared.target_evaluation_assignment_hash,
        }
        mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
        if mismatches:
            raise ExperimentValidationError(f"Completed prototype-pseudo fold has incompatible fields: {sorted(mismatches)}.")
        return result

    def _adaptation_summary(self, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
        full = [row for row in history_rows if row["stage"] == "full"]
        final = history_rows[-1]
        return {
            "adaptation_method": "prototype_pseudo",
            "final_train_prototype_pseudo_loss": final["train/prototype_pseudo_loss"],
            "final_weighted_prototype_pseudo_loss": final["train/weighted_prototype_pseudo_loss"],
            "final_train_prototype_raw": final["train/prototype_raw"],
            "final_train_pseudo_label_raw": final["train/pseudo_label_raw"],
            "mean_train_prototype_pseudo_loss_full_stage": sum(row["train/prototype_pseudo_loss"] for row in full) / len(full),
            "target_batch_cycles": sum(row["train/target_batch_cycles"] for row in full),
        }

    def _experiment_manifest_fields(self) -> dict[str, Any]:
        return {"attempted_adaptation_configurations": [self.config.adaptation.resolved_dict()]}

    def run_fold(self, fold: int, seed: int, *, dry_run: bool = False, validate_only: bool = False, resume_from: str | Path | None = None, interrupt_after_epoch: int | None = None):
        if dry_run:
            prepared = self._prepare_fold(fold)
            source_train, target_adaptation, _source_validation, _target_evaluation = self._loaders(prepared, seed)
            base = prepared.base
            return FoldExecutionResult(
                self.config.direction,
                seed,
                fold,
                "PENDING",
                self.config.run_dir(fold, seed),
                self.config.sha256(),
                {
                    "method": "prototype_pseudo",
                    "display_name": self.config.display_name,
                    "planned_source_train": len(base.source_train_dataset),
                    "planned_source_validation": len(base.source_validation_dataset),
                    "planned_target_adaptation": len(prepared.target_adaptation_dataset),
                    "planned_target_evaluation": len(base.target_evaluation_dataset or []),
                    "source_steps_per_epoch": len(source_train),
                    "target_steps_per_cycle": len(target_adaptation),
                    "target_training_labels_available": False,
                },
            )
        if not validate_only:
            return super().run_fold(fold, seed, dry_run=dry_run, validate_only=validate_only, resume_from=resume_from, interrupt_after_epoch=interrupt_after_epoch)
        prepared = self._prepare_fold(fold)
        base = prepared.base
        source_train, target_adaptation, _source_validation, _target_evaluation = self._loaders(prepared, seed)
        run_dir = self.config.run_dir(fold, seed)
        experiment_hash = self.config.sha256()
        model, feature_masks, _feature_shape, _mask_hash = self._model_and_masks(base)
        loss_fn = CorePADA3DACBLoss(int(self.config.model["num_rois"]), weights=self.config.loss_weights, label_smoothing=self.config.label_smoothing)
        method = self._build_adaptation_method()
        source_batch = next(iter(source_train))
        target_batch = next(iter(target_adaptation))
        UDATrainer._validate_target_batch(target_batch)
        before = {key: value.detach().clone() for key, value in model.state_dict().items()}
        with torch.no_grad():
            source_output = model(source_batch["x"], feature_masks)
            target_output = model(target_batch["x"], feature_masks)
            core = loss_fn(source_output, source_batch["y"], source_batch["c_target"], source_batch["g_bar"], stage="full")
            adaptation = method.compute(source_output, target_output, "full", labels_src=source_batch["y"])
            combined = core.total + adaptation.total
        if not torch.isfinite(combined):
            raise ExperimentValidationError("Validate-only combined prototype-pseudo loss is non-finite.")
        if any(not torch.equal(before[key], value) for key, value in model.state_dict().items()):
            raise ExperimentValidationError("Validate-only modified model parameters.")
        return FoldExecutionResult(
            self.config.direction, seed, fold, "PENDING", run_dir, experiment_hash,
            {
                "planned_source_train": len(base.source_train_dataset),
                "planned_source_validation": len(base.source_validation_dataset),
                "planned_target_adaptation": len(prepared.target_adaptation_dataset),
                "planned_target_evaluation": len(base.target_evaluation_dataset or []),
                "target_training_labels_available": False,
                "validated": True,
                "prototype_pseudo_loss": float(adaptation.total),
                "prototype_raw": float(adaptation.components["prototype_raw"]),
                "pseudo_label_raw": float(adaptation.components["pseudo_label_raw"]),
            },
        )


def run_prototype_pseudo_both_directions(config: PrototypePseudoExperimentConfig, *, dry_run: bool = False, validate_only: bool = False) -> dict[str, list[Any]]:
    outputs = {}
    for source, target in (("ADNI", "OASIS"), ("OASIS", "ADNI")):
        direction = copy.deepcopy(config)
        direction.source_domain, direction.target_domain = source, target
        direction.validate()
        outputs[direction.direction] = PrototypePseudoExperimentRunner(direction).run(dry_run=dry_run, validate_only=validate_only)
    return outputs
