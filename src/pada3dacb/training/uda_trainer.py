"""Fixed-epoch UDA trainer shared by the approved CORAL and MMD methods."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import torch

from pada3dacb.adaptation import AdaptationMethod
from pada3dacb.adaptation.cdan import CDANAdaptationMethod
from pada3dacb.adaptation.outputs import AdaptationLossOutput
from pada3dacb.adaptation.prototype_pseudo import (
    PrototypePseudoAdaptationConfig,
    PrototypePseudoAdaptationLoss,
)
from pada3dacb.exceptions import PhaseNotImplementedError, TrainingRuntimeError
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
    "label_name",
    "true_label",
    "diagnosis",
    "diagnosis_label",
    "c_target",
    "g_bar",
    "class_probabilities",
}
_SUPPORTED_METHODS = {"coral", "mmd", "cdan"}
_PROPOSED_METHOD_NAME = "prototype_pseudo"
_ALLOWED_TARGET_KEYS = {"x", "subject_id", "subject_hash", "cohort"}


class ProposedPrototypePseudoAdaptationMethod:
    """Trainer-facing stateless Phase 13 prototype + pseudo-label method."""

    name = _PROPOSED_METHOD_NAME
    feature = "z_and_concept_logits"

    def __init__(self, **configuration: float | int) -> None:
        self.config = PrototypePseudoAdaptationConfig(**configuration)
        self.loss = PrototypePseudoAdaptationLoss(self.config)

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
        total = result.total
        return AdaptationLossOutput(
            total=total,
            components={
                "prototype_pseudo": total,
                "prototype_raw": result.prototype_raw,
                "prototype_weighted": result.prototype_weighted,
                "prototype_alignment": result.prototype_alignment,
                "prototype_separation": result.prototype_separation,
                "pseudo_label_raw": result.pseudo_label_raw,
                "pseudo_label_weighted": result.pseudo_label_weighted,
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
        **kwargs: Any,
    ):
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
        self.adaptation_method = adaptation_method
        self.adaptation_weight = float(adaptation_weight)
        self.adaptation_configuration = dict(adaptation_configuration)
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
    def _validate_target_batch(batch: dict[str, Any]) -> None:
        require_batch_keys(batch, ["x"])
        forbidden = sorted(_FORBIDDEN_TARGET_KEYS.intersection(batch))
        unknown = sorted(set(batch) - _ALLOWED_TARGET_KEYS)
        if forbidden:
            raise TrainingRuntimeError(
                f"Target-adaptation batch contains forbidden label fields: {forbidden}."
            )
        if unknown:
            raise TrainingRuntimeError(
                f"Target-adaptation batch contains unsupported fields: {unknown}."
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
            self._validate_target_batch(raw_target)
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
