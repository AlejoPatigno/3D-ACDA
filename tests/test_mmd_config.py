from pathlib import Path

import pytest
import yaml

from pada3dacb.exceptions import ConfigurationError
from pada3dacb.experiments import load_mmd_config
from tests.phase11_helpers import make_mmd_environment


def test_mmd_config_accepts_fixture_and_preserves_ordered_kernel_hash(tmp_path: Path):
    config = load_mmd_config(make_mmd_environment(tmp_path))
    assert config.method == "mmd" and config.adaptation.feature == "z"
    first_hash = config.adaptation.kernel_hash()
    reversed_config = load_mmd_config(
        make_mmd_environment(tmp_path / "reversed", bandwidths=[2.0, 1.0, 0.5])
    )
    assert first_hash != reversed_config.adaptation.kernel_hash()
    assert config.sha256() != reversed_config.sha256()


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("adaptation", "weight", None),
        ("adaptation", "weight", -1.0),
        ("adaptation", "feature", "F"),
        ("adaptation", "active_during_warmup", True),
        ("adaptation", "estimator", "unbiased"),
        ("adaptation", "include_diagonal", False),
        ("adaptation", "compute_dtype", "float64"),
        ("model", "contextual_encoder", True),
        ("training", "early_stopping", True),
    ],
)
def test_mmd_rejects_invalid_configuration(tmp_path, section, key, value):
    path = make_mmd_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload[section][key] = value
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_mmd_config(path)


@pytest.mark.parametrize("bandwidths", [None, [], [0.0], [-1.0], [1.0, 1.0]])
def test_mmd_rejects_invalid_bandwidth_lists(tmp_path: Path, bandwidths):
    path = make_mmd_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["adaptation"]["kernel"]["bandwidths"] = bandwidths
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_mmd_config(path)


@pytest.mark.parametrize(
    ("key", "value"),
    [("name", "linear"), ("aggregation", "sum")],
)
def test_mmd_rejects_other_kernel_definitions(tmp_path: Path, key, value):
    path = make_mmd_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["adaptation"]["kernel"][key] = value
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_mmd_config(path)
