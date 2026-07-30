"""Minimal interface shared by approved adaptation methods."""

from __future__ import annotations

from typing import Protocol

from pada3dacb.adaptation.outputs import AdaptationLossOutput
from pada3dacb.models import PADA3DACBOutput


class AdaptationMethod(Protocol):
    name: str
    feature: str

    def compute(
        self,
        source_output: PADA3DACBOutput,
        target_output: PADA3DACBOutput,
        stage: str,
    ) -> AdaptationLossOutput: ...
