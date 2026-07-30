"""Source-supervised specialization of the fixed-epoch infrastructure."""

from pada3dacb.training.trainer import BaseFixedEpochTrainer


class SourceOnlyTrainer(BaseFixedEpochTrainer):
    """Uses only labeled source batches; method-level execution comes later."""

    uses_target_adaptation = False
