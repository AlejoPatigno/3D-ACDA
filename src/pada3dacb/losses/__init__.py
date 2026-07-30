"""Core non-adaptation scientific losses for PADA-3DACB."""

from pada3dacb.losses.anatomical import AnatomicalConsistencyLoss
from pada3dacb.losses.classification import ClassificationLoss
from pada3dacb.losses.concept import ConceptSupervisionLoss
from pada3dacb.losses.consistency import PredictionConsistencyLoss
from pada3dacb.losses.core_total import CoreLossWeights, CorePADA3DACBLoss
from pada3dacb.losses.outputs import CoreLossOutput

__all__ = [
    "AnatomicalConsistencyLoss",
    "ClassificationLoss",
    "ConceptSupervisionLoss",
    "CoreLossOutput",
    "CoreLossWeights",
    "CorePADA3DACBLoss",
    "PredictionConsistencyLoss",
]
