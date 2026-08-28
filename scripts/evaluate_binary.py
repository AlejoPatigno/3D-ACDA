"""Validate-only synthetic Phase 18B binary evaluation entry point."""
from __future__ import annotations

import argparse
import json
import sys

from acda3d.evaluation.binary import binary_evaluation_payload


def _synthetic_rows() -> list[dict[str, object]]:
    return [
        {"subject_hash": "synthetic-cn", "cohort": "ADNI", "true_label": 0, "prob_cn": 0.8, "prob_impaired": 0.2},
        {"subject_hash": "synthetic-impaired", "cohort": "OASIS", "true_label": 1, "prob_cn": 0.2, "prob_impaired": 0.8},
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="run the synthetic contract validation")
    parser.add_argument("--synthetic", action="store_true", help="use the built-in synthetic rows")
    parser.add_argument("--task", default="cn_vs_impaired")
    parser.add_argument("--real-run", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.real_run or not args.validate_only:
        print("Phase 18B binary CLI is validate-only; real runs are forbidden.", file=sys.stderr)
        return 2
    if args.task != "cn_vs_impaired":
        print("task must be cn_vs_impaired", file=sys.stderr)
        return 2
    payload = binary_evaluation_payload(_synthetic_rows(), task_hash="synthetic-phase18b")
    payload.update({"validate_only": True, "real_run": False, "synthetic": True})
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
