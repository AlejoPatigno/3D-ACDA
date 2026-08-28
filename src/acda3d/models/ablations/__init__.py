"""Explicit Phase 17 architecture-ablation compositions."""

from .mean_pooling import (
    MEAN_POOL_MODEL_VARIANT,
    MEAN_POOL_MODEL_VARIANT_HASH,
    MeanPoolACDA3D,
    MeanPoolAggregator,
    build_mean_pool_model,
    mean_pool_model_variant_hash,
)

__all__ = [
    "MEAN_POOL_MODEL_VARIANT",
    "MEAN_POOL_MODEL_VARIANT_HASH",
    "MeanPoolAggregator",
    "MeanPoolACDA3D",
    "build_mean_pool_model",
    "mean_pool_model_variant_hash",
]
