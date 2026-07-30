from __future__ import annotations

from pathlib import Path

import pandas as pd
import torch
import yaml


def make_baseline_environment(
    tmp_path: Path,
    *,
    n_splits: int = 2,
    n_epochs: int = 1,
    samples_per_class: int | None = None,
    tensor_shape: tuple[int, int, int] = (4, 4, 4),
) -> Path:
    rows = [
        {
            "x_path": str(tmp_path / f"{cohort}_{label}_{index}.pt"),
            "label": label,
            "cohort": cohort,
            "subject_id": f"{cohort}-{label}-{index}",
            "subject_hash": f"{cohort}-{label}-{index}-hash",
        }
        for cohort in ("ADNI", "OASIS")
        for label in ("CN", "MCI", "AD")
        for index in range(samples_per_class or max(2, n_splits))
    ]
    for row in rows:
        torch.save(torch.ones(1, *tensor_shape), row["x_path"])
    roi_path = tmp_path / "roi_masks.pt"
    roi_masks = torch.zeros(2, *tensor_shape)
    roi_masks[0, : tensor_shape[0] // 2] = 1
    roi_masks[1, tensor_shape[0] // 2 :] = 1
    torch.save({"roi_masks": roi_masks}, roi_path)
    inventory_path = tmp_path / "inventory.csv"
    pd.DataFrame(rows).to_csv(inventory_path, index=False)

    baseline_dir = tmp_path / "baselines"
    baseline_dir.mkdir(exist_ok=True)
    (baseline_dir / "aagn.yaml").write_text(
        yaml.safe_dump({"baseline": {"id": "aagn", "constructor": {"n_classes": 3}}}),
        encoding="utf-8",
    )
    (baseline_dir / "faster_snn.yaml").write_text(
        yaml.safe_dump(
            {"baseline": {"id": "faster_snn", "constructor": {"n_classes": 3}}}
        ),
        encoding="utf-8",
    )
    config = {
        "experiment": {
            "name": "synthetic-baselines",
            "method": "baseline",
            "baseline_names": ["aagn", "faster_snn"],
            "source_domain": "ADNI",
            "target_domain": "OASIS",
            "n_splits": n_splits,
            "folds": list(range(n_splits)),
            "seeds": [42],
        },
        "paths": {
            "artifact_index": str(inventory_path),
            "output_root": str(tmp_path / "runs"),
            "roi_masks": str(roi_path),
        },
        "baseline_configs": {
            "aagn": "baselines/aagn.yaml",
            "faster_snn": "baselines/faster_snn.yaml",
        },
        "training": {"n_epochs": n_epochs, "use_amp": False, "device": "cpu"},
        "evaluation": {"target_monitoring": True},
        "execution": {"sequential": True, "overwrite": False},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path
