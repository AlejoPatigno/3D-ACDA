"""CLI for Phase 3 derivative verification."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from acda3d.data.derivative_verification import (
    VerificationStatus,
    load_verification_config,
    verify_inventory,
)
from acda3d.exceptions import ACDA3DError, ConfigurationError, InvalidPathError
from acda3d.training.experiment_logging import setup_experiment_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify existing MRI derivatives without modifying them.")
    parser.add_argument("--config", default="configs/verification/derivatives.yaml")
    parser.add_argument("--inventory", default=None)
    parser.add_argument("--atlas", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--strict-physical-geometry", action="store_true")
    parser.add_argument("--subjects", nargs="*", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-overlays", action="store_true")
    return parser.parse_args()


def main() -> int:
    start = time.time()
    args = parse_args()
    logger = setup_experiment_logger("acda3d.verify_derivatives", level=logging.INFO)
    try:
        cfg, paths = load_verification_config(args.config)
        inventory = Path(args.inventory) if args.inventory else paths["inventory_csv"]
        atlas = Path(args.atlas) if args.atlas else paths["atlas_path"]
        output_dir = Path(args.output_dir) if args.output_dir else paths["output_dir"]
        if inventory is None or atlas is None or output_dir is None:
            raise InvalidPathError("--inventory, --atlas and --output-dir are required.")
        if args.sample_size is not None:
            cfg.overlay_sample_size = args.sample_size
        if args.seed is not None:
            cfg.overlay_seed = args.seed
        if args.strict_physical_geometry:
            cfg.strict_physical_geometry = True
        if args.no_overlays:
            cfg.generate_overlays = False
        if args.overwrite:
            cfg.overwrite_reports = True
        if output_dir.exists() and any(output_dir.iterdir()) and not cfg.overwrite_reports:
            raise InvalidPathError(f"Output directory is not empty; use --overwrite: {output_dir}")
        logger.info("configuration=%s", args.config)
        logger.info("inventory=%s", inventory)
        logger.info("atlas=%s", atlas)
        logger.info("output_dir=%s", output_dir)
        results, atlas_meta = verify_inventory(
            inventory,
            atlas,
            output_dir,
            cfg,
            subjects=set(args.subjects) if args.subjects else None,
        )
        counts: dict[str, int] = {}
        for result in results:
            counts[result.overall_status.value] = counts.get(result.overall_status.value, 0) + 1
        logger.info("atlas_status=%s", atlas_meta.atlas_integrity_status.value)
        logger.info("subjects=%d summary=%s runtime_seconds=%.3f", len(results), counts, time.time() - start)
        if cfg.fail_on_subject_failure and counts.get(VerificationStatus.FAILED.value, 0):
            return 2
        return 0
    except (ACDA3DError, OSError, ValueError) as exc:
        logger.error("%s", exc)
        if isinstance(exc, ConfigurationError):
            return 3
        if isinstance(exc, InvalidPathError):
            return 4
        return 1


if __name__ == "__main__":
    sys.exit(main())
