"""Compatibility facade for the task-scoped Phase 18B binary runtime.

The publication package exposes the historical import path, while the
validate-only implementation lives under ``acda3d.tasks`` so publication
code remains independent of model and data runtime dependencies.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_PUBLIC_NAMES = (
    "BINARY_PUBLICATION_METHODS",
    "BINARY_TASK_ID",
    "BINARY_TASK_TYPE",
    "BINARY_CLASS_ORDER",
    "BINARY_CLASS_TO_INDEX",
    "BINARY_MAPPING_CONTRACT",
    "BinaryPublicationConfig",
    "load_binary_publication_config",
    "BinaryPublicationRuntime",
    "validate_binary_publication",
    "validate_binary_concept_evaluation",
    "select_binary_checkpoint",
    "select_best_checkpoint_by_source_validation_macro_f1",
)

__all__ = list(_PUBLIC_NAMES)


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    implementation = import_module("acda3d.tasks.binary_runtime")
    value = getattr(implementation, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
