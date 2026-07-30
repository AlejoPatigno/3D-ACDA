from __future__ import annotations

from collections.abc import Mapping

import pytest

import pada3dacb.evaluation.report as report_module
from pada3dacb.evaluation.report import (
    ReportState,
    build_report_statistics,
    extract_computational_values,
    orchestrate_report,
)
from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    AuthorizationGateError,
    CheckpointPolicy,
    Direction,
    EvaluationPlan,
    EvaluationRequest,
    MethodId,
    RunMode,
    SubjectPrediction,
    ValueStatus,
)


def _request(mode: RunMode, analysis: AnalysisMode = AnalysisMode.SYNTHETIC_TEST_ONLY) -> EvaluationRequest:
    return EvaluationRequest(
        (MethodId.MMD,), (Direction.ADNI_TO_OASIS,),
        (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        analysis, mode, 10, 17,
    )


def _plan() -> EvaluationPlan:
    return EvaluationPlan(
        "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY,
        (MethodId.MMD,), (Direction.ADNI_TO_OASIS,),
        (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        ("method_status.csv", "evaluation_manifest.json"),
    )


def _subject(method: MethodId = MethodId.MMD) -> SubjectPrediction:
    return SubjectPrediction(
        method, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, "subject", 1,
        (0.1, 0.8, 0.1), 5, 2, ("b" * 64,),
    )


def _seams() -> tuple[dict[str, int], object, object, object]:
    calls = {"load": 0, "statistics": 0, "write": 0}

    def load() -> tuple[Mapping[str, tuple[SubjectPrediction, ...]], tuple[Mapping[str, object], ...]]:
        calls["load"] += 1
        return {"mmd": (_subject(),)}, ({"source_sha256": "c" * 64, "completed_folds": 5},)

    def statistics(
        tables: Mapping[str, tuple[SubjectPrediction, ...]],
    ) -> Mapping[str, bytes]:
        calls["statistics"] += 1
        assert tuple(tables) == ("mmd",)
        return {"metrics/predictive_metrics.csv": b"metric,value\naccuracy,1.0\n"}

    def write(bundle: object) -> None:
        calls["write"] += 1

    return calls, load, statistics, write


def test_dry_run_plans_without_loading_statistics_or_writes() -> None:
    calls, load, statistics, write = _seams()
    outcome = orchestrate_report(
        _request(RunMode.DRY_RUN), _plan(), gate_allowed=False,
        load_validated=load, build_statistics=statistics, write_bundle=write,
    )
    assert outcome.state is ReportState.PLANNED
    assert outcome.bundle is None
    assert calls == {"load": 0, "statistics": 0, "write": 0}


def test_validate_only_loads_canonical_tables_without_statistics_or_writes() -> None:
    calls, load, statistics, write = _seams()
    outcome = orchestrate_report(
        _request(RunMode.VALIDATE_ONLY), _plan(), gate_allowed=False,
        load_validated=load, build_statistics=statistics, write_bundle=write,
    )
    assert outcome.state is ReportState.VALIDATED
    assert outcome.bundle is None
    assert calls == {"load": 1, "statistics": 0, "write": 0}


def test_real_evaluate_gate_denial_stops_before_load_statistics_and_write() -> None:
    calls, load, statistics, write = _seams()
    real_plan = EvaluationPlan(
        _plan().evaluation_identity, AnalysisMode.REAL,
        _plan().methods, _plan().directions, _plan().checkpoint_policies,
        _plan().intended_relative_paths,
    )
    with pytest.raises(AuthorizationGateError, match="gate"):
        orchestrate_report(
            _request(RunMode.EVALUATE, AnalysisMode.REAL), real_plan,
            gate_allowed=False, load_validated=load,
            build_statistics=statistics, write_bundle=write,
        )
    assert calls == {"load": 0, "statistics": 0, "write": 0}


def test_synthetic_evaluate_builds_identity_bound_bundle_and_writes_once() -> None:
    calls, load, statistics, write = _seams()
    outcome = orchestrate_report(
        _request(RunMode.EVALUATE), _plan(), gate_allowed=False,
        load_validated=load, build_statistics=statistics, write_bundle=write,
    )
    assert outcome.state is ReportState.COMPLETED
    assert outcome.bundle is not None
    assert outcome.bundle.evaluation_identity == _plan().evaluation_identity
    assert tuple(outcome.bundle.subject_tables) == ("mmd",)
    assert tuple(outcome.bundle.result_sha256s) == ("metrics/predictive_metrics.csv",)
    assert calls == {"load": 1, "statistics": 1, "write": 1}


def test_report_rejects_noncanonical_subject_table_before_statistics() -> None:
    calls, _, statistics, write = _seams()

    def mixed_load() -> tuple[Mapping[str, tuple[SubjectPrediction, ...]], tuple[Mapping[str, object], ...]]:
        calls["load"] += 1
        return {"mmd": (_subject(), _subject(MethodId.CORAL))}, ()

    with pytest.raises(ValueError, match="method"):
        orchestrate_report(
            _request(RunMode.EVALUATE), _plan(), gate_allowed=False,
            load_validated=mixed_load, build_statistics=statistics, write_bundle=write,
        )
    assert calls == {"load": 1, "statistics": 0, "write": 0}


def _statistics_table(method: MethodId) -> tuple[SubjectPrediction, ...]:
    truths = (0, 0, 1, 1, 2, 2)
    return tuple(
        SubjectPrediction(
            method, Direction.ADNI_TO_OASIS,
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, f"subject-{index}", truth,
            tuple(0.9 if class_index == truth else 0.05 for class_index in range(3)),
            5, 1, (f"{index + 1:064x}",),
        )
        for index, truth in enumerate(truths)
    )


def test_report_statistics_composes_all_methods_and_fixed_inference_families() -> None:
    tables = {method.value: _statistics_table(method) for method in reversed(tuple(MethodId))}
    result = build_report_statistics(tables, bootstrap_replicates=5, bootstrap_seed=17)
    assert tuple(result.metrics) == tuple(MethodId)
    assert tuple(result.confusions) == tuple(MethodId)
    assert tuple(result.bootstrap_intervals) == tuple(MethodId)
    assert all(len(rows) == 12 for rows in result.bootstrap_intervals.values())
    assert tuple(row.comparator_method for row in result.mcnemar_results) == (
        MethodId.SOURCE_ONLY, MethodId.CORAL, MethodId.MMD,
        MethodId.CDAN, MethodId.AAGN, MethodId.FASTER_SNN,
    )
    assert len(result.paired_differences) == 30
    assert len(result.holm_rows) == 36
    assert all(row.family_size == 6 for row in result.holm_rows)
    assert result == build_report_statistics(tables, bootstrap_replicates=5, bootstrap_seed=17)


def test_report_statistics_bounds_metric_computation_per_resampled_pair(monkeypatch) -> None:
    calls = 0
    original = report_module.compute_metrics

    def counted(rows, *, allow_repeated_subjects=False):
        nonlocal calls
        calls += 1
        return original(rows, allow_repeated_subjects=allow_repeated_subjects)

    monkeypatch.setattr(report_module, "compute_metrics", counted)
    tables = {
        method.value: _statistics_table(method)
        for method in (MethodId.PROTOTYPE_PSEUDO, MethodId.MMD)
    }
    build_report_statistics(tables, bootstrap_replicates=3, bootstrap_seed=9)
    assert calls == 18


def test_report_statistics_retains_unavailable_missing_comparator_slots() -> None:
    tables = {method.value: _statistics_table(method) for method in MethodId if method is not MethodId.CDAN}
    result = build_report_statistics(tables, bootstrap_replicates=3, bootstrap_seed=9)
    missing_mcnemar = next(
        row for row in result.mcnemar_results if row.comparator_method is MethodId.CDAN
    )
    assert missing_mcnemar.reason == "comparator_method_unavailable"
    assert sum(row.comparator_method is MethodId.CDAN for row in result.paired_differences) == 5
    assert all(row.family_size == 6 for row in result.holm_rows)


def test_computational_extraction_reports_available_missing_and_conflicting_values() -> None:
    values = extract_computational_values((
        {"source_sha256": "a" * 64, "completed_folds": 5, "training_runtime_seconds": 12.5},
        {"source_sha256": "b" * 64, "completed_folds": 5, "training_runtime_seconds": 13.0},
    ))
    by_field = {value.field: value for value in values}
    assert by_field["completed_folds"].value == 5
    assert by_field["completed_folds"].status is ValueStatus.AVAILABLE
    assert by_field["training_runtime_seconds"].reason == "conflicting_values"
    assert by_field["peak_memory_bytes"].status is ValueStatus.NOT_RECORDED
    assert by_field["peak_memory_bytes"].reason == "not_recorded"
