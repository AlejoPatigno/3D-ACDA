"""Deterministic source folds and fixed target partitions for Phase 6."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import StratifiedKFold, train_test_split

from pada3dacb import __version__
from pada3dacb.binary import (
    BINARY_CLASS_ORDER,
    SPLIT_DISPOSITION,
    BinarySubjectRecord,
    build_binary_target_partition,
    generate_binary_source_folds,
)
from pada3dacb.data.records import CLASS_TO_INDEX, SUPPORTED_COHORTS, SubjectRecord
from pada3dacb.exceptions import ConfigurationError, SplitValidationError
from pada3dacb.paths import resolve_path


@dataclass(frozen=True)
class Direction:
    source: str
    target: str

    @property
    def name(self) -> str:
        return f"{self.source}_to_{self.target}"

    def validate(self) -> None:
        if self.source not in SUPPORTED_COHORTS or self.target not in SUPPORTED_COHORTS:
            raise ConfigurationError(f"Unsupported transfer direction: {self.name}.")
        if self.source == self.target:
            raise ConfigurationError("Source and target cohorts must differ.")


@dataclass
class SplitConfig:
    n_splits: int = 5
    seed: int = 42
    stratify_source: bool = True
    stratify_target: bool = True
    target_adaptation_fraction: float = 0.8
    overwrite: bool = False
    dry_run: bool = False

    def scientific_hash(self, direction: Direction) -> str:
        payload = {
            "n_splits": self.n_splits,
            "seed": self.seed,
            "stratify_source": self.stratify_source,
            "stratify_target": self.stratify_target,
            "target_adaptation_fraction": self.target_adaptation_fraction,
            "direction": asdict(direction),
            "label_mapping": CLASS_TO_INDEX,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def validate(self) -> None:
        if self.n_splits < 2:
            raise ConfigurationError("n_splits must be at least 2.")
        if not 0.0 < self.target_adaptation_fraction < 1.0:
            raise ConfigurationError("target_adaptation_fraction must be between 0 and 1.")
        if not self.stratify_source or not self.stratify_target:
            raise ConfigurationError("Phase 6 preserves stratification for source and target splits.")


@dataclass
class SplitRunConfig:
    splits: SplitConfig = field(default_factory=SplitConfig)
    directions: list[Direction] = field(default_factory=lambda: [Direction("ADNI", "OASIS"), Direction("OASIS", "ADNI")])
    artifact_index: Path | None = None
    artifact_root: Path | None = None
    split_root: Path | None = None
    config_path: Path | None = None

    def validate(self) -> None:
        self.splits.validate()
        if self.artifact_index is None or self.split_root is None:
            raise ConfigurationError("artifact_index and split_root are required.")
        for direction in self.directions:
            direction.validate()


def _binary_split_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def generate_binary_source_folds_for_records(
    records: Iterable[BinarySubjectRecord], *, n_splits: int = 5, seed: int = 42
) -> list[dict[str, Any]]:
    """Generate deterministic task-scoped folds without changing historical splits."""
    folds = generate_binary_source_folds(list(records), n_splits=n_splits, seed=seed)
    for fold in folds:
        fold["task"] = "CN_vs_Impaired"
        fold["n_splits"] = n_splits
        fold["seed"] = seed
        fold["splitter"] = "StratifiedKFold"
        fold["shuffle"] = True
        fold["random_state"] = seed
        fold["split_assignment_hash"] = _binary_split_hash({key: value for key, value in fold.items() if key != "split_identity"})
        fold["split_identity"] = _binary_split_hash(fold)
    return folds


def generate_binary_target_partition_for_records(
    records: Iterable[BinarySubjectRecord], *, seed: int = 42, adaptation_fraction: float = 0.8
) -> dict[str, Any]:
    """Generate a binary target partition with label-free adaptation membership."""
    partition = build_binary_target_partition(list(records), seed=seed, adaptation_fraction=adaptation_fraction)
    partition["seed"] = seed
    partition["target_adaptation_fraction"] = adaptation_fraction
    partition["splitter"] = "train_test_split"
    partition["stratify"] = True
    partition["random_state"] = seed
    partition["split_assignment_hash"] = _binary_split_hash({key: value for key, value in partition.items() if key != "split_identity"})
    partition["split_identity"] = _binary_split_hash(partition)
    return partition


def validate_binary_split_manifest(
    source_folds: Sequence[Mapping[str, Any]],
    target_partition: Mapping[str, Any],
    *,
    n_splits: int = 5,
    seed: int = 42,
    approved_person_universe: Iterable[str] | None = None,
) -> None:
    """Validate binary split identity and leakage contracts, never historical manifests."""
    expected = {"task": "CN_vs_Impaired", "class_order": list(BINARY_CLASS_ORDER), "mapping_contract": "phase-18b-binary-v1", "disposition": SPLIT_DISPOSITION, "identity_level": "person", "person_disjoint": True}
    if not isinstance(target_partition, Mapping) or any(target_partition.get(key) != value for key, value in expected.items()):
        raise SplitValidationError("Binary split manifest has incompatible task, class order, mapping, or disposition")
    if target_partition.get("seed") != seed or target_partition.get("target_adaptation_fraction") != 0.8 or target_partition.get("splitter") != "train_test_split" or target_partition.get("stratify") is not True or target_partition.get("random_state") != seed:
        raise SplitValidationError("Binary target split must use stratified 80/20 train_test_split with seed 42")
    target_adaptation = target_partition.get("target_adaptation", ())
    target_evaluation = target_partition.get("target_evaluation", ())

    def _unique_hashes(values: Any, label: str) -> set[str]:
        if not isinstance(values, (list, tuple)):
            raise SplitValidationError(f"Binary {label} must be an explicit list of person hashes")
        if any(not isinstance(value, str) or not value for value in values):
            raise SplitValidationError(f"Binary {label} contains an invalid person hash")
        if len(values) != len(set(values)):
            raise SplitValidationError(f"Binary {label} contains duplicate person hashes")
        return set(values)

    target_adaptation_set = _unique_hashes(target_adaptation, "target adaptation")
    target_evaluation_set = _unique_hashes(target_evaluation, "target evaluation")
    if target_adaptation_set & target_evaluation_set:
        raise SplitValidationError("Binary target adaptation and evaluation person hashes overlap")
    if approved_person_universe is not None:
        approved = set(approved_person_universe)
        if target_adaptation_set | target_evaluation_set != approved:
            raise SplitValidationError("Binary target split does not match the approved person universe")
    if len(source_folds) != n_splits:
        raise SplitValidationError(f"Binary source split must contain exactly {n_splits} folds")
    seen_validation: set[str] = set()
    expected_source: set[str] | None = None
    for index, fold in enumerate(source_folds):
        if any(fold.get(key) != value for key, value in expected.items()) or fold.get("fold") != index:
            raise SplitValidationError("Binary source fold has incompatible historical three-class task identity or class order")
        if fold.get("n_splits") != n_splits or fold.get("seed") != seed or fold.get("splitter") != "StratifiedKFold" or fold.get("shuffle") is not True or fold.get("random_state") != seed:
            raise SplitValidationError("Binary source folds must use StratifiedKFold(5, shuffle=True, random_state=42)")
        train = _unique_hashes(fold.get("source_train", ()), "source train")
        validation = _unique_hashes(fold.get("source_validation", ()), "source validation")
        if not train or not validation or train & validation:
            raise SplitValidationError("Binary source fold partitions are invalid")
        if expected_source is None:
            expected_source = train | validation
        if train | validation != expected_source:
            raise SplitValidationError("Binary source fold subject hashes are inconsistent")
        if seen_validation & validation:
            raise SplitValidationError("Binary source validation folds overlap")
        seen_validation.update(validation)
        if fold.get("split_identity") != _binary_split_hash({key: value for key, value in fold.items() if key != "split_identity"}):
            raise SplitValidationError("Binary source split identity hash is invalid")
    if expected_source != seen_validation:
        raise SplitValidationError("Every binary source subject must validate exactly once")
    if target_partition.get("split_identity") != _binary_split_hash({key: value for key, value in target_partition.items() if key != "split_identity"}):
        raise SplitValidationError("Binary target split identity hash is invalid")


@dataclass
class SplitResult:
    direction: Direction
    source_folds: pd.DataFrame
    target_split: pd.DataFrame
    protocol: dict[str, Any]
    reused: bool = False
    dry_run: bool = False


def load_split_config(path: str | Path) -> SplitRunConfig:
    config_path = Path(path).resolve()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    base = config_path.parent
    split_payload = payload.get("splits") or {}
    directions = [Direction(str(item["source"]).upper(), str(item["target"]).upper()) for item in payload.get("directions", [])]
    paths = payload.get("paths") or {}
    return SplitRunConfig(
        splits=SplitConfig(**{key: value for key, value in split_payload.items() if key in SplitConfig.__dataclass_fields__}),
        directions=directions or [Direction("ADNI", "OASIS"), Direction("OASIS", "ADNI")],
        artifact_index=resolve_path(paths.get("artifact_index"), base),
        artifact_root=resolve_path(paths.get("artifact_root"), base),
        split_root=resolve_path(paths.get("split_root"), base),
        config_path=config_path,
    )


def _record_row(record: SubjectRecord) -> dict[str, Any]:
    return {
        "subject_hash": record.subject_hash,
        "subject_id": record.subject_id,
        "cohort": record.cohort,
        "class_label": record.class_label,
        "label_index": record.label_index,
        "derivative_path": str(record.derivative_path),
        "concept_path": str(record.concept_path) if record.concept_path else None,
        "jacobian_path": str(record.jacobian_path) if record.jacobian_path else None,
    }


def generate_source_folds(records: Iterable[SubjectRecord], config: SplitConfig) -> pd.DataFrame:
    ordered = sorted(records, key=lambda record: record.identity)
    if not ordered:
        raise SplitValidationError("Source cohort has no records.")
    labels = np.asarray([record.class_label for record in ordered])
    counts = pd.Series(labels).value_counts().to_dict()
    missing = set(CLASS_TO_INDEX).difference(counts)
    if missing:
        raise SplitValidationError(f"Source cohort is missing classes: {sorted(missing)}.")
    if min(counts.values()) < config.n_splits:
        raise SplitValidationError(f"n_splits={config.n_splits} exceeds smallest source class count: {counts}.")
    splitter = StratifiedKFold(n_splits=config.n_splits, shuffle=True, random_state=config.seed)
    rows = []
    for fold, (train_indices, validation_indices) in enumerate(splitter.split(np.arange(len(ordered)), labels)):
        partitions = [(train_indices, "source_train"), (validation_indices, "source_validation")]
        for indices, partition in partitions:
            for index in sorted(indices, key=lambda value: ordered[value].identity):
                rows.append({**_record_row(ordered[index]), "fold": fold, "partition": partition})
    return pd.DataFrame(rows)


def generate_target_split(records: Iterable[SubjectRecord], config: SplitConfig) -> pd.DataFrame:
    ordered = sorted(records, key=lambda record: record.identity)
    if not ordered:
        raise SplitValidationError("Target cohort has no records.")
    labels = np.asarray([record.class_label for record in ordered])
    counts = pd.Series(labels).value_counts().to_dict()
    missing = set(CLASS_TO_INDEX).difference(counts)
    if missing:
        raise SplitValidationError(f"Target cohort is missing classes: {sorted(missing)}.")
    indices = np.arange(len(ordered))
    adaptation, evaluation = train_test_split(
        indices,
        train_size=config.target_adaptation_fraction,
        stratify=labels,
        random_state=config.seed,
        shuffle=True,
    )
    rows = []
    for selected, partition in ((adaptation, "target_adaptation"), (evaluation, "target_evaluation")):
        for index in sorted(selected, key=lambda value: ordered[value].identity):
            rows.append({**_record_row(ordered[index]), "partition": partition})
    return pd.DataFrame(rows)


def assignment_hash(source_folds: pd.DataFrame, target_split: pd.DataFrame) -> str:
    source_columns = ["cohort", "subject_hash", "class_label", "fold", "partition"]
    target_columns = ["cohort", "subject_hash", "class_label", "partition"]
    assignments = [
        source_folds[source_columns].sort_values(source_columns).to_dict("records"),
        target_split[target_columns].sort_values(target_columns).to_dict("records"),
    ]
    return hashlib.sha256(json.dumps(assignments, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_split_assignments(source_folds: pd.DataFrame, target_split: pd.DataFrame, n_splits: int) -> None:
    def source_id(frame: pd.DataFrame) -> set[tuple[str, str]]:
        return set(zip(frame["cohort"], frame["subject_hash"], strict=True))
    folds = sorted(source_folds["fold"].unique().tolist())
    if folds != list(range(n_splits)):
        raise SplitValidationError(f"Expected folds 0..{n_splits - 1}, got {folds}.")
    validation_counts: dict[tuple[str, str], int] = {}
    expected_source = source_id(source_folds)
    for fold in folds:
        current = source_folds[source_folds["fold"] == fold]
        train = source_id(current[current["partition"] == "source_train"])
        validation = source_id(current[current["partition"] == "source_validation"])
        if train & validation or train | validation != expected_source:
            raise SplitValidationError(f"Invalid source partition integrity in fold {fold}.")
        for identity in validation:
            validation_counts[identity] = validation_counts.get(identity, 0) + 1
    if set(validation_counts) != expected_source or set(validation_counts.values()) != {1}:
        raise SplitValidationError("Every source subject must appear in validation exactly once.")
    adaptation = source_id(target_split[target_split["partition"] == "target_adaptation"])
    evaluation = source_id(target_split[target_split["partition"] == "target_evaluation"])
    if adaptation & evaluation or adaptation | evaluation != source_id(target_split):
        raise SplitValidationError("Invalid target adaptation/evaluation partition integrity.")
    conflicting = pd.concat([source_folds.drop_duplicates(["cohort", "subject_hash"]), target_split]).groupby(["cohort", "subject_hash"])["class_label"].nunique()
    if (conflicting > 1).any():
        raise SplitValidationError("A subject appears under conflicting labels.")


def _artifact_index_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or None
    except OSError:
        return None


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _manifest_protocol(direction: Direction, config: SplitConfig, index_path: Path, source: list[SubjectRecord], target: list[SubjectRecord], source_folds: pd.DataFrame, target_split: pd.DataFrame) -> dict[str, Any]:
    return {
        "source_cohort": direction.source,
        "target_cohort": direction.target,
        "input_artifact_index_path": str(index_path),
        "input_artifact_index_hash": _artifact_index_hash(index_path),
        "number_of_source_subjects": len(source),
        "number_of_target_subjects": len(target),
        "class_counts": {"source": pd.Series([r.class_label for r in source]).value_counts().sort_index().to_dict(), "target": pd.Series([r.class_label for r in target]).value_counts().sort_index().to_dict()},
        "n_splits": config.n_splits,
        "target_adaptation_fraction": config.target_adaptation_fraction,
        "target_evaluation_fraction": round(1.0 - config.target_adaptation_fraction, 10),
        "stratify_source": config.stratify_source,
        "stratify_target": config.stratify_target,
        "seed": config.seed,
        "label_mapping": CLASS_TO_INDEX,
        "configuration_hash": config.scientific_hash(direction),
        "split_assignment_hash": assignment_hash(source_folds, target_split),
        "software_version": __version__,
        "git_commit": _git_commit(),
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _validate_existing(output: Path, expected: dict[str, Any]) -> SplitResult:
    protocol_path = output / "protocol.json"
    source_path = output / "source_folds.csv"
    target_path = output / "target_split.csv"
    if not all(path.is_file() for path in (protocol_path, source_path, target_path)):
        raise SplitValidationError(f"Existing split directory is incomplete: {output}.")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for key in ("configuration_hash", "input_artifact_index_hash"):
        if protocol.get(key) != expected.get(key):
            raise SplitValidationError(f"Existing split has incompatible {key}; use --overwrite.")
    source_folds, target_split = pd.read_csv(source_path), pd.read_csv(target_path)
    actual_hash = assignment_hash(source_folds, target_split)
    if protocol.get("split_assignment_hash") != actual_hash:
        raise SplitValidationError("Existing split assignment hash is invalid.")
    direction = Direction(protocol["source_cohort"], protocol["target_cohort"])
    validate_split_assignments(source_folds, target_split, int(protocol["n_splits"]))
    return SplitResult(direction, source_folds, target_split, protocol, reused=True)


def create_direction_splits(records: Iterable[SubjectRecord], direction: Direction, config: SplitConfig, index_path: str | Path, output_root: str | Path) -> SplitResult:
    direction.validate()
    config.validate()
    all_records = list(records)
    source = [record for record in all_records if record.cohort == direction.source]
    target = [record for record in all_records if record.cohort == direction.target]
    source_folds = generate_source_folds(source, config)
    target_split = generate_target_split(target, config)
    validate_split_assignments(source_folds, target_split, config.n_splits)
    index_path = Path(index_path).resolve()
    protocol = _manifest_protocol(direction, config, index_path, source, target, source_folds, target_split)
    output = Path(output_root).resolve() / direction.name
    if output.exists() and not config.overwrite and not config.dry_run:
        return _validate_existing(output, protocol)
    result = SplitResult(direction, source_folds, target_split, protocol, dry_run=config.dry_run)
    if config.dry_run:
        return result
    output.mkdir(parents=True, exist_ok=True)
    _atomic_text(output / "source_folds.csv", source_folds.to_csv(index=False))
    _atomic_text(output / "target_split.csv", target_split.to_csv(index=False))
    counts = pd.concat([
        source_folds.groupby(["fold", "partition", "class_label"]).size().rename("count").reset_index().assign(domain="source"),
        target_split.groupby(["partition", "class_label"]).size().rename("count").reset_index().assign(domain="target", fold=""),
    ], ignore_index=True)
    _atomic_text(output / "class_counts.csv", counts.to_csv(index=False))
    _atomic_text(output / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True))
    summary = {"direction": direction.name, "source_subjects": len(source), "target_subjects": len(target), "assignment_hash": protocol["split_assignment_hash"]}
    _atomic_text(output / "split_summary.json", json.dumps(summary, indent=2, sort_keys=True))
    _atomic_text(output / "split_summary.md", f"# Split Summary\n\n- Direction: {direction.name}\n- Source subjects: {len(source)}\n- Target subjects: {len(target)}\n- Assignment hash: `{protocol['split_assignment_hash']}`\n")
    resolved = {"splits": asdict(config), "direction": asdict(direction), "paths": {"artifact_index": str(index_path), "split_root": str(Path(output_root).resolve())}}
    _atomic_text(output / "configuration_resolved.yaml", yaml.safe_dump(resolved, sort_keys=True))
    return result
