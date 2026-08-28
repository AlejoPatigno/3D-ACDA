"""Minimal interface shared by approved adaptation methods."""

from __future__ import annotations

from typing import Protocol

from acda3d.adaptation.outputs import AdaptationLossOutput
from acda3d.models import ACDA3DOutput


class AdaptationMethod(Protocol):
    name: str
    feature: str

    def compute(
        self,
        source_output: ACDA3DOutput,
        target_output: ACDA3DOutput,
        stage: str,
    ) -> AdaptationLossOutput: ...
