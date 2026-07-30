from pathlib import Path

from pada3dacb.experiments import SourceOnlyExperimentRunner, load_source_only_config
from tests.phase9_helpers import make_source_only_environment


def test_interrupted_fold_resumes_with_same_manifest_identity(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    runner = SourceOnlyExperimentRunner(config)
    interrupted = runner.run_fold(0, 42, interrupt_after_epoch=1)
    assert interrupted.status == "INTERRUPTED"
    resumed = runner.run_fold(
        0, 42, resume_from=interrupted.run_dir / "checkpoint_last.pt"
    )
    assert resumed.status == "COMPLETED"
    assert resumed.experiment_hash == interrupted.experiment_hash
    assert resumed.metrics["last_epoch"] == 2
