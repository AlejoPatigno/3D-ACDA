"""Deterministic DataLoader builders preserving notebook defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from torch.utils.data import DataLoader, Dataset

from acda3d.training.reproducibility import make_torch_generator, seed_worker


@dataclass
class DataLoaderConfig:
    batch_size: int = 16
    num_workers: int = 2
    pin_memory: bool = True
    persistent_workers: bool = False
    prefetch_factor: int = 2
    drop_last_train: bool = True
    drop_last_eval: bool = False


def _loader(dataset: Dataset, config: DataLoaderConfig, *, shuffle: bool, drop_last: bool, seed: int) -> DataLoader:
    kwargs: dict[str, Any] = {
        "dataset": dataset,
        "batch_size": config.batch_size,
        "shuffle": shuffle,
        "drop_last": drop_last,
        "num_workers": config.num_workers,
        "pin_memory": config.pin_memory,
        "worker_init_fn": seed_worker,
        "generator": make_torch_generator(seed),
    }
    if config.num_workers > 0:
        kwargs["persistent_workers"] = config.persistent_workers
        kwargs["prefetch_factor"] = config.prefetch_factor
    return DataLoader(**kwargs)


def build_source_train_loader(dataset: Dataset, config: DataLoaderConfig | None = None, *, seed: int = 42) -> DataLoader:
    cfg = config or DataLoaderConfig()
    return _loader(dataset, cfg, shuffle=True, drop_last=cfg.drop_last_train, seed=seed)


def build_source_validation_loader(dataset: Dataset, config: DataLoaderConfig | None = None, *, seed: int = 42) -> DataLoader:
    cfg = config or DataLoaderConfig()
    return _loader(dataset, cfg, shuffle=False, drop_last=cfg.drop_last_eval, seed=seed)


def build_target_adaptation_loader(dataset: Dataset, config: DataLoaderConfig | None = None, *, seed: int = 42) -> DataLoader:
    cfg = config or DataLoaderConfig()
    return _loader(dataset, cfg, shuffle=True, drop_last=cfg.drop_last_train, seed=seed)


def build_target_evaluation_loader(dataset: Dataset, config: DataLoaderConfig | None = None, *, seed: int = 42) -> DataLoader:
    cfg = config or DataLoaderConfig()
    return _loader(dataset, cfg, shuffle=False, drop_last=cfg.drop_last_eval, seed=seed)


def build_supervised_loader(dataset: Dataset, config: DataLoaderConfig | None = None, *, training: bool = True, seed: int = 42) -> DataLoader:
    cfg = config or DataLoaderConfig()
    return _loader(dataset, cfg, shuffle=training, drop_last=cfg.drop_last_train if training else cfg.drop_last_eval, seed=seed)
