"""Synthetic, validate-only Phase 18B concept evaluation entry point."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace

from acda3d.evaluation.concepts.report import evaluate_binary_concept_records
from acda3d.evaluation.concepts.schemas import BINARY_CONCEPT_TASK_ID


def _synthetic_records() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            subject_hash="synthetic-cn-1", true_label=0, label_name="CN", K=2,
            predicted_concepts=(0.10, 0.20), concept_targets=(0.05, 0.25),
            anatomical_targets=(0.15, 0.30),
        ),
        SimpleNamespace(
            subject_hash="synthetic-impaired-1", true_label=1, label_name="Impaired", K=2,
            predicted_concepts=(0.75, 0.80), concept_targets=(0.70, 0.85),
            anatomical_targets=(0.65, 0.90),
        ),
    ]


def _json_default(value: object):
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"unsupported output value: {type(value).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default=BINARY_CONCEPT_TASK_ID)
    parser.add_argument(
        "--validate-only", action="store_true", default=False,
        help="run the synthetic contract (the only supported mode)",
    )
    args = parser.parse_args()
    if not args.validate_only:
        parser.error("--validate-only is required; real concept evaluation is not authorized")
    if args.task_id != BINARY_CONCEPT_TASK_ID:
        parser.error("only task_id=cn_vs_impaired is supported")
    result = evaluate_binary_concept_records(
        _synthetic_records(), task_id=args.task_id, bootstrap_replicates=32
    )
    output = {
        "task_id": result["task_id"],
        "class_order": list(result["class_order"]),
        "validate_only": True,
        "real_run": False,
        "synthetic": True,
        "profiles": result["profiles"],
        "provenance": result["provenance"],
    }
    print(json.dumps(output, default=_json_default, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
