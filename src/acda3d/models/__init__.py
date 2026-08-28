"""Explicit non-contextual 3D-ACDA model components."""

from acda3d.binary import binary_task_class_count, build_binary_model
from acda3d.models.acda3d import (
    ACDA3D,
    ACDA3DOutput,
    build_acda3d,
)
from acda3d.models.attention_aggregation import AttentionAggregator
from acda3d.models.checkpoint_migration import (
    CheckpointMigrationReport,
    load_binary_checkpoint,
    load_migrated_legacy_checkpoint,
    migrate_legacy_lite_state_dict,
)
from acda3d.models.classification_head import ClassificationHead
from acda3d.models.concept_bottleneck import ConceptBottleneck
from acda3d.models.encoder3d import Encoder3D, ResBlock3D
from acda3d.models.roi_mask_preparation import (
    ROIMaskPreparationConfig,
    prepare_feature_grid_roi_masks,
    roi_mask_cache_key,
)
from acda3d.models.roi_tokenizer import ROITokenizer

__all__ = [
    "AttentionAggregator",
    "build_binary_model",
    "binary_task_class_count",
    "CheckpointMigrationReport",
    "ClassificationHead",
    "ConceptBottleneck",
    "Encoder3D",
    "ACDA3D",
    "ACDA3DOutput",
    "ROITokenizer",
    "ROIMaskPreparationConfig",
    "ResBlock3D",
    "build_acda3d",
    "load_binary_checkpoint",
    "load_migrated_legacy_checkpoint",
    "migrate_legacy_lite_state_dict",
    "prepare_feature_grid_roi_masks",
    "roi_mask_cache_key",
]
