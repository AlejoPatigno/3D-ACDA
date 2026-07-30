from pathlib import Path

import pandas as pd
import torch


def make_artifact_index(tmp_path: Path, per_class: int = 5, shape: tuple[int, int, int] = (2, 2, 2), k: int = 2) -> Path:
    tmp_path = tmp_path.resolve()
    rows = []
    root = tmp_path / "cache"
    for cohort in ("ADNI", "OASIS"):
        for label in ("CN", "MCI", "AD"):
            for number in range(per_class):
                subject = f"{cohort}_{label}_{number:02d}"
                derivative = root / "mri" / f"{subject}.pt"
                concept = root / "concepts" / f"{subject}.pt"
                jacobian = root / "jacobians" / f"{subject}.pt"
                derivative.parent.mkdir(parents=True, exist_ok=True)
                concept.parent.mkdir(parents=True, exist_ok=True)
                jacobian.parent.mkdir(parents=True, exist_ok=True)
                torch.save(torch.full((1, *shape), float(number + 1), dtype=torch.float32), derivative)
                torch.save(torch.tensor([0.25, 0.75], dtype=torch.float32), concept)
                torch.save(torch.tensor([0.4, 0.6], dtype=torch.float32), jacobian)
                rows.append({
                    "subject_id": subject,
                    "subject_hash": f"hash_{subject}",
                    "cohort": cohort,
                    "class_label": label,
                    "label_index": {"CN": 0, "MCI": 1, "AD": 2}[label],
                    "derivative_path": str(derivative.relative_to(root)),
                    "concept_path": str(concept.relative_to(root)),
                    "jacobian_path": str(jacobian.relative_to(root)),
                    "concept_status": "COMPUTED",
                    "jacobian_status": "COMPUTED",
                    "atlas_configuration_hash": "atlas",
                    "precompute_configuration_hash": "precompute",
                    "inventory_row": len(rows),
                })
    index = root / "artifact_index.csv"
    pd.DataFrame(rows).to_csv(index, index=False)
    return index
