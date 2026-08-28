from pathlib import Path

from acda3d.experiments import SourceOnlyExperimentRunner, load_source_only_config
from tests.phase9_helpers import make_source_only_environment


def test_source_only_hash_and_target_isolation_remain_unchanged(tmp_path: Path):
    path = make_source_only_environment(tmp_path)
    before = load_source_only_config(path)
    after = load_source_only_config(path)
    assert before.sha256() == after.sha256()
    runner = SourceOnlyExperimentRunner(after)
    assert runner.uses_target_adaptation is False
    result = runner.run_fold(0, 42, dry_run=True)
    assert "planned_target_adaptation" not in result.metrics
