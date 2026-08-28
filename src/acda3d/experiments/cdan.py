"""Configuration and orchestration for 3D-ACDA + CDAN."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import torch
import yaml

from acda3d.adaptation import (
    CDANAdaptationMethod,
    DomainDiscriminator,
    DomainDiscriminatorConfig,
)
from acda3d.exceptions import (
    ConfigurationError,
    ExperimentValidationError,
    PhaseNotImplementedError,
)
from acda3d.experiments.coral import (
    CORALExperimentRunner,
    PreparedCORALFold,
    prepare_coral_fold_inputs,
    stable_weight_directory,
)
from acda3d.experiments.run_manifest import create_run_manifest, stable_hash
from acda3d.experiments.runner import FoldExecutionResult, SourceOnlyExperimentRunner
from acda3d.experiments.source_only import SourceOnlyExperimentConfig, load_source_only_config

CDAN_DISPLAY_NAME = "3D-ACDA + CDAN"
_ALLOWED_ADAPTATION_KEYS = {
    "name",
    "feature",
    "probability_source",
    "conditional_mode",
    "weight",
    "active_during_warmup",
    "grl",
    "domain_labels",
    "discriminator",
}


def _required_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"CDAN {field_name} must be a finite numeric value.") from exc



@dataclass(frozen=True)
class CDANDiscriminatorConfig:
    hidden_dims: tuple[int, ...] | None = None
    activation: str = "relu"
    dropout: float | None = None
    output_dim: int = 1
    initialization: str = "pytorch_default"
    optimizer_group: dict[str, float | None] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.hidden_dims or any(value <= 0 for value in self.hidden_dims):
            raise ConfigurationError("CDAN requires explicit positive discriminator.hidden_dims.")
        if self.activation not in {"relu", "gelu", "leaky_relu"} or self.dropout is None or not 0 <= self.dropout < 1:
            raise ConfigurationError("CDAN discriminator activation/dropout is invalid.")
        if self.output_dim != 1 or self.initialization != "pytorch_default":
            raise ConfigurationError("CDAN discriminator requires output_dim=1 and pytorch_default initialization.")
        group = self.optimizer_group
        if set(group) != {"learning_rate", "weight_decay"} or group["learning_rate"] is None or group["weight_decay"] is None:
            raise ConfigurationError("CDAN requires explicit discriminator optimizer settings.")
        if not math.isfinite(float(group["learning_rate"])) or float(group["learning_rate"]) <= 0 or not math.isfinite(float(group["weight_decay"])) or float(group["weight_decay"]) < 0:
            raise ConfigurationError("CDAN discriminator optimizer settings are invalid.")

    def resolved_dict(self, input_dim: int | None = None) -> dict[str, Any]:
        return {"input_dim": input_dim, "hidden_dims": list(self.hidden_dims or ()), "activation": self.activation, "dropout": self.dropout, "output_dim": self.output_dim, "initialization": self.initialization, "optimizer_group": dict(self.optimizer_group)}


@dataclass(frozen=True)
class CDANAdaptationConfig:
    name: str = "cdan"
    feature: str = "z"
    probability_source: str = "latent_probabilities"
    conditional_mode: str = "exact_outer_product"
    weight: float | None = None
    active_during_warmup: bool = False
    grl: dict[str, float | str | None] = field(default_factory=dict)
    domain_labels: dict[str, int] = field(default_factory=dict)
    discriminator: CDANDiscriminatorConfig = field(default_factory=CDANDiscriminatorConfig)

    def validate(self) -> None:
        if self.name != "cdan":
            raise PhaseNotImplementedError(f"Adaptation method {self.name!r} is not implemented in Phase 12.")
        if self.feature != "z" or self.probability_source != "latent_probabilities" or self.conditional_mode != "exact_outer_product":
            raise ConfigurationError("Phase 12 CDAN supports only z, latent_probabilities, and exact_outer_product.")
        if self.weight is None or not math.isfinite(self.weight) or self.weight < 0:
            raise ConfigurationError("CDAN requires a finite non-negative adaptation.weight.")
        if self.active_during_warmup:
            raise ConfigurationError("CDAN must be inactive during warm-up.")
        if self.grl.get("schedule") != "constant" or self.grl.get("coefficient") is None or not math.isfinite(float(self.grl["coefficient"])) or float(self.grl["coefficient"]) < 0:
            raise ConfigurationError("CDAN requires a finite non-negative constant GRL coefficient.")
        if self.domain_labels != {"source": 0, "target": 1}:
            raise ConfigurationError("CDAN uses fixed internal source=0 and target=1 domain labels.")
        self.discriminator.validate()

    def resolved_dict(self, input_dim: int | None = None) -> dict[str, Any]:
        return {"name": self.name, "feature": self.feature, "probability_source": self.probability_source, "conditional_mode": self.conditional_mode, "weight": self.weight, "active_during_warmup": self.active_during_warmup, "grl": dict(self.grl), "domain_labels": dict(self.domain_labels), "discriminator": self.discriminator.resolved_dict(input_dim)}

    def sha256(self) -> str:
        return stable_hash(self.resolved_dict())


@dataclass
class CDANExperimentConfig(SourceOnlyExperimentConfig):
    adaptation: CDANAdaptationConfig = field(default_factory=CDANAdaptationConfig)

    def validate(self) -> None:
        if self.method != "cdan":
            raise PhaseNotImplementedError(f"Method {self.method!r} is not implemented in Phase 12.")
        if self.display_name != CDAN_DISPLAY_NAME:
            raise ConfigurationError(f"CDAN display_name must be {CDAN_DISPLAY_NAME!r}.")
        self._validate_common()
        self.adaptation.validate()

    def resolved_dict(self) -> dict[str, Any]:
        value = super().resolved_dict()
        value["adaptation"] = self.adaptation.resolved_dict()
        return value

    def run_dir(self, fold: int, seed: int) -> Path:
        assert self.paths.output_root is not None and self.adaptation.weight is not None
        return self.paths.output_root / "cdan" / self.direction / f"seed_{seed}" / stable_weight_directory(self.adaptation.weight) / f"cdan_{self.adaptation.sha256()[:16]}" / f"fold_{fold}"


def load_cdan_config(path: str | Path, *, overrides: dict[str, Any] | None = None) -> CDANExperimentConfig:
    overrides = dict(overrides or {})
    value_overrides = {key: overrides.pop(key, None) for key in ("cdan_weight", "grl_coefficient", "domain_hidden_dims", "domain_dropout", "domain_learning_rate", "domain_weight_decay")}
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw_model = dict(payload.get("model") or {})
    raw_training = dict(payload.get("training") or {})
    if raw_model.get("contextual_encoder") is not False:
        raise ConfigurationError("Phase 12 CDAN requires contextual_encoder=false for the public 3D-ACDA model.")
    if raw_training.get("early_stopping") is not False:
        raise ConfigurationError("Phase 12 CDAN uses fixed epochs; early_stopping must be false.")
    base = load_source_only_config(path, overrides=overrides, validate=False)
    raw = dict(payload.get("adaptation") or {})
    unsupported = sorted(set(raw) - _ALLOWED_ADAPTATION_KEYS)
    if unsupported:
        raise ConfigurationError(f"Unsupported Phase 12 CDAN adaptation fields: {unsupported}.")
    grl = dict(raw.get("grl") or {})
    disc = dict(raw.get("discriminator") or {})
    group = dict(disc.get("optimizer_group") or {})
    def selected(key: str, default: Any) -> Any:
        return value_overrides[key] if value_overrides[key] is not None else default

    hidden_dims = selected("domain_hidden_dims", disc.get("hidden_dims"))
    try:
        parsed_hidden_dims = None if hidden_dims is None else tuple(int(v) for v in hidden_dims)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("CDAN discriminator.hidden_dims must be explicit positive integers.") from exc
    discriminator = CDANDiscriminatorConfig(
        parsed_hidden_dims,
        str(disc.get("activation", "relu")),
        _required_float(selected("domain_dropout", disc.get("dropout")), "discriminator.dropout"),
        int(disc.get("output_dim", 1)), str(disc.get("initialization", "pytorch_default")),
        {
            "learning_rate": _required_float(selected("domain_learning_rate", group.get("learning_rate")), "discriminator.optimizer_group.learning_rate"),
            "weight_decay": _required_float(selected("domain_weight_decay", group.get("weight_decay")), "discriminator.optimizer_group.weight_decay"),
        },
    )
    adaptation = CDANAdaptationConfig(
        str(raw.get("name", "cdan")), str(raw.get("feature", "z")), str(raw.get("probability_source", "latent_probabilities")), str(raw.get("conditional_mode", "exact_outer_product")),
        _required_float(selected("cdan_weight", raw.get("weight")), "adaptation.weight"), bool(raw.get("active_during_warmup", False)),
        {"schedule": grl.get("schedule", "constant"), "coefficient": _required_float(selected("grl_coefficient", grl.get("coefficient")), "grl.coefficient")}, dict(raw.get("domain_labels") or {}), discriminator,
    )
    inherited = {item.name: getattr(base, item.name) for item in fields(SourceOnlyExperimentConfig)}
    config = CDANExperimentConfig(**inherited, adaptation=adaptation)
    config.validate()
    return config


class CDANExperimentRunner(CORALExperimentRunner):
    method_name = "cdan"
    display_name = CDAN_DISPLAY_NAME
    loss_name = "cdan"
    checkpoint_metric_name = "source/val_macro_f1"
    checkpoint_metric_mode = "max"

    def __init__(self, config: CDANExperimentConfig):
        config.validate()
        self.config = config

    def _prepare_fold(self, fold: int) -> PreparedCORALFold:
        return prepare_coral_fold_inputs(self.config, fold)

    def _conditional_input_dim(self) -> int:
        tokenizer = dict(self.config.model.get("tokenizer") or {})
        embedding_dim = int(tokenizer.get("token_dim", self.config.model.get("token_dim", 128)))
        class_count = int(self.config.model.get("num_classes", 3))
        if embedding_dim <= 0 or class_count <= 0:
            raise ConfigurationError("CDAN conditional dimension requires positive model token_dim and class count.")
        return embedding_dim * class_count

    def _build_adaptation_method(self):
        dim = self._conditional_input_dim()
        disc = self.config.adaptation.discriminator
        return CDANAdaptationMethod(DomainDiscriminator(DomainDiscriminatorConfig(dim, disc.hidden_dims or (), disc.activation, float(disc.dropout))), float(self.config.adaptation.grl["coefficient"]))

    def _completed_reuse(
        self,
        run_dir: Path,
        experiment_hash: str,
        prepared: PreparedCORALFold,
    ) -> FoldExecutionResult | None:
        result = SourceOnlyExperimentRunner._completed_reuse(self, run_dir, experiment_hash)
        if result is None:
            return None
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "method": "cdan",
            "adaptation_method": "cdan",
            "adaptation_weight": self.config.adaptation.weight,
            "source_split_assignment_hash": prepared.base.source_assignment_hash,
            "target_adaptation_assignment_hash": prepared.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": prepared.target_evaluation_assignment_hash,
        }
        mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
        if mismatches:
            raise ExperimentValidationError(
                f"Completed CDAN fold has incompatible fields: {sorted(mismatches)}."
            )
        return result

    def _manifest(self, prepared: PreparedCORALFold, fold: int, seed: int, model: torch.nn.Module, feature_shape: tuple[int, ...], mask_hash: str, source_steps: int, target_steps: int) -> dict[str, Any]:
        base = prepared.base
        adaptation = self.config.adaptation
        input_dim = int(getattr(model, "token_dim", 128)) * 3
        return create_run_manifest(
            experiment_name=self.config.name, display_name=self.config.display_name, method="cdan", source_domain=self.config.source_domain, target_domain=self.config.target_domain, direction=self.config.direction, fold=fold, seed=seed,
            source_split_assignment_hash=base.source_assignment_hash, target_split_assignment_hash=base.target_assignment_hash, split_assignment_hash=base.protocol["split_assignment_hash"], target_adaptation_assignment_hash=prepared.target_adaptation_assignment_hash, target_evaluation_assignment_hash=prepared.target_evaluation_assignment_hash,
            artifact_index_hash=base.artifact_index_hash, atlas_hash=base.atlas_hash, roi_order_hash=base.roi_order_hash, model_configuration_hash=stable_hash(self.config.model), training_configuration_hash=stable_hash(asdict(self.config.training)), roi_mask_preparation_hash=mask_hash, feature_shape=list(feature_shape), experiment_hash=self.config.sha256(), model_parameter_count=sum(p.numel() for p in model.parameters()),
            adaptation_method="cdan", adaptation_feature="z", adaptation_probability_source="latent_probabilities", adaptation_conditional_mode="exact_outer_product", adaptation_weight=adaptation.weight, adaptation_configuration_hash=adaptation.sha256(), grl_schedule="constant", grl_coefficient=adaptation.grl["coefficient"], domain_discriminator_input_dim=input_dim, domain_discriminator_hidden_dims=list(adaptation.discriminator.hidden_dims or ()), domain_discriminator_activation=adaptation.discriminator.activation, domain_discriminator_dropout=adaptation.discriminator.dropout, domain_discriminator_parameter_count=sum((left + 1) * right for left, right in zip((input_dim, *(adaptation.discriminator.hidden_dims or ())), (*(adaptation.discriminator.hidden_dims or ()), 1), strict=True)), domain_discriminator_configuration_hash=stable_hash(adaptation.discriminator.resolved_dict(input_dim)), source_domain_label=0, target_domain_label=1, source_train_count=len(base.source_train_dataset), target_adaptation_count=len(prepared.target_adaptation_dataset), source_steps_per_epoch=source_steps, expected_target_cycles_per_epoch=(source_steps - 1) // target_steps, warmup_adaptation_active=False, full_adaptation_active=True, target_training_labels_available=False, diagnosis_labels_used_for_domain_loss=False,
        )

    def _adaptation_summary(self, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
        full = [row for row in history_rows if row["stage"] == "full"]
        return {"adaptation_method": "cdan", "adaptation_weight": self.config.adaptation.weight, "final_train_cdan_loss": history_rows[-1]["train/cdan_loss"], "mean_train_cdan_loss_full_stage": sum(row["train/cdan_loss"] for row in full) / len(full), "target_batch_cycles": sum(row["train/target_batch_cycles"] for row in full)}

    def _experiment_manifest_fields(self) -> dict[str, Any]:
        return {"attempted_adaptation_configurations": [self.config.adaptation.resolved_dict()]}


def run_cdan_both_directions(config: CDANExperimentConfig, *, dry_run: bool = False, validate_only: bool = False) -> dict[str, list[FoldExecutionResult]]:
    outputs = {}
    for source, target in (("ADNI", "OASIS"), ("OASIS", "ADNI")):
        direction = copy.deepcopy(config)
        direction.source_domain, direction.target_domain = source, target
        direction.validate()
        outputs[direction.direction] = CDANExperimentRunner(direction).run(dry_run=dry_run, validate_only=validate_only)
    return outputs
