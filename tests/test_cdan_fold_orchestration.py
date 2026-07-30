
import yaml

from pada3dacb.experiments import CDANExperimentRunner, load_cdan_config, run_cdan_both_directions
from tests.phase12_helpers import make_cdan_environment


def test_cdan_run_directory_contains_configuration_identity(tmp_path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    config.paths.output_root = tmp_path / "runs"

    run_dir = str(config.run_dir(0, 42))

    assert "cdan" in run_dir
    assert config.adaptation.sha256()[:16] in run_dir


def test_cdan_run_directory_changes_when_adaptation_hash_changes(tmp_path):
    first = load_cdan_config(make_cdan_environment(tmp_path / "a"))
    second_path = make_cdan_environment(tmp_path / "b")
    payload = yaml.safe_load(second_path.read_text(encoding="utf-8"))
    payload["adaptation"]["discriminator"]["optimizer_group"]["learning_rate"] = 0.002
    second_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    second = load_cdan_config(second_path)
    first.paths.output_root = second.paths.output_root = tmp_path / "runs"

    assert first.run_dir(0, 42) != second.run_dir(0, 42)


def test_cdan_runner_builds_discriminator_from_nested_model_token_dim(tmp_path):
    config = load_cdan_config(make_cdan_environment(tmp_path))

    method = CDANExperimentRunner(config)._build_adaptation_method()

    assert method.discriminator.config.input_dim == 18


def test_cdan_both_directions_orchestrates_approved_direction_pair(monkeypatch, tmp_path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    calls = []

    class FakeRunner:
        def __init__(self, config):
            self.config = config

        def run(self, *, dry_run=False, validate_only=False):
            calls.append((self.config.source_domain, self.config.target_domain, dry_run, validate_only))
            return []

    monkeypatch.setattr("pada3dacb.experiments.cdan.CDANExperimentRunner", FakeRunner)

    results = run_cdan_both_directions(config, dry_run=True, validate_only=True)

    assert list(results) == ["ADNI_to_OASIS", "OASIS_to_ADNI"]
    assert calls == [("ADNI", "OASIS", True, True), ("OASIS", "ADNI", True, True)]
