"""Phase 16 concept evaluation command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import sys
from collections.abc import Callable, Mapping, Sequence
from enum import IntEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, NamedTuple

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from pada3dacb.artifacts.concepts import ConceptNormalizer
from pada3dacb.evaluation.concepts.agreement import compute_all_agreement
from pada3dacb.evaluation.concepts.anatomy import compute_global_anatomy
from pada3dacb.evaluation.concepts.discovery import (
    NOT_APPLICABLE_STATUS,
    DiscoveryConfig,
    discover_candidates,
)
from pada3dacb.evaluation.concepts.fidelity import compute_global_fidelity
from pada3dacb.evaluation.concepts.inference import (
    load_checkpoint,
    run_real_evaluation,
    run_subject_inference,
)
from pada3dacb.evaluation.concepts.provenance import load_provenance_manifest
from pada3dacb.evaluation.concepts.report import (
    CooperativeReaderPolicy,
    PublicationBlocked,
    build_synthetic_fixture_bundle,
    commit_output,
    read_cooperative_publication,
    verify_completed_output,
)
from pada3dacb.evaluation.concepts.schemas import (
    VerifiedFixtureManifest,
    _is_verified_fixture_manifest,
    issue_real_evaluation_capability,
    verify_fixture_manifest,
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
from pada3dacb.models.pada3dacb import PADA3DACB

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
    absent_window_timeout_seconds: float | None


Executable = Callable[[CliSelection], int | ExitCode]


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _non_negative_finite_float(value: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(
            "absent-window timeout must be a finite, non-negative number"
        ) from error
    if not np.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError(
            "absent-window timeout must be a finite, non-negative number"
        )
    return parsed


def _direction_value(value: str) -> str:
    normalized = value.lower().replace("-", "_")
    try:
        Direction(normalized)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"unsupported direction: {value}") from error
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--output-root", type=Path)

    directions = parser.add_mutually_exclusive_group(required=True)
    directions.add_argument(
        "--direction",
        type=_direction_value,
        choices=[item.value for item in Direction],
    )
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
    parser.add_argument(
        "--absent-window-timeout-seconds",
        type=_non_negative_finite_float,
        metavar="SECONDS",
    )

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
    if args.absent_window_timeout_seconds is not None and mode is not RunMode.EVALUATE:
        parser.error("--absent-window-timeout-seconds is valid only for evaluation")
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
        absent_window_timeout_seconds=args.absent_window_timeout_seconds,
    )


def _validate_publication_policy(selection: CliSelection) -> None:
    value = selection.absent_window_timeout_seconds
    if value is None and not selection.overwrite:
        return
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not np.isfinite(value)
        or value < 0
    ):
        if value is None and selection.overwrite:
            raise ConfigurationError(
                "--absent-window-timeout-seconds is required with --overwrite"
            )
        raise ConfigurationError(
            "--absent-window-timeout-seconds must be finite and non-negative"
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
    approved_methods.update(config.get("baselines", ()))
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


def _load_verified_fixture_manifest(
    config: Mapping[str, Any],
    config_path: Path,
) -> VerifiedFixtureManifest:
    values = {
        name: config.get(name)
        for name in (
            "fixture_manifest_path",
            "fixture_manifest_sha256",
            "fixture_allowed_root",
        )
    }
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ConfigurationError(
            "synthetic execution requires fixture_manifest_path, "
            "fixture_manifest_sha256, and fixture_allowed_root"
        )
    base = config_path.resolve().parent

    def resolve(value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (base / path).resolve()

    try:
        return verify_fixture_manifest(
            resolve(values["fixture_manifest_path"]),
            values["fixture_manifest_sha256"],
            resolve(values["fixture_allowed_root"]),
        )
    except (OSError, TypeError, ValueError) as error:
        raise ConfigurationError(f"fixture manifest is invalid: {error}") from error


def _validate_synthetic_fixture(
    device: str = "cpu",
    fixture_manifest: VerifiedFixtureManifest | object = None,
) -> str:
    """Run the deterministic validate-only checkpoint/model tensor contract."""
    if not _is_verified_fixture_manifest(fixture_manifest):
        raise ConfigurationError("synthetic validate-only requires a verified fixture manifest")
    if device != "cpu":
        raise ConfigurationError("synthetic validate-only fixtures are CPU-only")
    assert isinstance(fixture_manifest, VerifiedFixtureManifest)
    fixture_payload_sha256 = fixture_manifest.fixture_payload_sha256

    # The fixture identity is part of the deterministic test execution, not a
    # scientific input: a different verified bundle produces a different
    # synthetic checkpoint while preserving the closed test-only seam.
    torch.manual_seed(16 ^ int(fixture_payload_sha256[:8], 16))
    model_config = {
        "num_rois": 3,
        "feature_dim": 8,
        "token_dim": 4,
        "num_classes": 3,
        "base_channels": 4,
        "concept_hidden_dim": 4,
        "token_dropout": 0.0,
        "concept_dropout": 0.0,
        "validate_inputs": True,
    }
    model = PADA3DACB(**model_config)
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "experiment_hash": "1" * 64,
        "model_hash": "2" * 64,
        "training_hash": "3" * 64,
        "epoch": 1,
        "logical_checkpoint": "best_source_f1",
        "config": model_config,
    }

    class _Atlas:
        K = 3

        @staticmethod
        def get_binary_masks() -> torch.Tensor:
            return torch.ones(3, 2, 2, 2, dtype=torch.float32)

    with TemporaryDirectory(prefix="pada3dacb-validate-only-") as directory:
        checkpoint_path = Path(directory) / "checkpoint.pt"
        torch.save(checkpoint, checkpoint_path)
        bundle = load_checkpoint(checkpoint_path, device)
        batch = {
            "x": torch.ones(1, 1, 16, 16, 16, dtype=torch.float32),
            "roi_masks": torch.ones(3, 2, 2, 2, dtype=torch.float32),
            "subject_id": ["synthetic-subject"],
            "subject_hash": ["4" * 64],
            "cohort": ["ADNI"],
            "label": torch.tensor([0]),
            "label_name": ["CN"],
            "concept_targets": torch.full((1, 3), 0.5, dtype=torch.float32),
            "anatomical_targets": torch.full((1, 3), 0.4, dtype=torch.float32),
        }
        dataloader = DataLoader(
            [batch], batch_size=1, collate_fn=lambda items: items[0]
        )
        records = run_subject_inference(
            model=bundle.model,
            dataloader=dataloader,
            concept_normalizer=ConceptNormalizer(
                np.zeros(3, dtype=np.float32), np.ones(3, dtype=np.float32)
            ),
            device=device,
            atlas_mgr=_Atlas(),
            method_id=MethodId.SOURCE_ONLY,
            direction=Direction.ADNI_TO_OASIS,
            source_domain="ADNI",
            target_domain="OASIS",
            seed=42,
            fold=0,
            logical_checkpoint="best_source_f1",
            checkpoint_epoch=bundle.epoch,
            checkpoint_policy=CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            experiment_hash=bundle.experiment_hash,
            roi_order_hash="5" * 64,
            normalizer_hash="6" * 64,
            concept_config_hash=canonical_sha256({}),
        )
    if len(records) != 1 or records[0].K != 3:
        raise ConfigurationError("synthetic validate-only inference returned an invalid record")
    return fixture_payload_sha256


def _synthetic_fixture_metrics(fixture_payload_sha256: str | None = None) -> dict[str, Any]:
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
        "fixture_payload_sha256": fixture_payload_sha256,
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


def _issue_cli_capability(config: Mapping[str, Any], gate: Mapping[str, Any], config_path: Path):
    manifest_value = config.get("manifest_path")
    if not isinstance(manifest_value, str) or not manifest_value.strip():
        raise ConfigurationError("authorized real evaluation requires a canonical manifest_path")
    manifest_path = (config_path.parent / manifest_value).resolve()
    try:
        manifest_bytes = manifest_path.read_bytes()
        load_provenance_manifest(manifest_path)
    except (OSError, UnicodeError, ValueError) as error:
        raise ConfigurationError("configured canonical manifest is invalid or unreadable") from error
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    try:
        return issue_real_evaluation_capability(gate, manifest_sha256, issuer="cli")
    except (TypeError, ValueError) as error:
        raise ConfigurationError("canonical manifest or authorization evidence is invalid") from error


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


def _identity_configuration(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """Exclude reuse routing controls from the configuration identity."""
    return {key: value for key, value in config.items() if key != "completed_reuse"}


def _verify_reuse_selection_match(
    output_manifest: Mapping[str, Any],
    selection: CliSelection,
    *,
    config: Mapping[str, Any],
    authorization_gate: Mapping[str, Any],
    resolved_top_k: Sequence[int] = (),
) -> None:
    """Reject reuse when the stored evaluation identity differs from the request."""
    stored = {
        "methods": output_manifest.get("methods"),
        "directions": output_manifest.get("directions"),
        "checkpoint_policies": output_manifest.get("checkpoint_policies"),
    }
    current = {
        "methods": [method.value for method in selection.methods],
        "directions": [direction.value for direction in selection.directions],
        "checkpoint_policies": [
            policy.logical_checkpoint for policy in selection.checkpoint_policies
        ],
    }
    for selector in ("methods", "directions", "checkpoint_policies"):
        if stored[selector] != current[selector]:
            raise ReuseVerificationError(
                "completed reuse output selector mismatch for "
                f"{selector}: stored {stored[selector]!r} does not match "
                f"the current CLI selection {current[selector]!r}"
            )

    identity_inputs = output_manifest.get("identity_inputs")
    if not isinstance(identity_inputs, Mapping):
        raise ReuseVerificationError(
            "completed reuse output is missing its identity_inputs mapping"
        )

    effective_top_k = tuple(selection.top_k) or tuple(resolved_top_k)
    analysis_mode = config.get("analysis_mode")
    if not isinstance(analysis_mode, str) or not analysis_mode:
        raise ReuseVerificationError(
            "completed reuse request configuration is missing analysis_mode"
        )
    current_identity = {
        "methods": current["methods"],
        "directions": current["directions"],
        "checkpoint_policies": [
            policy.value for policy in selection.checkpoint_policies
        ],
        "analysis_mode": analysis_mode,
        "configuration_sha256": canonical_sha256(_identity_configuration(config)),
        "authorization_sha256": canonical_sha256(authorization_gate),
        "bootstrap_replicates": selection.bootstrap_replicates,
        "bootstrap_seed": selection.bootstrap_seed,
        "top_k": list(effective_top_k),
        "device": selection.device,
    }
    for selector, expected in current_identity.items():
        if selector not in identity_inputs:
            raise ReuseVerificationError(
                "completed reuse output identity_inputs is missing "
                f"required selector {selector}"
            )
        stored_value = identity_inputs[selector]
        if stored_value != expected:
            raise ReuseVerificationError(
                "completed reuse output identity_inputs mismatch for "
                f"{selector}: stored {stored_value!r} does not match "
                f"the current CLI selection {expected!r}"
            )

    expected_evaluation_identity = canonical_sha256(identity_inputs)
    if output_manifest.get("evaluation_identity") != expected_evaluation_identity:
        raise ReuseVerificationError(
            "completed reuse output evaluation_identity does not match its identity_inputs"
        )


def _execute(selection: CliSelection) -> ExitCode:
    _validate_publication_policy(selection)
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
    if selection.run_mode is RunMode.REUSE:
        if reuse_output is None:
            raise ReuseVerificationError("completed reuse output is unavailable")
        if reuse_output.resolve() not in approved_reuse_roots:
            raise ReuseVerificationError("completed reuse output is not approved")
        fixture_manifest = None
        if config.get("analysis_mode") == AnalysisMode.SYNTHETIC_TEST_ONLY.value:
            try:
                fixture_manifest = _load_verified_fixture_manifest(config, selection.config_path)
            except (ConfigurationError, OSError, ValueError) as error:
                raise ReuseVerificationError(
                    "current synthetic fixture manifest verification failed"
                ) from error
        try:
            cooperative = read_cooperative_publication(
                reuse_output,
                policy=CooperativeReaderPolicy(
                    max_attempts=1,
                    delay_seconds=0.0,
                ),
                reader=verify_completed_output,
            )
        except (OSError, ValueError, PublicationBlocked) as error:
            raise ReuseVerificationError("completed reuse verification failed") from error
        if cooperative.status != "available":
            raise ReuseVerificationError("completed reuse output is unavailable")
        output_manifest = cooperative.value
        configured_top_k = config.get("top_k", ())
        if isinstance(configured_top_k, (str, bytes)) or not isinstance(configured_top_k, Sequence):
            raise ReuseVerificationError("configured top_k is not a valid sequence")
        _verify_reuse_selection_match(
            output_manifest,
            selection,
            config=config,
            authorization_gate=config.get("real_evaluation_gate", {}),
            resolved_top_k=tuple(int(value) for value in configured_top_k),
        )
        if fixture_manifest is not None:
            identity_inputs = output_manifest.get("identity_inputs")
            expected_fixture_files = list(fixture_manifest.fixture_files)
            if (
                not isinstance(identity_inputs, Mapping)
                or identity_inputs.get("fixture_manifest_sha256") != fixture_manifest.manifest_sha256
                or identity_inputs.get("fixture_payload_sha256") != fixture_manifest.fixture_payload_sha256
                or identity_inputs.get("fixture_files") != expected_fixture_files
            ):
                raise ReuseVerificationError(
                    "completed reuse output is bound to a different synthetic fixture"
                )
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
        not_applicable_issues = sorted(
            issue for issue in issues if issue.startswith("not_applicable:")
        )
        for issue in not_applicable_issues:
            _, method, status = issue.split(":", 2)
            if status != NOT_APPLICABLE_STATUS:
                raise ConfigurationError(f"unknown not-applicable discovery status: {issue}")
            print(f"{method}: {status}")
        blocking_issues = [
            issue for issue in issues if not issue.startswith("not_applicable:")
        ]
        candidate_issues = [
            issue for candidate in candidates for issue in candidate.issues
        ]
        if blocking_issues or candidate_issues:
            raise ConfigurationError(
                "real dry-run discovery failed: "
                + ", ".join(sorted(set(blocking_issues + candidate_issues)))
            )
        return ExitCode.SUCCESS
    if (
        request.analysis_mode is AnalysisMode.REAL
        and request.run_mode in {RunMode.VALIDATE_ONLY, RunMode.EVALUATE}
    ):
        unresolved = _unresolved_real_gates(gate)
        if unresolved:
            raise AuthorizationGateError("unresolved real evaluation gates: " + ", ".join(unresolved))
        raise ConfigurationError("real evaluation capability issuance is closed: external authorization issuer is not configured")
        capability = _issue_cli_capability(config, gate, selection.config_path)
        # Route the authorized request through the real orchestration seam. The
        # repository deliberately has no approved local data/statistics/publish
        # callbacks, so the seam returns the actionable closed error without
        # constructing a model or treating synthetic fixtures as real.
        run_real_evaluation(
            candidates=(),
            dataloader_factory=None,
            device=selection.device,
            concept_normalizer=None,
            atlas_mgr=None,
            capability=capability,
            verified_inputs=None,
            authorization_evidence=gate,
            statistics_callback=None,
            publish_callback=None,
        )
        raise ConfigurationError(
            "real concept evaluation remains closed: no approved local orchestration callback is configured"
        )

    if request.run_mode is RunMode.DRY_RUN:
        return ExitCode.SUCCESS
    if request.analysis_mode is AnalysisMode.SYNTHETIC_TEST_ONLY and request.run_mode in {
        RunMode.VALIDATE_ONLY,
        RunMode.EVALUATE,
    }:
        fixture_manifest = _load_verified_fixture_manifest(config, selection.config_path)
        fixture_payload_sha256 = fixture_manifest.fixture_payload_sha256
        if request.run_mode is RunMode.VALIDATE_ONLY:
            _validate_synthetic_fixture(selection.device, fixture_manifest)
            return ExitCode.SUCCESS

        metrics = _synthetic_fixture_metrics(fixture_payload_sha256)

        assert selection.output_root is not None
        identity_inputs = {
            "analysis_mode": request.analysis_mode.value,
            "configuration_sha256": canonical_sha256(_identity_configuration(config)),
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
            "fixture_manifest_sha256": fixture_manifest.manifest_sha256,
            "fixture_payload_sha256": fixture_payload_sha256,
            "fixture_files": list(fixture_manifest.fixture_files),
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
                absent_window_timeout_seconds=selection.absent_window_timeout_seconds,
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
    except (ConfigurationError, SelectorConflictError, UnsafePathError) as error:
        print(f"configuration error: {error}", file=sys.stderr)
        return int(ExitCode.CONFIGURATION_ERROR)
    except AuthorizationGateError as error:
        print(str(error), file=sys.stderr)
        return int(ExitCode.GATE_BLOCKED)
    except ReuseVerificationError as error:
        print(f"reuse verification failed: {error}", file=sys.stderr)
        return int(ExitCode.REUSE_REJECTED)
    except OutputCommitError:
        return int(ExitCode.OUTPUT_FAILURE)
    except Exception:
        return int(ExitCode.INTERNAL_ERROR)


if __name__ == "__main__":
    sys.exit(main())