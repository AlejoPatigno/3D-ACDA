from pathlib import Path

import pytest
import yaml

from pada3dacb.exceptions import ConfigurationError, PhaseNotImplementedError
from pada3dacb.experiments import load_cdan_config
from tests.phase12_helpers import make_cdan_environment


def _mutate_config(path: Path, *updates) -> Path:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    for update in updates:
        update(payload)
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_cdan_config_requires_explicit_real_run_hyperparameters(tmp_path: Path):
    required_field_mutations = [
        lambda payload: payload["adaptation"].__setitem__("weight", None),
        lambda payload: payload["adaptation"]["grl"].__setitem__("coefficient", None),
        lambda payload: payload["adaptation"]["discriminator"].__setitem__("hidden_dims", None),
        lambda payload: payload["adaptation"]["discriminator"].__setitem__("dropout", None),
        lambda payload: payload["adaptation"]["discriminator"]["optimizer_group"].__setitem__("learning_rate", None),
        lambda payload: payload["adaptation"]["discriminator"]["optimizer_group"].__setitem__("weight_decay", None),
    ]

    for index, mutation in enumerate(required_field_mutations):
        with pytest.raises(ConfigurationError):
            load_cdan_config(_mutate_config(make_cdan_environment(tmp_path / str(index)), mutation))


def test_cdan_config_accepts_declared_synthetic_fixture(tmp_path: Path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    assert config.adaptation.feature == "z"
    assert config.adaptation.conditional_mode == "exact_outer_product"


@pytest.mark.parametrize(
    "mutation,expected_error",
    [
        (lambda payload: payload["adaptation"].__setitem__("feature", "contextual"), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("probability_source", "softmax"), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("conditional_mode", "randomized_multilinear"), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("entropy_conditioning", True), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("active_during_warmup", True), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("weight", -0.1), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("weight", ".nan"), ConfigurationError),
        (lambda payload: payload["adaptation"]["grl"].__setitem__("schedule", "linear"), ConfigurationError),
        (lambda payload: payload["adaptation"]["grl"].__setitem__("coefficient", -1.0), ConfigurationError),
        (lambda payload: payload["adaptation"]["grl"].__setitem__("coefficient", ".inf"), ConfigurationError),
        (lambda payload: payload["adaptation"]["domain_labels"].__setitem__("target", 2), ConfigurationError),
        (lambda payload: payload["adaptation"]["discriminator"].__setitem__("hidden_dims", []), ConfigurationError),
        (lambda payload: payload["adaptation"]["discriminator"].__setitem__("hidden_dims", [8, 0]), ConfigurationError),
        (lambda payload: payload["adaptation"]["discriminator"].__setitem__("dropout", 1.0), ConfigurationError),
        (lambda payload: payload["adaptation"]["discriminator"]["optimizer_group"].__setitem__("learning_rate", 0.0), ConfigurationError),
        (lambda payload: payload["adaptation"]["discriminator"]["optimizer_group"].__setitem__("weight_decay", -0.01), ConfigurationError),
        (lambda payload: payload["training"].__setitem__("early_stopping", True), ConfigurationError),
        (lambda payload: payload["model"].__setitem__("contextual_encoder", True), ConfigurationError),
        (lambda payload: payload["experiment"].__setitem__("source_domain", "ADNI2"), ConfigurationError),
        (lambda payload: payload["experiment"].__setitem__("target_domain", "ADNI"), ConfigurationError),
        (lambda payload: payload["adaptation"].__setitem__("name", "prototype"), PhaseNotImplementedError),
    ],
)
def test_cdan_config_rejects_invalid_phase12_values(tmp_path: Path, mutation, expected_error):
    with pytest.raises(expected_error):
        load_cdan_config(_mutate_config(make_cdan_environment(tmp_path), mutation))


def test_cdan_resolved_identity_contains_required_adaptation_fields(tmp_path: Path):
    config = load_cdan_config(make_cdan_environment(tmp_path))

    resolved = config.resolved_dict()

    assert resolved["method"] == "cdan"
    assert resolved["adaptation"]["conditional_mode"] == "exact_outer_product"
    assert resolved["adaptation"]["grl"] == {"schedule": "constant", "coefficient": 1.0}
    assert resolved["adaptation"]["discriminator"]["optimizer_group"] == {
        "learning_rate": 0.001,
        "weight_decay": 0.0,
    }


def test_cdan_adaptation_and_experiment_hashes_change_with_cdan_parameters(tmp_path: Path):
    first = load_cdan_config(make_cdan_environment(tmp_path / "first"))
    second_path = make_cdan_environment(tmp_path / "second")
    payload = yaml.safe_load(second_path.read_text(encoding="utf-8"))
    payload["adaptation"]["grl"]["coefficient"] = 0.25
    payload["adaptation"]["discriminator"]["hidden_dims"] = [16, 4]
    second_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    second = load_cdan_config(second_path)

    assert first.adaptation.sha256() != second.adaptation.sha256()
    assert first.sha256() != second.sha256()
