"""CLI for restartable anatomical and concept artifact precomputation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pada3dacb.artifacts.cache import ensure_artifact_cache, load_precompute_config
from pada3dacb.training.experiment_logging import setup_experiment_logger
from pada3dacb.training.reproducibility import seed_everything


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--config", required=True)
    command.add_argument("--manifest")
    command.add_argument("--atlas")
    command.add_argument("--template")
    command.add_argument("--artifact-root")
    concepts = command.add_mutually_exclusive_group()
    concepts.add_argument("--compute-concepts", action="store_true")
    concepts.add_argument("--no-concepts", action="store_true")
    jacobians = command.add_mutually_exclusive_group()
    jacobians.add_argument("--compute-jacobians", action="store_true")
    jacobians.add_argument("--no-jacobians", action="store_true")
    command.add_argument("--subjects", nargs="*")
    command.add_argument("--cohorts", nargs="*")
    command.add_argument("--limit", type=int)
    command.add_argument("--seed", type=int)
    command.add_argument("--workers", type=int)
    command.add_argument("--resume", action="store_true")
    command.add_argument("--overwrite", action="store_true")
    command.add_argument("--dry-run", action="store_true")
    command.add_argument("--continue-on-error", action="store_true")
    command.add_argument("--save-intermediates", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = load_precompute_config(args.config)
    for name in ("manifest", "atlas", "template", "artifact_root"):
        value = getattr(args, name)
        if value is not None:
            setattr(config.paths, name, Path(value).resolve())
    if args.compute_concepts or args.no_concepts:
        config.precompute.compute_concepts = args.compute_concepts
    if args.compute_jacobians or args.no_jacobians:
        config.precompute.compute_jacobians = args.compute_jacobians
    for name in ("resume", "overwrite", "dry_run", "continue_on_error", "save_intermediates"):
        if getattr(args, name):
            setattr(config.precompute, name, True)
    if args.seed is not None:
        config.execution.seed = args.seed
    if args.workers is not None:
        config.execution.number_of_workers = args.workers
    setup_experiment_logger("pada3dacb.precompute", level=logging.INFO)
    seed_everything(config.execution.seed)
    index = ensure_artifact_cache(config, subjects=set(args.subjects or []), cohorts=set(args.cohorts or []), limit=args.limit)
    print(f"Phase 5 artifact planning/computation completed for {len(index)} subjects.")
    print(f"Artifact root: {config.paths.artifact_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
