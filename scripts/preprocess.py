"""CLI for Phase 4 preprocessing."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pada3dacb.data.preprocessing import load_preprocessing_config, run_preprocessing
from pada3dacb.exceptions import PADA3DACBError
from pada3dacb.training.experiment_logging import setup_experiment_logger
from pada3dacb.training.reproducibility import seed_everything


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run canonical MRI preprocessing.")
    parser.add_argument("--config", default="configs/preprocessing/default.yaml")
    parser.add_argument("--cohort", choices=["ADNI", "OASIS"], default=None)
    parser.add_argument("--input-root", default=None)
    parser.add_argument("--metadata-csv", default=None)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--target-shape", nargs=3, type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--subjects", nargs="*", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_experiment_logger("pada3dacb.preprocess", level=logging.INFO)
    try:
        cfg = load_preprocessing_config(args.config)
        if args.cohort:
            cfg.data.cohort = args.cohort
        if args.input_root:
            cfg.data.input_root = Path(args.input_root)
        if args.metadata_csv:
            cfg.data.metadata_csv = Path(args.metadata_csv)
        if args.output_root:
            cfg.data.output_root = Path(args.output_root)
        if args.target_shape:
            cfg.preprocessing.target_shape = tuple(args.target_shape)
        if args.seed is not None:
            cfg.execution.seed = args.seed
        if args.workers is not None:
            cfg.execution.number_of_workers = args.workers
        if args.resume:
            cfg.preprocessing.resume = True
        if args.overwrite:
            cfg.preprocessing.overwrite = True
        if args.dry_run:
            cfg.preprocessing.dry_run = True
        if args.continue_on_error:
            cfg.preprocessing.continue_on_error = True
        seed_everything(cfg.execution.seed)
        logger.info("configuration=%s cohort=%s input_root=%s output_root=%s", args.config, cfg.data.cohort, cfg.data.input_root, cfg.data.output_root)
        records = run_preprocessing(cfg, limit=args.limit, subjects=set(args.subjects) if args.subjects else None)
        failures = sum(record.status == "FAILED" for record in records)
        logger.info("processed_records=%d failures=%d", len(records), failures)
        if failures and cfg.preprocessing.fail_on_subject_failure:
            return 2
        return 0
    except (PADA3DACBError, OSError, ValueError) as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
