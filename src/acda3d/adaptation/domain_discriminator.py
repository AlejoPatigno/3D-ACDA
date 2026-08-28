"""Validated binary MLP domain discriminator used only by CDAN."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import torch
from torch import Tensor, nn

from acda3d.exceptions import ConfigurationError, LossContractError


@dataclass(frozen=True)
class DomainDiscriminatorConfig:
    input_dim: int
    hidden_dims: tuple[int, ...]
    activation: str = "relu"
    dropout: float = 0.0
    output_dim: int = 1
    initialization: str = "pytorch_default"

    def __init__(
        self,
        input_dim: int,
        hidden_dims: Iterable[int] | None,
        activation: str = "relu",
        dropout: float = 0.0,
        output_dim: int = 1,
        initialization: str = "pytorch_default",
    ) -> None:
        normalized_hidden_dims = () if hidden_dims is None else tuple(int(value) for value in hidden_dims)
        object.__setattr__(self, "input_dim", int(input_dim))
        object.__setattr__(self, "hidden_dims", normalized_hidden_dims)
        object.__setattr__(self, "activation", str(activation))
        object.__setattr__(self, "dropout", float(dropout))
        object.__setattr__(self, "output_dim", int(output_dim))
        object.__setattr__(self, "initialization", str(initialization))

    def validate(self) -> None:
        if self.input_dim <= 0 or not self.hidden_dims or any(value <= 0 for value in self.hidden_dims):
            raise ConfigurationError("CDAN discriminator requires positive input and hidden dimensions.")
        if self.activation not in {"relu", "gelu", "leaky_relu"}:
            raise ConfigurationError("CDAN discriminator activation must be relu, gelu, or leaky_relu.")
        if not 0.0 <= self.dropout < 1.0:
            raise ConfigurationError("CDAN discriminator dropout must be in [0, 1).")
        if self.output_dim != 1 or self.initialization != "pytorch_default":
            raise ConfigurationError("CDAN discriminator must use output_dim=1 and pytorch_default initialization.")

    def resolved_dict(self) -> dict[str, object]:
        return {
            "input_dim": self.input_dim,
            "hidden_dims": list(self.hidden_dims),
            "activation": self.activation,
            "dropout": self.dropout,
            "output_dim": self.output_dim,
            "initialization": self.initialization,
        }


class DomainDiscriminator(nn.Module):
    def __init__(self, config: DomainDiscriminatorConfig) -> None:
        super().__init__()
        config.validate()
        self.config = config
        activation: type[nn.Module] = {"relu": nn.ReLU, "gelu": nn.GELU, "leaky_relu": nn.LeakyReLU}[config.activation]
        dimensions = (config.input_dim, *config.hidden_dims)
        layers: list[nn.Module] = []
        for left, right in zip(dimensions, dimensions[1:], strict=False):
            layers.extend((nn.Linear(left, right), activation(), nn.Dropout(config.dropout)))
        layers.append(nn.Linear(dimensions[-1], 1))
        self.network = nn.Sequential(*layers)

    def forward(self, conditional_features: Tensor) -> Tensor:
        if conditional_features.ndim != 2 or conditional_features.shape[1] != self.config.input_dim:
            raise LossContractError("CDAN conditional features have an invalid discriminator input shape.")
        if not conditional_features.is_floating_point() or not torch.isfinite(conditional_features).all():
            raise LossContractError("CDAN conditional features must be finite floating-point values.")
        return self.network(conditional_features).squeeze(-1)
