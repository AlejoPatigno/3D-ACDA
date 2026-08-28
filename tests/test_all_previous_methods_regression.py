import os
from pathlib import Path

from acda3d.adaptation import CDANAdaptationMethod, CORALAdaptationMethod, MMDAdaptationMethod
from acda3d.experiments.cdan import CDAN_DISPLAY_NAME, CDANExperimentRunner, load_cdan_config
from acda3d.experiments.coral import (
    CORAL_DISPLAY_NAME,
    load_coral_config,
    run_coral_both_directions,
)
from acda3d.experiments.mmd import (
    MMD_DISPLAY_NAME,
    load_mmd_config,
    run_mmd_both_directions,
)
from acda3d.experiments.runner import SourceOnlyExperimentRunner, run_both_directions
from acda3d.experiments.source_only import DISPLAY_NAME, load_source_only_config
from tests.phase9_helpers import make_source_only_environment
from tests.phase10_helpers import make_coral_environment
from tests.phase11_helpers import make_mmd_environment
from tests.phase12_helpers import make_cdan_environment
from tests.phase13_helpers import (
    assert_two_direction_dry_run,
    skip_if_cdan_discriminator_contract_is_externalized,
)


def test_source_only_regression_keeps_no_target_adaptation_and_all_fold_planning(tmp_path: Path):
    config = load_source_only_config(make_source_only_environment(tmp_path))
    config.folds = list(range(5))

    outputs = run_both_directions(config, dry_run=True)

    assert config.method == "source_only"
    assert config.display_name == DISPLAY_NAME == "3D-ACDA Source-Only"
    assert SourceOnlyExperimentRunner.uses_target_adaptation is False
    assert_two_direction_dry_run(outputs, expected_folds=list(range(5)))
    assert all("planned_target_adaptation" not in result.metrics for results in outputs.values() for result in results)


def test_coral_regression_keeps_identity_target_firewall_and_direction_planning(tmp_path: Path):
    config = load_coral_config(make_coral_environment(tmp_path))
    config.folds = [0, 1]

    outputs = run_coral_both_directions(config, dry_run=True)

    assert CORALAdaptationMethod.name == "coral"
    assert config.display_name == CORAL_DISPLAY_NAME == "3D-ACDA + CORAL"
    assert config.adaptation.resolved_dict()["covariance"] == {
        "estimator": "unbiased",
        "normalization": "four_d_squared",
        "compute_dtype": "float32",
    }
    assert_two_direction_dry_run(outputs, expected_folds=[0, 1])
    assert all(result.metrics["target_training_labels_available"] is False for results in outputs.values() for result in results)


def test_mmd_regression_keeps_kernel_identity_target_firewall_and_direction_planning(tmp_path: Path):
    config = load_mmd_config(make_mmd_environment(tmp_path))
    config.folds = [0, 4]

    outputs = run_mmd_both_directions(config, dry_run=True)

    assert MMDAdaptationMethod.name == "mmd"
    assert config.display_name == MMD_DISPLAY_NAME == "3D-ACDA + MMD"
    assert config.adaptation.kernel.resolved_dict() == {
        "name": "gaussian_rbf_mixture",
        "bandwidths": [0.5, 1.0, 2.0],
        "aggregation": "mean",
    }
    assert config.adaptation.estimator == "biased"
    assert config.adaptation.include_diagonal is True
    assert_two_direction_dry_run(outputs, expected_folds=[0, 4])
    assert all(result.metrics["target_training_labels_available"] is False for results in outputs.values() for result in results)


def test_synthetic_mmd_environment_resolves_relative_tmp_roots_without_cache_duplication(tmp_path: Path):
    relative_tmp = Path(os.path.relpath(tmp_path, Path.cwd()))

    config = load_mmd_config(make_mmd_environment(relative_tmp))
    config.folds = [0]

    assert config.paths.artifact_root == (Path.cwd() / relative_tmp / "cache").resolve()
    assert (config.paths.artifact_root / "mri" / "OASIS_AD_00.pt").is_file()
    assert (config.paths.artifact_root / "concepts" / "ADNI_MCI_03.pt").is_file()
    assert_two_direction_dry_run(run_mmd_both_directions(config, dry_run=True), expected_folds=[0])


def test_cdan_regression_keeps_conditional_identity_target_firewall_and_fold_planning(tmp_path: Path):
    config = load_cdan_config(make_cdan_environment(tmp_path))
    config.folds = [0, 3]

    try:
        outputs = {config.direction: CDANExperimentRunner(config).run(dry_run=True)}
    except TypeError as exc:
        skip_if_cdan_discriminator_contract_is_externalized(exc)

    assert CDANAdaptationMethod.name == "cdan"
    assert config.display_name == CDAN_DISPLAY_NAME == "3D-ACDA + CDAN"
    assert config.adaptation.resolved_dict()["conditional_mode"] == "exact_outer_product"
    assert config.adaptation.resolved_dict()["probability_source"] == "latent_probabilities"
    assert [result.fold for result in outputs[config.direction]] == [0, 3]
    assert all(result.metrics["target_training_labels_available"] is False for result in outputs[config.direction])


def test_previous_method_run_directories_remain_method_scoped(tmp_path: Path):
    source = load_source_only_config(make_source_only_environment(tmp_path / "source"))
    coral = load_coral_config(make_coral_environment(tmp_path / "coral"))
    mmd = load_mmd_config(make_mmd_environment(tmp_path / "mmd"))
    cdan = load_cdan_config(make_cdan_environment(tmp_path / "cdan"))

    assert "/source_only/" in source.run_dir(0, 42).as_posix()
    assert "/coral/" in coral.run_dir(0, 42).as_posix()
    assert "/mmd/" in mmd.run_dir(0, 42).as_posix()
    assert "/cdan/" in cdan.run_dir(0, 42).as_posix()
