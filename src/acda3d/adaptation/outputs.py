"""Typed outputs for approved domain-adaptation losses."""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class AdaptationLossOutput:
    total: torch.Tensor
    components: dict[str, torch.Tensor]
    diagnostics: dict[str, torch.Tensor]

    def detached(self) -> dict[str, float]:
        values = {
            name: float(value.detach().cpu())
            for name, value in self.components.items()
        }
        values.update(
            {name: float(value.detach().cpu()) for name, value in self.diagnostics.items()}
        )
        return values
