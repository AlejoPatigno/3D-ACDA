from __future__ import annotations

import pytest

from pada3dacb.binary import (
    BINARY_ABLATIONS,
    MMD_BINARY_ABLATIONS,
    apply_binary_ablation_loss_plan,
    binary_ablation_plan,
    mmd_binary_ablation_plan,
)

MMD_COMPONENTS = {
    "L_cls_z": 1.0,
    "L_cls_c": 2.0,
    "L_cons": 3.0,
    "L_concept": 4.0,
    "L_anat": 5.0,
    "L_mmd": 6.0,
    "unrelated": 11.0,
}


def test_mmd_binary_registry_is_scoped_and_preserves_distinct_concept_semantics() -> None:
    assert MMD_BINARY_ABLATIONS == ("no_mmd", "no_cons", "no_concept", "no_anat", "mean_pool")
    assert BINARY_ABLATIONS == ("no_proto", "no_pl", "no_cons", "no_concept", "no_anat", "mean_pool")

    expected_disabled = {
        "no_mmd": ("L_mmd",),
        "no_cons": ("L_cons",),
        "no_concept": ("L_concept",),
        "no_anat": ("L_anat",),
        "mean_pool": (),
    }
    for candidate, disabled in expected_disabled.items():
        plan = mmd_binary_ablation_plan(candidate)
        assert binary_ablation_plan(candidate, base_method="mmd") == plan
        assert plan.base_method == "mmd"
        assert plan.disabled_loss_components == disabled
        assert plan.requires_target_adaptation is True
        assert plan.requires_target_forward is True
        assert plan.concept_classification_enabled is True
        effective = apply_binary_ablation_loss_plan(candidate, MMD_COMPONENTS, base_method="mmd")
        assert all(effective[name] == 0.0 for name in disabled)
        assert effective["L_cls_c"] == MMD_COMPONENTS["L_cls_c"]
        assert effective["unrelated"] == MMD_COMPONENTS["unrelated"]

    assert binary_ablation_plan("no_concept").disabled_loss_components == ("L_cls_c", "L_concept")
    with pytest.raises(ValueError, match="base_method"):
        binary_ablation_plan("no_mmd")
    with pytest.raises(ValueError, match="prototype_pseudo"):
        mmd_binary_ablation_plan("no_proto")
    with pytest.raises(ValueError, match="alias_not_approved"):
        mmd_binary_ablation_plan("mean_pooling")
