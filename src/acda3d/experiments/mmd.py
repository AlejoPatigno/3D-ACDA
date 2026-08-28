"""Configuration and orchestration for 3D-ACDA + MMD."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import torch
import yaml

from acda3d.adaptation import MMDAdaptationMethod
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
from acda3d.experiments.source_only import (
    SourceOnlyExperimentConfig,
    load_source_only_config,
)

MMD_DISPLAY_NAME = "3D-ACDA + MMD"


@dataclass(frozen=True)
class MMDKernelConfig:
    name: str = "gaussian_rbf_mixture"
    bandwidths: tuple[float, ...] | None = None
    aggregation: str = "mean"

    def validate(self) -> None:
        if self.name != "gaussian_rbf_mixture":
            raise ConfigurationError("MMD kernel must be 'gaussian_rbf_mixture'.")
        if self.aggregation != "mean":
            raise ConfigurationError("MMD kernel aggregation must be arithmetic mean.")
        if self.bandwidths is None or not self.bandwidths:
            raise ConfigurationError("MMD requires an explicit non-empty bandwidth list.")
        if any(not math.isfinite(value) or value <= 0 for value in self.bandwidths):
            raise ConfigurationError("Every MMD bandwidth must be finite and positive.")
        if len(set(self.bandwidths)) != len(self.bandwidths):
            raise ConfigurationError("Duplicate MMD bandwidths are not permitted.")

    def resolved_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bandwidths": None if self.bandwidths is None else list(self.bandwidths),
            "aggregation": self.aggregation,
        }


@dataclass(frozen=True)
class MMDAdaptationConfig:
    name: str = "mmd"
    feature: str = "z"
    weight: float | None = None
    active_during_warmup: bool = False
    kernel: MMDKernelConfig = field(default_factory=MMDKernelConfig)
    estimator: str = "biased"
    include_diagonal: bool = True
    compute_dtype: str = "float32"

    def validate(self) -> None:
        if self.name != "mmd":
            raise PhaseNotImplementedError(
                f"Adaptation method {self.name!r} is not implemented in Phase 11."
            )
        if self.feature != "z":
            raise ConfigurationError("MMD feature must be the subject embedding 'z'.")
        if self.weight is None:
            raise ConfigurationError("MMD requires an explicit adaptation.weight.")
        if not math.isfinite(self.weight) or self.weight < 0:
            raise ConfigurationError("MMD adaptation.weight must be finite and non-negative.")
        if self.active_during_warmup is not False:
            raise ConfigurationError("MMD must be inactive during warm-up.")
        self.kernel.validate()
        if self.estimator != "biased":
            raise ConfigurationError("MMD estimator must be 'biased'.")
        if self.include_diagonal is not True:
            raise ConfigurationError("Biased MMD must include diagonal kernel entries.")
        if self.compute_dtype != "float32":
            raise ConfigurationError("MMD compute_dtype must be float32.")

    def resolved_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kernel"] = self.kernel.resolved_dict()
        return payload

    def sha256(self) -> str:
        return stable_hash(self.resolved_dict())

    def kernel_hash(self) -> str:
        return stable_hash(
            {
                "kernel": self.kernel.resolved_dict(),
                "estimator": self.estimator,
                "include_diagonal": self.include_diagonal,
            }
        )


@dataclass
class MMDExperimentConfig(SourceOnlyExperimentConfig):
    adaptation: MMDAdaptationConfig = field(default_factory=MMDAdaptationConfig)

    def validate(self) -> None:
        if self.method != "mmd":
            raise PhaseNotImplementedError(f"Method {self.method!r} is not implemented in Phase 11.")
        if self.display_name != MMD_DISPLAY_NAME:
            raise ConfigurationError(f"MMD display_name must be {MMD_DISPLAY_NAME!r}.")
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
            / "mmd"
            / self.direction
            / f"seed_{seed}"
            / stable_weight_directory(self.adaptation.weight)
            / f"kernel_{self.adaptation.kernel_hash()[:16]}"
            / f"fold_{fold}"
        )


def load_mmd_config(
    path: str | Path,
    *,
    overrides: dict[str, Any] | None = None,
) -> MMDExperimentConfig:
    overrides = dict(overrides or {})
    weight_override = overrides.pop("mmd_weight", None)
    bandwidth_override = overrides.pop("mmd_bandwidths", None)
    base = load_source_only_config(path, overrides=overrides, validate=False)
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    adaptation_payload = dict(payload.get("adaptation") or {})
    kernel_payload = dict(adaptation_payload.get("kernel") or {})
    weight_value = (
        weight_override if weight_override is not None else adaptation_payload.get("weight")
    )
    bandwidth_values = (
        bandwidth_override
        if bandwidth_override is not None
        else kernel_payload.get("bandwidths")
    )
    kernel = MMDKernelConfig(
        name=str(kernel_payload.get("name", "gaussian_rbf_mixture")),
        bandwidths=(
            None
            if bandwidth_values is None
            else tuple(float(value) for value in bandwidth_values)
        ),
        aggregation=str(kernel_payload.get("aggregation", "mean")),
    )
    adaptation = MMDAdaptationConfig(
        name=str(adaptation_payload.get("name", "mmd")),
        feature=str(adaptation_payload.get("feature", "z")),
        weight=None if weight_value is None else float(weight_value),
        active_during_warmup=bool(adaptation_payload.get("active_during_warmup", False)),
        kernel=kernel,
        estimator=str(adaptation_payload.get("estimator", "biased")),
        include_diagonal=bool(adaptation_payload.get("include_diagonal", True)),
        compute_dtype=str(adaptation_payload.get("compute_dtype", "float32")),
    )
    inherited = {
        item.name: getattr(base, item.name)
        for item in fields(SourceOnlyExperimentConfig)
    }
    config = MMDExperimentConfig(**inherited, adaptation=adaptation)
    config.validate()
    return config


class MMDExperimentRunner(CORALExperimentRunner):
    """MMD experiment using the shared immutable UDA workflow."""

    method_name = "mmd"
    display_name = MMD_DISPLAY_NAME
    loss_name = "mmd"

    def __init__(self, config: MMDExperimentConfig):
        config.validate()
        self.config = config

    def _prepare_fold(self, fold: int) -> PreparedCORALFold:
        return prepare_coral_fold_inputs(self.config, fold)

    def _build_adaptation_method(self):
        assert self.config.adaptation.kernel.bandwidths is not None
        return MMDAdaptationMethod(self.config.adaptation.kernel.bandwidths)

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
        adaptation = self.config.adaptation
        assert adaptation.weight is not None and adaptation.kernel.bandwidths is not None
        return create_run_manifest(
            experiment_name=self.config.name,
            display_name=self.config.display_name,
            method="mmd",
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
            adaptation_method="mmd",
            adaptation_feature="z",
            adaptation_weight=adaptation.weight,
            adaptation_configuration_hash=adaptation.sha256(),
            mmd_kernel_name=adaptation.kernel.name,
            mmd_bandwidths=list(adaptation.kernel.bandwidths),
            mmd_kernel_aggregation=adaptation.kernel.aggregation,
            mmd_estimator=adaptation.estimator,
            mmd_include_diagonal=adaptation.include_diagonal,
            mmd_compute_dtype=adaptation.compute_dtype,
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
        result = SourceOnlyExperimentRunner._completed_reuse(self, run_dir, experiment_hash)
        if result is None:
            return None
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        adaptation = self.config.adaptation
        expected = {
            "method": "mmd",
            "adaptation_weight": adaptation.weight,
            "adaptation_configuration_hash": adaptation.sha256(),
            "mmd_kernel_name": adaptation.kernel.name,
            "mmd_bandwidths": list(adaptation.kernel.bandwidths or ()),
            "mmd_estimator": adaptation.estimator,
            "mmd_include_diagonal": adaptation.include_diagonal,
            "source_split_assignment_hash": prepared.base.source_assignment_hash,
            "target_adaptation_assignment_hash": prepared.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": prepared.target_evaluation_assignment_hash,
        }
        mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
        if mismatches:
            raise ExperimentValidationError(
                f"Completed MMD fold has incompatible fields: {sorted(mismatches)}."
            )
        return result

    def _adaptation_summary(self, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
        full_rows = [row for row in history_rows if row["stage"] == "full"]
        final = history_rows[-1]
        adaptation = self.config.adaptation
        return {
            "adaptation_method": "mmd",
            "adaptation_weight": adaptation.weight,
            "mmd_kernel_name": adaptation.kernel.name,
            "mmd_bandwidths": json.dumps(list(adaptation.kernel.bandwidths or ())),
            "mmd_estimator": adaptation.estimator,
            "final_train_mmd_loss": final["train/mmd_loss"],
            "final_weighted_mmd_loss": final["train/weighted_mmd_loss"],
            "mean_train_mmd_loss_full_stage": sum(
                row["train/mmd_loss"] for row in full_rows
            )
            / len(full_rows),
            "final_source_kernel_mean": final["train/source_kernel_mean"],
            "final_target_kernel_mean": final["train/target_kernel_mean"],
            "final_cross_kernel_mean": final["train/cross_kernel_mean"],
            "target_batch_cycles": sum(
                row["train/target_batch_cycles"] for row in full_rows
            ),
        }

    def _experiment_manifest_fields(self) -> dict[str, Any]:
        return {
            "attempted_adaptation_configurations": [
                self.config.adaptation.resolved_dict()
            ]
        }


def run_mmd_both_directions(
    config: MMDExperimentConfig,
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
        outputs[direction_config.direction] = MMDExperimentRunner(
            direction_config
        ).run(dry_run=dry_run, validate_only=validate_only)
    return outputs
