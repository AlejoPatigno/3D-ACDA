"""Runtime helpers shared by fixed-epoch trainers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import cycle
from typing import Any

import torch

from pada3dacb.exceptions import TrainingRuntimeError


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        key: value.to(device, non_blocking=True) if torch.is_tensor(value) else value
        for key, value in batch.items()
    }


def require_batch_keys(batch: dict[str, Any], keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in batch]
    if missing:
        raise TrainingRuntimeError(f"Batch is missing required keys: {missing}.")


def validate_nonempty_loader(loader: Any, name: str) -> None:
    try:
        length = len(loader)
    except TypeError as error:
        raise TrainingRuntimeError(f"{name} must have a defined number of batches.") from error
    if length == 0:
        raise TrainingRuntimeError(
            f"{name} contains zero batches. Review split size, batch_size, and drop_last."
        )


def iterate_source_with_cycled_target(
    source_loader: Iterable[Any], target_loader: Iterable[Any]
) -> Iterator[tuple[Any, Any]]:
    """Canonical UDA policy: one step per source batch and cyclic target batches."""
    validate_nonempty_loader(source_loader, "source_loader")
    validate_nonempty_loader(target_loader, "target_loader")
    target_iterator = cycle(target_loader)
    for source_batch in source_loader:
        yield source_batch, next(target_iterator)


def loader_generator_state(loader: Any) -> torch.Tensor | None:
    generator = getattr(loader, "generator", None)
    return generator.get_state() if isinstance(generator, torch.Generator) else None


def restore_loader_generator_state(loader: Any, state: torch.Tensor | None) -> None:
    if state is None:
        return
    generator = getattr(loader, "generator", None)
    if not isinstance(generator, torch.Generator):
        raise TrainingRuntimeError("Checkpoint has loader RNG state but loader has no generator.")
    generator.set_state(state)
