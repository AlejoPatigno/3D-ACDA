"""Reproducibility helpers for fixed-seed experiments."""

from __future__ import annotations

import platform
import random
from typing import Any

import numpy as np
import torch


def seed_everything(seed: int, deterministic: bool = True) -> None:
    """Seed Python, NumPy and PyTorch random number generators."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    if deterministic:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)


def seed_worker(worker_id: int) -> None:
    """Seed a DataLoader worker from PyTorch's worker seed."""
    worker_seed = (torch.initial_seed() + worker_id) % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def make_torch_generator(seed: int) -> torch.Generator:
    """Create a CPU torch generator seeded for DataLoader use."""
    generator = torch.Generator()
    generator.manual_seed(seed)
    return generator


def collect_reproducibility_metadata() -> dict[str, Any]:
    """Collect non-private runtime metadata useful for reproducibility."""
    cuda_available = torch.cuda.is_available()
    gpu_names = []
    if cuda_available:
        gpu_names = [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())]

    return {
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "cuda_available": cuda_available,
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "gpu_names": gpu_names,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
    }
