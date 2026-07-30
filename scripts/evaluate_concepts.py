"""Phase 16 concept evaluation command-line interface."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from collections.abc import Callable, Mapping, Sequence
from enum import IntEnum
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import yaml

from pada3dacb.evaluation.concepts.agreement import compute_all_agreement
from pada3dacb.evaluation.concepts.anatomy import compute_global_anatomy
from pada3dacb.evaluation.concepts.discovery import DiscoveryConfig, discover_candidates
from pada3dacb.evaluation.concepts.fidelity import compute_global_fidelity
from pada3dacb.evaluation.concepts.report import (
    build_synthetic_fixture_bundle,
    commit_output,
    verify_completed_output,
)
from pada3dacb.evaluation.concepts.stability import compute_all_stability
from pada3dacb.evaluation.concepts.statistics import (
    bootstrap_metric,
    paired_bootstrap_diff,
)
from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    AuthorizationGateError,
    CheckpointPolicy,
    ConfigurationError,
    Direction,
    EvaluationRequest,
    MethodId,
    OutputCommitError,
    ReuseVerificationError,
    RunMode,
    SelectorConflictError,
    UnsafePathError,
    canonical_sha256,
)

PADA_CONCEPT_METHODS = (
    MethodId.SOURCE_ONLY,
    MethodId.CORAL,
    MethodId.MMD,
    MethodId.CDAN,
    MethodId.PROTOTYPE_PSEUDO,
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
    artifact_root: Path | None
    output_root: Path | None
    directions: tuple[Direction, ...]
    methods: tuple[MethodId, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    run_mode: RunMode
    bootstrap_replicates: int
    bootstrap_seed: int | None
    top_k: tuple[int, ...]
    device: str
    overwrite: bool


Executable = Callable[[CliSelection], int | ExitCode]


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--output-root", type=Path)

    directions = parser.add_mutually_exclusive_group(required=True)
    directions.add_argument("--direction", choices=[item.value for item in Direction])
    directions.add_argument("--both-directions", action="store_true")

    methods = parser.add_mutually_exclusive_group(required=True)
    methods.add_argument("--method", action="append", choices=[item.value for item in MethodId])
    methods.add_argument("--all-pada-methods", action="store_true")

    parser.add_argument(
        "--checkpoint-policy",
        choices=("best_source_f1", "last"),
        default="best_source_f1",
    )
    parser.add_argument("--include-sensitivity", action="store_true")
    parser.add_argument("--bootstrap-replicates", type=_positive_integer, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int)
    parser.add_argument("--top-k", action="append", type=_positive_integer)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
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
    if mode is not RunMode.REUSE and args.artifact_root is None:
        parser.error("--artifact-root is required in every discovery mode")
    if mode is RunMode.EVALUATE:
        if args.output_root is None:
            parser.error("--output-root is required for evaluation")
        if args.bootstrap_seed is None:
            parser.error("--bootstrap-seed is required for evaluation")
    if args.overwrite and mode is not RunMode.EVALUATE:
        parser.error("--overwrite conflicts with inspection and reuse modes")
    if args.bootstrap_seed is not None and mode not in {RunMode.EVALUATE, RunMode.REUSE}:
        parser.error("--bootstrap-seed is valid only for evaluation or reuse")

    if args.runs_root is not None and args.output_root is not None and (_is_within(args.output_root, args.runs_root) or _is_within(args.runs_root, args.output_root)):
        parser.error("input and output roots must not overlap")

    if args.method is not None and len(args.method) != len(set(args.method)):
        parser.error("duplicate --method selectors are not allowed")
    top_k = tuple(args.top_k or ())
    if len(top_k) != len(set(top_k)):
        parser.error("duplicate --top-k values are not allowed")
    if args.include_sensitivity and args.checkpoint_policy == "last":
        parser.error("--include-sensitivity conflicts with --checkpoint-policy last")

    selected_directions = tuple(Direction) if args.both_directions else (Direction(args.direction),)
    selected_methods = (
        PADA_CONCEPT_METHODS
        if args.all_pada_methods
        else tuple(MethodId(item) for item in args.method)
    )
    primary = CheckpointPolicy.PRIMARY_BEST_SOURCE_F1 if args.checkpoint_policy == "best_source_f1" else CheckpointPolicy.SENSITIVITY_LAST
    policies = (primary,)
    if args.include_sensitivity:
        policies += (CheckpointPolicy.SENSITIVITY_LAST,)

    return CliSelection(
        config_path=args.config,
        runs_root=args.runs_root,
        artifact_root=args.artifact_root,
        output_root=args.output_root,
        directions=selected_directions,
        methods=selected_methods,
        checkpoint_policies=policies,
        run_mode=mode,
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
        top_k=top_k,
        device=args.device,
        overwrite=args.overwrite,
    )


def _load_configuration(selection: CliSelection) -> Mapping[str, Any]:
    try:
        config = yaml.safe_load(selection.config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ConfigurationError("evaluation configuration is unreadable") from error
    if not isinstance(config, Mapping):
        raise ConfigurationError("evaluation configuration must be a mapping")
    if config.get("schema_version") != "1.0" or config.get("protocol_version") != "1.0":
        raise ConfigurationError("evaluation schema or protocol version is unsupported")
    if config.get("class_order") != {"CN": 0, "MCI": 1, "AD": 2}:
        raise ConfigurationError("evaluation class order is unsupported")

    approved_methods = set(config.get("methods", ()))
    if any(item.value not in approved_methods for item in selection.methods):
        raise ConfigurationError("method selector is not approved by configuration")

    approved_directions = set(config.get("directions", ()))
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


def _library_versions() -> dict[str, str]:
    names = ("numpy", "scipy", "scikit-learn", "torch")
    return {
        "python": sys.version.split()[0],
        **{name: importlib.metadata.version(name) for name in names},
    }


def _synthetic_fixture_metrics() -> dict[str, Any]:
    """Evaluate one fixed, deterministic, fixture-only subject matrix."""
    predicted = np.array(
        [
            [0.1, 0.3, 0.5], [0.2, 0.4, 0.6],
            [0.3, 0.5, 0.7], [0.4, 0.6, 0.8],
            [0.5, 0.7, 0.9], [0.6, 0.8, 1.0],
        ],
        dtype=np.float64,
    )
    targets = predicted - 0.05
    anatomy = predicted + 0.10
    latent = np.array(
        [
            [0.8, 0.1, 0.1], [0.7, 0.2, 0.1],
            [0.1, 0.8, 0.1], [0.1, 0.7, 0.2],
            [0.1, 0.1, 0.8], [0.2, 0.1, 0.7],
        ],
        dtype=np.float64,
    )
    concept = latent.copy()
    concept[1] = (0.4, 0.5, 0.1)
    labels = np.array([0, 0, 1, 1, 2, 2], dtype=np.int64)

    fidelity = compute_global_fidelity(predicted, targets)
    anatomy_metrics = compute_global_anatomy(predicted, anatomy)
    agreement = compute_all_agreement(
        latent,
        concept,
        labels,
        consistency_loss_type="kl",
    )
    fidelity_profiles = np.abs(predicted[:2] - targets[:2])
    stability = compute_all_stability(
        fidelity_profiles,
        np.abs(predicted[:2] - anatomy[:2]),
        predicted[:2],
        np.array([[0.2, 0.3, 0.5], [0.3, 0.2, 0.5]], dtype=np.float64),
        k_values=[1, 2],
    )
    per_subject_mae = np.mean(np.abs(predicted - targets), axis=1)
    interval = bootstrap_metric(
        per_subject_mae,
        labels=labels,
        metric="concept_mae",
        n_replicates=100,
        seed=17,
    )
    paired = paired_bootstrap_diff(
        per_subject_mae,
        per_subject_mae + 0.01,
        labels=labels,
        comparator_method=MethodId.SOURCE_ONLY,
        metric="concept_mae",
        n_replicates=100,
        seed=17,
    )
    return {
        "fixture_only": True,
        "subject_count": int(labels.size),
        "roi_count": int(predicted.shape[1]),
        "concept_mae": fidelity.mae,
        "concept_rmse": fidelity.rmse,
        "anatomy_mae": anatomy_metrics.mae,
        "anatomy_rmse": anatomy_metrics.rmse,
        "top1_agreement_rate": agreement.top1_agreement_rate,
        "mean_js_divergence": agreement.mean_js_divergence,
        "mean_pairwise_rho_concept": stability.mean_pairwise_rho_concept,
        "concept_mae_ci_low": interval.ci_low,
        "concept_mae_ci_high": interval.ci_high,
        "paired_concept_mae_difference": paired.observed_difference,
        "paired_concept_mae_p_value": paired.raw_p_value,
    }


def _unresolved_real_gates(gate: Mapping[str, Any]) -> tuple[str, ...]:
    names = ("authorized_exports", "concept_normalizer", "atlas_hash", "protocol_approval")
    if not isinstance(gate, Mapping):
        return names
    unresolved = []
    for name in names:
        state = gate.get(name)
        digest = state.get("sha256") if isinstance(state, Mapping) else None
        if (
            not isinstance(state, Mapping)
            or state.get("resolved") is not True
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
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
    if selection.run_mode is RunMode.REUSE and (reuse_output is None or not reuse_output.is_dir()):
        raise ReuseVerificationError("completed reuse output is unavailable")
    if selection.run_mode is RunMode.REUSE:
        assert reuse_output is not None
        if reuse_output.resolve() not in approved_reuse_roots:
            raise ReuseVerificationError("completed reuse output is not approved")
        try:
            verify_completed_output(reuse_output)
        except (OSError, ValueError) as error:
            raise ReuseVerificationError("completed reuse verification failed") from error
        return ExitCode.SUCCESS

    request = _evaluation_request(selection, config)
    gate = config.get("real_evaluation_gate", {})
    if request.analysis_mode is AnalysisMode.REAL and request.run_mode is RunMode.DRY_RUN:
        assert selection.runs_root is not None
        assert selection.artifact_root is not None
        normalizer_config = config.get("concept_normalizer", {})
        atlas_config = config.get("atlas", {})
        discovery_config = DiscoveryConfig(
            runs_root=selection.runs_root,
            artifact_root=selection.artifact_root,
            methods=frozenset(selection.methods),
            directions=frozenset(selection.directions),
            checkpoint_policies=frozenset(selection.checkpoint_policies),
            expected_folds=tuple(int(value) for value in config.get("expected_folds", ())),
            expected_seeds=tuple(int(value) for value in config.get("expected_seeds", ())),
            expected_concept_normalizer_hash=(
                normalizer_config.get("expected_hash")
                if isinstance(normalizer_config, Mapping) else None
            ),
            expected_atlas_roi_order_hash=(
                atlas_config.get("expected_roi_order_hash")
                if isinstance(atlas_config, Mapping) else None
            ),
            expected_atlas_hash=(
                atlas_config.get("expected_atlas_hash")
                if isinstance(atlas_config, Mapping) else None
            ),
        )
        candidates, issues = discover_candidates(discovery_config)
        if issues or any(candidate.issues for candidate in candidates):
            raise ConfigurationError(
                "real dry-run discovery failed: " + ", ".join(sorted(set(issues)))
            )
        return ExitCode.SUCCESS
    if (
        request.analysis_mode is AnalysisMode.REAL
        and request.run_mode in {RunMode.VALIDATE_ONLY, RunMode.EVALUATE}
    ):
        unresolved = _unresolved_real_gates(gate)
        if unresolved:
            raise AuthorizationGateError("unresolved real evaluation gates: " + ", ".join(unresolved))
        raise AuthorizationGateError("real concept evaluation remains closed in Phase 16")

    if request.run_mode is RunMode.DRY_RUN:
        return ExitCode.SUCCESS
    if request.analysis_mode is AnalysisMode.SYNTHETIC_TEST_ONLY and request.run_mode in {
        RunMode.VALIDATE_ONLY,
        RunMode.EVALUATE,
    }:
        metrics = _synthetic_fixture_metrics()
        if request.run_mode is RunMode.VALIDATE_ONLY:
            return ExitCode.SUCCESS

        assert selection.output_root is not None
        identity_inputs = {
            "configuration_sha256": canonical_sha256(config),
            "authorization_sha256": canonical_sha256(gate),
            "ordered_input_sha256s": [],
            "methods": selection.methods,
            "directions": selection.directions,
            "checkpoint_policies": selection.checkpoint_policies,
            "bootstrap_replicates": selection.bootstrap_replicates,
            "bootstrap_seed": selection.bootstrap_seed,
            "top_k": selection.top_k or tuple(config.get("top_k", ())),
            "device": selection.device,
            "fixture_only": True,
        }
        evaluation_identity = canonical_sha256(identity_inputs)
        plan, artifacts = build_synthetic_fixture_bundle(
            evaluation_identity=evaluation_identity,
            methods=selection.methods,
            directions=selection.directions,
            checkpoint_policies=selection.checkpoint_policies,
            metrics=metrics,
            resolved_config=config,
            identity_inputs=identity_inputs,
            library_versions=_library_versions(),
            bootstrap_replicates=selection.bootstrap_replicates,
            bootstrap_seed=int(selection.bootstrap_seed),
        )
        try:
            commit_output(
                selection.output_root,
                plan,
                artifacts,
                overwrite=selection.overwrite,
            )
        except (OSError, RuntimeError, ValueError) as error:
            raise OutputCommitError("synthetic output commit failed") from error
        return ExitCode.SUCCESS

    return ExitCode.SUCCESS


def main(argv: Sequence[str] | None = None, *, executor: Executable = _execute) -> int:
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