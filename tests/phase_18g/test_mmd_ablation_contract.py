"""Phase 18G contracts for the MMD-primary ablation registry."""

import copy
from pathlib import Path

import pytest

from pada3dacb.ablations import AblationResolutionError
from pada3dacb.ablations.registry import (
    alias_target,
    get_ablation_spec,
    list_ablations,
    registry_specs,
)
from pada3dacb.ablations.resolver import resolve_ablation_config
from pada3dacb.experiments.ablations import (
    APPROVED_ABLATIONS,
    build_equivalence_reference,
    execute,
    load_ablation_config,
    planned_run_path,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "experiments" / "ablations.yaml"


def test_mean_pool_is_canonical_and_mean_pooling_is_alias_only() -> None:
    canonical_ids = tuple(spec.id for spec in registry_specs())

    assert "mean_pool" in canonical_ids
    assert "mean_pooling" not in canonical_ids
    assert alias_target("mean_pooling") == "mean_pool"
    assert "mean_pooling" in list_ablations()


def test_phase_18g_uses_3dacda_as_the_public_framework_display_name() -> None:
    assert get_ablation_spec("no_cons").display_name.startswith("3DACDA")
    assert get_ablation_spec("mean_pool").display_name.startswith("3DACDA")


def test_no_da_is_a_distinct_mmd_zero_framework_ablation() -> None:
    spec = get_ablation_spec("no_da")

    assert spec.display_name.startswith("3DACDA")
    assert spec.requires_target_adaptation is True
    assert spec.intervention is not None
    assert spec.intervention.parameter == "lambda_MMD"
    assert spec.intervention.old_value == 1.0
    assert spec.intervention.new_value == 0.0
    assert spec.equivalent_method is None
    assert "no_da" in APPROVED_ABLATIONS
    assert alias_target("source_only") != "no_da"


def test_mmd_adaptation_is_explicit_and_no_da_only_changes_its_weight() -> None:
    config = load_ablation_config(CONFIG)
    base = config.base_for_direction("ADNI_to_OASIS")

    no_da = resolve_ablation_config(base, "no_da")
    no_proto = resolve_ablation_config(base, "no_proto")

    assert no_da.adaptation_method == "mmd"
    assert no_da.adaptation_weight == 0.0
    assert no_proto.adaptation_method == "mmd"
    assert no_proto.adaptation_weight == 1.0
    assert no_da.losses.lambda_proto == 1.0
    assert no_proto.losses.lambda_proto == 0.0
    assert no_da.adaptation_configuration["kernel"]["bandwidths"]
    assert no_da.adaptation_configuration_hash
    assert no_da.to_dict()["adaptation"] == no_da.adaptation_configuration
    assert no_da.resolved_config_hash == resolve_ablation_config(base, "no_da").resolved_config_hash


@pytest.mark.parametrize(
    "override",
    (
        {"kernel": {"bandwidths": [0.25, 0.5, 1.0]}},
        {"kernel": {"aggregation": "sum"}},
        {"estimator": "unbiased"},
        {"include_diagonal": False},
        {"compute_dtype": "float64"},
    ),
)
def test_mmd_runtime_configuration_overrides_are_rejected(override: dict[str, object]) -> None:
    config = load_ablation_config(CONFIG)
    base = copy.deepcopy(config.base_for_direction("ADNI_to_OASIS"))
    base["adaptation"] = override

    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(base, "no_proto")

    assert error.value.reason == "unapproved_override"
    assert error.value.field == "adaptation"


def test_phase_18g_validate_only_computes_raw_mmd_and_keeps_target_forward() -> None:
    config = load_ablation_config(CONFIG)
    payload = execute(
        config,
        requested_names=("no_da",),
        source_domain="ADNI",
        target_domain="OASIS",
        fold=0,
        seed=42,
        validate_only=True,
    )

    plan = payload["plans"][0]
    assert plan["adaptation_method"] == "mmd"
    assert plan["adaptation_weight"] == 0.0
    assert plan["mmd_loss"] > 0.0
    assert plan["weighted_mmd_loss"] == 0.0
    assert plan["target_forward_executed"] is True
    assert plan["target_labels_in_adaptation"] is False


def test_mmd_identity_reference_and_output_path_are_distinct() -> None:
    config = load_ablation_config(CONFIG)
    mmd = build_equivalence_reference("no_da")
    prototype = build_equivalence_reference("no_proto")
    path = planned_run_path(config, "no_da", "ADNI_to_OASIS", 42, 0)

    assert mmd["adaptation_method"] == "mmd"
    assert mmd["adaptation_weight"] == 0.0
    assert mmd["adaptation_configuration_hash"]
    assert mmd["adaptation_method"] == prototype["adaptation_method"] == "mmd"
    assert mmd["adaptation_weight"] != prototype["adaptation_weight"]
    assert mmd["adaptation_configuration_hash"] != prototype["adaptation_configuration_hash"]
    assert mmd["equivalence_manifest_hash"] != prototype["equivalence_manifest_hash"]
    assert "no_da" in path.parts
