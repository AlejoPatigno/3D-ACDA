"""Prepare and inspect the Phase 18 publication freeze without running anything."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Keep this script runnable from a source checkout without importing runtime code.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml  # noqa: E402

from pada3dacb.publication.authorization import check_authorization, format_blockers  # noqa: E402
from pada3dacb.publication.experiment_matrix import RowState, generate_matrix  # noqa: E402
from pada3dacb.publication.freeze import (  # noqa: E402
    FreezeValidationError,
    build_freeze_payload,
    write_freeze,
)

DEFAULT_CONFIG = Path("configs/publication/publication_experiment_freeze.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--feasibility-only", action="store_true")
    parser.add_argument("--print-matrix", action="store_true")
    parser.add_argument("--print-blockers", action="store_true")
    parser.add_argument("--write-freeze", action="store_true")
    parser.add_argument("--overwrite-freeze", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load_config(args.config)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"CONFIGURATION ERROR: {exc}")
        return 2

    if args.print_matrix:
        try:
            matrix = _planning_matrix(config)
        except (KeyError, TypeError, ValueError) as exc:
            print(f"MATRIX BLOCKED: {exc}")
        else:
            print(json.dumps({"matrix_id": matrix.matrix_id, "rows": list(matrix.to_rows())}, indent=2))

    result = check_authorization(config)
    if args.print_blockers or args.validate_only or args.feasibility_only or args.print_matrix:
        print("BLOCKERS:")
        print(format_blockers(result))

    if args.feasibility_only:
        print("FEASIBILITY-ONLY: synthetic contracts only; no real data access.")
        return 4 if result.blockers else 0

    if args.write_freeze:
        if args.output_root is None:
            print("CONFIGURATION ERROR: --output-root is required with --write-freeze")
            return 2
        try:
            source = config.get("freeze_payload", config)
            payload = build_freeze_payload(source)
            destination = args.output_root / "publication_freeze.json"
            write_freeze(destination, payload, overwrite=args.overwrite_freeze)
        except (FreezeValidationError, OSError) as exc:
            print(f"FREEZE WRITE BLOCKED: {exc}")
            return 2
        print(f"PLANNING FREEZE WRITTEN: {destination}")
        return 0

    if args.device != "cpu":
        print("BLOCKERS:\n- resource_budget_unresolved: only CPU planning validation is supported")
        return 4
    if args.validate_only or args.print_blockers or args.print_matrix:
        return 4 if result.blockers else 0
    print("PREPARATION ONLY: no training, evaluation, publication analysis, or real-data access.")
    return 4 if result.blockers else 0


def _load_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("configuration root must be a mapping")
    return value


def _planning_matrix(config: dict[str, Any]):
    definition = config.get("matrix")
    if not isinstance(definition, dict):
        raise ValueError("matrix definition is missing")
    required = ("methods", "directions", "folds", "seeds")
    if any(field not in definition for field in required):
        raise ValueError("matrix dimensions must be explicit")
    return generate_matrix(
        methods=definition["methods"],
        directions=definition["directions"],
        folds=definition["folds"],
        seeds=definition["seeds"],
        state=RowState.BLOCKED_CONFIGURATION,
    )


if __name__ == "__main__":
    raise SystemExit(main())
