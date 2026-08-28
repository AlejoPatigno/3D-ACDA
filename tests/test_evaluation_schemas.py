from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

from acda3d.evaluation.schemas import (
    AGGREGATE_METRIC_NAMES,
    ANALYSIS_CLASS_INDICES,
    ANALYSIS_CLASS_LABELS,
    COMPARATOR_METHODS,
    PAIRED_METRIC_NAMES,
    PER_CLASS_METRIC_NAMES,
    PROTOCOL_VERSION,
    REQUIRED_PROVENANCE_FIELDS,
    SCHEMA_VERSION,
    AnalysisMode,
    BootstrapInterval,
    CandidateIssue,
    CandidateStatus,
    CanonicalPrediction,
    CheckpointPolicy,
    ComputationalValue,
    ConfusionResult,
    Direction,
    EvaluationBundle,
    EvaluationPlan,
    EvaluationRequest,
    ExpectedPopulation,
    HolmRow,
    IdentityMapping,
    InputFile,
    IssueCode,
    McNemarResult,
    MethodId,
    MetricSet,
    MetricValue,
    NormalizedBatch,
    PairedDifference,
    PerClassMetric,
    PredictionRole,
    ProvenanceRecord,
    ProvenanceValue,
    RunMode,
    SubjectPrediction,
    ValueStatus,
    canonical_json,
    canonical_sha256,
)


def test_fixed_public_inventory_and_versions() -> None:
    import acda3d.evaluation as public_api

    assert public_api.MethodId is MethodId
    assert public_api.SCHEMA_VERSION == SCHEMA_VERSION
    assert ANALYSIS_CLASS_LABELS == ("CN", "MCI", "AD")
    assert ANALYSIS_CLASS_INDICES == (0, 1, 2)
    assert SCHEMA_VERSION == "phase15-output-v2"
    assert PROTOCOL_VERSION == "phase15-statistical-v2"
    assert [item.value for item in MethodId] == [
        "source_only",
        "coral",
        "mmd",
        "cdan",
        "prototype_pseudo",
        "aagn",
        "faster_snn",
    ]


def test_direction_and_checkpoint_policies_are_predeclared() -> None:
    assert Direction.ADNI_TO_OASIS.cohorts == ("ADNI", "OASIS")
    assert Direction.OASIS_TO_ADNI.cohorts == ("OASIS", "ADNI")
    assert CheckpointPolicy.PRIMARY_BEST_SOURCE_F1.logical_checkpoint == "best_source_f1"
    assert CheckpointPolicy.SENSITIVITY_LAST.logical_checkpoint == "last"
    assert {item.value for item in PredictionRole} == {"source_oof", "target_evaluation"}


def test_closed_enums_reject_unknown_values() -> None:
    for enum_type, value in (
        (MethodId, "full"),
        (Direction, "pooled"),
        (CheckpointPolicy, "best_target_f1"),
        (RunMode, "train"),
        (IssueCode, "undefined_metric"),
    ):
        with pytest.raises(ValueError):
            enum_type(value)


def test_issue_code_taxonomy_is_exact() -> None:
    assert {item.value for item in IssueCode} == {
        "unsupported_method",
        "unsupported_direction",
        "unsupported_checkpoint_policy",
        "unsupported_class_order",
        "missing_required_field",
        "unapproved_identity_mapping",
        "provenance_conflict",
        "input_hash_mismatch",
        "target_evaluation_membership_unprovable",
        "unstable_subject_identity",
        "raw_identifier_persistence_attempt",
        "duplicate_prediction",
        "inconsistent_true_label",
        "non_finite_probability",
        "probability_out_of_range",
        "probability_sum_invalid",
        "incomplete_ensemble",
        "checkpoint_policy_mismatch",
        "incompatible_subjects",
    }


def test_metric_value_enforces_value_status_reason_contract() -> None:
    assert MetricValue.available(0.75).reason is None
    unavailable = MetricValue.unavailable("zero_true_support")
    assert unavailable.value is None
    assert unavailable.status is ValueStatus.UNAVAILABLE

    invalid = (
        {"value": float("nan"), "status": ValueStatus.AVAILABLE, "reason": None},
        {"value": None, "status": ValueStatus.AVAILABLE, "reason": None},
        {"value": 1.0, "status": ValueStatus.UNAVAILABLE, "reason": "missing_class"},
        {"value": None, "status": ValueStatus.UNAVAILABLE, "reason": None},
        {"value": 1.0, "status": ValueStatus.AVAILABLE, "reason": "should_be_null"},
    )
    for kwargs in invalid:
        with pytest.raises(ValueError):
            MetricValue(**kwargs)


def test_frozen_request_and_issue_contracts() -> None:
    request = EvaluationRequest(
        methods=(MethodId.SOURCE_ONLY,),
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        analysis_mode=AnalysisMode.SYNTHETIC_TEST_ONLY,
        run_mode=RunMode.VALIDATE_ONLY,
        bootstrap_replicates=10_000,
        bootstrap_seed=17,
    )
    with pytest.raises(FrozenInstanceError):
        request.bootstrap_seed = 3  # type: ignore[misc]
    with pytest.raises(ValueError):
        EvaluationRequest(
            methods=(),
            directions=request.directions,
            checkpoint_policies=request.checkpoint_policies,
            analysis_mode=request.analysis_mode,
            run_mode=request.run_mode,
            bootstrap_replicates=1,
            bootstrap_seed=0,
        )

    issue = CandidateIssue(IssueCode.INCOMPLETE_ENSEMBLE, CandidateStatus.INCOMPLETE)
    assert issue.detail is None
    with pytest.raises(FrozenInstanceError):
        issue.detail = "changed"  # type: ignore[misc]


def test_canonical_serialization_and_identity_are_stable() -> None:
    left = {"z": (MethodId.MMD, 2), "a": MetricValue.available(0.5)}
    right = {"a": MetricValue.available(0.5), "z": (MethodId.MMD, 2)}
    encoded = canonical_json(left)
    assert encoded == canonical_json(right)
    assert json.loads(encoded) == {
        "a": {"reason": None, "status": "available", "value": 0.5},
        "z": ["mmd", 2],
    }
    assert canonical_sha256(left) == canonical_sha256(right)
    assert len(canonical_sha256(left)) == 64


def test_canonical_serialization_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_json({"value": float("inf")})


def test_schema_module_has_no_io_or_training_imports() -> None:
    import acda3d.evaluation.schemas as schemas

    imports = {node.names[0].name.split(".")[0] for node in ast.walk(ast.parse(inspect.getsource(schemas))) if isinstance(node, ast.Import)}
    assert imports <= {"hashlib", "json", "math"}


def _provenance_record() -> ProvenanceRecord:
    values = {
        field: ProvenanceValue(field, f"value-{field}", "run_manifest", "a" * 64)
        for field in REQUIRED_PROVENANCE_FIELDS
    }
    return ProvenanceRecord(values, ("b" * 64,), ("row_manifest_equal",))


def test_identity_mapping_is_approved_frozen_and_canonical() -> None:
    mapping = IdentityMapping(
        "identity/adni_subjects.csv", "a" * 64, "participant_id", "subject_hash", True
    )
    assert json.loads(canonical_json(mapping)) == {
        "approved": True,
        "raw_identifier_field": "participant_id",
        "relative_path": "identity/adni_subjects.csv",
        "sha256": "a" * 64,
        "subject_hash_field": "subject_hash",
    }
    with pytest.raises(FrozenInstanceError):
        mapping.approved = False  # type: ignore[misc]
    invalid = (
        ("identity/map.csv", "a" * 64, "participant_id", "subject_hash", False),
        ("../private.csv", "a" * 64, "participant_id", "subject_hash", True),
        ("identity/map.csv", "bad", "participant_id", "subject_hash", True),
        ("identity/map.csv", "a" * 64, "", "subject_hash", True),
        ("identity/map.csv", "a" * 64, "subject_hash", "subject_hash", True),
        ("identity/map.csv", "a" * 64, "participant_id", "derived_hash", True),
    )
    for values in invalid:
        with pytest.raises(ValueError):
            IdentityMapping(*values)


def test_expected_population_is_external_ordered_and_contains_only_hashes() -> None:
    population = ExpectedPopulation(
        Direction.ADNI_TO_OASIS,
        PredictionRole.TARGET_EVALUATION,
        "populations/adni_to_oasis_target.csv",
        "b" * 64,
        ("hash-001", "hash-002"),
    )
    assert population.subject_hashes == ("hash-001", "hash-002")
    assert canonical_sha256(population) == canonical_sha256(population)
    invalid_subjects = ((), ("hash-001", "hash-001"), ("hash-002", "hash-001"), ("",))
    for subjects in invalid_subjects:
        with pytest.raises(ValueError):
            ExpectedPopulation(
                Direction.ADNI_TO_OASIS,
                PredictionRole.SOURCE_OOF,
                "populations/source.csv",
                "b" * 64,
                subjects,
            )
    for path, digest in (("/private.csv", "b" * 64), ("../escape.csv", "b" * 64), ("ok.csv", "bad")):
        with pytest.raises(ValueError):
            ExpectedPopulation(
                Direction.ADNI_TO_OASIS,
                PredictionRole.SOURCE_OOF,
                path,
                digest,
                ("hash-001",),
            )


def test_input_file_is_frozen_and_sanitized() -> None:
    item = InputFile("fold/predictions.csv", "a" * 64, 12, "shared_method", "v1")
    assert item.relative_path == "fold/predictions.csv"
    with pytest.raises(FrozenInstanceError):
        item.size_bytes = 13  # type: ignore[misc]
    for path in ("/private/predictions.csv", "../escape.csv", "raw\\subject.csv"):
        with pytest.raises(ValueError):
            InputFile(path, "a" * 64, 1, "shared_method", "v1")
    with pytest.raises(ValueError):
        InputFile("ok.csv", "not-a-hash", 1, "shared_method", "v1")


def test_provenance_values_forbid_identity_derivation() -> None:
    direct = ProvenanceValue("method_id", "mmd", "row", "a" * 64)
    assert direct.derivation_rule is None
    derived = ProvenanceValue("class_order", ("CN", "MCI", "AD"), "companion", "b" * 64, "fixed-v1")
    assert derived.derivation_rule == "fixed-v1"
    with pytest.raises(ValueError, match="subject_hash"):
        ProvenanceValue("subject_hash", "opaque", "companion", "b" * 64, "derive-id")


def test_provenance_record_requires_exact_fields_and_is_immutable() -> None:
    record = _provenance_record()
    assert tuple(record.values) == REQUIRED_PROVENANCE_FIELDS
    with pytest.raises(TypeError):
        record.values["method_id"] = record.values["method_id"]  # type: ignore[index]
    incomplete = dict(record.values)
    incomplete.pop("class_order")
    with pytest.raises(ValueError, match="required provenance"):
        ProvenanceRecord(incomplete, record.input_sha256s, ())


def test_canonical_prediction_validates_subject_probabilities_and_identity() -> None:
    prediction = CanonicalPrediction(
        MethodId.MMD,
        Direction.ADNI_TO_OASIS,
        17,
        2,
        "best_source_f1",
        PredictionRole.TARGET_EVALUATION,
        "subject-hash",
        1,
        (0.1, 0.7, 0.2),
        "c" * 64,
    )
    assert prediction.predicted_label == 1
    invalid_probabilities = ((0.1, 0.9), (0.1, float("nan"), 0.9), (-0.1, 0.5, 0.6), (0.1, 0.2, 0.3))
    for probabilities in invalid_probabilities:
        with pytest.raises(ValueError):
            CanonicalPrediction(
                prediction.method_id,
                prediction.direction,
                prediction.seed,
                prediction.fold,
                prediction.logical_checkpoint,
                prediction.role,
                prediction.subject_hash,
                prediction.true_label,
                probabilities,
                prediction.provenance_ref,
            )


def test_subject_prediction_is_final_frozen_and_has_no_fake_fold_or_seed() -> None:
    subject = SubjectPrediction(
        MethodId.MMD, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, "subject-hash", 1,
        (0.2, 0.6, 0.2), 5, 2, ("a" * 64, "b" * 64),
    )
    assert subject.predicted_label == 1
    assert "seed" not in subject.__dataclass_fields__
    assert "fold" not in subject.__dataclass_fields__
    with pytest.raises(FrozenInstanceError):
        subject.fold_count = 4  # type: ignore[misc]
    assert canonical_json(subject) == canonical_json(subject)


def test_subject_prediction_rejects_partial_or_invalid_final_rows() -> None:
    common = (
        MethodId.MMD, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, "subject-hash", 1, (0.2, 0.6, 0.2),
    )
    for fold_count, seed_count, hashes in (
        (0, 2, ("a" * 64,)), (5, 0, ("a" * 64,)), (5, 2, ("bad",)),
    ):
        with pytest.raises(ValueError):
            SubjectPrediction(*common, fold_count, seed_count, hashes)
    with pytest.raises(ValueError):
        SubjectPrediction(*common, 5, 2, ("a" * 64,), ValueStatus.UNAVAILABLE, None)


def test_subject_prediction_ties_use_smallest_fixed_class_index() -> None:
    subject = SubjectPrediction(
        MethodId.CORAL, Direction.OASIS_TO_ADNI, CheckpointPolicy.SENSITIVITY_LAST,
        "subject-hash", 2, (0.4, 0.4, 0.2), 5, 1, ("a" * 64,),
    )
    assert subject.predicted_label == 0


def _complete_metric_set() -> MetricSet:
    aggregates = {name: MetricValue.available(0.5) for name in AGGREGATE_METRIC_NAMES}
    per_class = tuple(
        PerClassMetric(
            ANALYSIS_CLASS_LABELS[index], index, MetricValue.available(2),
            metric, MetricValue.available(2 if metric == "support" else 0.5),
        )
        for index in ANALYSIS_CLASS_INDICES
        for metric in PER_CLASS_METRIC_NAMES
    )
    return MetricSet(6, aggregates, per_class)


def test_metric_result_schemas_are_frozen_complete_and_canonical() -> None:
    result = _complete_metric_set()
    assert tuple(result.aggregate_metrics) == AGGREGATE_METRIC_NAMES
    assert len(result.per_class_metrics) == 24
    assert canonical_json(result) == canonical_json(result)
    with pytest.raises(TypeError):
        result.aggregate_metrics["accuracy"] = MetricValue.available(1.0)  # type: ignore[index]


def test_metric_set_rejects_missing_or_misordered_rows() -> None:
    valid = _complete_metric_set()
    missing = dict(valid.aggregate_metrics)
    missing.pop("accuracy")
    with pytest.raises(ValueError, match="aggregate"):
        MetricSet(valid.subject_count, missing, valid.per_class_metrics)
    with pytest.raises(ValueError, match="per-class"):
        MetricSet(valid.subject_count, valid.aggregate_metrics, valid.per_class_metrics[:-1])
    with pytest.raises(ValueError, match="class label"):
        PerClassMetric("AD", 0, MetricValue.available(1), "support", MetricValue.available(1))


def test_confusion_result_enforces_fixed_shape_and_zero_support_rows() -> None:
    result = ConfusionResult(
        ((2, 0, 0), (0, 1, 1), (0, 0, 0)),
        ((1.0, 0.0, 0.0), (0.0, 0.5, 0.5), (None, None, None)),
        (MetricValue.available(2), MetricValue.available(2), MetricValue.unavailable("zero_true_support")),
    )
    assert result.subject_count == 4
    assert canonical_json(result) == canonical_json(result)
    with pytest.raises(ValueError):
        ConfusionResult(((1, 0),), ((1.0, 0.0),), (MetricValue.available(1),))
    with pytest.raises(ValueError, match="zero-support"):
        ConfusionResult(
            ((0, 0, 0), (0, 1, 0), (0, 0, 1)),
            ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            (MetricValue.unavailable("zero_true_support"), MetricValue.available(1), MetricValue.available(1)),
        )


def test_inferential_result_schemas_are_frozen_and_canonical() -> None:
    interval = BootstrapInterval(
        "accuracy", 0.75, 0.95, "percentile", 0.5, 1.0, 17,
        100, 95, 5, ValueStatus.AVAILABLE, None,
    )
    paired = PairedDifference(
        MethodId.CORAL, "accuracy", "prototype_pseudo-comparator", 0.1,
        0.95, "percentile", -0.1, 0.2, "centered_plus_one", 0.2,
        17, 100, 100, 0, ValueStatus.AVAILABLE, None,
    )
    mcnemar = McNemarResult(
        MethodId.CORAL, 4, 1, 1, 1, 1, 2, "exact_two_sided_mcnemar",
        1.0, ValueStatus.AVAILABLE, None, None,
    )
    holm = HolmRow(
        "paired_bootstrap", "accuracy", 6, 6, MethodId.CORAL,
        0.01, 1, 0.06, ValueStatus.AVAILABLE, None,
    )
    assert canonical_json((interval, paired, mcnemar, holm)) == canonical_json(
        (interval, paired, mcnemar, holm)
    )
    with pytest.raises(FrozenInstanceError):
        interval.successful = 94  # type: ignore[misc]


def test_inferential_counts_and_status_contracts_reject_invalid_rows() -> None:
    with pytest.raises(ValueError, match="counts"):
        BootstrapInterval(
            "accuracy", 0.5, 0.95, "percentile", 0.1, 0.9, 1,
            10, 8, 1, ValueStatus.AVAILABLE, None,
        )
    with pytest.raises(ValueError, match="unavailable"):
        BootstrapInterval(
            "accuracy", 0.5, 0.95, "percentile", None, None, 1,
            10, 8, 2, ValueStatus.UNAVAILABLE, None,
        )
    unavailable = PairedDifference(
        MethodId.MMD, "macro_ovr_roc_auc", "prototype_pseudo-comparator", None,
        0.95, "percentile", None, None, "centered_plus_one", None,
        2, 10, 0, 10, ValueStatus.UNAVAILABLE, "observed_metric_unavailable",
    )
    assert unavailable.raw_p_value is None


def test_mcnemar_and_holm_enforce_protocol_identity_and_ranges() -> None:
    zero = McNemarResult(
        MethodId.SOURCE_ONLY, 3, 1, 0, 0, 2, 0, "exact_two_sided_mcnemar",
        1.0, ValueStatus.AVAILABLE, None, "no_discordant_pairs",
    )
    assert zero.note_code == "no_discordant_pairs"
    with pytest.raises(ValueError, match="contingency"):
        McNemarResult(
            MethodId.CORAL, 4, 1, 1, 1, 0, 2, "exact_two_sided_mcnemar",
            1.0, ValueStatus.AVAILABLE, None, None,
        )
    with pytest.raises(ValueError, match="comparator"):
        HolmRow(
            "mcnemar_accuracy", None, 6, 1, MethodId.PROTOTYPE_PSEUDO,
            0.5, 1, 1.0, ValueStatus.AVAILABLE, None,
        )
    assert tuple(method.value for method in COMPARATOR_METHODS) == (
        "source_only", "coral", "mmd", "cdan", "aagn", "faster_snn",
    )
    assert PAIRED_METRIC_NAMES == (
        "accuracy", "balanced_accuracy", "macro_f1", "multiclass_mcc",
        "macro_ovr_roc_auc",
    )


def test_computational_value_enforces_finite_null_unit_and_source_contracts() -> None:
    available = ComputationalValue(
        "training_runtime_seconds", 12.5, "seconds",
        ValueStatus.AVAILABLE, None, "a" * 64,
    )
    missing = ComputationalValue(
        "peak_memory_bytes", None, "bytes",
        ValueStatus.NOT_RECORDED, "not_recorded", None,
    )
    assert canonical_json((available, missing)) == canonical_json((available, missing))
    with pytest.raises(ValueError, match="available"):
        ComputationalValue("runtime", float("nan"), "seconds", ValueStatus.AVAILABLE, None, "a" * 64)
    with pytest.raises(ValueError, match="null"):
        ComputationalValue("runtime", 1.0, "seconds", ValueStatus.NOT_RECORDED, "missing", None)


def test_evaluation_plan_is_frozen_exact_and_manifest_last() -> None:
    plan = EvaluationPlan(
        "a" * 64,
        AnalysisMode.SYNTHETIC_TEST_ONLY,
        (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,),
        (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        (
            "predictive/adni_to_oasis/primary_best_source_f1/inclusion_report.csv",
            "evaluation_manifest.json",
        ),
    )
    assert plan.intended_relative_paths[-1] == "evaluation_manifest.json"
    with pytest.raises(FrozenInstanceError):
        plan.evaluation_identity = "b" * 64  # type: ignore[misc]
    with pytest.raises(ValueError, match="manifest"):
        EvaluationPlan(
            plan.evaluation_identity, plan.analysis_mode, plan.methods,
            plan.directions, plan.checkpoint_policies,
            ("evaluation_manifest.json", "method_status.csv"),
        )
    with pytest.raises(ValueError, match="relative"):
        EvaluationPlan(
            plan.evaluation_identity, plan.analysis_mode, plan.methods,
            plan.directions, plan.checkpoint_policies,
            ("../escape.csv", "evaluation_manifest.json"),
        )


def test_evaluation_bundle_freezes_subject_tables_results_and_identity() -> None:
    subject = SubjectPrediction(
        MethodId.MMD, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, "subject-hash", 1,
        (0.2, 0.6, 0.2), 5, 2, ("a" * 64,),
    )
    bundle = EvaluationBundle(
        "b" * 64,
        {"mmd": (subject,)},
        {"metrics/predictive_metrics.csv": "c" * 64},
        (ComputationalValue(
            "completed_folds", 5, "count", ValueStatus.AVAILABLE, None, "d" * 64,
        ),),
    )
    assert canonical_json(bundle) == canonical_json(bundle)
    with pytest.raises(TypeError):
        bundle.subject_tables["mmd"] = ()  # type: ignore[index]
    with pytest.raises(ValueError, match="method"):
        EvaluationBundle(
            bundle.evaluation_identity, {"coral": (subject,)},
            bundle.result_sha256s, bundle.computational_values,
        )


def test_normalized_batch_uses_one_family_and_canonical_contracts() -> None:
    input_file = InputFile("fold/predictions.csv", "a" * 64, 12, "shared_method", "v1")
    batch = NormalizedBatch(
        "shared-method-v1",
        "shared_method",
        (input_file,),
        (_provenance_record(),),
        (),
        (),
        (CandidateIssue(IssueCode.INCOMPLETE_ENSEMBLE, CandidateStatus.INCOMPLETE),),
    )
    assert canonical_sha256(batch) == canonical_sha256(batch)
    with pytest.raises(ValueError, match="schema family"):
        NormalizedBatch("adapter", "baseline_combined", (input_file,), (), (), (), ())
