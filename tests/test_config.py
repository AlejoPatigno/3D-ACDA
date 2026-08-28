from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from acda3d.config import ProjectConfig, load_config
from acda3d.exceptions import ConfigurationError, UnsupportedExperimentError


def _valid_dict():
    return {
        "experiment": {
            "name": "test",
            "method": "prototype_pseudo",
            "source_domain": "ADNI",
            "target_domain": "OASIS",
            "seed": 42,
            "fold": 0,
        },
        "model": {
            "name": "3D-ACDA",
            "contextual_encoder": False,
            "num_classes": 3,
            "num_rois": 102,
        },
        "training": {
            "warmup_epochs": 5,
            "full_epochs": 50,
            "early_stopping": False,
            "batch_size": 16,
            "learning_rate": 0.0001,
            "weight_decay": 0.0001,
            "checkpoint_every": 5,
            "evaluate_source_every": 1,
            "evaluate_target_every": 1,
            "mixed_precision": True,
            "resume": True,
        },
    }


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_experiment_configs_load_and_validate():
    for path in Path("configs/experiments").glob("*.yaml"):
        config = load_config(path)
        config.validate()


def test_data_and_model_configs_load_without_path_requirements():
    for path in [
        Path("configs/data/paths.example.yaml"),
        Path("configs/data/adni.yaml"),
        Path("configs/data/oasis.yaml"),
        Path("configs/model/acda3d.yaml"),
    ]:
        config = load_config(path)
        config.validate()


@pytest.mark.parametrize(
    ("mutator", "error_type"),
    [
        (lambda d: d["model"].update({"contextual_encoder": True}), ConfigurationError),
        (lambda d: d["training"].update({"early_stopping": True}), ConfigurationError),
        (lambda d: d["model"].update({"name": "3D-ACDA-Full"}), ConfigurationError),
        (lambda d: d["experiment"].update({"method": "unknown"}), UnsupportedExperimentError),
        (lambda d: d["experiment"].update({"source_domain": "ADNI", "target_domain": "ADNI"}), ConfigurationError),
        (lambda d: d["training"].update({"full_epochs": 0}), ConfigurationError),
        (lambda d: d["training"].update({"batch_size": 0}), ConfigurationError),
        (lambda d: d["experiment"].update({"source_domain": "OTHER"}), ConfigurationError),
    ],
)
def test_invalid_configurations_are_rejected(tmp_path, mutator, error_type):
    data = _valid_dict()
    mutator(data)
    with pytest.raises(error_type):
        load_config(_write_config(tmp_path, data))


def test_baseline_can_use_baseline_model_name(tmp_path):
    data = _valid_dict()
    data["experiment"]["method"] = "baseline"
    data["model"]["name"] = "cnn_design_for_ad"
    config = load_config(_write_config(tmp_path, data))
    assert config.model.name == "cnn_design_for_ad"


def test_configuration_hash_is_stable_and_sensitive():
    data_a = _valid_dict()
    data_b = {
        "training": copy.deepcopy(data_a["training"]),
        "model": copy.deepcopy(data_a["model"]),
        "experiment": copy.deepcopy(data_a["experiment"]),
    }
    config_a = ProjectConfig.from_dict(data_a)
    config_b = ProjectConfig.from_dict(data_b)
    assert config_a.sha256() == config_b.sha256()

    data_b["training"]["full_epochs"] = 51
    config_c = ProjectConfig.from_dict(data_b)
    assert config_a.sha256() != config_c.sha256()


def test_save_resolved_config(tmp_path):
    config = ProjectConfig.from_dict(_valid_dict())
    target = config.save_resolved(tmp_path / "config_resolved.yaml")
    assert target.exists()
    assert "3D-ACDA" in target.read_text(encoding="utf-8")
