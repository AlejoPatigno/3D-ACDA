import pytest
import torch

from acda3d.exceptions import CheckpointMigrationError
from acda3d.models import (
    ACDA3D,
    load_migrated_legacy_checkpoint,
    migrate_legacy_lite_state_dict,
)


def model():
    return ACDA3D(2, 8, 6, base_channels=4, concept_hidden_dim=4)


def test_full_only_keys_are_dropped_and_retained_weights_load():
    source = model()
    legacy = dict(source.state_dict())
    legacy["ctx_enc.transformer.layers.0.weight"] = torch.ones(1)
    target = model()
    report = load_migrated_legacy_checkpoint(target, {"model_state_dict": legacy})
    assert report.dropped_full_only_keys == ("ctx_enc.transformer.layers.0.weight",)
    assert report.missing_retained_keys == ()
    assert report.unexpected_keys == ()
    for key, value in source.state_dict().items():
        assert torch.equal(value, target.state_dict()[key])


def test_explicit_renamed_prefix_mapping():
    target = model()
    legacy = {}
    for key, value in target.state_dict().items():
        renamed = key.replace("tokenizer.", "roi_tokenizer.", 1)
        legacy[renamed] = value
    _, report = migrate_legacy_lite_state_dict(legacy, target)
    assert any(old.startswith("roi_tokenizer.") for old, _ in report.renamed_keys)


def test_incompatible_shape_and_unknown_keys_fail():
    target = model()
    bad_shape = dict(target.state_dict())
    bad_shape["cls_head.fc.weight"] = torch.ones(4, 4)
    with pytest.raises(CheckpointMigrationError, match="Incompatible retained"):
        migrate_legacy_lite_state_dict(bad_shape, target)
    unknown = dict(target.state_dict())
    unknown["mystery.weight"] = torch.ones(1)
    with pytest.raises(CheckpointMigrationError, match="Unexpected"):
        migrate_legacy_lite_state_dict(unknown, target)


def test_missing_retained_keys_reported_only_in_relaxed_mode():
    target = model()
    state = dict(target.state_dict())
    removed = next(iter(state))
    state.pop(removed)
    with pytest.raises(CheckpointMigrationError, match="Missing retained"):
        migrate_legacy_lite_state_dict(state, target)
    _, report = migrate_legacy_lite_state_dict(state, target, strict_retained=False)
    assert removed in report.missing_retained_keys
