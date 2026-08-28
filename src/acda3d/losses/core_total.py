"""Core source-supervised 3D-ACDA objective without adaptation terms."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from acda3d.exceptions import LossContractError
from acda3d.losses.anatomical import AnatomicalConsistencyLoss
from acda3d.losses.classification import ClassificationLoss
from acda3d.losses.concept import ConceptSupervisionLoss
from acda3d.losses.consistency import PredictionConsistencyLoss
from acda3d.losses.outputs import CoreLossOutput
from acda3d.models.acda3d import ACDA3DOutput


@dataclass(frozen=True)
class CoreLossWeights:
    classification: float = 1.0
    concept_classification: float = 1.0
    prediction_consistency: float = 0.1
    concept_supervision: float = 0.5
    anatomical_consistency: float = 0.2
    warm_classification: float = 0.1
    warm_concept_classification: float = 1.0
    warm_prediction_consistency: float = 0.0
    warm_concept_supervision: float = 1.0
    warm_anatomical_consistency: float = 1.0

    def validate(self) -> None:
        if any(value < 0 for value in vars(self).values()):
            raise LossContractError("Core loss coefficients must be non-negative.")

    def effective(self, stage: str) -> dict[str, float]:
        """Return coefficients after applying canonical stage multipliers."""
        base = {
            "classification": self.classification,
            "concept_classification": self.concept_classification,
            "prediction_consistency": self.prediction_consistency,
            "concept_supervision": self.concept_supervision,
            "anatomical_consistency": self.anatomical_consistency,
        }
        if stage == "full":
            return base
        if stage != "warm":
            raise LossContractError(f"stage must be 'warm' or 'full', got {stage!r}.")
        return {
            "classification": base["classification"] * self.warm_classification,
            "concept_classification": base["concept_classification"]
            * self.warm_concept_classification,
            "prediction_consistency": base["prediction_consistency"]
            * self.warm_prediction_consistency,
            "concept_supervision": base["concept_supervision"]
            * self.warm_concept_supervision,
            "anatomical_consistency": base["anatomical_consistency"]
            * self.warm_anatomical_consistency,
        }


class CoreACDA3DLoss(nn.Module):
    def __init__(
        self,
        num_rois: int,
        *,
        roi_weights: torch.Tensor | None = None,
        weights: CoreLossWeights | None = None,
        label_smoothing: float = 0.1,
    ):
        super().__init__()
        self.weights = weights or CoreLossWeights()
        self.weights.validate()
        self.latent_classification = ClassificationLoss(label_smoothing)
        self.concept_classification = ClassificationLoss(label_smoothing)
        self.concept_supervision = ConceptSupervisionLoss()
        self.anatomical_consistency = AnatomicalConsistencyLoss(num_rois, roi_weights)
        self.prediction_consistency = PredictionConsistencyLoss()

    def forward(
        self,
        output: ACDA3DOutput,
        labels: torch.Tensor,
        concept_targets: torch.Tensor,
        g_bar: torch.Tensor,
        *,
        stage: str = "full",
    ) -> CoreLossOutput:
        classification = self.latent_classification(output.latent_logits, labels)
        concept_classification = self.concept_classification(output.concept_logits, labels)
        concept_supervision = self.concept_supervision(output.concepts, concept_targets)
        anatomical = self.anatomical_consistency(output.concepts, g_bar)
        consistency = self.prediction_consistency(
            output.latent_logits, output.concept_logits
        )
        effective = self.weights.effective(stage)
        total = (
            effective["classification"] * classification
            + effective["concept_classification"] * concept_classification
            + effective["concept_supervision"] * concept_supervision
            + effective["anatomical_consistency"] * anatomical
            + effective["prediction_consistency"] * consistency
        )
        if not torch.isfinite(total):
            raise LossContractError("Core total loss is non-finite.")
        return CoreLossOutput(
            total=total,
            classification=classification,
            concept_classification=concept_classification,
            concept_supervision=concept_supervision,
            anatomical_consistency=anatomical,
            prediction_consistency=consistency,
        )
