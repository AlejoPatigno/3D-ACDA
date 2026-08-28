"""Create immutable deterministic split manifests from a Phase 5 artifact index."""

from __future__ import annotations

import argparse
from pathlib import Path

from acda3d.data.artifact_wiring import load_artifact_index
from acda3d.data.splits import Direction, create_direction_splits, load_split_config
from acda3d.training.experiment_logging import setup_experiment_logger
from acda3d.training.reproducibility import seed_everything


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--config", required=True)
    command.add_argument("--artifact-index")
    command.add_argument("--artifact-root")
    command.add_argument("--split-root")
    command.add_argument("--source-domain", choices=["ADNI", "OASIS"])
    command.add_argument("--target-domain", choices=["ADNI", "OASIS"])
    command.add_argument("--all-directions", action="store_true")
    command.add_argument("--n-splits", type=int)
    command.add_argument("--target-adaptation-fraction", type=float)
    command.add_argument("--seed", type=int)
    command.add_argument("--overwrite", action="store_true")
    command.add_argument("--dry-run", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = load_split_config(args.config)
    for name in ("artifact_index", "artifact_root", "split_root"):
        value = getattr(args, name)
        if value is not None:
            setattr(config, name, Path(value).resolve())
    if args.n_splits is not None:
        config.splits.n_splits = args.n_splits
    if args.target_adaptation_fraction is not None:
        config.splits.target_adaptation_fraction = args.target_adaptation_fraction
    if args.seed is not None:
        config.splits.seed = args.seed
    config.splits.overwrite = args.overwrite
    config.splits.dry_run = args.dry_run
    if args.all_directions:
        directions = config.directions
    else:
        if not args.source_domain or not args.target_domain:
            raise SystemExit("Specify --all-directions or both --source-domain and --target-domain.")
        directions = [Direction(args.source_domain, args.target_domain)]
    config.directions = directions
    config.validate()
    assert config.artifact_index is not None and config.split_root is not None
    setup_experiment_logger("acda3d.splits")
    seed_everything(config.splits.seed)
    loaded = load_artifact_index(config.artifact_index, artifact_root=config.artifact_root, profile="classification_only")
    for direction in directions:
        result = create_direction_splits(loaded.records, direction, config.splits, config.artifact_index, config.split_root)
        state = "DRY_RUN" if result.dry_run else "REUSED" if result.reused else "CREATED"
        print(f"{direction.name}: {state} assignment_hash={result.protocol['split_assignment_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
