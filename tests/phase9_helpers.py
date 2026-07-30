import json
from pathlib import Path

import torch
import yaml

from pada3dacb.data.artifact_wiring import load_artifact_index
from pada3dacb.data.splits import Direction, SplitConfig, create_direction_splits
from tests.phase6_helpers import make_artifact_index


def make_source_only_environment(tmp_path: Path) -> Path:
    tmp_path = tmp_path.resolve()
    index = make_artifact_index(tmp_path, per_class=5, shape=(16, 16, 16), k=2)
    records = load_artifact_index(index, artifact_root=index.parent).records
    split_root = tmp_path / "splits"
    for direction in (Direction("ADNI", "OASIS"), Direction("OASIS", "ADNI")):
        create_direction_splits(records, direction, SplitConfig(), index, split_root)
    atlas_root = tmp_path / "atlas"
    atlas_root.mkdir()
    masks = torch.zeros(2, 16, 16, 16)
    masks[0, :8] = 1
    masks[1, 8:] = 1
    torch.save(
        {"roi_masks": masks, "label_values": [1, 2], "atlas_hash": "atlas"},
        atlas_root / "roi_masks.pt",
    )
    (atlas_root / "atlas_metadata.json").write_text(
        json.dumps({"atlas_hash": "atlas", "K": 2, "label_values": [1, 2]}),
        encoding="utf-8",
    )
    model_path = tmp_path / "model.yaml"
    model_path.write_text(
        yaml.safe_dump(
            {
                "model": {
                    "name": "PADA-3DACB",
                    "contextual_encoder": False,
                    "input_channels": 1,
                    "num_classes": 3,
                    "num_rois": 2,
                    "encoder": {"base_channels": 4, "output_channels": 8},
                    "tokenizer": {"feature_dim": 8, "token_dim": 6},
                    "token_processing": {"dropout": 0.2},
                    "concept_bottleneck": {"hidden_dim": 4, "dropout": 0.2},
                }
            }
        ),
        encoding="utf-8",
    )
    training_path = tmp_path / "training.yaml"
    training_path.write_text(
        yaml.safe_dump(
            {
                "training": {
                    "warmup_epochs": 1,
                    "full_epochs": 1,
                    "early_stopping": False,
                    "optimizer": {"name": "AdamW", "learning_rate": 0.001, "weight_decay": 0.0001},
                    "scheduler": {"name": "none", "parameters": {}},
                    "mixed_precision": False,
                    "gradient": {"clipping_value": 5.0, "fail_on_nonfinite_loss": True},
                    "checkpoint": {"save_last": True, "save_best_source_f1": True, "every_epochs": 1},
                    "evaluation": {"source_every_epochs": 1, "target_monitoring_every_epochs": 1, "target_monitoring_enabled": True},
                },
                "losses": {
                    "classification_weight": 1.0,
                    "concept_classification_weight": 1.0,
                    "prediction_consistency_weight": 0.1,
                    "concept_supervision_weight": 0.5,
                    "anatomical_consistency_weight": 0.2,
                    "label_smoothing": 0.1,
                    "warm_classification_multiplier": 0.1,
                    "warm_concept_classification_multiplier": 1.0,
                    "warm_prediction_consistency_multiplier": 0.0,
                    "warm_concept_supervision_multiplier": 1.0,
                    "warm_anatomical_consistency_multiplier": 1.0,
                },
                "roi_mask_preparation": {"mode": "nearest", "epsilon": 1e-8},
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "source_only.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment": {
                    "name": "synthetic_source_only",
                    "display_name": "PADA-3DACB Source-Only",
                    "method": "source_only",
                    "source_domain": "ADNI",
                    "target_domain": "OASIS",
                    "folds": [0],
                    "seeds": [42],
                },
                "paths": {
                    "artifact_index": str(index),
                    "artifact_root": str(index.parent),
                    "split_root": str(split_root),
                    "atlas_metadata": str(atlas_root / "atlas_metadata.json"),
                    "roi_masks": str(atlas_root / "roi_masks.pt"),
                    "output_root": str(tmp_path / "outputs"),
                },
                "model": {"config": str(model_path), "name": "PADA-3DACB", "contextual_encoder": False, "num_classes": 3, "num_rois": 2},
                "training": {"config": str(training_path), "early_stopping": False, "resume": True},
                "data_loader": {"batch_size": 12, "num_workers": 0, "pin_memory": False, "drop_last_train": True, "drop_last_eval": False},
                "evaluation": {"source_validation": True, "target_monitoring": True, "target_monitoring_label": "MONITORING ONLY — NOT A TRAINING LOSS", "export_checkpoints": ["best_source_f1", "last"]},
                "execution": {"overwrite": False, "continue_completed_folds": True, "fail_fast": True, "device": "cpu"},
            }
        ),
        encoding="utf-8",
    )
    return config_path
