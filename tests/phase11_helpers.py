from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader

from pada3dacb.adaptation import MMDAdaptationMethod
from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.training import FixedEpochTrainingConfig, UDATrainer
from tests.phase8_helpers import TinyPADA3DACB
from tests.phase10_helpers import make_coral_environment

SYNTHETIC_BANDWIDTHS = [0.5, 1.0, 2.0]


def make_mmd_environment(
    tmp_path: Path,
    *,
    weight: float | None = 1.0,
    bandwidths: list[float] | None = None,
) -> Path:
    coral_path = make_coral_environment(tmp_path)
    payload = yaml.safe_load(coral_path.read_text(encoding="utf-8"))
    payload["experiment"].update(
        {
            "name": "synthetic_mmd",
            "display_name": "PADA-3DACB + MMD",
            "method": "mmd",
        }
    )
    payload["adaptation"] = {
        "name": "mmd",
        "feature": "z",
        "weight": weight,
        "active_during_warmup": False,
        "kernel": {
            "name": "gaussian_rbf_mixture",
            "bandwidths": SYNTHETIC_BANDWIDTHS if bandwidths is None else bandwidths,
            "aggregation": "mean",
        },
        "estimator": "biased",
        "include_diagonal": True,
        "compute_dtype": "float32",
    }
    path = tmp_path / "mmd.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def make_mmd_target_loader(
    *,
    seed: int = 13,
    count: int = 4,
    batch_size: int = 2,
    include_label: bool = False,
) -> DataLoader:
    rows = []
    for index in range(count):
        row = {
            "x": torch.full((1, 2, 2, 2), float(index + 2) / 7),
            "subject_id": f"target-{index}",
            "subject_hash": f"hash-{index}",
            "cohort": "OASIS",
        }
        if include_label:
            row["true_label"] = "CN"
        rows.append(row)
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        rows,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        drop_last=True,
    )


def make_mmd_trainer(
    run_dir: Path,
    *,
    warmup_epochs: int = 1,
    full_epochs: int = 1,
    seed: int = 11,
    weight: float = 1.0,
    bandwidths: list[float] | None = None,
) -> UDATrainer:
    selected = list(bandwidths or SYNTHETIC_BANDWIDTHS)
    torch.manual_seed(seed)
    model = TinyPADA3DACB()
    config = FixedEpochTrainingConfig(
        warmup_epochs=warmup_epochs,
        full_epochs=full_epochs,
        learning_rate=1e-2,
        weight_decay=1e-4,
        checkpoint_every=1,
        target_monitoring_enabled=False,
        mixed_precision=True,
        seed=seed,
    )
    adaptation_configuration = {
        "name": "mmd",
        "feature": "z",
        "weight": weight,
        "active_during_warmup": False,
        "kernel": {
            "name": "gaussian_rbf_mixture",
            "bandwidths": selected,
            "aggregation": "mean",
        },
        "estimator": "biased",
        "include_diagonal": True,
        "compute_dtype": "float32",
    }
    return UDATrainer(
        model,
        CorePADA3DACBLoss(2),
        torch.ones(2, 1, 1, 1),
        run_dir,
        config=config,
        split_assignment_hash="split",
        atlas_hash="atlas",
        roi_order_hash="roi-order",
        adaptation_method=MMDAdaptationMethod(selected),
        adaptation_weight=weight,
        adaptation_configuration=adaptation_configuration,
        source_split_assignment_hash="source",
        target_adaptation_assignment_hash="target-adaptation",
        target_evaluation_assignment_hash="target-evaluation",
    )
