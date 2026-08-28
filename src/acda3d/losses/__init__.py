"""Core non-adaptation scientific losses for 3D-ACDA."""

from acda3d.losses.anatomical import AnatomicalConsistencyLoss
from acda3d.losses.classification import ClassificationLoss
from acda3d.losses.concept import ConceptSupervisionLoss
from acda3d.losses.consistency import PredictionConsistencyLoss
from acda3d.losses.core_total import CoreACDA3DLoss, CoreLossWeights
from acda3d.losses.outputs import CoreLossOutput

__all__ = [
    "AnatomicalConsistencyLoss",
    "ClassificationLoss",
    "ConceptSupervisionLoss",
    "CoreLossOutput",
    "CoreLossWeights",
    "CoreACDA3DLoss",
    "PredictionConsistencyLoss",
]
