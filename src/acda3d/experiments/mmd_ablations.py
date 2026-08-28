"""Binary MMD ablation composition over the shared UDA trainer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from acda3d.ablations.schemas import sha256_payload
from acda3d.adaptation import MMDAdaptationMethod
from acda3d.binary import MMDBinaryAblationPlan, mmd_binary_ablation_plan
from acda3d.losses import CoreACDA3DLoss, CoreLossWeights
from acda3d.training import FixedEpochTrainingConfig, UDATrainer

_MMD_CORE_OVERRIDES = {
    "no_cons": {"prediction_consistency": 0.0},
    "no_concept": {"concept_supervision": 0.0},
    "no_anat": {"anatomical_consistency": 0.0},
}
_DEFAULT_SOURCE_SPLIT_ASSIGNMENT_HASH = sha256_payload(
    {"phase": "18B", "assignment": "binary-source"}
)
_DEFAULT_TARGET_ADAPTATION_ASSIGNMENT_HASH = sha256_payload(
    {"phase": "18B", "assignment": "binary-target-adaptation"}
)
_DEFAULT_TARGET_EVALUATION_ASSIGNMENT_HASH = sha256_payload(
    {"phase": "18B", "assignment": "binary-target-evaluation"}
)
_MMD_DEFAULT_BANDWIDTHS = (0.5, 1.0, 2.0)
_MMD_PROTECTED_CONFIGURATION = {
    "name": "mmd",
    "feature": "z",
    "active_during_warmup": False,
    "kernel": {
        "name": "gaussian_rbf_mixture",
        "aggregation": "mean",
    },
    "estimator": "biased",
    "include_diagonal": True,
    "compute_dtype": "float32",
}


def _mmd_configuration(
    bandwidths: tuple[float, ...],
    mmd_weight: float,
) -> dict[str, Any]:
    configuration = {
        **_MMD_PROTECTED_CONFIGURATION,
        "kernel": {
            **_MMD_PROTECTED_CONFIGURATION["kernel"],
            "bandwidths": list(bandwidths),
        },
        "weight": mmd_weight,
    }
    return configuration


def _resolve_mmd_weight(candidate_id: str, value: float | None) -> float:
    expected = 0.0 if candidate_id == "no_mmd" else 1.0
    if value is None:
        return expected
    try:
        resolved = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("mmd_weight must be finite and non-negative") from error
    if not math.isfinite(resolved) or resolved < 0:
        raise ValueError("mmd_weight must be finite and non-negative")
    if resolved != expected:
        raise ValueError(
            f"unapproved MMD weight override for {candidate_id!r}; expected {expected}"
        )
    return resolved


@dataclass(frozen=True)
class BinaryMMDAblationComposition:
    """Resolved binary candidate components for the existing MMD UDA path."""

    plan: MMDBinaryAblationPlan
    core_loss_weights: CoreLossWeights
    mmd_weight: float
    bandwidths: tuple[float, ...]
    label_smoothing: float = 0.1

    @property
    def candidate_id(self) -> str:
        return self.plan.candidate_id

    @property
    def base_method(self) -> str:
        return self.plan.base_method

    @property
    def requires_target_adaptation(self) -> bool:
        return self.plan.requires_target_adaptation

    @property
    def requires_target_forward(self) -> bool:
        return self.plan.requires_target_forward

    @property
    def model_variant(self) -> str:
        return "3D-ACDA+MeanPoolAggregator" if self.plan.model_variant == "mean_pool" else "3D-ACDA"

    def build_loss(self, num_rois: int) -> CoreACDA3DLoss:
        return CoreACDA3DLoss(
            num_rois,
            weights=self.core_loss_weights,
            label_smoothing=self.label_smoothing,
        )

    @property
    def mmd_configuration(self) -> dict[str, Any]:
        return _mmd_configuration(self.bandwidths, self.mmd_weight)

    @property
    def mmd_configuration_hash(self) -> str:
        return sha256_payload(self.mmd_configuration)

    def build_adaptation(self) -> MMDAdaptationMethod:
        return MMDAdaptationMethod(self.bandwidths)

    def build_trainer(
        self,
        *,
        model: torch.nn.Module,
        roi_masks: torch.Tensor,
        run_dir: str | Path,
        seed: int = 42,
        training_config: FixedEpochTrainingConfig | None = None,
        warmup_epochs: int = 0,
        full_epochs: int = 1,
        source_split_assignment_hash: str = _DEFAULT_SOURCE_SPLIT_ASSIGNMENT_HASH,
        target_adaptation_assignment_hash: str = _DEFAULT_TARGET_ADAPTATION_ASSIGNMENT_HASH,
        target_evaluation_assignment_hash: str = _DEFAULT_TARGET_EVALUATION_ASSIGNMENT_HASH,
    ) -> UDATrainer:
        """Build the shared trainer while retaining the target adaptation path."""
        config = training_config or FixedEpochTrainingConfig(
            warmup_epochs=warmup_epochs,
            full_epochs=full_epochs,
            mixed_precision=False,
            target_monitoring_enabled=False,
            device="cpu",
            seed=seed,
        )
        return UDATrainer(
            model,
            self.build_loss(int(getattr(model, "num_rois", roi_masks.shape[0]))),
            roi_masks,
            run_dir,
            config=config,
            split_assignment_hash=source_split_assignment_hash,
            atlas_hash="binary-atlas",
            roi_order_hash="binary-roi-order",
            adaptation_method=self.build_adaptation(),
            adaptation_weight=self.mmd_weight,
            adaptation_configuration=self.mmd_configuration,
            source_split_assignment_hash=source_split_assignment_hash,
            target_adaptation_assignment_hash=target_adaptation_assignment_hash,
            target_evaluation_assignment_hash=target_evaluation_assignment_hash,
            task_id="cn_vs_impaired",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "base_method": self.base_method,
            "model_variant": self.model_variant,
            "core_loss_weights": vars(self.core_loss_weights),
            "mmd_weight": self.mmd_weight,
            "bandwidths": list(self.bandwidths),
            "mmd_configuration": self.mmd_configuration,
            "mmd_configuration_hash": self.mmd_configuration_hash,
            "requires_target_adaptation": self.requires_target_adaptation,
            "requires_target_forward": self.requires_target_forward,
            "target_label_firewall": {
                "target_adaptation_batch_keys": ["x", "subject_id", "subject_hash", "cohort"],
                "target_labels_in_adaptation": False,
            },
            "checkpoint_selection": {
                "split": "source_validation",
                "metric": "macro_f1",
                "target_labels_used": False,
            },
        }


def _core_weights(candidate_id: str) -> CoreLossWeights:
    values = vars(CoreLossWeights())
    values.update(_MMD_CORE_OVERRIDES.get(candidate_id, {}))
    return CoreLossWeights(**values)


def _validate_bandwidths(bandwidths: Any) -> tuple[float, ...]:
    if isinstance(bandwidths, (str, bytes)):
        raise ValueError("MMD bandwidths must be a non-empty sequence")
    try:
        values = tuple(float(value) for value in bandwidths)
    except (TypeError, ValueError) as error:
        raise ValueError("MMD bandwidths must be a non-empty sequence") from error
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("MMD bandwidths must be finite and positive")
    if len(set(values)) != len(values):
        raise ValueError("MMD bandwidths must be unique")
    return values


def compose_binary_mmd_ablation(
    candidate: str | MMDBinaryAblationPlan,
    *,
    num_rois: int,
    bandwidths: Any,
    mmd_weight: float | None = None,
    label_smoothing: float = 0.1,
) -> BinaryMMDAblationComposition:
    """Resolve one MMD candidate without changing the historical namespace."""
    if isinstance(num_rois, bool) or not isinstance(num_rois, int) or num_rois <= 0:
        raise ValueError("num_rois must be a positive integer")
    plan = mmd_binary_ablation_plan(candidate)
    values = _resolve_mmd_weight(plan.candidate_id, mmd_weight)
    if not math.isfinite(float(label_smoothing)) or not 0 <= float(label_smoothing) <= 1:
        raise ValueError("label_smoothing must be within [0, 1]")
    return BinaryMMDAblationComposition(
        plan=plan,
        core_loss_weights=_core_weights(plan.candidate_id),
        mmd_weight=values,
        bandwidths=_validate_bandwidths(bandwidths),
        label_smoothing=float(label_smoothing),
    )


def binary_mmd_ablation_identity(
    candidate: str | MMDBinaryAblationPlan,
    direction: str,
    fold: int,
    seed: int,
    *,
    bandwidths: Any | None = None,
    mmd_weight: float | None = None,
) -> dict[str, Any]:
    """Create an identity bound to the complete protected MMD configuration."""
    plan = mmd_binary_ablation_plan(candidate)
    if not isinstance(direction, str) or "_to_" not in direction:
        raise ValueError("direction must be SOURCE_to_TARGET")
    if isinstance(fold, bool) or not isinstance(fold, int) or fold < 0:
        raise ValueError("fold must be a non-negative integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    resolved_bandwidths = _validate_bandwidths(
        _MMD_DEFAULT_BANDWIDTHS if bandwidths is None else bandwidths
    )
    resolved_weight = _resolve_mmd_weight(plan.candidate_id, mmd_weight)
    configuration = _mmd_configuration(resolved_bandwidths, resolved_weight)
    identity = {
        "schema_version": "phase18b.binary-mmd-ablation.v1",
        "candidate_id": plan.candidate_id,
        "base_method": plan.base_method,
        "direction": direction,
        "fold": fold,
        "seed": seed,
        "mmd_configuration": configuration,
        "mmd_configuration_hash": sha256_payload(configuration),
    }
    return {**identity, "identity_hash": sha256_payload(identity)}


def binary_mmd_ablation_output_path(
    output_root: str | Path,
    candidate: str | MMDBinaryAblationPlan,
    direction: str,
    fold: int,
    seed: int,
    *,
    bandwidths: Any | None = None,
    mmd_weight: float | None = None,
) -> Path:
    plan = mmd_binary_ablation_plan(candidate)
    identity = binary_mmd_ablation_identity(
        plan,
        direction,
        fold,
        seed,
        bandwidths=bandwidths,
        mmd_weight=mmd_weight,
    )
    path = (
        Path(output_root)
        / "mmd_ablations"
        / plan.candidate_id
        / direction
        / f"seed_{seed}"
        / f"fold_{fold}"
    )
    default_identity = binary_mmd_ablation_identity(plan, direction, fold, seed)
    if identity["mmd_configuration_hash"] != default_identity["mmd_configuration_hash"]:
        path /= f"config_{identity['mmd_configuration_hash'][:16]}"
    return path
