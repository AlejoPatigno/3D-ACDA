import yaml

from acda3d.experiments import CDANExperimentRunner, load_cdan_config
from tests.phase12_helpers import make_cdan_environment


def _mutate(path, mutation):
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutation(payload)
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_cdan_configuration_hash_changes_with_grl_and_discriminator(tmp_path):
    first = load_cdan_config(make_cdan_environment(tmp_path / "a"))
    second = load_cdan_config(
        _mutate(
            make_cdan_environment(tmp_path / "b"),
            lambda payload: payload["adaptation"]["grl"].__setitem__("coefficient", 0.25),
        )
    )
    third = load_cdan_config(
        _mutate(
            make_cdan_environment(tmp_path / "c"),
            lambda payload: payload["adaptation"]["discriminator"].__setitem__("hidden_dims", [16, 4]),
        )
    )

    assert first.adaptation.sha256() != second.adaptation.sha256()
    assert first.adaptation.sha256() != third.adaptation.sha256()
    assert first.sha256() != second.sha256()
    assert first.sha256() != third.sha256()


def test_cdan_checkpoint_policy_uses_source_macro_f1_only(tmp_path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    runner = CDANExperimentRunner(config)

    assert runner.checkpoint_metric_name == "source/val_macro_f1"
    assert runner.checkpoint_metric_mode == "max"
    assert "target" not in runner.checkpoint_metric_name
