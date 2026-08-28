"""Safe Phase 15 predictive-evaluation command-line boundary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from acda3d.evaluation.aggregation import (
    AggregationError,
    aggregate_source_oof,
    aggregate_target_ensemble,
)
from acda3d.evaluation.discovery import (
    ADAPTER_REGISTRY,
    BaselineCombinedAdapter,
    SharedMethodAdapter,
    discover_candidates,
)
from acda3d.evaluation.report import (
    build_output_plan,
    build_report_statistics,
    extract_computational_values,
    project_and_commit_output,
    verify_reuse,
)
from acda3d.evaluation.schemas import (
    ANALYSIS_CLASS_LABELS,
    PROTOCOL_VERSION,
    SCHEMA_VERSION,
    AnalysisMode,
    AuthorizationGateError,
    CheckpointPolicy,
    ConfigurationError,
    Direction,
    EvaluationRequest,
    MethodId,
    OutputCommitError,
    PredictionRole,
    ReuseVerificationError,
    RunMode,
    SelectorConflictError,
    UnsafePathError,
    canonical_sha256,
)


class ExitCode(IntEnum):
    SUCCESS = 0
    VALIDATION_INCOMPLETE = 2
    CONFIGURATION_ERROR = 3
    GATE_BLOCKED = 4
    REUSE_REJECTED = 5
    OUTPUT_FAILURE = 6
    INTERNAL_ERROR = 70


class CliSelection(NamedTuple):
    config_path: Path
    runs_root: Path | None
    output_root: Path | None
    directions: tuple[Direction, ...]
    methods: tuple[MethodId, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    run_mode: RunMode
    bootstrap_replicates: int
    bootstrap_seed: int | None
    overwrite: bool


Executor = Callable[[CliSelection], int | ExitCode]


def _library_versions() -> dict[str, str]:
    names = ("numpy", "scipy", "scikit-learn", "torch")
    return {
        "python": sys.version.split()[0],
        **{name: importlib.metadata.version(name) for name in names},
    }


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--output-root", type=Path)

    directions = parser.add_mutually_exclusive_group(required=True)
    directions.add_argument("--direction", choices=[item.value for item in Direction])
    directions.add_argument("--both-directions", action="store_true")

    methods = parser.add_mutually_exclusive_group(required=True)
    methods.add_argument("--method", action="append", choices=[item.value for item in MethodId])
    methods.add_argument("--all-methods", action="store_true")

    parser.add_argument(
        "--checkpoint-policy", choices=("best_source_f1", "last"), default="best_source_f1"
    )
    parser.add_argument("--include-sensitivity", action="store_true")
    parser.add_argument("--bootstrap-replicates", type=_positive_integer, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int)
    parser.add_argument("--overwrite", action="store_true")

    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--validate-only", action="store_true")
    modes.add_argument("--reuse", action="store_true")
    return parser


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _resolve_mode(args: argparse.Namespace) -> RunMode:
    if args.dry_run:
        return RunMode.DRY_RUN
    if args.validate_only:
        return RunMode.VALIDATE_ONLY
    if args.reuse:
        return RunMode.REUSE
    return RunMode.EVALUATE


def parse_cli(argv: Sequence[str] | None = None) -> CliSelection:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = _resolve_mode(args)

    if mode is not RunMode.REUSE and args.runs_root is None:
        parser.error("--runs-root is required in every discovery mode")
    if mode is RunMode.EVALUATE:
        if args.output_root is None:
            parser.error("--output-root is required for evaluation")
        if args.bootstrap_seed is None:
            parser.error("--bootstrap-seed is required for evaluation")
    if args.overwrite and mode is not RunMode.EVALUATE:
        parser.error("--overwrite conflicts with inspection and reuse modes")
    if args.bootstrap_seed is not None and mode not in {RunMode.EVALUATE, RunMode.REUSE}:
        parser.error("--bootstrap-seed is valid only for evaluation or reuse")
    if args.include_sensitivity and args.checkpoint_policy == "last":
        parser.error("--include-sensitivity conflicts with checkpoint policy last")
    if args.method and len(args.method) != len(set(args.method)):
        parser.error("--method values must be unique")
    if (
        args.runs_root is not None
        and args.output_root is not None
        and (
            _is_within(args.output_root, args.runs_root)
            or _is_within(args.runs_root, args.output_root)
        )
    ):
        parser.error("input and output roots must not overlap")

    selected_directions = (
        tuple(Direction) if args.both_directions else (Direction(args.direction),)
    )
    selected_methods = tuple(MethodId) if args.all_methods else tuple(MethodId(item) for item in args.method)
    primary = (
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1
        if args.checkpoint_policy == "best_source_f1"
        else CheckpointPolicy.SENSITIVITY_LAST
    )
    policies = (primary,)
    if args.include_sensitivity:
        policies += (CheckpointPolicy.SENSITIVITY_LAST,)

    return CliSelection(
        args.config,
        args.runs_root,
        args.output_root,
        selected_directions,
        selected_methods,
        policies,
        mode,
        args.bootstrap_replicates,
        args.bootstrap_seed,
        args.overwrite,
    )


def _load_configuration(selection: CliSelection) -> Mapping[str, Any]:
    try:
        config = yaml.safe_load(selection.config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ConfigurationError("evaluation configuration is unreadable") from error
    if not isinstance(config, Mapping):
        raise ConfigurationError("evaluation configuration must be a mapping")
    if config.get("schema_version") != SCHEMA_VERSION or config.get("protocol_version") != PROTOCOL_VERSION:
        raise ConfigurationError("evaluation schema or protocol version is unsupported")
    if config.get("class_order") != {label: index for index, label in enumerate(ANALYSIS_CLASS_LABELS)}:
        raise ConfigurationError("evaluation class order is unsupported")
    approved_methods = set(config.get("methods", ()))
    approved_directions = set(config.get("directions", ()))
    if any(item.value not in approved_methods for item in selection.methods):
        raise ConfigurationError("method selector is not approved by configuration")
    if any(item.value not in approved_directions for item in selection.directions):
        raise ConfigurationError("direction selector is not approved by configuration")
    return config


def _evaluation_request(selection: CliSelection, config: Mapping[str, Any]) -> EvaluationRequest:
    try:
        analysis_mode = AnalysisMode(config["analysis_mode"])
    except (KeyError, ValueError) as error:
        raise ConfigurationError("analysis mode is missing or unsupported") from error
    return EvaluationRequest(
        selection.methods,
        selection.directions,
        selection.checkpoint_policies,
        analysis_mode,
        selection.run_mode,
        selection.bootstrap_replicates,
        0 if selection.bootstrap_seed is None else selection.bootstrap_seed,
    )


def _validated_batches(
    candidates, config: Mapping[str, Any], runs_root: Path,
    validation_issues: list[str] | None = None,
    candidate_failures: dict[str, list[str]] | None = None,
):
    batches = []
    validated_pairs = []
    expected_subjects = {}
    required_roles = {PredictionRole.SOURCE_OOF, PredictionRole.TARGET_EVALUATION}
    for candidate in candidates:
        if candidate.issues:
            if validation_issues is not None:
                validation_issues.extend(issue.code.value for issue in candidate.issues)
            if candidate_failures is not None:
                key = f"{candidate.method_id.value}:{candidate.direction.value}:{candidate.checkpoint_policy.value}:{candidate.seed}:{candidate.fold}"
                candidate_failures[key] = [issue.code.value for issue in candidate.issues]
            continue
        if {population.role for population in candidate.expected_populations} != required_roles:
            if validation_issues is not None:
                validation_issues.append(
                    f"missing_expected_population:{candidate.method_id.value}:"
                    f"{candidate.direction.value}:{candidate.checkpoint_policy.value}"
                )
            if candidate_failures is not None:
                key = f"{candidate.method_id.value}:{candidate.direction.value}:{candidate.checkpoint_policy.value}:{candidate.seed}:{candidate.fold}"
                candidate_failures[key] = ["missing_expected_population"]
            continue
        for population in candidate.expected_populations:
            expected_subjects[
                (
                    candidate.method_id,
                    candidate.direction,
                    candidate.checkpoint_policy.logical_checkpoint,
                    population.role,
                )
            ] = population.subject_hashes
        family = ADAPTER_REGISTRY[candidate.method_id].schema_family
        if family == "shared_method":
            batch = SharedMethodAdapter().normalize(candidate, runs_root)
        else:
            rules = config[family].get("approved_derivation_rules")
            batch = BaselineCombinedAdapter().normalize(candidate, runs_root, rules)
        if batch.issues:
            if validation_issues is not None:
                validation_issues.extend(issue.code.value for issue in batch.issues)
            if candidate_failures is not None:
                key = f"{candidate.method_id.value}:{candidate.direction.value}:{candidate.checkpoint_policy.value}:{candidate.seed}:{candidate.fold}"
                candidate_failures[key] = [issue.code.value for issue in batch.issues]
            continue
        batches.append(batch)
        validated_pairs.append((candidate, batch))

    source_hashes: dict[str, tuple[str, ...]] = {}
    provenance_records = []
    input_hashes = set()
    grouped = defaultdict(list)
    for batch in batches:
        hashes = tuple(sorted(item.sha256 for item in batch.input_files))
        input_hashes.update(hashes)
        provenance_records.extend(batch.provenance_records)
        for record in batch.provenance_records:
            source_hashes[canonical_sha256(record)] = hashes
        for row in batch.predictions:
            grouped[(row.method_id, row.direction, row.logical_checkpoint, row.role)].append(row)

    expected_folds = tuple(config.get("expected_folds", ()))
    expected_seeds = tuple(config.get("expected_seeds", ()))
    target_tables = defaultdict(list)
    try:
        for (method, direction, checkpoint, role), rows in grouped.items():
            subjects = expected_subjects[(method, direction, checkpoint, role)]
            if role is PredictionRole.SOURCE_OOF:
                aggregate_source_oof(
                    rows, expected_subjects=subjects, expected_seeds=expected_seeds,
                    source_hashes_by_provenance=source_hashes,
                )
            else:
                result = aggregate_target_ensemble(
                    rows, expected_subjects=subjects, expected_folds=expected_folds,
                    expected_seeds=expected_seeds, source_hashes_by_provenance=source_hashes,
                )
                target_tables[(direction, checkpoint)].append((method, result.final_predictions))
    except AggregationError:
        if validation_issues is not None:
            validation_issues.append("aggregation_contract_incomplete")
        if candidate_failures is not None:
            for candidate in candidates:
                key = f"{candidate.method_id.value}:{candidate.direction.value}:{candidate.checkpoint_policy.value}:{candidate.seed}:{candidate.fold}"
                if key not in candidate_failures:
                    candidate_failures[key] = ["aggregation_contract_incomplete"]
        return None

    for tables in target_tables.values():
        reference = tuple((row.subject_hash, row.true_label) for row in tables[0][1])
        if any(tuple((row.subject_hash, row.true_label) for row in table) != reference for _, table in tables[1:]):
            return None
    if not grouped:
        return None
    normalized_tables = {}
    for (direction, checkpoint), tables in target_tables.items():
        policy = next(
            item for item in CheckpointPolicy if item.logical_checkpoint == checkpoint
        )
        normalized_tables[(direction, policy)] = dict(tables)
    return (
        normalized_tables, tuple(provenance_records), tuple(sorted(input_hashes)),
        tuple(validated_pairs),
    )


def _report_rows(candidates, validated_pairs, config, evaluation_identity):
    grouped = defaultdict(list)
    batch_by_key = {
        (candidate.method_id, candidate.direction, candidate.seed, candidate.fold,
         candidate.checkpoint_policy): batch
        for candidate, batch in validated_pairs
    }
    for candidate in candidates:
        key = (
            candidate.method_id, candidate.direction, candidate.seed, candidate.fold,
            candidate.checkpoint_policy,
        )
        grouped[
            (candidate.method_id, candidate.direction, candidate.checkpoint_policy)
        ].append((candidate, batch_by_key.get(key)))
    status_rows, inclusion_by_scope, computational_rows = [], defaultdict(list), []
    expected_folds = tuple(config.get("expected_folds", ()))
    expected_seeds = tuple(config.get("expected_seeds", ()))
    for (method, direction, policy), items in grouped.items():
        public_name = ADAPTER_REGISTRY[method].public_name
        valid_items = tuple((candidate, batch) for candidate, batch in items if batch is not None)
        completed_folds = sorted({candidate.fold for candidate, _ in valid_items})
        completed_seeds = sorted({candidate.seed for candidate, _ in valid_items})
        group_status = "included" if len(valid_items) == len(items) else (
            "excluded" if not valid_items else "incomplete"
        )
        status_rows.append({
            "schema_version": SCHEMA_VERSION,
            "evaluation_identity": evaluation_identity,
            "method_id": method.value, "public_model_name": public_name,
            "direction": direction.value, "checkpoint_policy": policy.value,
            "expected_folds": ";".join(map(str, expected_folds)),
            "completed_folds": ";".join(map(str, completed_folds)),
            "expected_seeds": ";".join(map(str, expected_seeds)),
            "completed_seeds": ";".join(map(str, completed_seeds)),
            "status": group_status,
            "reason_code": None if group_status == "included" else "validation_incomplete",
            "reason_detail": None,
        })
        for candidate, batch in items:
            valid = batch is not None
            hashes = (
                ";".join(sorted(item.sha256 for item in batch.input_files))
                if valid else ""
            )
            reason = None if valid else (
                candidate.issues[0].code.value if candidate.issues
                else "validation_incomplete"
            )
            for population in candidate.expected_populations:
                inclusion_by_scope[(direction, policy)].append({
                    "schema_version": SCHEMA_VERSION,
                    "evaluation_identity": evaluation_identity,
                    "method_id": method.value, "public_model_name": public_name,
                    "direction": direction.value, "checkpoint_policy": policy.value,
                    "seed": candidate.seed, "fold": candidate.fold,
                    "prediction_role": population.role.value,
                    "expected": True, "present": valid,
                    "provenance_valid": valid, "identity_valid": valid,
                    "probability_valid": valid, "complete": valid,
                    "status": "included" if valid else "excluded", "reason_code": reason,
                    "reason_detail": None, "input_sha256s": hashes,
                })
        source_hash = next(
            (item.sha256 for _, batch in valid_items for item in batch.input_files), None
        )
        for value in extract_computational_values(()) :
            computational_rows.append({
                "schema_version": SCHEMA_VERSION,
                "evaluation_identity": evaluation_identity,
                "method_id": method.value, "direction": direction.value,
                "checkpoint_policy": policy.value, "field": value.field,
                "value": value.value, "unit": value.unit,
                "status": value.status.value, "reason": value.reason,
                "source_file_sha256": source_hash,
            })
    return tuple(status_rows), dict(inclusion_by_scope), tuple(computational_rows)


def _unresolved_real_gates(gate: object) -> tuple[str, ...]:
    names = ("authorized_exports", "D-14-001", "D-14-002", "protocol_approval")
    if not isinstance(gate, Mapping):
        return names
    unresolved = []
    for name in names:
        state = gate.get(name)
        if (
            not isinstance(state, Mapping)
            or state.get("resolved") is not True
            or not isinstance(state.get("sha256"), str)
            or len(state["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in state["sha256"])
        ):
            unresolved.append(name)
    if not unresolved and gate.get("authorized") is not True:
        unresolved.extend(names)
    return tuple(unresolved)


def _execute(selection: CliSelection) -> ExitCode:
    config = _load_configuration(selection)
    configured_reuse = config.get("completed_reuse", {})
    root_values = (
        configured_reuse.get("approved_output_roots", ())
        if isinstance(configured_reuse, Mapping) else ()
    )
    approved_reuse_roots = {
        (Path(value) if Path(value).is_absolute() else selection.config_path.parent / value).resolve()
        for value in root_values if isinstance(value, str) and value
    }
    reuse_output = selection.output_root
    if selection.run_mode is RunMode.REUSE and reuse_output is None:
        if len(approved_reuse_roots) != 1:
            raise ReuseVerificationError("reuse output root is absent or ambiguous")
        reuse_output = next(iter(approved_reuse_roots))
    if selection.run_mode is RunMode.REUSE and (
        reuse_output is None or not reuse_output.is_dir()
    ):
        raise ReuseVerificationError("completed reuse output is unavailable")
    if selection.runs_root is None or not selection.runs_root.is_dir():
        raise ConfigurationError("runs root is unavailable")

    request = _evaluation_request(selection, config)
    gate = config.get("real_evaluation_gate", {})
    if request.run_mode is RunMode.EVALUATE and request.analysis_mode is AnalysisMode.REAL:
        unresolved = _unresolved_real_gates(gate)
        if unresolved:
            raise AuthorizationGateError(
                "unresolved real evaluation gates: " + ", ".join(unresolved)
            )
    folds = tuple(config.get("expected_folds", ()))
    seeds = tuple(config.get("expected_seeds", ()))
    candidates = discover_candidates(config, selection.runs_root, request, folds, seeds)
    candidate_issues = tuple(
        issue.code.value for candidate in candidates for issue in candidate.issues
    )
    if candidate_issues:
        print("validation issues: " + ", ".join(sorted(candidate_issues)), file=sys.stderr)
    if selection.run_mode is RunMode.DRY_RUN:
        return (
            ExitCode.VALIDATION_INCOMPLETE if candidate_issues else ExitCode.SUCCESS
        )

    validation_issues: list[str] = []
    candidate_failures: dict[str, list[str]] = {}
    validated = _validated_batches(
        candidates, config, selection.runs_root, validation_issues, candidate_failures
    )
    if validated is None:
        print("validation issues: " + ", ".join(validation_issues), file=sys.stderr)
        return ExitCode.VALIDATION_INCOMPLETE
    canonical_tables, provenance_records, input_hashes, validated_pairs = validated
    library_versions = _library_versions()
    bootstrap_policy = {
        "replicates": request.bootstrap_replicates,
        "seed": request.bootstrap_seed,
        "ci_policy": "percentile_95_linear",
    }
    gate_states = dict.fromkeys(
        ("authorized_exports", "D-14-001", "D-14-002", "protocol_approval"), False
    )
    identity_inputs = {
        "configuration_sha256": hashlib.sha256(
            selection.config_path.read_bytes()
        ).hexdigest(),
        "authorization_sha256": canonical_sha256(gate),
        "ordered_input_sha256s": list(input_hashes),
    }
    evaluation_identity = canonical_sha256({
        "analysis_mode": request.analysis_mode.value,
        "methods": [item.value for item in request.methods],
        "directions": [item.value for item in request.directions],
        "checkpoint_policies": [item.value for item in request.checkpoint_policies],
        "bootstrap": bootstrap_policy, "gate_states": gate_states,
        "library_versions": library_versions, **identity_inputs,
    })
    expected_scopes = tuple(
        (direction, policy) for direction in request.directions
        for policy in request.checkpoint_policies
    )
    included_methods = tuple(
        method for method in request.methods
        if all(method in canonical_tables.get(scope, {}) for scope in expected_scopes)
    )
    if not included_methods:
        return ExitCode.VALIDATION_INCOMPLETE
    canonical_tables = {
        scope: {
            method: rows for method, rows in canonical_tables.get(scope, {}).items()
            if method in included_methods
        }
        for scope in expected_scopes
    }
    plan = build_output_plan(
        evaluation_identity, request.analysis_mode, request.methods,
        request.directions, request.checkpoint_policies,
        included_methods=included_methods, include_artifact_index=True,
    )
    if selection.run_mode is RunMode.REUSE:
        assert reuse_output is not None
        if reuse_output.resolve() not in approved_reuse_roots:
            raise ReuseVerificationError("completed reuse root is not approved")
        verify_reuse(
            reuse_output, plan,
            expected_identity_inputs=identity_inputs,
            expected_library_versions=library_versions,
            expected_bootstrap=bootstrap_policy,
            expected_gate_states=gate_states,
            expected_disposition="completed",
        )
        return ExitCode.SUCCESS
    if selection.run_mode is RunMode.VALIDATE_ONLY:
        return (
            ExitCode.VALIDATION_INCOMPLETE if validation_issues else ExitCode.SUCCESS
        )
    if request.analysis_mode is not AnalysisMode.SYNTHETIC_TEST_ONLY:
        raise ConfigurationError("real evaluation execution remains closed")
    if selection.output_root is None:
        raise ConfigurationError("output root is required")
    method_status_rows, inclusion_rows, computational_rows = _report_rows(
        candidates, validated_pairs, config, evaluation_identity
    )
    statistics = {
        scope: build_report_statistics(
            {method.value: rows for method, rows in tables.items()},
            bootstrap_replicates=request.bootstrap_replicates,
            bootstrap_seed=request.bootstrap_seed,
        )
        for scope, tables in canonical_tables.items()
    }
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    failure_records = tuple(
        {
            "method_id": key.split(":")[0],
            "direction": key.split(":")[1],
            "checkpoint_policy": key.split(":")[2],
            "status": "excluded",
            "issues": failures,
        }
        for key, failures in candidate_failures.items()
    )
    project_and_commit_output(
        selection.output_root, plan, canonical_tables, statistics,
        root_metadata={
            "resolved_config": config,
            "provenance_records": (
                *provenance_records,
                *failure_records,
            ),
            "method_status_rows": method_status_rows,
            "computational_rows": computational_rows, "log_events": (),
        },
        policy_metadata={
            scope: {"inclusion_rows": inclusion_rows[scope]}
            for scope in canonical_tables
        },
        identity_inputs=identity_inputs,
        library_versions=library_versions,
        bootstrap_replicates=request.bootstrap_replicates,
        bootstrap_seed=request.bootstrap_seed,
        ci_policy="percentile_95_linear",
        gate_states=gate_states,
        created_utc=started,
        completed_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        disposition="completed_overwrite" if selection.overwrite else "completed",
        overwrite=selection.overwrite,
    )
    return ExitCode.SUCCESS


def main(argv: Sequence[str] | None = None, *, executor: Executor = _execute) -> int:
    try:
        selection = parse_cli(argv)
        return int(executor(selection))
    except SystemExit as error:
        return int(ExitCode.SUCCESS if error.code == 0 else ExitCode.CONFIGURATION_ERROR)
    except (ConfigurationError, SelectorConflictError, UnsafePathError):
        return int(ExitCode.CONFIGURATION_ERROR)
    except AuthorizationGateError as error:
        print(str(error), file=sys.stderr)
        return int(ExitCode.GATE_BLOCKED)
    except ReuseVerificationError:
        return int(ExitCode.REUSE_REJECTED)
    except OutputCommitError:
        return int(ExitCode.OUTPUT_FAILURE)
    except Exception:
        return int(ExitCode.INTERNAL_ERROR)


if __name__ == "__main__":
    sys.exit(main())
