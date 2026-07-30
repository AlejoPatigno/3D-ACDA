import inspect
from pathlib import Path

from pada3dacb.experiments import SourceOnlyExperimentRunner, load_source_only_config
from pada3dacb.training import SourceOnlyTrainer
from tests.phase9_helpers import make_source_only_environment


def test_source_only_constructs_only_target_evaluation_not_adaptation(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    result = SourceOnlyExperimentRunner(config).run_fold(0, 42, validate_only=True)
    assert result.metrics["validated"]
    assert not SourceOnlyExperimentRunner.uses_target_adaptation
    assert not SourceOnlyTrainer.uses_target_adaptation
    source = inspect.getsource(SourceOnlyExperimentRunner)
    assert "build_target_adaptation_loader" not in source
    assert '"target_adaptation_loader_constructed": False' in source
