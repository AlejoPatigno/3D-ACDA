"""Configured, read-only prediction discovery and shared-method normalization."""
from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .provenance import (
    hydrate_provenance,
    inspect_input_file,
    sha256_exact,
    validate_prediction_rows,
    verify_identity_mapping,
)
from .schemas import (
    CandidateIssue,
    CandidateStatus,
    CheckpointPolicy,
    Direction,
    EvaluationRequest,
    ExpectedPopulation,
    IdentityMapping,
    IssueCode,
    MethodId,
    NormalizedBatch,
    PredictionRole,
    UnsafePathError,
    canonical_sha256,
)


@dataclass(frozen=True)
class AdapterSpec:
    method_id: MethodId
    public_name: str
    schema_family: str


@dataclass(frozen=True)
class CandidateFiles:
    method_id: MethodId
    direction: Direction
    seed: int
    fold: int
    checkpoint_policy: CheckpointPolicy
    prediction_files: tuple[tuple[PredictionRole, Path], ...]
    companion_files: tuple[Path, ...]
    issues: tuple[CandidateIssue, ...] = ()
    identity_mappings: tuple[tuple[PredictionRole, IdentityMapping, Path], ...] = ()
    expected_populations: tuple[ExpectedPopulation, ...] = ()


ADAPTER_REGISTRY: Mapping[MethodId, AdapterSpec] = MappingProxyType(
    {
        MethodId.SOURCE_ONLY: AdapterSpec(MethodId.SOURCE_ONLY, "3D-ACDA Source-Only", "shared_method"),
        MethodId.CORAL: AdapterSpec(MethodId.CORAL, "3D-ACDA + CORAL", "shared_method"),
        MethodId.MMD: AdapterSpec(MethodId.MMD, "3D-ACDA + MMD", "shared_method"),
        MethodId.CDAN: AdapterSpec(MethodId.CDAN, "3D-ACDA + CDAN", "shared_method"),
        MethodId.PROTOTYPE_PSEUDO: AdapterSpec(MethodId.PROTOTYPE_PSEUDO, "3D-ACDA", "shared_method"),
        MethodId.AAGN: AdapterSpec(MethodId.AAGN, "AAGN", "baseline_combined"),
        MethodId.FASTER_SNN: AdapterSpec(MethodId.FASTER_SNN, "FasterSNN", "baseline_combined"),
    }
)


def _configured_path(root: Path, pattern: str, values: Mapping[str, Any]) -> Path:
    try:
        relative = pattern.format_map(values)
    except (KeyError, ValueError) as error:
        raise ValueError("configured pattern contains an unknown placeholder") from error
    path = root / relative
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError as error:
        raise UnsafePathError("configured pattern escapes runs_root") from error
    return path


def _candidate_controls(
    config: Mapping[str, Any], root: Path, direction: Direction
) -> tuple[
    tuple[tuple[PredictionRole, IdentityMapping, Path], ...],
    tuple[ExpectedPopulation, ...],
    tuple[CandidateIssue, ...],
]:
    mappings = []
    populations = []
    issues = []
    identity_config = config.get("identity_companions", {})
    population_config = config.get("expected_population_companions", {}).get(direction.value, {})
    for role, cohort in zip(PredictionRole, direction.cohorts, strict=True):
        identity = identity_config.get(cohort, {})
        if isinstance(identity, Mapping) and identity.get("approved") is True:
            try:
                mapping = IdentityMapping(
                    identity["relative_path"], identity["sha256"],
                    identity["raw_identifier_field"], identity["subject_hash_field"], True,
                )
                path = _configured_path(root, mapping.relative_path, {})
                if not path.is_file() or sha256_exact(path) != mapping.sha256:
                    raise ValueError
                mappings.append((role, mapping, path))
            except (KeyError, TypeError, ValueError, OSError):
                issues.append(CandidateIssue(
                    IssueCode.UNAPPROVED_IDENTITY_MAPPING, CandidateStatus.EXCLUDED
                ))
        population = population_config.get(role.value, {})
        if isinstance(population, Mapping) and population.get("relative_path") is not None:
            try:
                path = _configured_path(root, population["relative_path"], {})
                if not path.is_file() or sha256_exact(path) != population["sha256"]:
                    raise ValueError
                with path.open(newline="", encoding="utf-8") as stream:
                    subject_hashes = tuple(row["subject_hash"] for row in csv.DictReader(stream))
                populations.append(ExpectedPopulation(
                    direction, role, population["relative_path"],
                    population["sha256"], subject_hashes,
                ))
            except (KeyError, TypeError, ValueError, OSError):
                issues.append(CandidateIssue(
                    IssueCode.INCOMPLETE_ENSEMBLE, CandidateStatus.INCOMPLETE
                ))
    return tuple(mappings), tuple(populations), tuple(issues)


def discover_candidates(
    config: Mapping[str, Any],
    runs_root: Path,
    request: EvaluationRequest,
    folds: tuple[int, ...],
    seeds: tuple[int, ...],
) -> tuple[CandidateFiles, ...]:
    candidates: list[CandidateFiles] = []
    for method in request.methods:
        spec = ADAPTER_REGISTRY[method]
        family = config.get(spec.schema_family)
        if not isinstance(family, Mapping) or not isinstance(family.get("prediction_pattern"), str):
            raise ValueError(f"{spec.schema_family} discovery configuration is required")
        direction_values = family.get("direction_values", {})
        for direction in request.directions:
            producer_direction = direction_values.get(direction.value, direction.value)
            for policy in request.checkpoint_policies:
                for seed in seeds:
                    for fold in folds:
                        common = {
                            "method": method.value, "direction": producer_direction,
                            "seed": seed, "fold": fold,
                            "logical_checkpoint": policy.logical_checkpoint,
                        }
                        if spec.schema_family == "shared_method":
                            roles = family.get("role_directories")
                            if not isinstance(roles, Mapping):
                                raise ValueError("shared role directories are required")
                            prediction_files = tuple(
                                (role, _configured_path(runs_root, family["prediction_pattern"], {
                                    **common, "role_directory": roles[role.value],
                                }))
                                for role in PredictionRole
                            )
                        else:
                            path = _configured_path(runs_root, family["prediction_pattern"], common)
                            prediction_files = ((PredictionRole.TARGET_EVALUATION, path),)
                        companion_files = tuple(
                            _configured_path(runs_root, item, common)
                            for item in family.get("companion_patterns", ())
                        )
                        missing = sum(not path.is_file() for _, path in prediction_files)
                        missing += sum(not path.is_file() for path in companion_files)
                        issues = (
                            (CandidateIssue(IssueCode.MISSING_REQUIRED_FIELD, CandidateStatus.INCOMPLETE),)
                            if missing else ()
                        )
                        mappings, populations, control_issues = _candidate_controls(
                            config, runs_root, direction
                        )
                        candidates.append(CandidateFiles(
                            method, direction, seed, fold, policy,
                            prediction_files, companion_files, issues + control_issues,
                            mappings, populations,
                        ))
    return tuple(candidates)


class SharedMethodAdapter:
    """Normalize one complete shared-method fold without importing producers."""

    schema_family = "shared_method"
    schema_version = "shared-prediction-v1"

    def normalize(self, candidate: CandidateFiles, runs_root: Path) -> NormalizedBatch:
        if candidate.issues:
            return NormalizedBatch("shared-method-v1", self.schema_family, (), (), (), (), candidate.issues)
        input_files = []
        issues: list[CandidateIssue] = []
        companion_path = candidate.companion_files[0]
        companion_file, companion_issues = inspect_input_file(
            runs_root, companion_path, self.schema_family, "run-manifest-v1"
        )
        issues.extend(companion_issues)
        if companion_file is None:
            return NormalizedBatch("shared-method-v1", self.schema_family, (), (), (), (), tuple(issues))
        input_files.append(companion_file)
        manifest = json.loads(companion_path.read_text(encoding="utf-8"))
        if (
            candidate.method_id is MethodId.SOURCE_ONLY
            and "target_evaluation_assignment_hash" not in manifest
        ):
            issues.append(CandidateIssue(
                IssueCode.TARGET_EVALUATION_MEMBERSHIP_UNPROVABLE,
                CandidateStatus.EXCLUDED,
            ))
            return NormalizedBatch(
                "shared-method-v1", self.schema_family, tuple(input_files), (), (), (),
                tuple(issues),
            )
        provenance_records = []
        predictions = []

        for role, prediction_path in candidate.prediction_files:
            input_file, input_issues = inspect_input_file(
                runs_root, prediction_path, self.schema_family, self.schema_version
            )
            issues.extend(input_issues)
            if input_file is None:
                continue
            input_files.append(input_file)
            with prediction_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            if not rows:
                issues.append(CandidateIssue(IssueCode.MISSING_REQUIRED_FIELD, CandidateStatus.EXCLUDED))
                continue
            first = rows[0]
            expected = {
                "method_id": candidate.method_id.value,
                "direction": candidate.direction.value,
                "seed": candidate.seed,
                "fold": candidate.fold,
                "logical_checkpoint": candidate.checkpoint_policy.logical_checkpoint,
                "checkpoint_epoch": int(first["checkpoint_epoch"]),
                "experiment_hash": first["experiment_hash"],
            }
            record, record_issues = hydrate_provenance(
                expected,
                input_file.sha256,
                (("run_manifest", companion_file.sha256, manifest),),
            )
            issues.extend(record_issues)
            if record is None:
                continue
            provenance_records.append(record)
            canonical_rows = [
                {
                    "subject_hash": row.get("subject_hash"),
                    "true_label": int(row["true_label_index"]),
                    "probabilities": (
                        row["probability_CN"], row["probability_MCI"], row["probability_AD"]
                    ),
                }
                for row in rows
            ]
            normalized, row_issues = validate_prediction_rows(
                canonical_rows,
                candidate.method_id,
                candidate.direction,
                candidate.seed,
                candidate.fold,
                candidate.checkpoint_policy.logical_checkpoint,
                role,
                canonical_sha256(record),
            )
            predictions.extend(normalized)
            issues.extend(row_issues)
        return NormalizedBatch(
            "shared-method-v1",
            self.schema_family,
            tuple(input_files),
            tuple(provenance_records),
            tuple(predictions),
            (),
            tuple(issues),
        )


class BaselineCombinedAdapter:
    """Partition a combined baseline export by declared method, policy, and role."""

    schema_family = "baseline_combined"
    schema_version = "baseline-prediction-v1"

    def normalize(
        self,
        candidate: CandidateFiles,
        runs_root: Path,
        derivation_rules: Mapping[str, tuple[str, str, str]] | None = None,
    ) -> NormalizedBatch:
        if candidate.issues:
            return NormalizedBatch("baseline-combined-v1", self.schema_family, (), (), (), (), candidate.issues)
        issues: list[CandidateIssue] = []
        input_files = []
        prediction_path = candidate.prediction_files[0][1]
        prediction_file, found = inspect_input_file(
            runs_root, prediction_path, self.schema_family, self.schema_version
        )
        issues.extend(found)
        companions: list[tuple[str, str, Mapping[str, Any]]] = []
        for index, path in enumerate(candidate.companion_files):
            item, found = inspect_input_file(runs_root, path, self.schema_family, "baseline-companion-v1")
            issues.extend(found)
            if item is not None:
                input_files.append(item)
                kind = "run_manifest" if index == 0 else "fold_result"
                companions.append((kind, item.sha256, json.loads(path.read_text(encoding="utf-8"))))
        if prediction_file is None or not companions:
            return NormalizedBatch("baseline-combined-v1", self.schema_family, tuple(input_files), (), (), (), tuple(issues))
        input_files.insert(0, prediction_file)
        manifest = companions[0][2]
        if "target_evaluation_assignment_hash" not in manifest:
            issues.append(CandidateIssue(
                IssueCode.TARGET_EVALUATION_MEMBERSHIP_UNPROVABLE,
                CandidateStatus.EXCLUDED,
            ))
        if manifest.get("baseline_id") != candidate.method_id.value:
            issues.append(CandidateIssue(IssueCode.PROVENANCE_CONFLICT, CandidateStatus.EXCLUDED))
        with prediction_path.open(newline="", encoding="utf-8") as stream:
            rows = [
                row for row in csv.DictReader(stream)
                if row.get("checkpoint") == candidate.checkpoint_policy.logical_checkpoint
            ]
        expected = {
            "method_id": candidate.method_id.value,
            "direction": candidate.direction.value,
            "seed": candidate.seed,
            "fold": candidate.fold,
            "logical_checkpoint": candidate.checkpoint_policy.logical_checkpoint,
        }
        record, found = hydrate_provenance(
            expected, prediction_file.sha256, tuple(companions), derivation_rules
        )
        issues.extend(found)
        if issues or record is None:
            return NormalizedBatch(
                "baseline-combined-v1", self.schema_family, tuple(input_files),
                (() if record is None else (record,)), (), (), tuple(issues),
            )
        predictions = []
        role_names = {
            "source_validation": PredictionRole.SOURCE_OOF,
            "target_monitoring": PredictionRole.TARGET_EVALUATION,
        }
        for split, role in role_names.items():
            selected = [row for row in rows if row.get("split") == split]
            if any(row.get("method") != "baseline" or row.get("model") != candidate.method_id.value for row in selected):
                issues.append(CandidateIssue(IssueCode.PROVENANCE_CONFLICT, CandidateStatus.EXCLUDED))
                continue
            identity = next(
                (control for control in candidate.identity_mappings if control[0] is role),
                None,
            )
            if identity is not None:
                _, mapping, mapping_path = identity
                with mapping_path.open(newline="", encoding="utf-8") as stream:
                    mapping_rows = list(csv.DictReader(stream))
                selected, mapping_issues = verify_identity_mapping(
                    selected, mapping_rows, mapping, mapping_path
                )
                issues.extend(mapping_issues)
                if mapping_issues:
                    continue
            canonical_rows = [
                {
                    "subject_hash": row.get("subject_hash"),
                    "true_label": int(row["label"]),
                    "probabilities": (row["prob_cn"], row["prob_mci"], row["prob_ad"]),
                }
                for row in selected
            ]
            normalized, found = validate_prediction_rows(
                canonical_rows, candidate.method_id, candidate.direction,
                candidate.seed, candidate.fold, candidate.checkpoint_policy.logical_checkpoint,
                role, canonical_sha256(record),
            )
            predictions.extend(normalized)
            issues.extend(found)
        return NormalizedBatch(
            "baseline-combined-v1", self.schema_family, tuple(input_files),
            (record,), tuple(predictions), (), tuple(issues),
        )


# Task-scoped binary discovery is additive; historical adapters above retain their
# three-class schema families and configuration surface.
@dataclass(frozen=True)
class BinaryDiscoveryConfig:
    runs_root: Path
    task: str = "cn_vs_impaired"
    expected_task_hash: str | None = None
    pattern: str = "**/*.json"
    expected_folds: tuple[int, ...] = ()
    expected_seeds: tuple[int, ...] = ()
    class_order: tuple[str, str] = ("CN", "Impaired")

    def validate(self) -> None:
        if self.task != "cn_vs_impaired":
            raise ValueError("binary discovery requires task=cn_vs_impaired")
        if self.class_order != ("CN", "Impaired"):
            raise ValueError("binary discovery class order must be CN, Impaired")
        if self.expected_task_hash is not None and not self.expected_task_hash:
            raise ValueError("expected_task_hash cannot be empty")
        for name, values in (("expected_folds", self.expected_folds), ("expected_seeds", self.expected_seeds)):
            if len(values) != len(set(values)) or any(isinstance(value, bool) or value < 0 for value in values):
                raise ValueError(f"{name} must contain unique non-negative integers")


@dataclass(frozen=True)
class BinaryCandidate:
    path: Path
    task: str
    task_hash: str | None
    fold: int | None
    seed: int | None
    rows: tuple[Mapping[str, Any], ...]


def _read_binary_candidate(path: Path) -> Mapping[str, Any] | None:
    try:
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8") as stream:
                return {"rows": tuple(csv.DictReader(stream))}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error):
        return None
    if isinstance(payload, list):
        return {"rows": tuple(payload)}
    return payload if isinstance(payload, Mapping) else None


def discover_binary_candidates(config: BinaryDiscoveryConfig) -> tuple[BinaryCandidate, ...]:
    """Discover only files explicitly bound to the binary task and task hash."""
    config.validate()
    root = config.runs_root
    if not root.is_dir():
        return ()
    candidates: list[BinaryCandidate] = []
    for path in sorted(root.glob(config.pattern)):
        if not path.is_file():
            continue
        payload = _read_binary_candidate(path)
        if payload is None:
            continue
        task = payload.get("task", payload.get("task_id"))
        order = payload.get("class_order")
        if task != config.task or order not in (None, ["CN", "Impaired"], ("CN", "Impaired")):
            continue
        task_hash = payload.get("task_hash")
        if config.expected_task_hash is not None and task_hash != config.expected_task_hash:
            continue
        raw_rows = payload.get("rows", payload.get("predictions", ()))
        if not isinstance(raw_rows, (list, tuple)):
            continue
        rows = tuple(row for row in raw_rows if isinstance(row, Mapping))
        if not rows:
            continue
        fold = payload.get("fold")
        seed = payload.get("seed")
        try:
            fold = None if fold is None else int(fold)
            seed = None if seed is None else int(seed)
        except (TypeError, ValueError):
            continue
        if config.expected_folds and fold not in config.expected_folds:
            continue
        if config.expected_seeds and seed not in config.expected_seeds:
            continue
        candidates.append(BinaryCandidate(path, task, task_hash, fold, seed, rows))
    return tuple(candidates)


def discover_task_scoped_candidates(config: BinaryDiscoveryConfig) -> tuple[BinaryCandidate, ...]:
    return discover_binary_candidates(config)
