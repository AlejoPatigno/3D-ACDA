from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path

import pytest

from pada3dacb.evaluation.provenance import (
    confined_relative_path,
    hydrate_provenance,
    inspect_input_file,
    raw_identifier_persistence_issues,
    sha256_exact,
    validate_prediction_rows,
    verify_identity_mapping,
)
from pada3dacb.evaluation.schemas import (
    CandidateStatus,
    Direction,
    IdentityMapping,
    IssueCode,
    MethodId,
    PredictionRole,
    UnsafePathError,
)
from tests.phase15_discovery_fixtures import canonical_rows, provenance_values, write_input


def _codes(issues: tuple[object, ...]) -> set[IssueCode]:
    return {issue.code for issue in issues}  # type: ignore[attr-defined]


def test_exact_byte_hash_and_sanitized_relative_path(tmp_path: Path) -> None:
    path = write_input(tmp_path)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha256_exact(path, chunk_size=7) == expected
    assert confined_relative_path(tmp_path, path) == "fold/predictions.csv"
    item, issues = inspect_input_file(tmp_path, path, "shared_method", "v1", expected)
    assert issues == ()
    assert item is not None and item.sha256 == expected and item.size_bytes == path.stat().st_size


def test_path_escape_is_terminal_and_hash_mismatch_is_visible(tmp_path: Path) -> None:
    outside = tmp_path.parent / "private.csv"
    outside.write_bytes(b"private")
    with pytest.raises(UnsafePathError):
        confined_relative_path(tmp_path, outside)

    path = write_input(tmp_path)
    item, issues = inspect_input_file(tmp_path, path, "shared_method", "v1", "0" * 64)
    assert item is None
    assert _codes(issues) == {IssueCode.INPUT_HASH_MISMATCH}
    assert str(outside) not in repr(issues)


def test_complete_provenance_is_ordered_and_conflicts_fail_closed() -> None:
    row_sha = "a" * 64
    record, issues = hydrate_provenance(provenance_values(), row_sha)
    assert issues == ()
    assert record is not None
    assert record.values["method_id"].source_kind == "row"

    companion = ("run_manifest", "b" * 64, {"method_id": "coral"})
    record, issues = hydrate_provenance(provenance_values(), row_sha, (companion,))
    assert record is None
    assert _codes(issues) == {IssueCode.PROVENANCE_CONFLICT}


def test_missing_provenance_requires_an_explicit_derivation_rule() -> None:
    values = provenance_values()
    values.pop("source_subject_assignment_hash")
    source = ("run_manifest", "b" * 64, {"legacy_source_hash": "approved-hash"})

    record, issues = hydrate_provenance(values, "a" * 64, (source,))
    assert record is None
    assert _codes(issues) == {IssueCode.MISSING_REQUIRED_FIELD}

    rules = {"source_subject_assignment_hash": ("run_manifest", "legacy_source_hash", "legacy-source-v1")}
    record, issues = hydrate_provenance(values, "a" * 64, (source,), rules)
    assert issues == () and record is not None
    derived = record.values["source_subject_assignment_hash"]
    assert derived.value == "approved-hash"
    assert derived.derivation_rule == "legacy-source-v1"


def test_approved_identity_mapping_is_verified_and_raw_ids_are_discarded(tmp_path: Path) -> None:
    companion = tmp_path / "identity.csv"
    companion.write_bytes(b"approved exact bytes")
    mapping = IdentityMapping(
        "identity.csv", sha256_exact(companion), "subject_id", "subject_hash", True
    )
    rows = ({"subject_id": "private-a", "true_label": 0, "probabilities": (1.0, 0.0, 0.0)},)
    mapped, issues = verify_identity_mapping(
        rows,
        ({"subject_id": "private-a", "subject_hash": "hash-a"},),
        mapping,
        companion,
    )
    assert issues == ()
    assert mapped == ({"true_label": 0, "probabilities": (1.0, 0.0, 0.0), "subject_hash": "hash-a"},)
    assert "private-a" not in repr(mapped)


def test_identity_mapping_fails_closed_for_unapproved_hash_duplicate_and_conflict(tmp_path: Path) -> None:
    companion = tmp_path / "identity.csv"
    companion.write_bytes(b"approved exact bytes")
    mapping = IdentityMapping(
        "identity.csv", sha256_exact(companion), "subject_id", "subject_hash", True
    )
    raw = ({"subject_id": "private-a", "true_label": 0, "probabilities": (1.0, 0.0, 0.0)},)
    _, issues = verify_identity_mapping(raw, (), None, companion)
    assert _codes(issues) == {IssueCode.UNAPPROVED_IDENTITY_MAPPING}

    companion.write_bytes(b"changed")
    _, issues = verify_identity_mapping(raw, (), mapping, companion)
    assert _codes(issues) == {IssueCode.UNAPPROVED_IDENTITY_MAPPING}
    companion.write_bytes(b"approved exact bytes")

    duplicate = (
        {"subject_id": "private-a", "subject_hash": "hash-a"},
        {"subject_id": "private-a", "subject_hash": "hash-b"},
    )
    _, issues = verify_identity_mapping(raw, duplicate, mapping, companion)
    assert _codes(issues) == {IssueCode.UNSTABLE_SUBJECT_IDENTITY}

    conflicting = ({**raw[0], "subject_hash": "different"},)
    _, issues = verify_identity_mapping(
        conflicting,
        ({"subject_id": "private-a", "subject_hash": "hash-a"},),
        mapping,
        companion,
    )
    assert _codes(issues) == {IssueCode.UNSTABLE_SUBJECT_IDENTITY}


def test_raw_identifier_persistence_guard_is_recursive_and_sanitized() -> None:
    clean = {"subject_hash": "hash-a", "nested": ["available"]}
    assert raw_identifier_persistence_issues(clean, ("subject_id",), ("private-a",)) == ()
    for unsafe in (
        {"subject_id": "private-a"},
        {"nested": [{"message": "private-a"}]},
        ["safe", ("private-a",)],
    ):
        issues = raw_identifier_persistence_issues(unsafe, ("subject_id",), ("private-a",))
        assert _codes(issues) == {IssueCode.RAW_IDENTIFIER_PERSISTENCE_ATTEMPT}
        assert "private-a" not in repr(issues)


def test_direct_supplied_hash_needs_no_identity_companion(tmp_path: Path) -> None:
    rows = ({"subject_hash": "hash-a", "true_label": 0, "probabilities": (1.0, 0.0, 0.0)},)
    mapped, issues = verify_identity_mapping(rows, (), None, tmp_path / "missing.csv")
    assert mapped == rows
    assert issues == ()


def test_prediction_rows_discard_raw_ids_and_preserve_supplied_hashes() -> None:
    rows = canonical_rows()
    predictions, issues = validate_prediction_rows(
        rows,
        MethodId.MMD,
        Direction.ADNI_TO_OASIS,
        17,
        2,
        "best_source_f1",
        PredictionRole.TARGET_EVALUATION,
        "c" * 64,
    )
    assert issues == ()
    assert [item.subject_hash for item in predictions] == ["hash-a", "hash-b"]
    assert "private-a" not in repr(predictions)
    assert all(item.predicted_label == item.true_label for item in predictions)


def test_prediction_defects_use_distinct_issue_codes() -> None:
    common = (
        MethodId.MMD,
        Direction.ADNI_TO_OASIS,
        17,
        2,
        "best_source_f1",
        PredictionRole.TARGET_EVALUATION,
        "c" * 64,
    )
    cases = (
        ({"subject_hash": "a", "true_label": 0, "probabilities": (float("nan"), 0.5, 0.5)}, IssueCode.NON_FINITE_PROBABILITY),
        ({"subject_hash": "a", "true_label": 0, "probabilities": (-0.1, 0.5, 0.6)}, IssueCode.PROBABILITY_OUT_OF_RANGE),
        ({"subject_hash": "a", "true_label": 0, "probabilities": (0.1, 0.2, 0.3)}, IssueCode.PROBABILITY_SUM_INVALID),
        ({"subject_id": "raw-only", "true_label": 0, "probabilities": (1.0, 0.0, 0.0)}, IssueCode.UNSTABLE_SUBJECT_IDENTITY),
    )
    for row, expected in cases:
        predictions, issues = validate_prediction_rows([row], *common)
        assert predictions == ()
        assert _codes(issues) == {expected}
        assert all(issue.status is CandidateStatus.EXCLUDED for issue in issues)
        assert "raw-only" not in repr(issues)


def test_duplicate_and_inconsistent_labels_are_rejected() -> None:
    rows = canonical_rows()
    duplicate = [rows[0], dict(rows[0])]
    _, issues = validate_prediction_rows(duplicate, MethodId.MMD, Direction.ADNI_TO_OASIS, 1, 0, "last", PredictionRole.SOURCE_OOF, "c" * 64)
    assert IssueCode.DUPLICATE_PREDICTION in _codes(issues)

    conflict = [rows[0], {**rows[0], "true_label": 2}]
    _, issues = validate_prediction_rows(conflict, MethodId.MMD, Direction.ADNI_TO_OASIS, 1, 0, "last", PredictionRole.SOURCE_OOF, "c" * 64)
    assert IssueCode.INCONSISTENT_TRUE_LABEL in _codes(issues)


def test_provenance_module_does_not_import_training_code() -> None:
    import pada3dacb.evaluation.provenance as provenance

    tree = ast.parse(inspect.getsource(provenance))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert all(module is None or not module.startswith("pada3dacb.training") for module in imported)
