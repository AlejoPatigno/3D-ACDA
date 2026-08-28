from __future__ import annotations

import pytest

from acda3d.ablations import (
    AblationResolutionError,
    list_ablations,
    resolve_ablation_config,
    validate_target_adaptation_batch,
)

PRIMARY_LOSSES = {
    "lambda_z": 1.0,
    "lambda_c": 1.0,
    "lambda_cons": 0.1,
    "lambda_cbm": 0.5,
    "lambda_anat": 0.2,
    "lambda_proto": 1.0,
    "lambda_pl": 0.1,
    "tau_p": 0.95,
    "proto_margin": 1.0,
    "lambda_sep": 0.1,
    "label_smoothing": 0.1,
    "warm_lambda_z": 0.1,
    "warm_lambda_c": 1.0,
    "warm_lambda_cbm": 1.0,
    "warm_lambda_anat": 1.0,
    "warm_lambda_cons": 0.0,
}


def base_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "base_method": "3D-ACDA",
        "model": {"name": "3D-ACDA", "contextual_encoder": False},
        "losses": PRIMARY_LOSSES,
        "approval": {"status": "approved", "approval_id": "maintainer-phase17"},
        "epochs": {"warm": 1, "full": 1},
        "matrix": {
            "directions": ["ADNI_to_OASIS", "OASIS_to_ADNI"],
            "folds": [0],
            "seeds": [42],
        },
        "assignments": {
            "source": ["source-0"],
            "target_adaptation": ["target-adapt-0"],
            "target_evaluation": ["target-eval-0"],
        },
        "precomputed_artifacts": {"concepts": "fixture-concepts", "jacobians": "fixture-jacobians"},
    }
    config.update(overrides)
    return config


def test_registry_exposes_runnable_and_blocked_inventory_in_stable_order() -> None:
    names = list_ablations()
    assert names[:6] == ("no_proto", "no_pl", "no_cons", "no_concept", "no_anat", "mean_pool")
    assert "no_domain_adaptation" in names
    assert "full" in names
    assert "CFS" in names
    assert "no_prototype" in names


def test_resolve_approved_loss_candidate_changes_only_one_coefficient() -> None:
    resolved = resolve_ablation_config(base_config(), "no_proto")
    assert resolved.candidate_id == "no_proto"
    assert resolved.losses.lambda_proto == 0.0
    assert resolved.losses.lambda_pl == 0.1
    assert resolved.losses.lambda_cbm == 0.5
    assert resolved.intervention.parameter == "lambda_proto"
    assert resolved.intervention.new_value == 0.0
    assert resolved.resolved_config_hash
    assert resolved.model_variant_hash


def test_blocked_alias_is_structured_and_fail_closed() -> None:
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(base_config(), "no_prototype")
    assert error.value.reason == "alias_not_approved"


def test_unresolved_helper_coefficient_is_rejected() -> None:
    config = base_config(losses={**PRIMARY_LOSSES, "lambda_proto": 0.2})
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(config, "no_proto")
    assert error.value.reason == "unresolved_coefficient"


def test_target_adaptation_batch_accepts_exact_unlabeled_contract() -> None:
    batch = {
        "x": "fixture",
        "subject_id": "subject-0",
        "subject_hash": "hash-0",
        "cohort": "OASIS",
    }
    validate_target_adaptation_batch(batch)
    assert resolve_ablation_config(base_config(target_adaptation_batch=batch), "no_pl").candidate_id == "no_pl"


@pytest.mark.parametrize(
    "batch",
    [
        {"x": "fixture", "subject_id": "subject-0", "cohort": "OASIS"},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "artifact": "forbidden"},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "y": 1},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "label": 1},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "label_name": "diagnosis"},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "true_label": 1},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "c_target": 1},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "g_bar": 1},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "diagnosis": 1},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "stored_diagnostic_probabilities": {}},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "concept_targets": {}},
        {"x": "fixture", "subject_id": "subject-0", "subject_hash": "hash-0", "cohort": "OASIS", "jacobian_targets": {}},
    ],
)
def test_target_adaptation_batch_rejects_missing_extra_and_forbidden_fields(batch: dict[str, object]) -> None:
    with pytest.raises(AblationResolutionError) as error:
        validate_target_adaptation_batch(batch)
    assert error.value.reason == "target_label_firewall_violation"
    assert error.value.field == "target_adaptation_batch"


def test_incomplete_matrix_and_target_labels_are_rejected() -> None:
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(base_config(matrix={"directions": ["ADNI_to_OASIS"]}), "no_pl")
    assert error.value.reason == "incomplete_matrix"

    config = base_config(
        target_adaptation_batch={"x": "fixture", "diagnosis": "forbidden"},
    )
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(config, "no_pl")
    assert error.value.reason == "target_label_firewall_violation"


def test_contextual_variants_and_source_only_claim_are_rejected() -> None:
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(base_config(), "full")
    assert error.value.reason == "architecture_disposition_blocked"

    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(base_config(), "no_domain_adaptation")
    assert error.value.reason == "source_only_not_proven"


def test_all_six_approved_candidates_are_single_interventions() -> None:
    parameters = {
        "no_proto": "lambda_proto",
        "no_pl": "lambda_pl",
        "no_cons": "lambda_cons",
        "no_concept": "lambda_cbm",
        "no_anat": "lambda_anat",
    }
    resolved = {name: resolve_ablation_config(base_config(), name) for name in parameters}
    assert {item.intervention.parameter for item in resolved.values()} == set(parameters.values())
    assert resolve_ablation_config(base_config(), "mean_pool").model_variant.aggregator == "MeanPoolAggregator"
    assert len({item.resolved_config_hash for item in resolved.values()}) == 5
    assert len({item.model_variant_hash for item in resolved.values()}) == 1
    assert resolve_ablation_config(base_config(), "mean_pool").model_variant_hash != next(iter(resolved.values())).model_variant_hash


def test_multiple_override_and_contextual_model_fail_closed() -> None:
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(
            base_config(overrides={"lambda_proto": 0.0, "lambda_pl": 0.0}),
            "no_proto",
        )
    assert error.value.reason == "multiple_interventions"

    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(
            base_config(model={"name": "3D-ACDA", "contextual_encoder": True}),
            "no_proto",
        )
    assert error.value.reason == "architecture_disposition_blocked"


def test_missing_explicit_approval_is_not_promoted_to_runnable() -> None:
    config = base_config()
    config.pop("approval")
    with pytest.raises(AblationResolutionError) as error:
        resolve_ablation_config(config, "no_anat")
    assert error.value.reason == "candidate_not_approved"
