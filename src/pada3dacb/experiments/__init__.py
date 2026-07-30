"""Experiment orchestration for approved source-only, CORAL and MMD methods."""

from pada3dacb.experiments.baselines import (
    BaselineExperimentConfig,
    BaselineFoldResult,
    load_baseline_config,
    run_all_requested_baselines,
    run_baseline_both_directions,
    train_baseline_cv_fold,
)
from pada3dacb.experiments.cdan import (
    CDAN_DISPLAY_NAME,
    CDANAdaptationConfig,
    CDANDiscriminatorConfig,
    CDANExperimentConfig,
    CDANExperimentRunner,
    load_cdan_config,
    run_cdan_both_directions,
)
from pada3dacb.experiments.coral import (
    CORAL_DISPLAY_NAME,
    CORALAdaptationConfig,
    CORALExperimentConfig,
    CORALExperimentRunner,
    load_coral_config,
    prepare_coral_fold_inputs,
    run_coral_both_directions,
    stable_weight_directory,
)
from pada3dacb.experiments.mmd import (
    MMD_DISPLAY_NAME,
    MMDAdaptationConfig,
    MMDExperimentConfig,
    MMDExperimentRunner,
    MMDKernelConfig,
    load_mmd_config,
    run_mmd_both_directions,
)
from pada3dacb.experiments.runner import (
    FoldExecutionResult,
    SourceOnlyExperimentRunner,
    prepare_fold_inputs,
    run_both_directions,
)
from pada3dacb.experiments.source_only import (
    DISPLAY_NAME,
    SourceOnlyExperimentConfig,
    load_source_only_config,
)

__all__ = [
    "BaselineExperimentConfig",
    "BaselineFoldResult",
    "CDAN_DISPLAY_NAME",
    "CDANAdaptationConfig",
    "CDANDiscriminatorConfig",
    "CDANExperimentConfig",
    "CDANExperimentRunner",
    "CORAL_DISPLAY_NAME",
    "CORALAdaptationConfig",
    "CORALExperimentConfig",
    "CORALExperimentRunner",
    "DISPLAY_NAME",
    "FoldExecutionResult",
    "MMD_DISPLAY_NAME",
    "MMDAdaptationConfig",
    "MMDExperimentConfig",
    "MMDExperimentRunner",
    "MMDKernelConfig",
    "SourceOnlyExperimentConfig",
    "SourceOnlyExperimentRunner",
    "load_source_only_config",
    "load_baseline_config",
    "load_cdan_config",
    "load_coral_config",
    "load_mmd_config",
    "prepare_coral_fold_inputs",
    "prepare_fold_inputs",
    "run_all_requested_baselines",
    "run_baseline_both_directions",
    "run_both_directions",
    "run_cdan_both_directions",
    "run_coral_both_directions",
    "run_mmd_both_directions",
    "stable_weight_directory",
    "train_baseline_cv_fold",
]
