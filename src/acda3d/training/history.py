"""Durable epoch-by-epoch training history."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TrainingHistory:
    rows: list[dict[str, Any]] = field(default_factory=list)

    def append(self, row: dict[str, Any]) -> None:
        self.rows.append(dict(row))

    def flush(self, run_dir: Path) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        all_fields = sorted({key for row in self.rows for key in row})
        path = run_dir / "training_history.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=all_fields)
            writer.writeheader()
            writer.writerows(self.rows)
        runtime = {
            "epochs_completed": len(self.rows),
            "total_train_seconds": sum(float(row.get("epoch_train_seconds", 0)) for row in self.rows),
            "total_source_validation_seconds": sum(
                float(row.get("source_validation_seconds", 0)) for row in self.rows
            ),
            "total_target_monitoring_seconds": sum(
                float(row.get("target_monitoring_seconds", 0)) for row in self.rows
            ),
        }
        (run_dir / "runtime.json").write_text(
            json.dumps(runtime, indent=2, sort_keys=True), encoding="utf-8"
        )
