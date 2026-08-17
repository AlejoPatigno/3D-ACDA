"""Task-scoped, synthetic-only validation for the Phase 18B binary methods.

This module is intentionally separate from the historical experiment runners.  It
constructs the retained PADA-3DACB architecture with an explicit two-class task
and exercises only CPU tensors; it never opens a data path or starts training.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import yaml
from torch import nn

from pada3dacb.adaptation.cdan import (
    CDANAdaptationMethod,
    conditional_outer_product,
    expected_conditional_dimension,
)
from pada3dacb.adaptation.domain_discriminator import (
    DomainDiscriminator,
    DomainDiscriminatorConfig,
)
from pada3dacb.adaptation.prototype import build_source_prototypes
from pada3dacb.adaptation.prototype_pseudo import (
    PrototypePseudoAdaptationConfig,
    PrototypePseudoAdaptationLoss,
)
from pada3dacb.adaptation.pseudo_label import pseudo_label_cross_entropy
from pada3dacb.binary import (
    BINARY_ABLATIONS,
    BINARY_CANONICAL_LOSS_COMPONENTS,
    apply_binary_ablation_loss_plan,
    binary_ablation_plan,
    binary_model_architecture_identity,
    build_binary_ablation,
)
from pada3dacb.exceptions import ConfigurationError
from pada3dacb.models.pada3dacb import PADA3DACBOutput, build_pada3dacb

BINARY_PUBLICATION_METHODS = (
    "source_only",
    "coral",
    "mmd",
    "cdan",
    "prototype_pseudo",
)
BINARY_TASK_ID = "cn_vs_impaired"
BINARY_TASK_TYPE = "binary_classification"
BINARY_CLASS_ORDER = ("CN", "Impaired")
BINARY_CLASS_TO_INDEX = {"CN": 0, "Impaired": 1}
BINARY_MAPPING_CONTRACT = "phase-18b-binary-v1"


@dataclass(frozen=True)
class BinaryPublicationConfig:
    """Resolved task contract accepted by :class:`BinaryPublicationRuntime`."""

    task_id: str
    task_type: str
    class_order: tuple[str, ...]
    class_to_index: dict[str, int]
    mapping_contract: str
    n_classes: int
    methods: tuple[str, ...]
    ablations: tuple[str, ...]
    validate_only: bool
    model: dict[str, Any]
    authorization: dict[str, bool]
    config_path: Path | None = None

    @classmethod
    def from_mapping(
        cls, payload: Mapping[str, Any], *, config_path: str | Path | None = None
    ) -> BinaryPublicationConfig:
        if not isinstance(payload, Mapping):
            raise ConfigurationError("Binary publication configuration must be a mapping.")
        task_id = str(payload.get("task_id", "")).strip().lower()
        if task_id != BINARY_TASK_ID:
            raise ConfigurationError(
                "Binary publication runtime requires task_id='cn_vs_impaired'; "
                "historical configurations are not converted."
            )
        if payload.get("task_type") != BINARY_TASK_TYPE:
            raise ConfigurationError(
                "Binary publication runtime requires task_type='binary_classification'."
            )
        raw_order = payload.get("class_order")
        if not isinstance(raw_order, (list, tuple)) or any(
            not isinstance(item, str) for item in raw_order
        ):
            raise ConfigurationError("Binary class_order must be exactly [CN, Impaired].")
        order = tuple(raw_order)
        if order != BINARY_CLASS_ORDER:
            raise ConfigurationError("Binary class_order must be exactly [CN, Impaired].")
        raw_ids = payload.get("class_to_index", payload.get("class_ids"))
        if not isinstance(raw_ids, Mapping):
            raise ConfigurationError("Binary class_to_index is required.")
        if set(raw_ids) != set(BINARY_CLASS_TO_INDEX) or any(
            type(value) is not int for value in raw_ids.values()
        ):
            raise ConfigurationError("Binary class_to_index must be CN=0 and Impaired=1.")
        class_to_index = dict(raw_ids)
        if class_to_index != BINARY_CLASS_TO_INDEX:
            raise ConfigurationError("Binary class_to_index must be CN=0 and Impaired=1.")
        if "class_to_index" in payload and payload.get("class_to_index") != BINARY_CLASS_TO_INDEX:
            raise ConfigurationError("class_to_index and class_ids must agree with the fixed binary vocabulary.")
        if "class_ids" in payload and payload.get("class_ids") != BINARY_CLASS_TO_INDEX:
            raise ConfigurationError("class_ids must be CN=0 and Impaired=1.")
        if payload.get("mapping_contract") != BINARY_MAPPING_CONTRACT:
            raise ConfigurationError("Binary mapping_contract must be phase-18b-binary-v1.")
        if payload.get("n_classes") != 2:
            raise ConfigurationError("Binary publication runtime requires n_classes=2.")
        raw_methods = payload.get("methods")
        if not isinstance(raw_methods, (list, tuple)) or any(
            not isinstance(item, str) for item in raw_methods
        ):
            raise ConfigurationError("Binary publication methods must be an ordered list of method IDs.")
        methods = tuple(raw_methods)
        if methods != BINARY_PUBLICATION_METHODS:
            raise ConfigurationError(
                "Binary publication methods must be exactly source_only, coral, mmd, cdan, prototype_pseudo."
            )
        raw_ablations = payload.get("ablations")
        if not isinstance(raw_ablations, (list, tuple)) or tuple(raw_ablations) != BINARY_ABLATIONS:
            raise ConfigurationError(
                "Binary ablations must be exactly no_proto, no_pl, no_cons, no_concept, no_anat, mean_pool."
            )
        ablations = tuple(raw_ablations)
        mode = payload.get("mode", payload.get("validation_mode"))
        training = payload.get("training")
        if mode is None and isinstance(training, Mapping):
            mode = training.get("mode")
        if mode != "validate_only":
            raise ConfigurationError("Phase 18B binary runtime is validate-only.")
        if not isinstance(training, Mapping) or any(
            training.get(field) is not expected
            for field, expected in (
                ("real_run", False),
                ("predictive_evaluation", False),
                ("publication_metrics", False),
            )
        ) or training.get("device") != "cpu":
            raise ConfigurationError(
                "Binary publication validation requires CPU-only, non-real-run training flags."
            )
        model = dict(payload.get("model") or {})
        if model.get("name") != "PADA-3DACB" or model.get("num_classes") != 2:
            raise ConfigurationError(
                "Binary publication runtime requires PADA-3DACB with num_classes=2; "
                "historical three-class models are rejected."
            )
        authorization = payload.get("authorization")
        if not isinstance(authorization, Mapping):
            raise ConfigurationError("Fail-closed binary authorization flags are required.")
        expected_authorization = {
            "freeze_approved": False,
            "real_execution_authorized": False,
            "publication_authorized": False,
            "phase_19_forbidden": True,
        }
        resolved_authorization = dict(authorization)
        if resolved_authorization != expected_authorization:
            raise ConfigurationError(
                "Binary validate-only runtime requires fail-closed authorization flags."
            )
        return cls(
            task_id=task_id,
            task_type=BINARY_TASK_TYPE,
            class_order=order,
            class_to_index=class_to_index,
            mapping_contract=BINARY_MAPPING_CONTRACT,
            n_classes=2,
            methods=methods,
            ablations=ablations,
            validate_only=True,
            model=model,
            authorization=expected_authorization,
            config_path=None if config_path is None else Path(config_path).resolve(),
        )

    def model_payload(self) -> dict[str, Any]:
        """Return an explicit task-bound model payload without default conversion."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "class_order": list(self.class_order),
            "class_ids": dict(self.class_to_index),
            "model": {**self.model, "num_classes": self.n_classes},
        }


def load_binary_publication_config(path: str | Path) -> BinaryPublicationConfig:
    """Load and strictly validate the binary publication YAML contract."""
    config_path = Path(path).expanduser().resolve(strict=False)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except OSError as error:
        raise ConfigurationError(f"Unable to read binary publication config: {config_path}") from error
    return BinaryPublicationConfig.from_mapping(payload, config_path=config_path)


class BinaryPublicationRuntime:
    """Synthetic CPU contract runner for the five Phase 18B core methods."""

    def __init__(self, config: BinaryPublicationConfig):
        if not isinstance(config, BinaryPublicationConfig):
            raise ConfigurationError("BinaryPublicationRuntime requires BinaryPublicationConfig.")
        self.config = config
        if not config.validate_only:
            raise ConfigurationError("BinaryPublicationRuntime only supports validate-only mode.")

    @classmethod
    def from_path(cls, path: str | Path) -> BinaryPublicationRuntime:
        return cls(load_binary_publication_config(path))

    @staticmethod
    def conditional_features(z: torch.Tensor, probabilities: torch.Tensor) -> torch.Tensor:
        """Build the exact differentiable two-class CDAN outer product."""
        return conditional_outer_product(z, probabilities, class_count=2)

    def _model_payload(self) -> dict[str, Any]:
        model = dict(self.config.model)
        # Small dimensions keep contract checks synthetic and CPU-only while retaining
        # the same encoder/tokenizer/attention/concept architecture.
        model.setdefault("num_rois", 2)
        model.setdefault("encoder", {"base_channels": 2, "output_channels": 8})
        model.setdefault("tokenizer", {"feature_dim": 8, "token_dim": 8})
        model.setdefault("concept_bottleneck", {"hidden_dim": 4})
        model.setdefault("token_processing", {"dropout": 0.0})
        model.setdefault("num_classes", 2)
        return {
            **self.config.model_payload(),
            "model": model,
        }

    def _synthetic_outputs(self) -> tuple[PADA3DACBOutput, PADA3DACBOutput]:
        torch.manual_seed(18_002)
        model = build_pada3dacb(self._model_payload())
        model.eval()
        x_source = torch.randn(2, 1, 16, 16, 16)
        x_target = torch.randn(2, 1, 16, 16, 16)
        num_rois = int(model.num_rois)
        roi_masks = torch.ones(num_rois, 2, 2, 2)
        return model(x_source, roi_masks), model(x_target, roi_masks)

    @staticmethod
    def _shape_result(
        method: str, source: PADA3DACBOutput, *, z_dimension: int
    ) -> dict[str, Any]:
        return {
            "method": method,
            "latent_logits_shape": tuple(source.latent_logits.shape),
            "concept_logits_shape": tuple(source.concept_logits.shape),
            "concepts_shape": tuple(source.concepts.shape),
            "alpha_shape": tuple(source.alpha.shape),
            "classifier_cardinality": int(source.latent_logits.shape[1]),
            "concept_cardinality": int(source.concepts.shape[1]),
            "z_dimension": z_dimension,
            "device": source.z.device.type,
            "validate_only": True,
            "real_run": False,
        }

    def validate_method(self, method: str) -> dict[str, Any]:
        method = str(method).strip().lower()
        if method not in BINARY_PUBLICATION_METHODS:
            raise ConfigurationError(f"Unsupported binary publication method: {method!r}.")
        source, target = self._synthetic_outputs()
        if source.latent_logits.shape[1] != 2 or source.concept_logits.shape[1] != 2:
            raise ConfigurationError("Binary runtime model heads must emit exactly two raw logits.")
        if source.concepts.ndim != 2 or source.alpha.ndim != 2:
            raise ConfigurationError("Concepts and alpha must remain rank-2 (B,K) tensors.")
        result = self._shape_result(method, source, z_dimension=int(source.z.shape[1]))
        labels = torch.tensor([0, 1], dtype=torch.long)
        cross_entropy = nn.CrossEntropyLoss()
        classification = cross_entropy(source.latent_logits, labels)
        concept_classification = cross_entropy(source.concept_logits, labels)
        result.update(
            {
                "classification_loss": float(classification.detach()),
                "concept_classification_loss": float(concept_classification.detach()),
                "classification_loss_name": "CrossEntropyLoss",
                "adaptation_feature": "z",
            }
        )

        if method == "source_only":
            result["adaptation_loss"] = 0.0
        elif method == "coral":
            from pada3dacb.adaptation.coral import CORALAdaptationMethod

            adaptation = CORALAdaptationMethod().compute(source, target, "full")
            result["adaptation_loss"] = float(adaptation.total.detach())
            result["adaptation_equation"] = "unchanged_coral_on_z"
        elif method == "mmd":
            from pada3dacb.adaptation.mmd import MMDAdaptationMethod

            adaptation = MMDAdaptationMethod((1.0, 2.0)).compute(source, target, "full")
            result["adaptation_loss"] = float(adaptation.total.detach())
            result["adaptation_equation"] = "unchanged_mmd_on_z"
        elif method == "cdan":
            source.z.retain_grad()
            source.latent_probabilities.retain_grad()
            conditional_dimension = expected_conditional_dimension(int(source.z.shape[1]), 2)
            discriminator = DomainDiscriminator(
                DomainDiscriminatorConfig(conditional_dimension, (8,), "relu", 0.0)
            )
            adaptation = CDANAdaptationMethod(discriminator, 1.0).compute(
                source, target, "full"
            )
            adaptation.total.backward()
            result.update(
                {
                    "adaptation_loss": float(adaptation.total.detach()),
                    "conditional_dimension": conditional_dimension,
                    "grl_schedule": "constant",
                    "domain_loss_name": "BCEWithLogitsLoss",
                    "gradient_reaches_z": source.z.grad is not None and bool(torch.any(source.z.grad != 0)),
                    "gradient_reaches_p": source.latent_probabilities.grad is not None
                    and bool(torch.any(source.latent_probabilities.grad != 0)),
                }
            )
        else:
            adaptation = PrototypePseudoAdaptationLoss(
                PrototypePseudoAdaptationConfig(num_classes=2, tau_p=0.95)
            )(
                source.z,
                labels,
                target.z,
                target.concept_logits,
                stage="full",
            )
            result.update(
                {
                    "adaptation_loss": float(adaptation.total.detach()),
                    "prototype_class_count": 2,
                    "pseudo_loss_name": "CrossEntropyLoss",
                    "target_labels_used": False,
                }
            )
        return result

    def validate_all(self) -> dict[str, dict[str, Any]]:
        """Validate every declared method without training or predictive evaluation."""
        return {method: self.validate_method(method) for method in self.config.methods}

    def validate_concept_evaluation(
        self, records: Sequence[Any], **kwargs: Any
    ) -> dict[str, Any]:
        """Run task-scoped concept metrics over retained synthetic records."""
        if self.config.task_id != BINARY_TASK_ID:
            raise ConfigurationError("binary concept evaluation task identity is incompatible")
        from pada3dacb.evaluation.concepts.report import evaluate_binary_concept_records

        return evaluate_binary_concept_records(
            records, task_id=self.config.task_id, **kwargs
        )

    def validate_ablation(self, candidate: str, *, execute: bool = False) -> dict[str, Any]:
        """Validate one approved binary ablation with a synthetic CPU forward only."""
        if execute:
            raise ConfigurationError(
                "Binary ablation runtime is validate-only; execution and authorization are forbidden."
            )
        candidate_id = str(candidate).strip()
        if candidate_id not in self.config.ablations:
            raise ConfigurationError(f"Unsupported or blocked binary ablation: {candidate!r}.")
        torch.manual_seed(18_003 + self.config.ablations.index(candidate_id))
        model = build_binary_ablation(candidate_id, self._model_payload())
        model.eval()
        x_source = torch.randn(2, 1, 16, 16, 16)
        roi_masks = torch.ones(int(model.num_rois), 2, 2, 2)
        with torch.no_grad():
            output = model(x_source, roi_masks)
        if output.latent_logits.shape != (2, 2) or output.concept_logits.shape != (2, 2):
            raise ConfigurationError("Binary ablation heads must emit finite logits shaped (B,2).")
        if not torch.isfinite(output.latent_logits).all() or not torch.isfinite(output.concept_logits).all():
            raise ConfigurationError("Binary ablation logits must be finite.")
        metadata = dict(model.binary_metadata)
        plan = binary_ablation_plan(candidate_id)
        effective_components = apply_binary_ablation_loss_plan(
            plan, BINARY_CANONICAL_LOSS_COMPONENTS
        )
        return {
            "candidate_id": candidate_id,
            "class_order": BINARY_CLASS_ORDER,
            "latent_logits_shape": tuple(output.latent_logits.shape),
            "concept_logits_shape": tuple(output.concept_logits.shape),
            "classifier_cardinality": int(output.latent_logits.shape[1]),
            "concept_classifier_cardinality": int(output.concept_logits.shape[1]),
            "alpha_shape": tuple(output.alpha.shape),
            "intervention": metadata["intervention"],
            "ablation_plan": plan.to_dict(),
            "effective_loss_components": effective_components,
            "model_architecture_identity": binary_model_architecture_identity(model),
            "intervention_applied": True,
            "identity_hash": metadata["identity_hash"],
            "prediction_keys": ("prob_cn", "prob_impaired"),
            "validate_only": True,
            "real_run": False,
            "authorization": dict(self.config.authorization),
        }

    def validate_all_ablations(self) -> dict[str, dict[str, Any]]:
        """Validate exactly the six approved binary candidates."""
        return {candidate: self.validate_ablation(candidate) for candidate in self.config.ablations}

    def validate_prototype_batch(
        self, *, source_labels: torch.Tensor, target_logits: torch.Tensor
    ) -> dict[str, Any]:
        source_z = torch.randn(source_labels.shape[0], 4)
        prototypes, valid = build_source_prototypes(source_z, source_labels, class_count=2)
        pseudo = pseudo_label_cross_entropy(target_logits, tau_p=0.95, class_count=2)
        return {
            "valid_source": valid.tolist(),
            "prototype_shape": tuple(prototypes.shape),
            "accepted_count": pseudo.accepted_count,
            "loss": float(pseudo.loss.detach()),
            "loss_name": "CrossEntropyLoss",
        }

    def validate_pseudo_batch(self, logits: torch.Tensor, *, tau: float) -> dict[str, Any]:
        pseudo = pseudo_label_cross_entropy(logits, tau_p=tau, class_count=2)
        return {
            "accepted_count": pseudo.accepted_count,
            "loss": float(pseudo.loss.detach()),
            "loss_name": "CrossEntropyLoss",
        }

    def run(self, *_args: Any, **_kwargs: Any) -> None:
        raise ConfigurationError(
            "Binary publication runtime is validate-only; real training and evaluation are forbidden."
        )

    execute = run


def validate_binary_publication(path: str | Path) -> dict[str, dict[str, Any]]:
    """Convenience entry point for the complete synthetic CPU contract."""
    return BinaryPublicationRuntime.from_path(path).validate_all()


def validate_binary_concept_evaluation(
    records: Sequence[Any], **kwargs: Any
) -> dict[str, Any]:
    """Task-scoped binary concept evaluation with no artifact regeneration."""
    from pada3dacb.evaluation.concepts.report import evaluate_binary_concept_records

    return evaluate_binary_concept_records(
        records, task_id=BINARY_TASK_ID, **kwargs
    )



def select_binary_checkpoint(candidates: Any) -> Mapping[str, Any]:
    """Select checkpoints only by source-validation macro-F1."""
    from pada3dacb.binary import select_best_checkpoint_by_source_validation_macro_f1
    return select_best_checkpoint_by_source_validation_macro_f1(candidates)


select_best_checkpoint_by_source_validation_macro_f1 = select_binary_checkpoint
