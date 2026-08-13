"""Deterministic, planning-only Phase 18 experiment matrix contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .canonical_json import identity_sha256, is_sha256

METHODS = (
    "source_only",
    "coral",
    "mmd",
    "cdan",
    "prototype_pseudo",
    "aagn",
    "faster_snn",
)
DIRECTIONS = ("adni_to_oasis", "oasis_to_adni")
FOLDS = (0, 1, 2, 3, 4)
PUBLIC_METHOD_NAMES = {
    "source_only": "PADA-3DACB Source-Only",
    "coral": "PADA-3DACB + CORAL",
    "mmd": "PADA-3DACB + MMD",
    "cdan": "PADA-3DACB + CDAN",
    "prototype_pseudo": "PADA-3DACB",
    "aagn": "AAGN / ROI-aware gating",
    "faster_snn": "FasterSNN",
}
_COHORTS = {
    "adni_to_oasis": ("ADNI", "OASIS"),
    "oasis_to_adni": ("OASIS", "ADNI"),
}
_INITIAL_STATES = {
    "PLANNED",
    "BLOCKED_CONFIGURATION",
    "BLOCKED_DATA",
    "BLOCKED_RESOURCES",
}


class MatrixValidationError(ValueError):
    """Raised when a matrix would omit, duplicate, or mutate a planned cell."""


class RowKind(str, Enum):
    TRAINING = "training"
    CHECKPOINT_PROJECTION = "checkpoint_projection"


class RowState(str, Enum):
    PLANNED = "PLANNED"
    BLOCKED_CONFIGURATION = "BLOCKED_CONFIGURATION"
    BLOCKED_DATA = "BLOCKED_DATA"
    BLOCKED_RESOURCES = "BLOCKED_RESOURCES"


# Compatibility names make the row contract explicit without coupling it to a runner.
MatrixRowKind = RowKind
MatrixStatus = RowState


@dataclass(frozen=True)
class ExperimentRow:
    row_id: str
    matrix_id: str
    row_kind: RowKind
    parent_training_id: str | None
    training_invocation: bool
    method_id: str
    public_method_name: str
    source_cohort: str
    target_cohort: str
    direction: str
    fold: int
    seed: int
    checkpoint_policy: str
    split_assignment_hash: str
    target_adaptation_assignment_hash: str
    target_evaluation_assignment_hash: str
    resolved_config_hash: str
    artifact_identity_hash: str
    state: RowState
    completion_allowed: bool
    blocked_reasons: tuple[str, ...]

    @property
    def training_id(self) -> str:
        """Return the stable ID used by a linked checkpoint projection."""

        return self.row_id

    def to_mapping(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "matrix_id": self.matrix_id,
            "row_kind": self.row_kind.value,
            "parent_training_id": self.parent_training_id,
            "training_invocation": self.training_invocation,
            "method_id": self.method_id,
            "public_method_name": self.public_method_name,
            "source_cohort": self.source_cohort,
            "target_cohort": self.target_cohort,
            "direction": self.direction,
            "fold": self.fold,
            "seed": self.seed,
            "checkpoint_policy": self.checkpoint_policy,
            "split_assignment_hash": self.split_assignment_hash,
            "target_adaptation_assignment_hash": self.target_adaptation_assignment_hash,
            "target_evaluation_assignment_hash": self.target_evaluation_assignment_hash,
            "resolved_config_hash": self.resolved_config_hash,
            "artifact_identity_hash": self.artifact_identity_hash,
            "state": self.state.value,
            "completion_allowed": self.completion_allowed,
            "blocked_reasons": list(self.blocked_reasons),
        }


@dataclass(frozen=True)
class ExperimentMatrix:
    matrix_id: str
    rows: tuple[ExperimentRow, ...]
    seeds: tuple[int, ...]
    resolved_seed_policy: Mapping[str, Any] | None = None

    @property
    def training_rows(self) -> tuple[ExperimentRow, ...]:
        return tuple(row for row in self.rows if row.row_kind is RowKind.TRAINING)

    @property
    def projection_rows(self) -> tuple[ExperimentRow, ...]:
        return tuple(
            row for row in self.rows if row.row_kind is RowKind.CHECKPOINT_PROJECTION
        )

    @property
    def counts(self) -> dict[str, int]:
        training = len(self.training_rows)
        projections = len(self.projection_rows)
        return {
            "training": training,
            "checkpoint_projection": projections,
            "total": training + projections,
        }

    def to_rows(self) -> tuple[dict[str, Any], ...]:
        return tuple(row.to_mapping() for row in self.rows)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "phase18.matrix.v1",
            "matrix_id": self.matrix_id,
            "methods": list(METHODS),
            "directions": list(DIRECTIONS),
            "folds": list(FOLDS),
            "seeds": list(self.seeds),
            "resolved_seed_policy": None if self.resolved_seed_policy is None else dict(self.resolved_seed_policy),
            "checkpoint_policies": ["best_source_f1", "last"],
            "rows": [row.to_mapping() for row in self.rows],
            "matrix_content_hash": matrix_content_hash(self),
        }


def generate_matrix(
    *,
    seeds: Sequence[int],
    resolved_seed_policy: Mapping[str, Any] | None = None,
    methods: Sequence[str] = METHODS,
    directions: Sequence[str] = DIRECTIONS,
    folds: Sequence[int] = FOLDS,
    state: RowState | str = RowState.BLOCKED_CONFIGURATION,
) -> ExperimentMatrix:
    """Materialize the complete matrix from an explicit seed input.

    This function only creates planning records. It never loads data, starts a
    training invocation, or infers a seed/configuration from repository state.
    """

    canonical_methods = _validate_dimension(methods, METHODS, "method")
    canonical_directions = _validate_dimension(directions, DIRECTIONS, "direction")
    canonical_folds = _validate_dimension(folds, FOLDS, "fold")
    ordered_seeds = _validate_seeds(seeds, resolved_seed_policy=resolved_seed_policy)
    row_state = _validate_state(state)

    definition = {
        "schema_version": "phase18.matrix.v1",
        "methods": list(canonical_methods),
        "directions": list(canonical_directions),
        "folds": list(canonical_folds),
        "seeds": list(ordered_seeds),
        "checkpoint_policies": ["best_source_f1", "last"],
        "resolved_seed_policy": None if resolved_seed_policy is None else dict(resolved_seed_policy),
    }
    matrix_id = identity_sha256(definition)
    rows: list[ExperimentRow] = []
    for method_id in canonical_methods:
        for direction in canonical_directions:
            source_cohort, target_cohort = _COHORTS[direction]
            for seed in ordered_seeds:
                for fold in canonical_folds:
                    training_identity = _row_identity(
                        matrix_id=matrix_id,
                        row_kind=RowKind.TRAINING,
                        method_id=method_id,
                        public_method_name=PUBLIC_METHOD_NAMES[method_id],
                        source_cohort=source_cohort,
                        target_cohort=target_cohort,
                        direction=direction,
                        fold=fold,
                        seed=seed,
                        checkpoint_policy="best_source_f1",
                        parent_training_id=None,
                    )
                    training_id = identity_sha256(training_identity)
                    common = {
                        "matrix_id": matrix_id,
                        "method_id": method_id,
                        "public_method_name": PUBLIC_METHOD_NAMES[method_id],
                        "source_cohort": source_cohort,
                        "target_cohort": target_cohort,
                        "direction": direction,
                        "fold": fold,
                        "seed": seed,
                        "split_assignment_hash": "unresolved",
                        "target_adaptation_assignment_hash": "unresolved",
                        "target_evaluation_assignment_hash": "unresolved",
                        "resolved_config_hash": "unresolved",
                        "artifact_identity_hash": "unresolved",
                        "state": row_state,
                        "completion_allowed": False,
                        "blocked_reasons": _blocked_reasons(row_state),
                    }
                    rows.append(
                        ExperimentRow(
                            row_id=training_id,
                            row_kind=RowKind.TRAINING,
                            parent_training_id=None,
                            training_invocation=True,
                            checkpoint_policy="best_source_f1",
                            **common,
                        )
                    )
                    projection_identity = _row_identity(
                        matrix_id=matrix_id,
                        row_kind=RowKind.CHECKPOINT_PROJECTION,
                        method_id=method_id,
                        public_method_name=PUBLIC_METHOD_NAMES[method_id],
                        source_cohort=source_cohort,
                        target_cohort=target_cohort,
                        direction=direction,
                        fold=fold,
                        seed=seed,
                        checkpoint_policy="last",
                        parent_training_id=training_id,
                    )
                    rows.append(
                        ExperimentRow(
                            row_id=identity_sha256(projection_identity),
                            row_kind=RowKind.CHECKPOINT_PROJECTION,
                            parent_training_id=training_id,
                            training_invocation=False,
                            checkpoint_policy="last",
                            **common,
                        )
                    )

    validate_matrix(rows, resolved_seed_policy=resolved_seed_policy)
    return ExperimentMatrix(
            matrix_id=matrix_id,
            rows=tuple(rows),
            seeds=ordered_seeds,
            resolved_seed_policy=None if resolved_seed_policy is None else dict(resolved_seed_policy),
        )


def validate_matrix(
    rows: Sequence[ExperimentRow],
    *,
    resolved_seed_policy: Mapping[str, Any] | None = None,
) -> None:
    """Fail closed on identity, seed, duplicate, and row-role violations."""

    if not rows:
        raise MatrixValidationError("matrix is empty")
    seed_values = [row.seed for row in rows if isinstance(row, ExperimentRow)]
    if any(type(seed) is not int for seed in seed_values):
        raise MatrixValidationError("seed must be an explicit integer")
    seeds = tuple(sorted(set(seed_values)))
    _validate_seeds(seeds, resolved_seed_policy=resolved_seed_policy)
    expected_matrix_id = identity_sha256(
        {
            "schema_version": "phase18.matrix.v1",
            "methods": list(METHODS),
            "directions": list(DIRECTIONS),
            "folds": list(FOLDS),
            "seeds": list(seeds),
            "checkpoint_policies": ["best_source_f1", "last"],
            "resolved_seed_policy": None
            if resolved_seed_policy is None
            else dict(resolved_seed_policy),
        }
    )
    if any(isinstance(row, ExperimentRow) and row.matrix_id != expected_matrix_id for row in rows):
        raise MatrixValidationError("matrix identity does not match its dimensions and seed policy")
    row_ids: set[str] = set()
    training_by_cell: dict[tuple[str, str, int, int], ExperimentRow] = {}
    training_ids: set[str] = {
        row.row_id
        for row in rows
        if isinstance(row, ExperimentRow) and row.row_kind is RowKind.TRAINING
    }
    projection_by_parent: dict[str, ExperimentRow] = {}
    for row in rows:
        if not isinstance(row, ExperimentRow):
            raise MatrixValidationError("matrix rows must be ExperimentRow values")
        if row.row_kind is RowKind.CHECKPOINT_PROJECTION and row.parent_training_id not in training_ids:
            raise MatrixValidationError("invalid parent_training_id")
        _validate_row(row)
        if row.row_id in row_ids:
            if row.row_kind is RowKind.TRAINING:
                raise MatrixValidationError("duplicate training row")
            raise MatrixValidationError("duplicate row identity")
        row_ids.add(row.row_id)
        cell = (row.method_id, row.direction, row.fold, row.seed)
        if row.row_kind is RowKind.TRAINING:
            if cell in training_by_cell:
                raise MatrixValidationError("duplicate training row")
            training_by_cell[cell] = row
            training_ids.add(row.row_id)
        else:
            if row.training_invocation:
                raise MatrixValidationError("checkpoint projection cannot be a training row")
            if row.parent_training_id in projection_by_parent:
                raise MatrixValidationError("duplicate checkpoint projection")
            projection_by_parent[row.parent_training_id] = row
    if set(projection_by_parent) != training_ids:
        raise MatrixValidationError("each training row requires exactly one checkpoint projection")
    matrix_ids = {row.matrix_id for row in rows}
    if len(matrix_ids) != 1:
        raise MatrixValidationError("matrix rows must share one matrix identity")
    seeds = {row.seed for row in training_by_cell.values()}
    expected_cells = {
        (method_id, direction, fold, seed)
        for method_id in METHODS
        for direction in DIRECTIONS
        for fold in FOLDS
        for seed in seeds
    }
    if set(training_by_cell) != expected_cells:
        raise MatrixValidationError("incomplete matrix")
    for parent_id, projection in projection_by_parent.items():
        training = next(row for row in rows if row.row_id == parent_id)
        if (
            projection.method_id,
            projection.direction,
            projection.fold,
            projection.seed,
        ) != (
            training.method_id,
            training.direction,
            training.fold,
            training.seed,
        ):
            raise MatrixValidationError("checkpoint projection does not match parent training row")


def _validate_row(row: ExperimentRow) -> None:
    if row.row_kind is RowKind.TRAINING:
        if row.parent_training_id is not None or row.training_invocation is not True:
            raise MatrixValidationError("projection cannot be represented as a training row")
        if row.checkpoint_policy != "best_source_f1":
            raise MatrixValidationError("training row requires best_source_f1")
    elif row.row_kind is RowKind.CHECKPOINT_PROJECTION:
        if not row.parent_training_id or row.training_invocation is not False:
            raise MatrixValidationError("checkpoint projection has invalid parent or invocation")
        if row.checkpoint_policy != "last":
            raise MatrixValidationError("checkpoint projection requires last")
    else:
        raise MatrixValidationError("unsupported row kind")
    if not is_sha256(row.matrix_id):
        raise MatrixValidationError("matrix identity must be a lowercase SHA-256 digest")
    if type(row.training_invocation) is not bool or type(row.completion_allowed) is not bool:
        raise MatrixValidationError("matrix invocation and completion flags must be bool")
    if row.method_id not in METHODS:
        raise MatrixValidationError("unsupported method")
    if row.public_method_name != PUBLIC_METHOD_NAMES[row.method_id]:
        raise MatrixValidationError("public method identity does not match method")
    if row.direction not in DIRECTIONS:
        raise MatrixValidationError("direction must be canonical lowercase")
    if (row.source_cohort, row.target_cohort) != _COHORTS[row.direction]:
        raise MatrixValidationError("direction-to-cohort mapping is inconsistent")
    if row.fold not in FOLDS:
        raise MatrixValidationError("fold must be one of 0..4")
    if type(row.seed) is not int:
        raise MatrixValidationError("seed must be an explicit integer")
    if row.state.value not in _INITIAL_STATES:
        raise MatrixValidationError("row state is not planning-only")
    if row.completion_allowed is not False:
        raise MatrixValidationError("completion is forbidden in Phase 18")
    expected_row_id = identity_sha256(
        _row_identity(
            matrix_id=row.matrix_id,
            row_kind=row.row_kind,
            method_id=row.method_id,
            public_method_name=row.public_method_name,
            source_cohort=row.source_cohort,
            target_cohort=row.target_cohort,
            direction=row.direction,
            fold=row.fold,
            seed=row.seed,
            checkpoint_policy=row.checkpoint_policy,
            parent_training_id=row.parent_training_id,
        )
    )
    if row.row_id != expected_row_id:
        raise MatrixValidationError("row identity does not match its ordered fields")


def _row_identity(
    *,
    matrix_id: str,
    row_kind: RowKind,
    method_id: str,
    public_method_name: str,
    source_cohort: str,
    target_cohort: str,
    direction: str,
    fold: int,
    seed: int,
    checkpoint_policy: str,
    parent_training_id: str | None,
) -> dict[str, Any]:
    return {
        "matrix_id": matrix_id,
        "row_kind": row_kind.value,
        "method_id": method_id,
        "public_method_name": public_method_name,
        "source_cohort": source_cohort,
        "target_cohort": target_cohort,
        "direction": direction,
        "fold": fold,
        "seed": seed,
        "checkpoint_policy": checkpoint_policy,
        "parent_training_id": parent_training_id,
    }


def _validate_dimension(
    values: Sequence[Any], canonical: tuple[Any, ...], label: str
) -> tuple[Any, ...]:
    values_tuple = tuple(values)
    if len(values_tuple) != len(set(values_tuple)):
        raise MatrixValidationError(f"duplicate {label} dimension")
    if set(values_tuple) != set(canonical):
        raise MatrixValidationError(f"unsupported or incomplete {label} dimension")
    return canonical


def _validate_seeds(
    seeds: Sequence[int], *, resolved_seed_policy: Mapping[str, Any] | None
) -> tuple[int, ...]:
    values = tuple(seeds)
    if not values:
        raise MatrixValidationError("seed input must be explicit and non-empty")
    if any(type(seed) is not int for seed in values):
        raise MatrixValidationError("seeds must be explicit integers")
    if len(values) != len(set(values)):
        raise MatrixValidationError("duplicate seed input")
    ordered = tuple(sorted(values))
    if ordered == (42,):
        if resolved_seed_policy is not None and (
            not isinstance(resolved_seed_policy, Mapping)
            or resolved_seed_policy.get("resolved") is not True
            or resolved_seed_policy.get("seeds") != list(ordered)
        ):
            raise MatrixValidationError("resolved seed policy does not match matrix seeds")
        return ordered
    if not isinstance(resolved_seed_policy, Mapping) or resolved_seed_policy.get("resolved") is not True:
        raise MatrixValidationError("publication seed policy must be [42] unless an explicit resolved seed policy is supplied")
    if resolved_seed_policy.get("seeds") != list(ordered):
        raise MatrixValidationError("resolved seed policy does not match matrix seeds")
    return ordered


def matrix_content_hash(matrix: ExperimentMatrix | Mapping[str, Any]) -> str:
    """Hash the complete canonical row set, not the human-facing matrix ID."""

    if isinstance(matrix, ExperimentMatrix):
        rows = [row.to_mapping() for row in matrix.rows]
    else:
        rows = dict(matrix).get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise MatrixValidationError("complete matrix rows are required")
    return identity_sha256({"schema_version": "phase18.matrix.v1", "rows": list(rows)})


def _validate_state(state: RowState | str) -> RowState:
    try:
        resolved = state if isinstance(state, RowState) else RowState(state)
    except ValueError as exc:
        raise MatrixValidationError("row state is not planning-only") from exc
    if resolved.value not in _INITIAL_STATES:
        raise MatrixValidationError("row state is not planning-only")
    return resolved


def _blocked_reasons(state: RowState) -> tuple[str, ...]:
    return {
        RowState.PLANNED: ("authorization_blocked", "unresolved_scientific_value"),
        RowState.BLOCKED_CONFIGURATION: ("authorization_blocked", "unresolved_scientific_value"),
        RowState.BLOCKED_DATA: ("missing_assignment",),
        RowState.BLOCKED_RESOURCES: ("resource_budget_unresolved",),
    }[state]
