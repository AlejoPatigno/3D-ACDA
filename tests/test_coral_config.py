from pathlib import Path

import pytest
import yaml

from acda3d.exceptions import ConfigurationError
from acda3d.experiments import load_coral_config, stable_weight_directory
from tests.phase10_helpers import make_coral_environment


def test_coral_config_requires_explicit_weight_and_has_stable_identity(tmp_path: Path):
    config = load_coral_config(make_coral_environment(tmp_path), overrides={"coral_weight": 1.0})
    assert config.method == "coral" and config.adaptation.feature == "z"
    assert "weight_" in str(config.run_dir(0, 42))
    assert stable_weight_directory(1.0) != stable_weight_directory(1.0000000000000002)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("adaptation", "weight", None),
        ("adaptation", "weight", -1.0),
        ("adaptation", "feature", "F"),
        ("adaptation", "active_during_warmup", True),
        ("model", "contextual_encoder", True),
        ("training", "early_stopping", True),
    ],
)
def test_coral_rejects_forbidden_configuration(tmp_path, section, key, value):
    path = make_coral_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload[section][key] = value
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_coral_config(path)
