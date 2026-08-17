"""Fixed-epoch UDA trainer shared by the approved CORAL and MMD methods."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import torch
from torch import nn

if TYPE_CHECKING:
    from pada3dacb.ablations.resolver import ResolvedAblationConfig

from pada3dacb.adaptation import AdaptationMethod
from pada3dacb.adaptation.cdan import CDANAdaptationMethod
from pada3dacb.adaptation.outputs import AdaptationLossOutput
from pada3dacb.adaptation.prototype_pseudo import (
    PrototypePseudoAdaptationConfig,
    PrototypePseudoAdaptationLoss,
)
from pada3dacb.binary import apply_binary_ablation_loss_plan, binary_ablation_plan
from pada3dacb.exceptions import PhaseNotImplementedError, TrainingRuntimeError
from pada3dacb.losses.outputs import CoreLossOutput
from pada3dacb.training.checkpointing import configuration_hash
from pada3dacb.training.runtime import (
    iterate_source_with_cycled_target,
    loader_generator_state,
    move_batch,
    require_batch_keys,
    restore_loader_generator_state,
    validate_nonempty_loader,
)
from pada3dacb.training.trainer import BaseFixedEpochTrainer

_FORBIDDEN_TARGET_KEYS = {
    "y",
    "label",
    "labels",
    "label_name",
    "true_label",
    "diagnosis",
    "binary_label",
    "binary_label_name",
    "original_label",
    "original_label_name",
    "target_label",
    "diagnosis_label",
    "c_target",
    "concept",
    "concept_target",
    "concept_targets",
    "g_bar",
    "jacobian",
    "jacobian_target",
    "jacobian_targets",
    "class_probabilities",
    "artifact",
    "artifact_hash",
}
_SUPPORTED_METHODS = {"coral", "mmd", "cdan"}
_PROPOSED_METHOD_NAME = "prototype_pseudo"
_ALLOWED_TARGET_KEYS = {"x", "subject_id", "subject_hash", "cohort"}
_APPROVED_LOSS_ABLATIONS = {"no_proto", "no_pl", "no_cons", "no_concept", "no_anat"}
_CORE_COMPONENTS = {
    "L_cls_z": ("lambda_z", "warm_lambda_z"),
    "L_cls_c": ("lambda_c", "warm_lambda_c"),
    "L_cons": ("lambda_cons", "warm_lambda_cons"),
    "L_concept": ("lambda_cbm", "warm_lambda_cbm"),
    "L_anat": ("lambda_anat", "warm_lambda_anat"),
}


@dataclass(frozen=True)
class ComposedCoreLossOutput(CoreLossOutput):
    """Core loss output with auditable raw/weighted/activity diagnostics."""

    component_diagnostics: dict[str, float | bool]

    def detached(self) -> dict[str, float]:
        values = super().detached()
        values.update(
            {
                key: float(value) if not isinstance(value, bool) else float(value)
                for key, value in self.component_diagnostics.items()
            }
        )
        return values


class ComposedCoreLoss(nn.Module):
    """Apply one resolved loss-component override without computing disabled terms."""

    def __init__(
        self,
        base_loss: nn.Module,
        contract: ResolvedAblationConfig,
        *,
        binary_plan: Any | None = None,
    ) -> None:
        super().__init__()
        _validate_loss_contract(contract)
        self.base_loss = base_loss
        self.contract = contract
        self.binary_plan = binary_ablation_plan(binary_plan) if binary_plan is not None else None

    def forward(
        self,
        output: Any,
        labels: torch.Tensor,
        concept_targets: torch.Tensor,
        g_bar: torch.Tensor,
        *,
        stage: str = "full",
    ) -> ComposedCoreLossOutput:
        if stage not in {"warm", "full"}:
            raise TrainingRuntimeError(f"stage must be 'warm' or 'full', got {stage!r}.")
        coefficients = self.contract.losses
        disabled = set(self.binary_plan.disabled_loss_components) if self.binary_plan else set()
        diagnostics: dict[str, float | bool] = {}
        raw: dict[str, torch.Tensor] = {}
        weighted: dict[str, torch.Tensor] = {}
        reference = output.latent_logits
        for term, (coefficient_name, warm_name) in _CORE_COMPONENTS.items():
            coefficient = float(getattr(coefficients, coefficient_name))
            if stage == "warm":
                coefficient *= float(getattr(coefficients, warm_name))
            if term in disabled:
                coefficient = 0.0
            active = coefficient > 0.0
            if active:
                if term == "L_cls_z":
                    value = self.base_loss.latent_classification(output.latent_logits, labels)
                elif term == "L_cls_c":
                    value = self.base_loss.concept_classification(output.concept_logits, labels)
                elif term == "L_cons":
                    value = self.base_loss.prediction_consistency(output.latent_logits, output.concept_logits)
                elif term == "L_concept":
                    value = self.base_loss.concept_supervision(output.concepts, concept_targets)
                else:
                    value = self.base_loss.anatomical_consistency(output.concepts, g_bar)
            else:
                value = reference.sum() * 0.0
            raw[term] = value
            weighted[term] = value * value.new_tensor(coefficient)
            diagnostics[f"{term}_raw"] = float(value.detach().cpu())
            diagnostics[f"{term}_weighted"] = float(weighted[term].detach().cpu())
            diagnostics[f"{term}_active"] = active

        total = sum(weighted.values(), reference.sum() * 0.0)
        if not torch.isfinite(total):
            raise TrainingRuntimeError("Composed core loss is non-finite.")
        return ComposedCoreLossOutput(
            total=total,
            classification=raw["L_cls_z"],
            concept_classification=raw["L_cls_c"],
            concept_supervision=raw["L_concept"],
            anatomical_consistency=raw["L_anat"],
            prediction_consistency=raw["L_cons"],
            component_diagnostics=diagnostics,
        )


def _validate_loss_contract(contract: ResolvedAblationConfig) -> None:
    from pada3dacb.ablations.schemas import InterventionKind

    if contract.candidate_id not in _APPROVED_LOSS_ABLATIONS:
        raise TrainingRuntimeError("only the five approved loss-component ablations are supported")
    intervention = contract.intervention
    expected_parameters = {
        "no_proto": "lambda_proto",
        "no_pl": "lambda_pl",
        "no_cons": "lambda_cons",
        "no_concept": "lambda_cbm",
        "no_anat": "lambda_anat",
    }
    if (
        intervention.kind is not InterventionKind.LOSS_OVERRIDE
        or intervention.new_value != 0.0
        or intervention.parameter != expected_parameters[contract.candidate_id]
    ):
        raise TrainingRuntimeError("resolved ablation must contain exactly its approved zero loss override")
    canonical = {
        "lambda_z": 1.0,
        "lambda_c": 1.0,
        "lambda_cons": 0.1,
        "lambda_cbm": 0.5,
        "lambda_anat": 0.2,
        "lambda_proto": 1.0,
        "lambda_pl": 0.1,
        "tau_p": 0.95,
        "proto_margin": 1.0,
        "lambda_sep": 0.1,
        "label_smoothing": 0.1,
        "warm_lambda_z": 0.1,
        "warm_lambda_c": 1.0,
        "warm_lambda_cbm": 1.0,
        "warm_lambda_anat": 1.0,
        "warm_lambda_cons": 0.0,
    }
    for name, expected in canonical.items():
        if getattr(contract.losses, name) != (0.0 if name == intervention.parameter else expected):
            raise TrainingRuntimeError("resolved ablation contains an unapproved coefficient override")


class ProposedPrototypePseudoAdaptationMethod:
    """Trainer-facing stateless Phase 13 prototype + pseudo-label method."""

    name = _PROPOSED_METHOD_NAME
    feature = "z_and_concept_logits"

    def __init__(
        self,
        *,
        resolved_ablation: ResolvedAblationConfig | None = None,
        **configuration: float | int,
    ) -> None:
        if resolved_ablation is not None:
            self.config = PrototypePseudoAdaptationLoss.from_resolved(resolved_ablation).config
        else:
            self.config = PrototypePseudoAdaptationConfig(**configuration)
        self.loss = PrototypePseudoAdaptationLoss(self.config)
        self.binary_ablation_plan: Any | None = None

    def resolved_configuration(self) -> dict[str, float | int | str]:
        return {
            "method": self.name,
            "lambda_proto": self.config.lambda_proto,
            "lambda_pl": self.config.lambda_pl,
            "tau_p": self.config.tau_p,
            "proto_margin": self.config.proto_margin,
            "lambda_sep": self.config.lambda_sep,
            "num_classes": self.config.num_classes,
            "stateful_adaptation": "none",
        }

    def compute(self, source_output: Any, target_output: Any, stage: str, *, labels_src: torch.Tensor) -> AdaptationLossOutput:
        result = self.loss(source_output.z, labels_src, target_output.z, target_output.concept_logits, stage=stage)
        effective = apply_binary_ablation_loss_plan(
            self.binary_ablation_plan,
            {"L_proto": result.prototype_weighted, "L_pl": result.pseudo_label_weighted},
        ) if self.binary_ablation_plan is not None else {
            "L_proto": result.prototype_weighted,
            "L_pl": result.pseudo_label_weighted,
        }
        disabled = set(self.binary_ablation_plan.disabled_loss_components) if self.binary_ablation_plan else set()
        total = effective["L_proto"] + effective["L_pl"]
        return AdaptationLossOutput(
            total=total,
            components={
                "prototype_pseudo": total,
                "prototype_raw": result.prototype_raw,
                "prototype_weighted": effective["L_proto"],
                "prototype_alignment": result.prototype_alignment,
                "prototype_separation": result.prototype_separation,
                "pseudo_label_raw": result.pseudo_label_raw,
                "pseudo_label_weighted": effective["L_pl"],
                "L_proto_raw": result.prototype_raw,
                "L_proto_weighted": effective["L_proto"],
                "L_proto_active": total.new_tensor(float(result.prototype_active and "L_proto" not in disabled)),
                "L_pl_raw": result.pseudo_label_raw,
                "L_pl_weighted": effective["L_pl"],
                "L_pl_active": total.new_tensor(float(result.pseudo_label_active and "L_pl" not in disabled)),
            },
            diagnostics={
                "accepted_count": total.new_tensor(float(result.accepted_count)),
                "rejected_count": total.new_tensor(float(result.rejected_count)),
                "acceptance_rate": total.new_tensor(float(result.acceptance_rate)),
                "adaptation_active": total.new_tensor(1.0 if result.adaptation_active else 0.0),
                "classes_with_source_prototypes": total.new_tensor(float(len(result.classes_with_source_prototypes))),
                "classes_with_target_prototypes": total.new_tensor(float(len(result.classes_with_target_prototypes))),
                "classes_with_both_prototypes": total.new_tensor(float(len(result.classes_with_both_prototypes))),
                "prototype_distance_mean": total.new_tensor(float(result.prototype_distance_mean or 0.0)),
            },
        )


class UDATrainer(BaseFixedEpochTrainer):
    """Pair source and unlabeled target batches only during the full stage."""

    uses_target_adaptation = True

    def __init__(
        self,
        *args: Any,
        adaptation_method: AdaptationMethod,
        adaptation_weight: float,
        adaptation_configuration: dict[str, Any],
        source_split_assignment_hash: str,
        target_adaptation_assignment_hash: str,
        target_evaluation_assignment_hash: str,
        task_id: str | None = None,
        ablation_contract: ResolvedAblationConfig | None = None,
        **kwargs: Any,
    ):
        if ablation_contract is not None:
            _validate_loss_contract(ablation_contract)
            if adaptation_method.name != _PROPOSED_METHOD_NAME:
                raise TrainingRuntimeError("loss-component ablations require prototype_pseudo adaptation")
            adaptation_method = ProposedPrototypePseudoAdaptationMethod(
                resolved_ablation=ablation_contract
            )
        is_proposed = adaptation_method.name == _PROPOSED_METHOD_NAME
        if not is_proposed and (adaptation_method.name not in _SUPPORTED_METHODS or adaptation_method.feature != "z"):
            raise PhaseNotImplementedError(
                f"Adaptation method {adaptation_method.name!r} is not implemented for this UDA trainer."
            )
        if adaptation_weight < 0:
            raise TrainingRuntimeError("Adaptation weight must be non-negative.")
        if is_proposed and float(adaptation_weight) != 1.0:
            raise TrainingRuntimeError("Prototype-pseudo adaptation uses its canonical internal weights; adaptation_weight must be 1.0.")
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.is_binary_task = str(task_id).lower() == "cn_vs_impaired" or getattr(self.model, "num_classes", None) == 2
        self.binary_ablation_plan = (
            binary_ablation_plan(ablation_contract.candidate_id)
            if ablation_contract is not None and self.is_binary_task
            else None
        )
        if is_proposed and isinstance(adaptation_method, ProposedPrototypePseudoAdaptationMethod):
            model_classes = getattr(self.model, "num_classes", None)
            if isinstance(model_classes, int) and adaptation_method.config.num_classes != model_classes:
                adaptation_method.config = replace(adaptation_method.config, num_classes=model_classes)
                adaptation_method.loss = PrototypePseudoAdaptationLoss(adaptation_method.config)
            if self.binary_ablation_plan is not None:
                disabled = set(self.binary_ablation_plan.disabled_loss_components)
                adaptation_method.config = replace(
                    adaptation_method.config,
                    lambda_proto=0.0 if "L_proto" in disabled else adaptation_method.config.lambda_proto,
                    lambda_pl=0.0 if "L_pl" in disabled else adaptation_method.config.lambda_pl,
                )
                adaptation_method.loss = PrototypePseudoAdaptationLoss(adaptation_method.config)
            adaptation_method.binary_ablation_plan = self.binary_ablation_plan
        self.adaptation_method = adaptation_method
        self.adaptation_weight = float(adaptation_weight)
        self.ablation_contract = ablation_contract
        self.adaptation_configuration = dict(adaptation_configuration)
        if ablation_contract is not None:
            self.loss_fn = ComposedCoreLoss(
                self.loss_fn,
                ablation_contract,
                binary_plan=self.binary_ablation_plan,
            ).to(self.device)
            self.resolved_configuration["ablation"] = ablation_contract.to_dict()
        if is_proposed and isinstance(adaptation_method, ProposedPrototypePseudoAdaptationMethod):
            self.adaptation_configuration = adaptation_method.resolved_configuration()
        if self.adaptation_name == "cdan":
            if not isinstance(adaptation_method, CDANAdaptationMethod):
                raise TrainingRuntimeError("CDAN requires CDANAdaptationMethod.")
            adaptation_method.discriminator.to(self.device)
            self.adaptation_configuration["discriminator"] = {
                **dict(self.adaptation_configuration["discriminator"]),
                "input_dim": adaptation_method.discriminator.config.input_dim,
            }
            self.adaptation_configuration_hash = configuration_hash(self.adaptation_configuration)
            self.resolved_configuration["adaptation"] = self.adaptation_configuration
            group = dict(self.adaptation_configuration["discriminator"]["optimizer_group"])
            self.optimizer = torch.optim.AdamW([
                {"params": self.model.parameters(), "lr": self.config.learning_rate, "weight_decay": self.config.weight_decay},
                {"params": adaptation_method.discriminator.parameters(), "lr": float(group["learning_rate"]), "weight_decay": float(group["weight_decay"])},
            ])
        self.source_split_assignment_hash = source_split_assignment_hash
        self.target_adaptation_assignment_hash = target_adaptation_assignment_hash
        self.target_evaluation_assignment_hash = target_evaluation_assignment_hash
        self.adaptation_configuration_hash = configuration_hash(
            self.adaptation_configuration
        )
        self.resolved_configuration["adaptation"] = self.adaptation_configuration

    @property
    def adaptation_name(self) -> str:
        return self.adaptation_method.name

    def _validate_adaptation_loader(self, target_adaptation_loader: Any | None) -> None:
        if target_adaptation_loader is None:
            raise TrainingRuntimeError(
                f"{self.adaptation_name.upper()} requires a target_adaptation_loader."
            )
        validate_nonempty_loader(target_adaptation_loader, "target_adaptation_loader")
        source_batch_size = getattr(self, "_source_batch_size", None)
        target_batch_size = getattr(target_adaptation_loader, "batch_size", None)
        if target_batch_size is None or int(target_batch_size) < 2:
            raise TrainingRuntimeError(
                "Every adaptation target batch must contain at least two samples."
            )
        if source_batch_size is not None and int(source_batch_size) < 2:
            raise TrainingRuntimeError(
                "Every adaptation source batch must contain at least two samples."
            )

    def fit(self, source_train_loader: Any, *args: Any, **kwargs: Any):
        self._source_batch_size = getattr(source_train_loader, "batch_size", None)
        if self._source_batch_size is None or int(self._source_batch_size) < 2:
            raise TrainingRuntimeError(
                "Every adaptation source batch must contain at least two samples."
            )
        return super().fit(source_train_loader, *args, **kwargs)

    @staticmethod
    def _validate_target_batch(batch: dict[str, Any], *, strict: bool = False) -> None:
        require_batch_keys(batch, ["x"])
        forbidden = sorted(_FORBIDDEN_TARGET_KEYS.intersection(batch))
        allowed_keys = _ALLOWED_TARGET_KEYS if strict else {"x", "subject_id", "subject_hash", "cohort"}
        unknown = sorted(set(batch) - allowed_keys)
        if forbidden:
            raise TrainingRuntimeError(
                "Target-adaptation batch contains forbidden label fields "
                f"(supervision or artifact fields): {forbidden}."
            )
        if strict and set(batch) != _ALLOWED_TARGET_KEYS:
            missing = sorted(_ALLOWED_TARGET_KEYS - set(batch))
            raise TrainingRuntimeError(
                "Strict target-adaptation batches must contain exactly "
                f"{sorted(_ALLOWED_TARGET_KEYS)}; missing fields: {missing}; "
                f"unsupported fields: {unknown}."
            )
        if unknown:
            raise TrainingRuntimeError(
                "Target-adaptation batch contains unsupported fields; "
                f"allowed fields are exactly {sorted(allowed_keys)}: {unknown}."
            )
        if batch["x"].shape[0] < 2:
            raise TrainingRuntimeError(
                "Every adaptation target batch must contain at least two samples."
            )

    def _warm_metrics(self, source_loader: Any) -> dict[str, float]:
        common = {
            "source_embedding_mean_norm": 0.0,
            "target_embedding_mean_norm": 0.0,
            "source_batches": float(len(source_loader)),
            "target_batches_consumed": 0.0,
            "target_batch_cycles": 0.0,
        }
        if self.adaptation_name == "coral":
            return {
                **common,
                "coral_loss": 0.0,
                "weighted_coral_loss": 0.0,
                "source_covariance_frobenius": 0.0,
                "target_covariance_frobenius": 0.0,
                "covariance_difference_frobenius": 0.0,
            }
        if self.adaptation_name == "cdan":
            return {**common, "cdan_loss": 0.0, "weighted_cdan_loss": 0.0,
                    "source_domain_loss": 0.0, "target_domain_loss": 0.0,
                    "domain_accuracy": 0.0, "source_domain_accuracy": 0.0,
                    "target_domain_accuracy": 0.0, "source_domain_logit_mean": 0.0,
                    "target_domain_logit_mean": 0.0, "source_conditional_norm": 0.0,
                    "target_conditional_norm": 0.0, "model_gradient_norm": 0.0,
                    "discriminator_gradient_norm": 0.0}
        if self.adaptation_name == _PROPOSED_METHOD_NAME:
            return {
                **common,
                "prototype_pseudo_loss": 0.0,
                "weighted_prototype_pseudo_loss": 0.0,
                "prototype_raw": 0.0,
                "prototype_weighted": 0.0,
                "prototype_alignment": 0.0,
                "prototype_separation": 0.0,
                "pseudo_label_raw": 0.0,
                "pseudo_label_weighted": 0.0,
                "accepted_count": 0.0,
                "rejected_count": 0.0,
                "acceptance_rate": 0.0,
                "adaptation_active": 0.0,
                "classes_with_source_prototypes": 0.0,
                "classes_with_target_prototypes": 0.0,
                "classes_with_both_prototypes": 0.0,
                "prototype_distance_mean": 0.0,
                "L_proto_raw": 0.0,
                "L_proto_weighted": 0.0,
                "L_proto_active": 0.0,
                "L_pl_raw": 0.0,
                "L_pl_weighted": 0.0,
                "L_pl_active": 0.0,
            }
        return {
            **common,
            "mmd_loss": 0.0,
            "weighted_mmd_loss": 0.0,
            "source_kernel_mean": 0.0,
            "target_kernel_mean": 0.0,
            "cross_kernel_mean": 0.0,
            "source_target_mean_distance": 0.0,
            "minimum_bandwidth": 0.0,
            "maximum_bandwidth": 0.0,
            "number_of_bandwidths": 0.0,
        }

    def _train_epoch_for_stage(
        self, source_loader: Any, target_adaptation_loader: Any | None, stage: str
    ) -> dict[str, float]:
        if stage == "warm":
            return {**super()._train_epoch(source_loader, stage), **self._warm_metrics(source_loader)}
        assert target_adaptation_loader is not None
        self.model.train()
        sums: dict[str, float] = {}
        batches = 0
        for raw_source, raw_target in iterate_source_with_cycled_target(
            source_loader, target_adaptation_loader
        ):
            require_batch_keys(raw_source, ["x", "y", "c_target", "g_bar"])
            self._validate_target_batch(raw_target, strict=getattr(self, "is_binary_task", False) or getattr(self, "ablation_contract", None) is not None)
            if raw_source["x"].shape[0] < 2:
                raise TrainingRuntimeError(
                    "Every source adaptation batch must contain at least two samples."
                )
            source = move_batch(raw_source, self.device)
            target = move_batch(raw_target, self.device)
            self.optimizer.zero_grad(set_to_none=True)
            with torch.autocast(
                device_type=self.device.type,
                enabled=self.config.mixed_precision and self.device.type == "cuda",
            ):
                source_output = self.model(source["x"], self.roi_masks)
                target_output = self.model(target["x"], self.roi_masks)
                core = self.loss_fn(
                    source_output,
                    source["y"],
                    source["c_target"],
                    source["g_bar"],
                    stage="full",
                )
                if self.adaptation_name == _PROPOSED_METHOD_NAME:
                    if not isinstance(self.adaptation_method, ProposedPrototypePseudoAdaptationMethod):
                        raise TrainingRuntimeError("Prototype-pseudo trainer requires ProposedPrototypePseudoAdaptationMethod.")
                    adaptation = self.adaptation_method.compute(
                        source_output, target_output, "full", labels_src=source["y"]
                    )
                    weighted_adaptation = adaptation.total
                else:
                    adaptation = self.adaptation_method.compute(
                        source_output, target_output, "full"
                    )
                    weighted_adaptation = self.adaptation_weight * adaptation.total
                total = core.total + weighted_adaptation
            if self.config.fail_on_nonfinite_loss and not torch.isfinite(total):
                raise TrainingRuntimeError(
                    f"Non-finite {self.adaptation_name.upper()} total loss before backward."
                )
            if self.scaler.is_enabled():
                self.scaler.scale(total).backward()
                self.scaler.unscale_(self.optimizer)
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    self._combined_parameters(), self.config.gradient_clip_norm
                )
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                total.backward()
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    self._combined_parameters(), self.config.gradient_clip_norm
                )
                self.optimizer.step()
            values = core.detached()
            values.update(adaptation.detached())
            values.update(
                {
                    "total": float(total.detach().cpu()),
                    f"{self.adaptation_name}_loss": float(adaptation.total.detach().cpu()),
                    f"weighted_{self.adaptation_name}_loss": float(
                        weighted_adaptation.detach().cpu()
                    ),
                    "gradient_norm": float(gradient_norm.detach().cpu()),
                    **self._gradient_diagnostics(),
                }
            )
            for key, value in values.items():
                sums[key] = sums.get(key, 0.0) + value
            batches += 1
            self.global_step += 1
        target_batches = len(target_adaptation_loader)
        averaged = {key: value / batches for key, value in sums.items()}
        averaged.update(
            {
                "source_batches": float(batches),
                "target_batches_consumed": float(batches),
                "target_batch_cycles": float((batches - 1) // target_batches),
            }
        )
        return averaged


    def _combined_parameters(self):
        if self.adaptation_name == "cdan":
            method = self.adaptation_method
            assert isinstance(method, CDANAdaptationMethod)
            return [*self.model.parameters(), *method.discriminator.parameters()]
        return self.model.parameters()

    def _gradient_diagnostics(self) -> dict[str, float]:
        if self.adaptation_name != "cdan":
            return {}
        method = self.adaptation_method
        assert isinstance(method, CDANAdaptationMethod)
        def norm(values: Iterable[torch.nn.Parameter]) -> torch.Tensor:
            return torch.sqrt(
                sum(
                    (value.grad.detach().float().norm() ** 2 for value in values if value.grad is not None),
                    torch.tensor(0.0, device=self.device),
                )
            )

        return {
            "model_gradient_norm": float(norm(self.model.parameters()).cpu()),
            "discriminator_gradient_norm": float(norm(method.discriminator.parameters()).cpu()),
        }

    def _loader_states(
        self, source_loader: Any, target_adaptation_loader: Any | None
    ) -> dict[str, torch.Tensor | None]:
        assert target_adaptation_loader is not None
        return {
            "source_train": loader_generator_state(source_loader),
            "target_adaptation": loader_generator_state(target_adaptation_loader),
        }

    def _checkpoint_extra(self) -> dict[str, Any]:
        payload = {
            "adaptation_method": self.adaptation_name,
            "adaptation_configuration": self.adaptation_configuration,
            "adaptation_configuration_hash": self.adaptation_configuration_hash,
            "source_split_assignment_hash": self.source_split_assignment_hash,
            "target_adaptation_assignment_hash": self.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": self.target_evaluation_assignment_hash,
        }
        if getattr(self, "is_binary_task", False):
            payload.update({
                "task_id": "cn_vs_impaired",
                "class_order": ["CN", "Impaired"],
                "mapping_contract": "phase-18b-binary-v1",
                "split_identity": self.source_split_assignment_hash,
                "configuration_payload": dict(self.adaptation_configuration),
                "configuration_payload_hash": configuration_hash(self.adaptation_configuration),
                "binary_classifier_cardinality": 2,
            })
        if self.adaptation_name == "coral":
            payload["coral_weight"] = self.adaptation_weight
            return payload
        if self.adaptation_name == "cdan":
            method = self.adaptation_method
            assert isinstance(method, CDANAdaptationMethod)
            discriminator = dict(self.adaptation_configuration["discriminator"])
            payload.update({"cdan_weight": self.adaptation_weight, "cdan_feature": "z",
                "cdan_probability_source": "latent_probabilities", "cdan_conditional_mode": "exact_outer_product",
                "grl_schedule": self.adaptation_configuration["grl"]["schedule"],
                "grl_coefficient": self.adaptation_configuration["grl"]["coefficient"],
                "domain_discriminator_state_dict": method.discriminator.state_dict(),
                "domain_discriminator_configuration": discriminator,
                "domain_discriminator_configuration_hash": configuration_hash(discriminator),
                "model_optimizer_group_configuration": {"learning_rate": self.config.learning_rate, "weight_decay": self.config.weight_decay},
                "discriminator_optimizer_group_configuration": discriminator["optimizer_group"]})
            return payload
        if self.adaptation_name == _PROPOSED_METHOD_NAME:
            payload.update({
                "prototype_pseudo_weight": 1.0,
                "prototype_pseudo_stateful_adaptation": "none",
            })
            return payload
        kernel = dict(self.adaptation_configuration["kernel"])
        payload.update(
            {
                "mmd_weight": self.adaptation_weight,
                "mmd_feature": "z",
                "mmd_estimator": self.adaptation_configuration["estimator"],
                "mmd_include_diagonal": self.adaptation_configuration["include_diagonal"],
                "mmd_kernel_name": kernel["name"],
                "mmd_bandwidths": list(kernel["bandwidths"]),
            }
        )
        return payload

    def _validate_resume_extra(self, checkpoint: dict[str, Any]) -> None:
        if self.adaptation_name == "cdan":
            method = self.adaptation_method
            assert isinstance(method, CDANAdaptationMethod)
            state = checkpoint.get("domain_discriminator_state_dict")
            if state is None:
                raise TrainingRuntimeError("CDAN resume checkpoint lacks discriminator state.")
            method.discriminator.load_state_dict(state, strict=True)
        expected = self._checkpoint_extra()
        expected.pop("domain_discriminator_state_dict", None)
        mismatches = [key for key, value in expected.items() if checkpoint.get(key) != value]
        if mismatches:
            raise TrainingRuntimeError(
                f"Incompatible {self.adaptation_name.upper()} resume checkpoint fields: "
                f"{sorted(mismatches)}."
            )

    def _restore_extra_loader_states(
        self, target_adaptation_loader: Any | None, states: dict[str, Any]
    ) -> None:
        if target_adaptation_loader is None:
            raise TrainingRuntimeError(
                f"{self.adaptation_name.upper()} resume requires target loader state."
            )
        restore_loader_generator_state(
            target_adaptation_loader, states.get("target_adaptation")
        )

    def _history_metadata(self, stage: str) -> dict[str, Any]:
        values: dict[str, Any] = {
            "adaptation/name": self.adaptation_name,
            "adaptation/weight": self.adaptation_weight,
            "adaptation_active": stage == "full",
        }
        if self.adaptation_name == "cdan":
            values.update({"adaptation/feature": "z", "adaptation/probability_source": "latent_probabilities",
                           "adaptation/conditional_mode": "exact_outer_product",
                           "adaptation/grl_coefficient": self.adaptation_configuration["grl"]["coefficient"]})
        if self.adaptation_name == "mmd":
            kernel = dict(self.adaptation_configuration["kernel"])
            values.update(
                {
                    "adaptation/kernel_name": kernel["name"],
                    "adaptation/kernel_bandwidths": json.dumps(
                        kernel["bandwidths"], separators=(",", ":")
                    ),
                    "adaptation/estimator": self.adaptation_configuration["estimator"],
                }
            )
        if self.adaptation_name == _PROPOSED_METHOD_NAME:
            values.update(
                {
                    "adaptation/stateful_adaptation": "none",
                    "adaptation/tau_p": self.adaptation_configuration["tau_p"],
                    "adaptation/lambda_proto": self.adaptation_configuration["lambda_proto"],
                    "adaptation/lambda_pl": self.adaptation_configuration["lambda_pl"],
                }
            )
        return values
