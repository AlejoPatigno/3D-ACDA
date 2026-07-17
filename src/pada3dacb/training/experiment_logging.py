"""Experiment logging setup."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


class _ContextFilter(logging.Filter):
    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        record.experiment_context = " ".join(
            f"{key}={value}" for key, value in sorted(self.context.items())
        )
        return True


def setup_experiment_logger(
    name: str,
    log_file: Path | None = None,
    level: int = logging.INFO,
    context: dict[str, Any] | None = None,
) -> logging.Logger:
    """Configure a console/file logger without duplicate handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(experiment_context)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    logger.handlers.clear()
    logger.filters.clear()
    logger.addFilter(_ContextFilter(context))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
