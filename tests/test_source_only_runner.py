import json
from pathlib import Path

from acda3d.experiments import SourceOnlyExperimentRunner, load_source_only_config
from tests.phase9_helpers import make_source_only_environment


def test_one_fold_smoke_outputs_and_completed_reuse(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    runner = SourceOnlyExperimentRunner(config)
    result = runner.run_fold(0, 42)
    assert result.status == "COMPLETED" and not result.reused
    expected = {
        "run_manifest.json", "input_validation.json", "checkpoint_last.pt",
        "checkpoint_best_source_f1.pt", "training_history.csv", "fold_metrics.json",
    }
    assert expected.issubset({path.name for path in result.run_dir.iterdir()})
    manifest = json.loads((result.run_dir / "run_manifest.json").read_text())
    assert manifest["status"] == "COMPLETED"
    checkpoint_time = (result.run_dir / "checkpoint_last.pt").stat().st_mtime_ns
    reused = runner.run_fold(0, 42)
    assert reused.reused and reused.status == "COMPLETED"
    assert (result.run_dir / "checkpoint_last.pt").stat().st_mtime_ns == checkpoint_time


def test_completed_fold_with_changed_experiment_hash_is_rejected(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    runner = SourceOnlyExperimentRunner(config)
    runner.run_fold(0, 42)
    config.model["tokenizer"]["token_dim"] = 7
    try:
        runner.run_fold(0, 42)
    except Exception as error:
        assert "incompatible" in str(error)
    else:
        raise AssertionError("Incompatible completed fold was reused.")
