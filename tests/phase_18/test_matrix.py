from __future__ import annotations

from dataclasses import replace

import pytest

from pada3dacb.publication.experiment_matrix import (
    DIRECTIONS,
    METHODS,
    MatrixValidationError,
    RowKind,
    RowState,
    generate_matrix,
    matrix_content_hash,
    validate_matrix,
)
from pada3dacb.publication.validation import validate_matrix_input


def test_matrix_has_deterministic_complete_cardinality_and_counts() -> None:
    matrix = generate_matrix(seeds=[42])

    assert matrix.counts == {"training": 70, "checkpoint_projection": 70, "total": 140}
    assert len(matrix.training_rows) == 70
    assert len(matrix.projection_rows) == 70
    assert [row.method_id for row in matrix.training_rows[:10]] == ["source_only"] * 10
    assert matrix.training_rows[0].direction == "adni_to_oasis"
    assert matrix.training_rows[0].fold == 0
    assert matrix.training_rows[-1].method_id == "faster_snn"
    assert matrix.training_rows[-1].direction == "oasis_to_adni"
    assert matrix.training_rows[-1].fold == 4


def test_matrix_rows_have_training_and_projection_semantics() -> None:
    matrix = generate_matrix(seeds=[42])

    for training, projection in zip(
        matrix.training_rows, matrix.projection_rows, strict=True
    ):
        assert training.row_kind is RowKind.TRAINING
        assert training.training_invocation is True
        assert training.parent_training_id is None
        assert training.checkpoint_policy == "best_source_f1"
        assert projection.row_kind is RowKind.CHECKPOINT_PROJECTION
        assert projection.training_invocation is False
        assert projection.parent_training_id == training.row_id
        assert projection.checkpoint_policy == "last"
        assert projection.state in {
            RowState.PLANNED,
            RowState.BLOCKED_CONFIGURATION,
            RowState.BLOCKED_DATA,
            RowState.BLOCKED_RESOURCES,
        }
        assert projection.completion_allowed is False


def test_matrix_identity_and_order_are_repeatable() -> None:
    policy = {"seeds": [7, 42], "resolved": True, "source": "test"}
    first = generate_matrix(seeds=[7, 42], resolved_seed_policy=policy)
    second = generate_matrix(seeds=[42, 7], resolved_seed_policy=policy)

    assert first.matrix_id == second.matrix_id
    assert [row.row_id for row in first.rows] == [row.row_id for row in second.rows]
    assert [row.seed for row in first.training_rows[:4]] == [7, 7, 7, 7]


def test_matrix_requires_explicit_seed_input() -> None:
    with pytest.raises(TypeError):
        generate_matrix()  # type: ignore[call-arg]


def test_default_publication_matrix_rejects_unapproved_seed_set() -> None:
    with pytest.raises(MatrixValidationError, match="publication seed policy"):
        generate_matrix(seeds=[7, 42])

    with pytest.raises(MatrixValidationError, match="resolved seed policy"):
        generate_matrix(
            seeds=[42],
            resolved_seed_policy={"seeds": [7, 42], "resolved": True},
        )


def test_non_default_seed_set_requires_resolved_policy() -> None:
    matrix = generate_matrix(
        seeds=[7, 42],
        resolved_seed_policy={"seeds": [7, 42], "resolved": True, "source": "maintainer"},
    )

    assert matrix.seeds == (7, 42)


def test_row_validation_rejects_alternate_seeds_without_resolved_policy() -> None:
    matrix = generate_matrix(
        seeds=[7, 42],
        resolved_seed_policy={"seeds": [7, 42], "resolved": True, "source": "maintainer"},
    )

    with pytest.raises(MatrixValidationError, match="publication seed policy"):
        validate_matrix(matrix.rows)

    assert validate_matrix(
        matrix.rows,
        resolved_seed_policy=matrix.resolved_seed_policy,
    ) is None


def test_matrix_content_hash_binds_complete_rows() -> None:
    matrix = generate_matrix(seeds=[42])
    altered = replace(matrix.training_rows[0], public_method_name="forged")

    assert matrix_content_hash(matrix) != matrix_content_hash(replace(matrix, rows=(altered, *matrix.rows[1:])))


def test_validation_binds_outer_matrix_identity_to_validated_rows() -> None:
    matrix = generate_matrix(seeds=[42])
    forged_typed = replace(matrix, matrix_id="f" * 64)
    forged_mapping = matrix.to_mapping()
    forged_mapping["matrix_id"] = "f" * 64

    typed_report = validate_matrix_input(forged_typed)
    mapping_report = validate_matrix_input(forged_mapping)

    assert any("outer matrix identity" in blocker.message for blocker in typed_report)
    assert any("outer matrix identity" in blocker.message for blocker in mapping_report)


def test_matrix_identity_is_bound_to_dimensions_and_seed_policy() -> None:
    matrix = generate_matrix(seeds=[42])
    forged = tuple(replace(row, matrix_id="f" * 64) for row in matrix.rows)

    with pytest.raises(MatrixValidationError, match="matrix identity"):
        validate_matrix(forged)


def test_matrix_rejects_aliases_invalid_dimensions_and_unsupported_methods() -> None:
    with pytest.raises(MatrixValidationError, match="direction"):
        generate_matrix(seeds=[42], directions=["ADNI -> OASIS", DIRECTIONS[1]])
    with pytest.raises(MatrixValidationError, match="fold"):
        generate_matrix(seeds=[42], folds=[0, 1, 2, 3, 5])
    with pytest.raises(MatrixValidationError, match="method"):
        generate_matrix(seeds=[42], methods=[*METHODS[:-1], "historical_alias"])


def test_matrix_rejects_duplicate_training_rows_and_orphan_or_projection_training() -> None:
    matrix = generate_matrix(seeds=[42])
    with pytest.raises(MatrixValidationError, match="duplicate training"):
        validate_matrix((*matrix.rows, matrix.training_rows[0]))

    orphan = replace(matrix.projection_rows[0], parent_training_id="not-a-training-row")
    with pytest.raises(MatrixValidationError, match="parent_training_id"):
        validate_matrix((*matrix.rows[:70], orphan))

    projection_as_training = replace(
        matrix.projection_rows[0], row_kind=RowKind.TRAINING, training_invocation=True
    )
    with pytest.raises(MatrixValidationError, match="projection"):
        validate_matrix((*matrix.rows[:70], projection_as_training))
