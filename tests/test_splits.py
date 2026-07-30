import pandas as pd
import pytest

from pada3dacb.data.artifact_wiring import load_artifact_index
from pada3dacb.data.splits import (
    Direction,
    SplitConfig,
    assignment_hash,
    create_direction_splits,
    generate_source_folds,
    generate_target_split,
    validate_split_assignments,
)
from pada3dacb.exceptions import SplitValidationError
from tests.phase6_helpers import make_artifact_index


def test_split_determinism_integrity_and_seed(tmp_path):
    index = make_artifact_index(tmp_path)
    records = load_artifact_index(index, artifact_root=index.parent).records
    source = [record for record in records if record.cohort == "ADNI"]
    target = [record for record in records if record.cohort == "OASIS"]
    config = SplitConfig()
    source_a, target_a = generate_source_folds(source, config), generate_target_split(target, config)
    source_b, target_b = generate_source_folds(source, config), generate_target_split(target, config)
    pd.testing.assert_frame_equal(source_a, source_b)
    pd.testing.assert_frame_equal(target_a, target_b)
    validate_split_assignments(source_a, target_a, 5)
    assert assignment_hash(source_a, target_a) == assignment_hash(source_b, target_b)
    assert set(target_a.partition) == {"target_adaptation", "target_evaluation"}
    assert len(target_a) == len(target)
    changed = SplitConfig(seed=19)
    assert assignment_hash(generate_source_folds(source, changed), generate_target_split(target, changed)) != assignment_hash(source_a, target_a)


def test_bidirectional_protocol_and_fixed_target(tmp_path):
    index = make_artifact_index(tmp_path)
    records = load_artifact_index(index, artifact_root=index.parent).records
    config = SplitConfig()
    forward = create_direction_splits(records, Direction("ADNI", "OASIS"), config, index, tmp_path / "splits")
    reverse = create_direction_splits(records, Direction("OASIS", "ADNI"), config, index, tmp_path / "splits")
    assert forward.protocol["split_assignment_hash"] != reverse.protocol["split_assignment_hash"]
    assert forward.target_split.duplicated(["cohort", "subject_hash"]).sum() == 0
    assert set(forward.target_split.partition) == {"target_adaptation", "target_evaluation"}


def test_insufficient_class_support(tmp_path):
    index = make_artifact_index(tmp_path, per_class=4)
    records = load_artifact_index(index, artifact_root=index.parent).records
    source = [record for record in records if record.cohort == "ADNI"]
    with pytest.raises(SplitValidationError, match="smallest source class"):
        generate_source_folds(source, SplitConfig(n_splits=5))


def test_manifest_immutability_overwrite_and_dry_run(tmp_path):
    index = make_artifact_index(tmp_path)
    records = load_artifact_index(index, artifact_root=index.parent).records
    direction = Direction("ADNI", "OASIS")
    root = tmp_path / "splits"
    created = create_direction_splits(records, direction, SplitConfig(), index, root)
    reused = create_direction_splits(records, direction, SplitConfig(), index, root)
    assert not created.reused and reused.reused
    with pytest.raises(SplitValidationError, match="incompatible configuration_hash"):
        create_direction_splits(records, direction, SplitConfig(seed=7), index, root)
    replaced = create_direction_splits(records, direction, SplitConfig(seed=7, overwrite=True), index, root)
    assert not replaced.reused
    dry_root = tmp_path / "dry"
    dry = create_direction_splits(records, direction, SplitConfig(dry_run=True), index, dry_root)
    assert dry.dry_run and not dry_root.exists()
