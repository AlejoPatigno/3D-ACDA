from __future__ import annotations

import inspect

import pytest

from acda3d.publication.canonical_json import identity_sha256
from acda3d.publication.feasibility import (
    EVIDENCE_TYPES,
    EvidenceType,
    ProductionShapeMetadata,
    ResourceBudgetClosureError,
    ResourceBudgetStatus,
    SyntheticFeasibilityStatus,
    build_resource_budget,
    run_synthetic_feasibility,
    validate_budget_closure,
)

CLASS_LABELS = ("CN", "MCI", "AD")
ROI_LABELS = tuple(f"roi_{index:03d}" for index in range(102))
MATRIX_ID = identity_sha256({"matrix": "synthetic"})


def probe_callbacks() -> dict[str, object]:
    return {
        "matrix_identity_hash": MATRIX_ID,
        "forward_callback": lambda batch: True,
        "backward_callback": lambda batch, output: True,
    }


def production_shape(*, batch_size: int = 2) -> ProductionShapeMetadata:
    return ProductionShapeMetadata(
        input_shape=(batch_size, 1, 8, 10, 12),
        feature_shape=(batch_size, 256, 2, 3, 3),
        roi_mask_shape=(102, 2, 3, 3),
        token_shape=(batch_size, 102, 128),
        embedding_shape=(batch_size, 128),
        concepts_shape=(batch_size, 102),
        c_target_shape=(batch_size, 102),
        g_bar_shape=(batch_size, 102),
        diagnosis_logits_shape=(batch_size, 3),
        class_labels=CLASS_LABELS,
        roi_labels=ROI_LABELS,
    )


def test_synthetic_probe_is_faithful_and_has_no_real_authority() -> None:
    result = run_synthetic_feasibility(
        production_shape=production_shape(),
        requested_batch_size=2,
        forward_callback=lambda batch: batch["x"].shape == (2, 1, 8, 10, 12),
        backward_callback=lambda batch, output: output is True,
        matrix_identity_hash=MATRIX_ID,
    )

    assert result.status is SyntheticFeasibilityStatus.PASS
    assert result.evidence_type is EvidenceType.MEASURED_SYNTHETIC
    assert result.production_fit_established is True
    assert result.real_data_accessed is False
    assert result.real_resource_fields_resolved is False
    assert result.synthetic_forward_success is True
    assert result.synthetic_backward_success is True
    assert result.requested_batch_size == 2


def test_missing_production_shape_is_resource_blocked() -> None:
    result = run_synthetic_feasibility(production_shape=None, requested_batch_size=2)

    assert result.status is SyntheticFeasibilityStatus.RESOURCE_BLOCKED
    assert result.evidence_type is EvidenceType.BLOCKED
    assert result.production_fit_established is False
    assert "production_shape_unavailable" in result.failure_reasons


def test_reduced_probe_is_labeled_and_cannot_establish_fit() -> None:
    result = run_synthetic_feasibility(
        production_shape=production_shape(),
        requested_batch_size=2,
        reduced_engineering_probe=True,
        **probe_callbacks(),
    )

    assert result.status is SyntheticFeasibilityStatus.PASS
    assert result.observation_namespace == "non_publication_engineering_probe"
    assert result.production_fit_established is False
    assert result.evidence_type is EvidenceType.MEASURED_SYNTHETIC


def test_shape_contract_rejects_reduced_or_wrong_scientific_channels() -> None:
    shape = production_shape()
    invalid = ProductionShapeMetadata(
        **{**shape.__dict__, "roi_mask_shape": (101, 2, 3, 3)}
    )

    result = run_synthetic_feasibility(
        production_shape=invalid, requested_batch_size=2, **probe_callbacks()
    )

    assert result.status is SyntheticFeasibilityStatus.FAIL
    assert result.evidence_type is EvidenceType.BLOCKED
    assert "shape_mismatch" in result.failure_reasons


def test_evidence_type_vocabulary_is_exact() -> None:
    assert {item.value for item in EvidenceType} == {
        "measured_synthetic",
        "extrapolated_from_synthetic",
        "not_recorded",
        "blocked",
    }
    assert set(EVIDENCE_TYPES) == {item.value for item in EvidenceType}


def test_mapping_shape_metadata_preserves_explicit_labels() -> None:
    metadata = production_shape().to_mapping()
    result = run_synthetic_feasibility(
        production_shape=metadata, requested_batch_size=2, **probe_callbacks()
    )

    assert result.status is SyntheticFeasibilityStatus.PASS
    assert result.production_input_shape == (2, 1, 8, 10, 12)

    metadata["class_labels"] = ["AD", "MCI", "CN"]
    invalid = run_synthetic_feasibility(
        production_shape=metadata, requested_batch_size=2, **probe_callbacks()
    )
    assert invalid.status is SyntheticFeasibilityStatus.FAIL
    assert "class_order_mismatch" in invalid.failure_reasons


def test_failed_callback_and_non_cpu_request_fail_closed() -> None:
    failed = run_synthetic_feasibility(
        production_shape=production_shape(),
        requested_batch_size=2,
        forward_callback=lambda batch: False,
        backward_callback=lambda batch, output: True,
        matrix_identity_hash=MATRIX_ID,
    )
    assert failed.status is SyntheticFeasibilityStatus.FAIL
    assert failed.synthetic_forward_success is False

    blocked = run_synthetic_feasibility(
        production_shape=production_shape(), requested_batch_size=2, device="cuda",
        **probe_callbacks(),
    )
    assert blocked.status is SyntheticFeasibilityStatus.RESOURCE_BLOCKED
    assert blocked.evidence_type is EvidenceType.BLOCKED


def test_arbitrary_callback_values_do_not_establish_success() -> None:
    backward_called = False

    def backward(batch: object, output: object) -> object:
        nonlocal backward_called
        backward_called = True
        return object()

    result = run_synthetic_feasibility(
        production_shape=production_shape(),
        requested_batch_size=2,
        matrix_identity_hash=MATRIX_ID,
        forward_callback=lambda batch: {"success": True},
        backward_callback=backward,
    )

    assert result.status is SyntheticFeasibilityStatus.FAIL
    assert result.production_fit_established is False
    assert result.synthetic_forward_success is False
    assert result.synthetic_backward_success is None
    assert backward_called is False
    assert "synthetic_forward_invalid_result" in result.failure_reasons


def test_non_boolean_backward_result_does_not_establish_production_fit() -> None:
    result = run_synthetic_feasibility(
        production_shape=production_shape(),
        requested_batch_size=2,
        matrix_identity_hash=MATRIX_ID,
        forward_callback=lambda batch: True,
        backward_callback=lambda batch, output: {"success": True},
    )

    assert result.status is SyntheticFeasibilityStatus.FAIL
    assert result.production_fit_established is False
    assert result.synthetic_forward_success is True
    assert result.synthetic_backward_success is False
    assert "synthetic_backward_invalid_result" in result.failure_reasons


def test_no_training_or_real_data_imports_are_used() -> None:
    import acda3d.publication.feasibility as feasibility

    source = inspect.getsource(feasibility)
    assert "acda3d.training" not in source
    assert "train.py" not in source
    assert "ADNI" not in source
    assert "OASIS" not in source


def test_resource_budget_keeps_synthetic_values_non_closing() -> None:
    budget = build_resource_budget(
        methods=7,
        directions=2,
        folds=5,
        seeds=1,
        synthetic_peak_memory_bytes=1234,
        synthetic_step_time_seconds=0.25,
    )

    assert budget.primary_cell_count == 70
    assert budget.sensitivity_projection_count == 70
    assert budget.status is ResourceBudgetStatus.UNRESOLVED_BLOCKING
    assert budget.fields["wall_time_per_primary_cell"].evidence_type is EvidenceType.EXTRAPOLATED_FROM_SYNTHETIC
    assert budget.fields["gpu_vram"].evidence_type is EvidenceType.BLOCKED
    assert budget.to_mapping()["real_budget_closed"] is False
    with pytest.raises(ResourceBudgetClosureError, match="real evidence"):
        validate_budget_closure(budget)


def test_budget_closure_rejects_missing_real_evidence_even_with_planning_arithmetic() -> None:
    budget = build_resource_budget()

    assert budget.formulas["primary_cell_count"] == "7 × 2 × 5 × 1 = 70"
    assert budget.fields["total_wall_time"].status == "unresolved_blocking"
    with pytest.raises(ResourceBudgetClosureError):
        budget.require_real_closure()


def test_observation_records_unrecorded_optional_values_explicitly() -> None:
    result = run_synthetic_feasibility(
        production_shape=production_shape(),
        matrix_identity_hash=identity_sha256({"matrix": "synthetic"}),
        forward_callback=lambda batch: True,
        backward_callback=lambda batch, output: True,
    )

    payload = result.to_mapping()
    assert payload["synthetic_peak_memory_bytes"] == "not_recorded"
    assert payload["synthetic_wall_time_seconds"] == "not_recorded"
    assert payload["device"] == "cpu"
    assert payload["dtype"] == "float32"


def test_noop_feasibility_is_resource_blocked_without_callbacks_or_matrix_identity() -> None:
    result = run_synthetic_feasibility(production_shape=production_shape(), requested_batch_size=2)

    assert result.status is SyntheticFeasibilityStatus.RESOURCE_BLOCKED
    assert result.production_fit_established is False
    assert "matrix_identity_required" in result.failure_reasons
    assert "forward_callback_required" in result.failure_reasons
    assert "backward_callback_required" in result.failure_reasons


def test_g_bar_shape_is_required_to_match_batch_and_102_rois() -> None:
    shape = production_shape()
    invalid = ProductionShapeMetadata(**{**shape.__dict__, "g_bar_shape": (2, 101)})

    result = run_synthetic_feasibility(
        invalid,
        requested_batch_size=2,
        matrix_identity_hash=identity_sha256({"matrix": "synthetic"}),
        forward_callback=lambda batch: True,
        backward_callback=lambda batch, output: True,
    )

    assert result.status is SyntheticFeasibilityStatus.FAIL
    assert "g_bar_shape_mismatch" in result.failure_reasons
