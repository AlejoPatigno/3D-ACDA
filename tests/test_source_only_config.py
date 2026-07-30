from pathlib import Path

import pytest
import yaml

from pada3dacb.exceptions import ConfigurationError, PhaseNotImplementedError
from pada3dacb.experiments import load_source_only_config
from tests.phase9_helpers import make_source_only_environment


def test_source_only_config_composes_approved_phase8_values(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    assert config.method == "source_only"
    assert config.display_name == "PADA-3DACB Source-Only"
    assert config.training.total_epochs == 2
    assert config.loss_weights.effective("warm") == {
        "classification": 0.1, "concept_classification": 1.0,
        "prediction_consistency": 0.0, "concept_supervision": 0.5,
        "anatomical_consistency": 0.2,
    }


@pytest.mark.parametrize(("section", "key", "value", "error"), [
    ("experiment", "method", "coral", PhaseNotImplementedError),
    ("training", "early_stopping", True, ConfigurationError),
    ("model", "contextual_encoder", True, ConfigurationError),
])
def test_source_only_rejects_forbidden_configuration(tmp_path, section, key, value, error):
    path = make_source_only_environment(tmp_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload[section][key] = value
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(error):
        load_source_only_config(path)
