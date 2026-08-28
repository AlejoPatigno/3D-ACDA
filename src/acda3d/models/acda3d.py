"""Direct production implementation of the former Lite 3D-ACDA path."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

import torch
from torch import nn

from acda3d.exceptions import ConfigurationError, ModelContractError
from acda3d.models.attention_aggregation import AttentionAggregator
from acda3d.models.classification_head import ClassificationHead
from acda3d.models.concept_bottleneck import ConceptBottleneck
from acda3d.models.encoder3d import Encoder3D
from acda3d.models.roi_tokenizer import ROITokenizer

PUBLIC_MODEL_NAME = "3D-ACDA"
CLASS_ORDER = ("CN", "MCI", "AD")


@dataclass(frozen=True)
class ACDA3DOutput(Mapping[str, torch.Tensor]):
    """Stable retained forward tensors plus documented notebook aliases."""

    F: torch.Tensor
    T: torch.Tensor
    U: torch.Tensor
    z: torch.Tensor
    alpha: torch.Tensor
    latent_logits: torch.Tensor
    latent_probabilities: torch.Tensor
    concepts: torch.Tensor
    concept_logits: torch.Tensor
    concept_probabilities: torch.Tensor

    @property
    def logits(self) -> torch.Tensor:
        return self.latent_logits

    @property
    def probs(self) -> torch.Tensor:
        return self.latent_probabilities

    @property
    def c(self) -> torch.Tensor:
        return self.concepts

    @property
    def cbm_logits(self) -> torch.Tensor:
        return self.concept_logits

    @property
    def logits_cbm(self) -> torch.Tensor:
        return self.concept_logits

    @property
    def probs_cbm(self) -> torch.Tensor:
        return self.concept_probabilities

    def to_legacy_dict(self) -> dict[str, torch.Tensor]:
        """Return the eight keys consumed by the canonical notebook trainer."""
        return {
            "F": self.F,
            "T": self.T,
            "U": self.U,
            "z": self.z,
            "alpha": self.alpha,
            "logits": self.latent_logits,
            "c": self.concepts,
            "cbm_logits": self.concept_logits,
        }

    def __getitem__(self, key: str) -> torch.Tensor:
        aliases = {
            "logits": "latent_logits",
            "probs": "latent_probabilities",
            "c": "concepts",
            "cbm_logits": "concept_logits",
            "logits_cbm": "concept_logits",
            "probs_cbm": "concept_probabilities",
        }
        name = aliases.get(key, key)
        if name not in {field.name for field in fields(self)}:
            raise KeyError(key)
        return getattr(self, name)

    def __iter__(self) -> Iterator[str]:
        return (field.name for field in fields(self))

    def __len__(self) -> int:
        return len(fields(self))


class ACDA3D(nn.Module):
    """Explicit 3D-ACDA model with no contextual ROI encoder."""

    public_name = PUBLIC_MODEL_NAME
    class_order = CLASS_ORDER

    def __init__(
        self,
        num_rois: int = 84,
        feature_dim: int = 256,
        token_dim: int = 128,
        num_classes: int = 3,
        base_channels: int = 32,
        concept_hidden_dim: int = 64,
        token_dropout: float = 0.2,
        concept_dropout: float = 0.2,
        validate_inputs: bool = True,
    ):
        super().__init__()
        if num_classes not in {2, len(CLASS_ORDER)}:
            raise ModelContractError("3D-ACDA supports only the historical three-class or Phase 18B binary head.")
        if min(num_rois, feature_dim, token_dim, base_channels, concept_hidden_dim) <= 0:
            raise ModelContractError("All model dimensions must be positive.")
        self.num_rois = num_rois
        self.feature_dim = feature_dim
        self.token_dim = token_dim
        self.num_classes = num_classes
        self.class_order = ("CN", "Impaired") if num_classes == 2 else CLASS_ORDER
        self.validate_inputs = validate_inputs
        self.encoder = Encoder3D(feature_dim=feature_dim, base_channels=base_channels)
        self.tokenizer = ROITokenizer(num_rois, feature_dim, token_dim)
        self.token_norm = nn.LayerNorm(token_dim)
        self.token_mlp = nn.Sequential(
            nn.Linear(token_dim, token_dim),
            nn.GELU(),
            nn.Dropout(token_dropout),
            nn.Linear(token_dim, token_dim),
        )
        self.token_dropout = nn.Dropout(token_dropout)
        self.aggregator = AttentionAggregator(token_dim)
        self.cls_head = ClassificationHead(token_dim, num_classes)
        self.cbm = ConceptBottleneck(
            num_rois, token_dim, num_classes, concept_hidden_dim, concept_dropout
        )

    def _validate_x(self, x: torch.Tensor) -> None:
        if x.ndim != 5 or x.shape[1] != 1:
            raise ModelContractError(f"x must have shape (B,1,H,W,D), got {tuple(x.shape)}.")
        if x.dtype != torch.float32:
            raise ModelContractError(f"x must use float32, got {x.dtype}.")
        if not torch.isfinite(x).all():
            raise ModelContractError("x must contain only finite values.")
        if x.device != next(self.parameters()).device:
            raise ModelContractError("x and model parameters must be on the same device.")

    def forward(self, x: torch.Tensor, roi_masks: torch.Tensor) -> ACDA3DOutput:
        if self.validate_inputs:
            self._validate_x(x)
        feature_map = self.encoder(x)
        tokens = self.tokenizer(feature_map, roi_masks)
        tokens = self.token_norm(tokens)
        tokens = tokens + self.token_mlp(tokens)
        tokens = self.token_dropout(tokens)
        non_contextual_tokens = tokens
        embedding, attention = self.aggregator(non_contextual_tokens)
        latent_logits = self.cls_head(embedding)
        concepts, concept_logits = self.cbm(non_contextual_tokens)
        return ACDA3DOutput(
            F=feature_map,
            T=tokens,
            U=non_contextual_tokens,
            z=embedding,
            alpha=attention,
            latent_logits=latent_logits,
            latent_probabilities=torch.softmax(latent_logits, dim=-1),
            concepts=concepts,
            concept_logits=concept_logits,
            concept_probabilities=torch.softmax(concept_logits, dim=-1),
        )

    @torch.no_grad()
    def predict(self, x: torch.Tensor, roi_masks: torch.Tensor) -> dict[str, torch.Tensor]:
        output = self(x, roi_masks)
        return {
            "y_hat": output.concept_probabilities.argmax(dim=-1),
            "p_tilde": output.concept_probabilities,
            "c": output.concepts,
            "alpha": output.alpha,
        }


def _config_mapping(config: Any) -> dict[str, Any]:
    if hasattr(config, "model") and not isinstance(config, Mapping):
        config = config.model
    if is_dataclass(config):
        return {field.name: getattr(config, field.name) for field in fields(config)}
    if isinstance(config, Mapping):
        data = dict(config)
        return dict(data.get("model", data))
    raise ConfigurationError("Model configuration must be a mapping or ModelConfig instance.")


def build_acda3d(config: Any, roi_masks: torch.Tensor | None = None) -> ACDA3D:
    """Validate configuration and instantiate only retained model components."""
    task_id = getattr(config, "task_id", None)
    task_type = getattr(config, "task_type", None)
    if isinstance(config, Mapping):
        task_id = config.get("task_id", config.get("task"))
        task_type = config.get("task_type")
        if isinstance(task_id, str) and task_id.strip().lower() in {"cn_vs_impaired", "cn_vs_impaired_task"}:
            task_id = "cn_vs_impaired"
    data = _config_mapping(config)
    if task_id == "cn_vs_impaired":
        if task_type not in {None, "binary_classification"}:
            raise ConfigurationError("CN_vs_Impaired requires task_type='binary_classification'.")
        if int(data.get("num_classes", 3)) != 2:
            raise ConfigurationError("CN_vs_Impaired is the sole publication class source and requires num_classes=2.")
        if isinstance(config, Mapping):
            if config.get("class_order") not in (None, ["CN", "Impaired"], ("CN", "Impaired")):
                raise ConfigurationError("CN_vs_Impaired requires class_order=[CN, Impaired].")
            if config.get("class_ids") not in (None, {"CN": 0, "Impaired": 1}):
                raise ConfigurationError("CN_vs_Impaired requires class_ids CN=0 and Impaired=1.")
    if data.get("name", PUBLIC_MODEL_NAME) != PUBLIC_MODEL_NAME:
        raise ConfigurationError(f"The production model name must be {PUBLIC_MODEL_NAME!r}.")
    if data.get("contextual_encoder", False) is not False:
        raise ConfigurationError("contextual_encoder must be false for 3D-ACDA.")
    if int(data.get("input_channels", 1)) != 1:
        raise ConfigurationError("3D-ACDA requires one MRI input channel.")
    encoder = dict(data.get("encoder") or {})
    tokenizer = dict(data.get("tokenizer") or {})
    token_processing = dict(data.get("token_processing") or {})
    concept = dict(data.get("concept_bottleneck") or {})
    num_rois = int(data.get("num_rois", 84))
    if roi_masks is not None and (
        roi_masks.ndim != 4 or roi_masks.shape[0] != num_rois
    ):
        raise ConfigurationError(
            f"Injected ROI masks must begin with configured K={num_rois}, got {tuple(roi_masks.shape)}."
        )
    return ACDA3D(
        num_rois=num_rois,
        feature_dim=int(tokenizer.get("feature_dim", encoder.get("output_channels", 256))),
        token_dim=int(tokenizer.get("token_dim", 128)),
        num_classes=int(data.get("num_classes", 3)),
        base_channels=int(encoder.get("base_channels", 32)),
        concept_hidden_dim=int(concept.get("hidden_dim", 64)),
        token_dropout=float(token_processing.get("dropout", 0.2)),
        concept_dropout=float(concept.get("dropout", 0.2)),
    )


@classmethod
def from_config(cls, config: Any) -> ACDA3D:
    """Create ACDA3D from configuration dictionary or object."""
    from acda3d.config import ModelConfig
    if isinstance(config, ModelConfig):
        config = config.model_dump()
    elif hasattr(config, "model"):
        config = config.model
    return build_acda3d(config)


ACDA3D.from_config = from_config
