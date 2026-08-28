from pathlib import Path

import torch

from acda3d.adaptation import coral_loss
from acda3d.experiments import (
    CORALExperimentRunner,
    SourceOnlyExperimentRunner,
    load_coral_config,
    load_source_only_config,
)
from tests.phase10_helpers import make_coral_environment


def test_source_only_and_coral_identities_and_boundaries_remain_stable(tmp_path: Path):
    coral_path = make_coral_environment(tmp_path)
    source_path = tmp_path / "source_only.yaml"
    source = load_source_only_config(source_path)
    coral = load_coral_config(coral_path)
    assert source.sha256() == load_source_only_config(source_path).sha256()
    assert coral.sha256() == load_coral_config(coral_path).sha256()
    source_runner = SourceOnlyExperimentRunner(source)
    coral_runner = CORALExperimentRunner(coral)
    assert source_runner.uses_target_adaptation is False
    assert coral_runner.uses_target_adaptation is True
    assert source.method == "source_only"
    assert coral_runner.method_name == "coral"
    assert source.display_name == "3D-ACDA Source-Only"
    assert coral.display_name == "3D-ACDA + CORAL"

    features = torch.tensor([[1.0, 2.0], [2.0, 4.0], [4.0, 1.0]])
    torch.testing.assert_close(coral_loss(features, features + 10), torch.tensor(0.0))
    assert source.method != "prototype_pseudo"
    assert coral.method != "prototype_pseudo"
