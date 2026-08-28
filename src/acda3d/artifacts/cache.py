"""Restartable Phase 5 artifact cache orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml

from acda3d import __version__
from acda3d.artifacts.atlas import AtlasConfig, AtlasROIManager, export_atlas_metadata
from acda3d.artifacts.concepts import (
    ConceptTargetConfig,
    build_subject_concept_target,
    extract_tissue_loss_proxy,
    fit_concept_normalizer,
)
from acda3d.artifacts.jacobians import JacobianConfig, compute_g_bar_from_template_and_subject
from acda3d.exceptions import ArtifactValidationError, ConfigurationError
from acda3d.paths import resolve_path


@dataclass
class PrecomputeConfig:
    expected_spatial_shape: tuple[int, int, int] = (128, 128, 128)
    expected_num_rois: int = 102
    background_label: int = 0
    compute_concepts: bool = True
    compute_jacobians: bool = True
    overwrite: bool = False
    resume: bool = True
    continue_on_error: bool = True
    dry_run: bool = False
    save_sidecars: bool = True
    save_intermediates: bool = False
    source_file_hashes: bool = False


@dataclass
class PrecomputePaths:
    manifest: Path | None = None
    atlas: Path | None = None
    template: Path | None = None
    artifact_root: Path | None = None


@dataclass
class ExecutionConfig:
    seed: int = 42
    number_of_workers: int = 1
    progress_every: int = 10


@dataclass
class PrecomputeRunConfig:
    precompute: PrecomputeConfig = field(default_factory=PrecomputeConfig)
    atlas: AtlasConfig = field(default_factory=AtlasConfig)
    concepts: ConceptTargetConfig = field(default_factory=ConceptTargetConfig)
    jacobians: JacobianConfig = field(default_factory=JacobianConfig)
    paths: PrecomputePaths = field(default_factory=PrecomputePaths)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    config_path: Path | None = None

    def validate(self) -> None:
        if not all((self.paths.manifest, self.paths.atlas, self.paths.artifact_root)):
            raise ConfigurationError("manifest, prepared atlas and artifact_root are required.")
        if self.precompute.compute_jacobians and self.paths.template is None:
            raise ConfigurationError("Jacobian computation requires an explicit template path.")
        if self.execution.number_of_workers != 1:
            raise ConfigurationError("Phase 5 canonical Jacobian execution requires number_of_workers=1.")
        if self.precompute.expected_num_rois <= 0 or len(self.precompute.expected_spatial_shape) != 3:
            raise ConfigurationError("Expected ROI count and spatial shape must be positive.")

    def to_dict(self) -> dict[str, Any]:
        def clean(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, tuple):
                return list(value)
            if hasattr(value, "__dataclass_fields__"):
                return clean(asdict(value))
            if isinstance(value, dict):
                return {key: clean(item) for key, item in value.items()}
            return value

        return clean({"precompute": self.precompute, "atlas": self.atlas, "concepts": self.concepts, "jacobians": self.jacobians, "paths": self.paths, "execution": self.execution})

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def artifact_sha256(self, branch: str) -> str:
        if branch not in {"concept", "jacobian"}:
            raise ValueError(f"Unknown artifact branch: {branch}.")
        scientific = {
            "expected_spatial_shape": self.precompute.expected_spatial_shape,
            "expected_num_rois": self.precompute.expected_num_rois,
            "background_label": self.precompute.background_label,
            "atlas": asdict(self.atlas),
            branch: asdict(self.concepts if branch == "concept" else self.jacobians),
        }
        payload = json.dumps(scientific, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def load_precompute_config(path: str | Path) -> PrecomputeRunConfig:
    config_path = Path(path).resolve()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    base = config_path.parent
    precompute = dict(payload.get("precompute") or {})
    if "expected_spatial_shape" in precompute:
        precompute["expected_spatial_shape"] = tuple(int(value) for value in precompute["expected_spatial_shape"])
    atlas_payload = dict(payload.get("atlas") or {})
    paths_payload = dict(payload.get("paths") or {})
    data_payload = dict(payload.get("data") or {})
    config = PrecomputeRunConfig(
        precompute=PrecomputeConfig(**{key: value for key, value in precompute.items() if key in PrecomputeConfig.__dataclass_fields__}),
        atlas=AtlasConfig(**{key: value for key, value in atlas_payload.items() if key in AtlasConfig.__dataclass_fields__}),
        concepts=ConceptTargetConfig(**{key: value for key, value in (payload.get("concepts") or {}).items() if key in ConceptTargetConfig.__dataclass_fields__}),
        jacobians=JacobianConfig(**{key: value for key, value in (payload.get("jacobians") or {}).items() if key in JacobianConfig.__dataclass_fields__}),
        paths=PrecomputePaths(
            manifest=resolve_path(data_payload.get("preprocessing_manifest") or paths_payload.get("manifest"), base),
            atlas=resolve_path(atlas_payload.get("prepared_path") or paths_payload.get("atlas"), base),
            template=resolve_path((payload.get("jacobians") or {}).get("template_path") or paths_payload.get("template"), base),
            artifact_root=resolve_path(paths_payload.get("artifact_root"), base),
        ),
        execution=ExecutionConfig(**{key: value for key, value in (payload.get("execution") or {}).items() if key in ExecutionConfig.__dataclass_fields__}),
        config_path=config_path,
    )
    return config


def _hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()


def _safe_id(value: Any) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(value)).strip("_")
    if not cleaned:
        raise ArtifactValidationError("Subject identifier is empty after sanitization.")
    return cleaned


def load_inventory(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["inventory_row"] = np.arange(len(frame), dtype=int)
    aliases = {"output_path": "derivative_path", "x_path": "derivative_path", "label": "class_label"}
    for source, target in aliases.items():
        if target not in frame and source in frame:
            frame[target] = frame[source]
    if "subject_hash" not in frame and "subject_id" in frame:
        frame["subject_hash"] = frame["subject_id"].astype(str).map(lambda value: hashlib.sha256(value.encode()).hexdigest()[:16])
    required = {"subject_hash", "cohort", "class_label", "derivative_path"}
    missing = required.difference(frame.columns)
    if missing:
        raise ArtifactValidationError(f"Inventory is missing columns: {sorted(missing)}.")
    identity = "subject_id" if "subject_id" in frame else "subject_hash"
    if frame[identity].astype(str).duplicated().any():
        raise ArtifactValidationError("Inventory contains duplicate subjects.")
    resolved = frame["derivative_path"].map(lambda value: str(Path(value).resolve()))
    if resolved.duplicated().any():
        raise ArtifactValidationError("Inventory contains duplicate derivative paths.")
    frame["derivative_path"] = resolved
    return frame.sort_values(["cohort", identity], kind="stable").reset_index(drop=True)


def load_model_ready_tensor(path: str | Path, expected_shape: tuple[int, int, int]) -> torch.Tensor:
    obj = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(obj, dict):
        matches = [obj[key] for key in ("x", "image", "mri", "tensor", "volume") if key in obj]
        if not matches:
            raise ArtifactValidationError(f"Unsupported serialized MRI dictionary at {path}.")
        obj = matches[0]
    if not torch.is_tensor(obj):
        raise ArtifactValidationError(f"Unsupported serialized MRI object at {path}: {type(obj).__name__}.")
    if obj.device.type != "cpu" or obj.dtype != torch.float32 or tuple(obj.shape) != (1, *expected_shape) or not torch.isfinite(obj).all():
        raise ArtifactValidationError(f"MRI tensor at {path} must be CPU float32 with shape {(1, *expected_shape)} and finite values; got {obj.device}, {obj.dtype}, {tuple(obj.shape)}.")
    return obj.contiguous()


def _atomic_tensor(path: Path, tensor: torch.Tensor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    torch.save(tensor.detach().cpu().float().contiguous(), temporary)
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _validate_cached(path: Path, sidecar: Path, key: str, expected_k: int, config_hash: str, atlas_hash: str, derivative_path: str) -> tuple[bool, str | None]:
    if not path.exists() or not sidecar.exists():
        return False, "missing"
    try:
        tensor = torch.load(path, map_location="cpu", weights_only=True)
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        valid = torch.is_tensor(tensor) and tensor.dtype == torch.float32 and tuple(tensor.shape) == (expected_k,) and bool(torch.isfinite(tensor).all())
        valid = valid and metadata.get("precompute_configuration_hash") == config_hash and metadata.get("atlas_hash") == atlas_hash and metadata.get("derivative_path") == derivative_path and metadata.get("artifact_type") == key
        return (True, None) if valid else (False, "incompatible")
    except (OSError, ValueError, RuntimeError, pickle.UnpicklingError, json.JSONDecodeError):
        return False, "corrupt"


def _sidecar(row: pd.Series, artifact_type: str, tensor: torch.Tensor, manager: AtlasROIManager, config: PrecomputeRunConfig, runtime: float, normalizer_hash: str | None = None) -> dict[str, Any]:
    derivative = Path(row["derivative_path"])
    return {
        "safe_subject_id": _safe_id(row.get("subject_id", row["subject_hash"])), "cohort": row["cohort"], "class_label": row["class_label"],
        "derivative_path": str(derivative), "derivative_file_size": derivative.stat().st_size, "derivative_modified_time": derivative.stat().st_mtime,
        "derivative_hash": _hash_file(derivative) if config.precompute.source_file_hashes else None,
        "preprocessing_configuration_hash": row.get("preprocessing_configuration_hash", row.get("configuration_hash")),
        "atlas_path": manager.atlas_path, "atlas_hash": manager.atlas_hash, "roi_label_ordering": manager.label_values,
        "artifact_type": artifact_type, "artifact_shape": list(tensor.shape), "artifact_dtype": str(tensor.dtype),
        "artifact_statistics": {"minimum": float(tensor.min()), "maximum": float(tensor.max()), "mean": float(tensor.mean()), "standard_deviation": float(tensor.std(unbiased=False)), "finite": bool(torch.isfinite(tensor).all())},
        "concept_normalizer_hash": normalizer_hash, "jacobian_configuration": asdict(config.jacobians) if artifact_type == "jacobian" else None,
        "precompute_configuration_hash": config.sha256(), "software_version": __version__, "git_commit": _git_commit(), "runtime_seconds": runtime, "status": "complete", "warnings": [], "errors": [],
    }


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or None
    except OSError:
        return None


def ensure_artifact_cache(config: PrecomputeRunConfig, *, subjects: set[str] | None = None, cohorts: set[str] | None = None, limit: int | None = None) -> pd.DataFrame:
    config.validate()
    assert config.paths.manifest and config.paths.atlas and config.paths.artifact_root
    frame = load_inventory(config.paths.manifest)
    identity = "subject_id" if "subject_id" in frame else "subject_hash"
    if subjects:
        frame = frame[frame[identity].astype(str).isin(subjects)]
    if cohorts:
        frame = frame[frame["cohort"].astype(str).isin(cohorts)]
    if limit is not None:
        frame = frame.head(limit)
    if frame.empty:
        raise ArtifactValidationError("No subjects remain after inventory filtering.")
    manager = AtlasROIManager(config.paths.atlas, AtlasConfig(expected_num_rois=config.precompute.expected_num_rois, drop_background=True, min_voxels_per_roi=config.atlas.min_voxels_per_roi, eps=config.atlas.eps, label_values=config.atlas.label_values))
    if manager.shape != config.precompute.expected_spatial_shape:
        raise ArtifactValidationError(f"Atlas grid {manager.shape} does not match configured MRI grid {config.precompute.expected_spatial_shape}.")
    root = config.paths.artifact_root
    config_hash = config.sha256()
    concept_hash = config.artifact_sha256("concept")
    jacobian_hash = config.artifact_sha256("jacobian")
    inventory_hash = _inventory_hash(frame)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    normalizers: dict[str, Any] = {}
    features: dict[int, np.ndarray] = {}
    for cohort, cohort_frame in frame.groupby("cohort", sort=True):
        if config.precompute.compute_concepts:
            cohort_features, cohort_labels = [], []
            for index, row in cohort_frame.iterrows():
                try:
                    tensor = load_model_ready_tensor(row["derivative_path"], config.precompute.expected_spatial_shape)
                    feature = extract_tissue_loss_proxy(tensor, manager, config.concepts)
                    features[index] = feature
                    cohort_features.append(feature)
                    cohort_labels.append(row["class_label"])
                except (OSError, ValueError, RuntimeError) as error:
                    failures.append({"inventory_row": row["inventory_row"], "subject": row[identity], "branch": "concept_proxy", "error": str(error)})
                    if not config.precompute.continue_on_error:
                        raise
            if cohort_features:
                normalizers[str(cohort)] = fit_concept_normalizer(np.stack(cohort_features), cohort_labels, config.concepts.normal_class_name, config.concepts.eps, roi_labels=manager.label_values, cohorts=[str(cohort)] * len(cohort_features), configuration_hash=concept_hash, inventory_hash=inventory_hash)
    if config.precompute.dry_run:
        for _, row in frame.iterrows():
            safe = _safe_id(row[identity])
            rows.append({"subject_hash": row["subject_hash"], "subject_id": row.get("subject_id"), "cohort": row["cohort"], "class_label": row["class_label"], "derivative_path": row["derivative_path"], "concept_path": f"concepts/subjects/{safe}.pt", "jacobian_path": f"jacobians/subjects/{safe}.pt", "concept_status": "PLANNED" if config.precompute.compute_concepts else "DISABLED", "jacobian_status": "PLANNED" if config.precompute.compute_jacobians else "DISABLED", "inventory_row": row["inventory_row"]})
        _write_reports(root, config, manager, rows, failures, dry_run=True)
        return pd.DataFrame(rows)
    export_atlas_metadata(manager, root / "atlas")
    for cohort, normalizer in normalizers.items():
        normalizer.save(root / "concepts" / "normalizers" / f"{_safe_id(cohort)}.json")
    template = load_model_ready_tensor(config.paths.template, config.precompute.expected_spatial_shape)[0].numpy() if config.precompute.compute_jacobians and config.paths.template else None
    for index, row in frame.iterrows():
        started = time.perf_counter()
        safe = _safe_id(row[identity])
        concept_path, jacobian_path = root / "concepts" / "subjects" / f"{safe}.pt", root / "jacobians" / "subjects" / f"{safe}.pt"
        concept_sidecar, jacobian_sidecar = root / "sidecars" / f"{safe}.concept.json", root / "sidecars" / f"{safe}.jacobian.json"
        record = {"subject_hash": row["subject_hash"], "subject_id": row.get("subject_id"), "cohort": row["cohort"], "class_label": row["class_label"], "derivative_path": row["derivative_path"], "concept_path": str(concept_path.relative_to(root)), "jacobian_path": str(jacobian_path.relative_to(root)), "concept_status": "DISABLED", "jacobian_status": "DISABLED", "atlas_configuration_hash": manager.atlas_hash, "preprocessing_configuration_hash": row.get("preprocessing_configuration_hash", row.get("configuration_hash")), "precompute_configuration_hash": config_hash, "concept_configuration_hash": concept_hash, "jacobian_configuration_hash": jacobian_hash, "concept_vector_shape": None, "jacobian_vector_shape": None, "inventory_row": row["inventory_row"], "warnings": "", "errors": ""}
        try:
            tensor = load_model_ready_tensor(row["derivative_path"], config.precompute.expected_spatial_shape)
            if config.precompute.compute_concepts and index in features:
                valid, reason = _validate_cached(concept_path, concept_sidecar, "concept", manager.K, concept_hash, manager.atlas_hash, row["derivative_path"])
                if valid and config.precompute.resume and not config.precompute.overwrite:
                    record["concept_status"] = "SKIPPED_VALID"
                elif concept_path.exists() and not config.precompute.overwrite:
                    record["concept_status"] = f"INVALID_EXISTING_{reason}"
                    record["errors"] = f"Concept artifact is {reason}; use --overwrite."
                else:
                    normalizer = normalizers[str(row["cohort"])]
                    vector = build_subject_concept_target(tensor, manager, normalizer, config.concepts)
                    _atomic_tensor(concept_path, vector)
                    concept_metadata = _sidecar(row, "concept", vector, manager, config, time.perf_counter() - started, hashlib.sha256(json.dumps(normalizer.to_dict(), sort_keys=True).encode()).hexdigest())
                    concept_metadata["precompute_configuration_hash"] = concept_hash
                    _atomic_json(concept_sidecar, concept_metadata)
                    record["concept_status"], record["concept_vector_shape"] = "COMPUTED", json.dumps(list(vector.shape))
            if config.precompute.compute_jacobians and template is not None:
                valid, reason = _validate_cached(jacobian_path, jacobian_sidecar, "jacobian", manager.K, jacobian_hash, manager.atlas_hash, row["derivative_path"])
                if valid and config.precompute.resume and not config.precompute.overwrite:
                    record["jacobian_status"] = "SKIPPED_VALID"
                elif jacobian_path.exists() and not config.precompute.overwrite:
                    record["jacobian_status"] = f"INVALID_EXISTING_{reason}"
                    record["errors"] = (record["errors"] + " | " if record["errors"] else "") + f"Jacobian artifact is {reason}; use --overwrite."
                else:
                    branch_start = time.perf_counter()
                    vector = compute_g_bar_from_template_and_subject(template, tensor[0].numpy(), manager, config.jacobians)
                    _atomic_tensor(jacobian_path, vector)
                    jacobian_metadata = _sidecar(row, "jacobian", vector, manager, config, time.perf_counter() - branch_start)
                    jacobian_metadata["precompute_configuration_hash"] = jacobian_hash
                    _atomic_json(jacobian_sidecar, jacobian_metadata)
                    record["jacobian_status"], record["jacobian_vector_shape"] = "COMPUTED", json.dumps(list(vector.shape))
        except (OSError, ValueError, RuntimeError) as error:
            record["errors"] = str(error)
            failures.append({"inventory_row": row["inventory_row"], "subject": row[identity], "branch": "subject", "error": str(error)})
            if not config.precompute.continue_on_error:
                rows.append(record)
                break
        record["runtime_seconds"] = time.perf_counter() - started
        rows.append(record)
    _write_reports(root, config, manager, rows, failures, dry_run=False)
    return pd.DataFrame(rows)


def _write_reports(root: Path, config: PrecomputeRunConfig, manager: AtlasROIManager, rows: list[dict[str, Any]], failures: list[dict[str, Any]], *, dry_run: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(root / ("dry_run_plan.csv" if dry_run else "artifact_index.csv"), index=False)
    pd.DataFrame(failures, columns=["inventory_row", "subject", "branch", "error"]).to_csv(root / "failures.csv", index=False)
    skipped = [row for row in rows if "SKIPPED" in str(row.get("concept_status")) or "SKIPPED" in str(row.get("jacobian_status"))]
    pd.DataFrame(skipped).to_csv(root / "skipped.csv", index=False)
    summary = {"dry_run": dry_run, "subjects": len(rows), "failures": len(failures), "K": manager.K, "atlas_hash": manager.atlas_hash, "precompute_configuration_hash": config.sha256()}
    _atomic_json(root / "artifact_summary.json", summary)
    (root / "artifact_summary.md").write_text(f"# Artifact Summary\n\n- Dry run: {dry_run}\n- Subjects: {len(rows)}\n- Failures: {len(failures)}\n- ROIs: {manager.K}\n", encoding="utf-8")
    (root / "configuration_resolved.yaml").write_text(yaml.safe_dump(config.to_dict(), sort_keys=True), encoding="utf-8")
    _atomic_json(root / "precompute_metadata.json", {"canonical_source": "notebooks/archive/precompute_original.ipynb", "software_version": __version__, "no_atlas_resampling": True, "model_ready_derivatives_modified": False})


def load_precomputed_artifacts(root: str | Path) -> pd.DataFrame:
    path = Path(root) / "artifact_index.csv"
    if not path.is_file():
        raise ArtifactValidationError(f"Artifact index does not exist: {path}.")
    return pd.read_csv(path)


build_all_precomputed_artifacts = ensure_artifact_cache
