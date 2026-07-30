from pathlib import Path

import pytest
import yaml

from pada3dacb.exceptions import ConfigurationError, PhaseNotImplementedError
from pada3dacb.experiments.prototype_pseudo import (
    PROTOTYPE_PSEUDO_DISPLAY_NAME,
    load_prototype_pseudo_config,
)
from tests.phase12_helpers import make_cdan_environment


def make_proposed_environment(tmp_path: Path) -> Path:
    source = make_cdan_environment(tmp_path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["experiment"].update(
        {
            "name": "synthetic_prototype_pseudo",
            "display_name": "PADA-3DACB",
            "method": "prototype_pseudo",
        }
    )
    payload["training"]["config"] = "configs/training/default.yaml"
    payload["adaptation"] = {
        "name": "prototype_pseudo",
        "feature": "z_and_concept_logits",
        "active_during_warmup": False,
        "prototype": {"lambda_proto": 1.0, "proto_margin": 1.0, "lambda_sep": 0.1},
        "pseudo_label": {"lambda_pl": 0.1, "tau_p": 0.95, "probability_source": "concept_logits"},
    }
    path = tmp_path / "prototype_pseudo.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _mutate_config(path: Path, mutation) -> Path:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutation(payload)
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_prototype_pseudo_config_loads_canonical_values(tmp_path: Path):
    config = load_prototype_pseudo_config(make_proposed_environment(tmp_path))

    assert config.method == "prototype_pseudo"
    assert config.display_name == PROTOTYPE_PSEUDO_DISPLAY_NAME == "PADA-3DACB"
    assert config.training.warmup_epochs == 5
    assert config.training.full_epochs == 50
    assert config.training.learning_rate == 1e-4
    assert config.training.weight_decay == 1e-4
    assert config.training.seed == 42
    assert config.data_loader["batch_size"] == 16
    assert config.adaptation.prototype == {
        "lambda_proto": 1.0,
        "proto_margin": 1.0,
        "lambda_sep": 0.1,
    }
    assert config.adaptation.pseudo_label == {
        "lambda_pl": 0.1,
        "tau_p": 0.95,
        "probability_source": "concept_logits",
    }
    assert config.loss_weights.effective("warm")["classification"] == 0.1


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["adaptation"]["prototype"].__setitem__("lambda_proto", None),
        lambda payload: payload["adaptation"]["prototype"].__setitem__("proto_margin", None),
        lambda payload: payload["adaptation"]["prototype"].__setitem__("lambda_sep", None),
        lambda payload: payload["adaptation"]["pseudo_label"].__setitem__("lambda_pl", None),
        lambda payload: payload["adaptation"]["pseudo_label"].__setitem__("tau_p", None),
    ],
)
def test_prototype_pseudo_real_run_rejects_unresolved_scientific_values(tmp_path: Path, mutation):
    with pytest.raises(ConfigurationError):
        load_prototype_pseudo_config(_mutate_config(make_proposed_environment(tmp_path), mutation))


@pytest.mark.parametrize(
    "mutation,expected_error",
    [
        (lambda payload: payload["experiment"].__setitem__("display_name", "PADA-3DACB + Prototype"), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("name", "coral"), PhaseNotImplementedError),
        (lambda payload: payload["adaptation"].__setitem__("feature", "z"), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("active_during_warmup", True), ConfigurationError),
        (lambda payload: payload["adaptation"]["pseudo_label"].__setitem__("probability_source", "latent_probabilities"), ConfigurationError),
        (lambda payload: payload["adaptation"]["prototype"].__setitem__("lambda_proto", -1.0), ConfigurationError),
        (lambda payload: payload["adaptation"]["pseudo_label"].__setitem__("tau_p", 1.01), ConfigurationError),
        (lambda payload: payload.__setitem__("baselines", {"svm": {}}), ConfigurationError),
        (lambda payload: payload.__setitem__("phase14", {"confusion_matrices": True}), ConfigurationError),
    ],
)
def test_prototype_pseudo_config_rejects_invalid_or_later_phase_fields(tmp_path: Path, mutation, expected_error):
    with pytest.raises(expected_error):
        load_prototype_pseudo_config(_mutate_config(make_proposed_environment(tmp_path), mutation))


def test_prototype_pseudo_hash_changes_for_each_scientific_value(tmp_path: Path):
    base = load_prototype_pseudo_config(make_proposed_environment(tmp_path / "base"))
    mutations = [
        lambda payload: payload["adaptation"]["prototype"].__setitem__("lambda_proto", 0.9),
        lambda payload: payload["adaptation"]["prototype"].__setitem__("proto_margin", 1.1),
        lambda payload: payload["adaptation"]["prototype"].__setitem__("lambda_sep", 0.2),
        lambda payload: payload["adaptation"]["pseudo_label"].__setitem__("lambda_pl", 0.2),
        lambda payload: payload["adaptation"]["pseudo_label"].__setitem__("tau_p", 0.9),
    ]

    for index, mutation in enumerate(mutations):
        changed = load_prototype_pseudo_config(
            _mutate_config(make_proposed_environment(tmp_path / str(index)), mutation)
        )
        assert changed.adaptation.sha256() != base.adaptation.sha256()
        assert changed.sha256() != base.sha256()
