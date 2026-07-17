"""Read-only verification of existing MRI derivatives and atlas geometry."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import pandas as pd
import torch
import yaml
from nibabel.orientations import aff2axcodes

from pada3dacb.exceptions import ConfigurationError, InvalidPathError
from pada3dacb.paths import ensure_directory, resolve_path


class VerificationStatus(StrEnum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    INSUFFICIENT_METADATA = "INSUFFICIENT_METADATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


_RANK = {
    VerificationStatus.FAILED: 4,
    VerificationStatus.WARNING: 3,
    VerificationStatus.INSUFFICIENT_METADATA: 2,
    VerificationStatus.PASSED: 1,
    VerificationStatus.NOT_APPLICABLE: 0,
}


@dataclass
class VerificationConfig:
    expected_spatial_shape: tuple[int, int, int] | None = None
    expected_channels: tuple[int, ...] = (1,)
    expected_num_rois: int | None = 102
    allowed_formats: tuple[str, ...] = (".nii", ".nii.gz", ".mnc", ".pt", ".npy", ".npz")
    supported_tensor_keys: tuple[str, ...] = ("image", "mri", "x", "volume", "tensor")
    background_label: float = 0.0
    affine_atol: float = 1e-3
    spacing_atol: float = 1e-3
    bounding_box_atol: float = 1e-2
    finite_fraction_min: float = 1.0
    nonzero_fraction_min: float = 0.001
    extreme_abs_value_warning: float | None = 1_000_000.0
    strict_physical_geometry: bool = False
    compute_world_bounding_boxes: bool = True
    compute_file_hashes: bool = False
    generate_overlays: bool = True
    overlay_sample_size: int = 30
    overlay_seed: int = 42
    overlay_slices_per_axis: int = 3
    overwrite_reports: bool = False
    fail_on_subject_failure: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> VerificationConfig:
        blocked = ["registration", "resampling", "interpolation", "skull_stripping", "normalization"]
        enabled = [name for name in blocked if data.get(name) is True]
        if enabled:
            raise ConfigurationError(
                "Phase 3 verification cannot enable prohibited operations: " + ", ".join(enabled)
            )
        cleaned = dict(data)
        if cleaned.get("expected_spatial_shape") is not None:
            cleaned["expected_spatial_shape"] = tuple(cleaned["expected_spatial_shape"])
        for key in ("expected_channels", "allowed_formats", "supported_tensor_keys"):
            if key in cleaned and cleaned[key] is not None:
                cleaned[key] = tuple(cleaned[key])
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in cleaned.items() if k in fields})


@dataclass
class NumericalSummary:
    finite_fraction: float = 0.0
    nonzero_fraction: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    standard_deviation: float | None = None
    has_nan: bool = False
    has_posinf: bool = False
    has_neginf: bool = False
    is_constant: bool = False
    warning_messages: list[str] = field(default_factory=list)
    failure_messages: list[str] = field(default_factory=list)


@dataclass
class ImageMetadata:
    path: str
    file_format: str
    object_type: str | None = None
    selected_key: str | None = None
    shape: tuple[int, ...] | None = None
    spatial_shape: tuple[int, int, int] | None = None
    channel_shape: tuple[int, ...] | None = None
    dtype: str | None = None
    affine: list[list[float]] | None = None
    spacing: tuple[float, float, float] | None = None
    orientation: tuple[str, str, str] | None = None
    determinant: float | None = None
    world_bounding_box: list[list[float]] | None = None
    numerical: NumericalSummary = field(default_factory=NumericalSummary)
    tensor_contract_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    numerical_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    warning_messages: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)


@dataclass
class AtlasMetadata:
    path: str
    file_format: str
    shape: tuple[int, int, int] | None = None
    dtype: str | None = None
    affine: list[list[float]] | None = None
    spacing: tuple[float, float, float] | None = None
    orientation: tuple[str, str, str] | None = None
    determinant: float | None = None
    world_bounding_box: list[list[float]] | None = None
    labels: list[float] = field(default_factory=list)
    non_background_labels: list[float] = field(default_factory=list)
    atlas_integrity_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    warning_messages: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)


@dataclass
class GeometryComparison:
    shape_match: bool | None = None
    spacing_match: bool | None = None
    orientation_match: bool | None = None
    affine_match: bool | None = None
    bounding_box_match: bool | None = None
    determinant_sign_match: bool | None = None
    physical_geometry_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    array_grid_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    warning_messages: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    row_number: int
    subject_hash: str
    cohort: str | None
    class_label: str | None
    derivative_path: str
    metadata: ImageMetadata
    geometry: GeometryComparison
    atlas_integrity_status: VerificationStatus
    overlay_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    overall_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def status_aggregate(statuses: list[VerificationStatus]) -> VerificationStatus:
    """Aggregate component statuses without collapsing metadata limitations."""
    useful = [status for status in statuses if status != VerificationStatus.NOT_APPLICABLE]
    if not useful:
        return VerificationStatus.NOT_APPLICABLE
    return max(useful, key=lambda status: _RANK[status])


def load_verification_config(path: str | Path) -> tuple[VerificationConfig, dict[str, Path | None]]:
    config_path = Path(path).expanduser().resolve(strict=False)
    with config_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("Verification configuration must be a mapping.")
    cfg = VerificationConfig.from_mapping(payload.get("verification") or {})
    paths = payload.get("paths") or {}
    return cfg, {
        "inventory_csv": resolve_path(paths.get("inventory_csv"), config_path.parent),
        "atlas_path": resolve_path(paths.get("atlas_path"), config_path.parent),
        "output_dir": resolve_path(paths.get("output_dir"), config_path.parent),
    }


def safe_subject_hash(value: str, row_number: int) -> str:
    raw = value if value else f"row-{row_number}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def file_format(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nii.gz"):
        return ".nii.gz"
    return path.suffix.lower()


def numerical_summary(array: np.ndarray, cfg: VerificationConfig) -> tuple[NumericalSummary, VerificationStatus]:
    arr = np.asarray(array)
    finite = np.isfinite(arr)
    total = int(arr.size)
    summary = NumericalSummary()
    if total == 0:
        summary.failure_messages.append("Array is empty.")
        return summary, VerificationStatus.FAILED
    summary.has_nan = bool(np.isnan(arr).any())
    summary.has_posinf = bool(np.isposinf(arr).any())
    summary.has_neginf = bool(np.isneginf(arr).any())
    summary.finite_fraction = float(finite.mean())
    finite_values = arr[finite]
    if finite_values.size:
        summary.minimum = float(np.min(finite_values))
        summary.maximum = float(np.max(finite_values))
        summary.mean = float(np.mean(finite_values))
        summary.standard_deviation = float(np.std(finite_values))
        summary.nonzero_fraction = float(np.count_nonzero(finite_values) / total)
        summary.is_constant = bool(np.all(finite_values == finite_values.flat[0]))
    if summary.finite_fraction < cfg.finite_fraction_min or summary.has_nan or summary.has_posinf or summary.has_neginf:
        summary.failure_messages.append("Array contains non-finite values.")
    if summary.nonzero_fraction < cfg.nonzero_fraction_min:
        summary.warning_messages.append("Nonzero voxel fraction is below configured threshold.")
    if summary.is_constant:
        summary.warning_messages.append("Array is constant over finite voxels.")
    if (
        cfg.extreme_abs_value_warning is not None
        and summary.maximum is not None
        and max(abs(summary.minimum or 0.0), abs(summary.maximum)) > cfg.extreme_abs_value_warning
    ):
        summary.warning_messages.append("Array contains extreme finite values.")
    if summary.failure_messages:
        status = VerificationStatus.FAILED
    elif summary.warning_messages:
        status = VerificationStatus.WARNING
    else:
        status = VerificationStatus.PASSED
    return summary, status


def affine_diagnostics(affine: np.ndarray | None) -> tuple[VerificationStatus, list[str], float | None]:
    if affine is None:
        return VerificationStatus.INSUFFICIENT_METADATA, ["Affine metadata are unavailable."], None
    failures = []
    arr = np.asarray(affine, dtype=float)
    if arr.shape != (4, 4):
        failures.append("Affine is not 4x4.")
    if not np.isfinite(arr).all():
        failures.append("Affine contains non-finite values.")
    if arr.shape == (4, 4) and not np.allclose(arr[3], [0, 0, 0, 1]):
        failures.append("Affine final row is not homogeneous [0, 0, 0, 1].")
    det = None
    if arr.shape == (4, 4) and np.isfinite(arr[:3, :3]).all():
        det = float(np.linalg.det(arr[:3, :3]))
        if not np.isfinite(det) or abs(det) < 1e-12:
            failures.append("Affine spatial transform is singular or invalid.")
    if failures:
        return VerificationStatus.FAILED, failures, det
    return VerificationStatus.PASSED, [], det


def world_bounding_box(spatial_shape: tuple[int, int, int], affine: list[list[float]] | None) -> list[list[float]] | None:
    if affine is None:
        return None
    aff = np.asarray(affine, dtype=float)
    corners = np.array(np.meshgrid(*[(0, dim - 1) for dim in spatial_shape], indexing="ij")).reshape(3, -1).T
    hom = np.c_[corners, np.ones(corners.shape[0])]
    world = (aff @ hom.T).T[:, :3]
    return [np.min(world, axis=0).tolist(), np.max(world, axis=0).tolist()]


def _nib_metadata(path: Path, cfg: VerificationConfig) -> tuple[ImageMetadata, np.ndarray]:
    img = nib.load(str(path))
    data = np.asanyarray(img.dataobj)
    affine = np.asarray(img.affine, dtype=float)
    fmt = file_format(path)
    meta = ImageMetadata(path=str(path), file_format=fmt, object_type=type(img).__name__)
    meta.shape = tuple(int(v) for v in data.shape)
    meta.spatial_shape = tuple(int(v) for v in data.shape[:3])
    meta.channel_shape = tuple(int(v) for v in data.shape[3:]) if data.ndim > 3 else None
    meta.dtype = str(data.dtype)
    meta.affine = affine.tolist()
    meta.spacing = tuple(float(v) for v in img.header.get_zooms()[:3])
    meta.orientation = tuple(str(v) for v in aff2axcodes(affine))
    aff_status, aff_messages, det = affine_diagnostics(affine)
    meta.determinant = det
    if aff_status == VerificationStatus.FAILED:
        meta.error_messages.extend(aff_messages)
    if cfg.compute_world_bounding_boxes and meta.spatial_shape is not None and aff_status == VerificationStatus.PASSED:
        meta.world_bounding_box = world_bounding_box(meta.spatial_shape, meta.affine)
    meta.numerical, meta.numerical_status = numerical_summary(data, cfg)
    meta.warning_messages.extend(meta.numerical.warning_messages)
    meta.error_messages.extend(meta.numerical.failure_messages)
    meta.tensor_contract_status = tensor_contract_status(meta, cfg)
    return meta, data


def _tensor_from_object(obj: Any, cfg: VerificationConfig) -> tuple[torch.Tensor | None, str | None, list[str]]:
    if torch.is_tensor(obj):
        return obj.detach().cpu(), None, []
    if isinstance(obj, dict):
        for key in cfg.supported_tensor_keys:
            if key in obj:
                value = obj[key]
                if torch.is_tensor(value):
                    return value.detach().cpu(), key, []
                return None, key, [f"Supported key {key!r} did not contain a tensor."]
        return None, None, ["Dictionary does not contain a supported tensor key."]
    return None, None, [f"Unsupported .pt object type: {type(obj).__name__}."]


def _pt_metadata(path: Path, cfg: VerificationConfig) -> tuple[ImageMetadata, np.ndarray | None]:
    try:
        obj = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        obj = torch.load(path, map_location="cpu")
    tensor, selected_key, errors = _tensor_from_object(obj, cfg)
    meta = ImageMetadata(path=str(path), file_format=".pt", object_type=type(obj).__name__, selected_key=selected_key)
    if tensor is None:
        meta.error_messages.extend(errors)
        meta.tensor_contract_status = VerificationStatus.FAILED
        meta.numerical_status = VerificationStatus.NOT_APPLICABLE
        return meta, None
    arr = tensor.numpy()
    meta.shape = tuple(int(v) for v in arr.shape)
    meta.dtype = str(tensor.dtype)
    if arr.ndim == 3:
        meta.spatial_shape = tuple(int(v) for v in arr.shape)
        meta.channel_shape = None
    elif arr.ndim == 4 and arr.shape[0] in cfg.expected_channels:
        meta.channel_shape = (int(arr.shape[0]),)
        meta.spatial_shape = tuple(int(v) for v in arr.shape[1:])
        arr = arr[0]
    else:
        meta.error_messages.append("Tensor shape does not match supported 3D or channel-first 4D contracts.")
    meta.numerical, meta.numerical_status = numerical_summary(arr, cfg)
    meta.warning_messages.extend(meta.numerical.warning_messages)
    meta.error_messages.extend(meta.numerical.failure_messages)
    meta.tensor_contract_status = tensor_contract_status(meta, cfg)
    return meta, arr


def _numpy_metadata(path: Path, cfg: VerificationConfig) -> tuple[ImageMetadata, np.ndarray | None]:
    loaded = np.load(path)
    if isinstance(loaded, np.lib.npyio.NpzFile):
        if "array" not in loaded:
            meta = ImageMetadata(path=str(path), file_format=".npz", object_type="NpzFile")
            meta.error_messages.append(".npz file lacks supported key 'array'.")
            meta.tensor_contract_status = VerificationStatus.FAILED
            return meta, None
        arr = loaded["array"]
    else:
        arr = np.asarray(loaded)
    meta = ImageMetadata(path=str(path), file_format=file_format(path), object_type=type(loaded).__name__)
    meta.shape = tuple(int(v) for v in arr.shape)
    meta.dtype = str(arr.dtype)
    if arr.ndim == 3:
        meta.spatial_shape = tuple(int(v) for v in arr.shape)
    elif arr.ndim == 4 and arr.shape[0] in cfg.expected_channels:
        meta.channel_shape = (int(arr.shape[0]),)
        meta.spatial_shape = tuple(int(v) for v in arr.shape[1:])
        arr = arr[0]
    else:
        meta.error_messages.append("Array shape does not match supported 3D or channel-first 4D contracts.")
    meta.numerical, meta.numerical_status = numerical_summary(arr, cfg)
    meta.warning_messages.extend(meta.numerical.warning_messages)
    meta.error_messages.extend(meta.numerical.failure_messages)
    meta.tensor_contract_status = tensor_contract_status(meta, cfg)
    return meta, arr


def tensor_contract_status(meta: ImageMetadata, cfg: VerificationConfig) -> VerificationStatus:
    failures = []
    warnings = []
    if meta.spatial_shape is None:
        failures.append("Spatial shape could not be interpreted.")
    elif cfg.expected_spatial_shape is not None and meta.spatial_shape != cfg.expected_spatial_shape:
        failures.append("Spatial shape does not match expected shape.")
    if meta.shape is not None and np.prod(meta.shape) == 0:
        failures.append("Tensor is empty.")
    if meta.channel_shape is not None and meta.channel_shape[0] not in cfg.expected_channels:
        failures.append("Channel count is not supported.")
    if meta.numerical_status == VerificationStatus.FAILED:
        failures.append("Numerical integrity failed.")
    meta.error_messages.extend(failures)
    meta.warning_messages.extend(warnings)
    if failures:
        return VerificationStatus.FAILED
    if warnings:
        return VerificationStatus.WARNING
    return VerificationStatus.PASSED


def extract_image_metadata(path: str | Path, cfg: VerificationConfig) -> tuple[ImageMetadata, np.ndarray | None]:
    p = Path(path)
    fmt = file_format(p)
    if fmt not in cfg.allowed_formats:
        meta = ImageMetadata(path=str(p), file_format=fmt)
        meta.error_messages.append(f"Unsupported derivative format: {fmt}")
        meta.tensor_contract_status = VerificationStatus.FAILED
        return meta, None
    if not p.exists():
        meta = ImageMetadata(path=str(p), file_format=fmt)
        meta.error_messages.append("Derivative file is missing.")
        meta.tensor_contract_status = VerificationStatus.FAILED
        return meta, None
    try:
        if fmt in {".nii", ".nii.gz", ".mnc"}:
            return _nib_metadata(p, cfg)
        if fmt == ".pt":
            return _pt_metadata(p, cfg)
        if fmt in {".npy", ".npz"}:
            return _numpy_metadata(p, cfg)
    except (OSError, ValueError, RuntimeError, nib.filebasedimages.ImageFileError) as exc:
        meta = ImageMetadata(path=str(p), file_format=fmt)
        meta.error_messages.append(f"Could not read derivative: {exc}")
        meta.tensor_contract_status = VerificationStatus.FAILED
        return meta, None
    raise AssertionError("unreachable")


def validate_atlas(atlas_path: str | Path, cfg: VerificationConfig) -> tuple[AtlasMetadata, np.ndarray | None]:
    path = Path(atlas_path)
    meta = AtlasMetadata(path=str(path), file_format=file_format(path))
    if not path.exists():
        meta.error_messages.append("Atlas file is missing.")
        meta.atlas_integrity_status = VerificationStatus.FAILED
        return meta, None
    try:
        img = nib.load(str(path))
        data = np.asanyarray(img.dataobj)
        affine = np.asarray(img.affine, dtype=float)
    except (OSError, ValueError, RuntimeError, nib.filebasedimages.ImageFileError) as exc:
        meta.error_messages.append(f"Could not read atlas: {exc}")
        meta.atlas_integrity_status = VerificationStatus.FAILED
        return meta, None
    meta.shape = tuple(int(v) for v in data.shape[:3]) if data.ndim >= 3 else None
    meta.dtype = str(data.dtype)
    meta.affine = affine.tolist()
    meta.spacing = tuple(float(v) for v in img.header.get_zooms()[:3])
    meta.orientation = tuple(str(v) for v in aff2axcodes(affine))
    aff_status, aff_messages, det = affine_diagnostics(affine)
    meta.determinant = det
    if aff_status == VerificationStatus.FAILED:
        meta.error_messages.extend(aff_messages)
    if cfg.compute_world_bounding_boxes and meta.shape is not None and aff_status == VerificationStatus.PASSED:
        meta.world_bounding_box = world_bounding_box(meta.shape, meta.affine)
    if data.ndim != 3:
        meta.error_messages.append("Atlas does not have exactly three spatial dimensions.")
    if not np.isfinite(data).all():
        meta.error_messages.append("Atlas contains non-finite values.")
    if not np.allclose(data, np.round(data), atol=1e-6, equal_nan=False):
        meta.error_messages.append("Atlas labels are not integer-like.")
    finite_labels = np.unique(data[np.isfinite(data)])
    meta.labels = [float(v) for v in finite_labels.tolist()]
    meta.non_background_labels = [float(v) for v in finite_labels.tolist() if not np.isclose(v, cfg.background_label)]
    if not meta.non_background_labels:
        meta.error_messages.append("Atlas contains no non-background labels.")
    for label in meta.non_background_labels:
        if not np.any(np.isclose(data, label)):
            meta.error_messages.append(f"ROI label {label} is empty.")
    if cfg.expected_num_rois is not None and len(meta.non_background_labels) != cfg.expected_num_rois:
        meta.warning_messages.append(
            f"Atlas has {len(meta.non_background_labels)} non-background labels; expected {cfg.expected_num_rois}."
        )
    if meta.error_messages:
        meta.atlas_integrity_status = VerificationStatus.FAILED
    elif meta.warning_messages:
        meta.atlas_integrity_status = VerificationStatus.WARNING
    else:
        meta.atlas_integrity_status = VerificationStatus.PASSED
    return meta, data


def compare_geometry(image: ImageMetadata, atlas: AtlasMetadata, cfg: VerificationConfig) -> GeometryComparison:
    comp = GeometryComparison()
    comp.shape_match = image.spatial_shape == atlas.shape if image.spatial_shape and atlas.shape else None
    comp.array_grid_status = VerificationStatus.PASSED if comp.shape_match else VerificationStatus.FAILED
    if comp.shape_match is False:
        comp.error_messages.append("Image and atlas spatial shapes differ.")
    if image.affine is None or atlas.affine is None:
        comp.physical_geometry_status = VerificationStatus.INSUFFICIENT_METADATA
        comp.warning_messages.append("Physical metadata are unavailable for image or atlas.")
        return comp
    img_aff = np.asarray(image.affine, dtype=float)
    atl_aff = np.asarray(atlas.affine, dtype=float)
    img_aff_status, img_aff_messages, _ = affine_diagnostics(img_aff)
    atl_aff_status, atl_aff_messages, _ = affine_diagnostics(atl_aff)
    if img_aff_status == VerificationStatus.FAILED or atl_aff_status == VerificationStatus.FAILED:
        comp.physical_geometry_status = VerificationStatus.FAILED
        comp.error_messages.extend([f"image: {msg}" for msg in img_aff_messages])
        comp.error_messages.extend([f"atlas: {msg}" for msg in atl_aff_messages])
        return comp
    comp.affine_match = bool(np.allclose(img_aff, atl_aff, atol=cfg.affine_atol))
    comp.spacing_match = (
        bool(np.allclose(image.spacing, atlas.spacing, atol=cfg.spacing_atol))
        if image.spacing and atlas.spacing
        else None
    )
    comp.orientation_match = image.orientation == atlas.orientation if image.orientation and atlas.orientation else None
    comp.determinant_sign_match = (
        bool(np.sign(image.determinant) == np.sign(atlas.determinant))
        if image.determinant is not None and atlas.determinant is not None
        else None
    )
    comp.bounding_box_match = (
        bool(np.allclose(image.world_bounding_box, atlas.world_bounding_box, atol=cfg.bounding_box_atol))
        if image.world_bounding_box is not None and atlas.world_bounding_box is not None
        else None
    )
    failed = [
        comp.affine_match is False,
        comp.spacing_match is False,
        comp.orientation_match is False,
        comp.determinant_sign_match is False,
        comp.bounding_box_match is False and cfg.strict_physical_geometry,
    ]
    warning = comp.bounding_box_match is False and not cfg.strict_physical_geometry
    if any(failed):
        comp.physical_geometry_status = VerificationStatus.FAILED
        comp.error_messages.append("Physical geometry differs beyond configured tolerances.")
    elif warning:
        comp.physical_geometry_status = VerificationStatus.WARNING
        comp.warning_messages.append("World-space bounding boxes differ beyond configured tolerance.")
    else:
        comp.physical_geometry_status = VerificationStatus.PASSED
    return comp


def read_inventory(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise InvalidPathError(f"Inventory file does not exist: {p}")
    df = pd.read_csv(p)
    if "derivative_path" not in df.columns:
        raise ConfigurationError("Inventory must contain a derivative_path column.")
    df = df.copy()
    df["_row_number"] = np.arange(1, len(df) + 1)
    return df


def select_overlay_sample(results: list[VerificationResult], sample_size: int, seed: int) -> list[VerificationResult]:
    candidates = [r for r in results if r.geometry.array_grid_status == VerificationStatus.PASSED]
    rng = np.random.default_rng(seed)
    groups: dict[tuple[str, str], list[VerificationResult]] = defaultdict(list)
    for result in candidates:
        groups[(result.cohort or "UNKNOWN", result.class_label or "UNKNOWN")].append(result)
    ordered: list[VerificationResult] = []
    for key in sorted(groups):
        group = groups[key]
        indices = rng.permutation(len(group))
        ordered.extend(group[int(i)] for i in indices)
    return ordered[: max(sample_size, 0)]


def verify_inventory(
    inventory_csv: str | Path,
    atlas_path: str | Path,
    output_dir: str | Path,
    cfg: VerificationConfig,
    *,
    subjects: set[str] | None = None,
) -> tuple[list[VerificationResult], AtlasMetadata]:
    from pada3dacb.data.quality_control import generate_subject_overlays

    output = ensure_directory(output_dir)
    overlays_dir = ensure_directory(output / "overlays")
    atlas_meta, atlas_array = validate_atlas(atlas_path, cfg)
    if atlas_meta.atlas_integrity_status == VerificationStatus.FAILED:
        save_atlas_report(output, atlas_meta)
        raise ConfigurationError("Atlas validation failed; derivative verification cannot continue.")
    df = read_inventory(inventory_csv)
    duplicated_rows = df.duplicated().to_numpy()
    duplicated_paths = df["derivative_path"].duplicated(keep=False).to_numpy()
    results = []
    for _, row in df.iterrows():
        row_number = int(row["_row_number"])
        subject_id = str(row.get("subject_id", "") or "")
        if subjects and subject_id not in subjects:
            continue
        derivative_path = Path(str(row["derivative_path"]))
        meta, image_array = extract_image_metadata(derivative_path, cfg)
        geometry = compare_geometry(meta, atlas_meta, cfg)
        warnings = [*meta.warning_messages, *geometry.warning_messages]
        failures = [*meta.error_messages, *geometry.error_messages]
        if duplicated_rows[row_number - 1]:
            warnings.append("Duplicate inventory row detected.")
        if duplicated_paths[row_number - 1]:
            warnings.append("Duplicate derivative path detected.")
        result = VerificationResult(
            row_number=row_number,
            subject_hash=safe_subject_hash(subject_id or str(derivative_path), row_number),
            cohort=_optional_str(row.get("cohort")),
            class_label=_optional_str(row.get("class_label")),
            derivative_path=str(derivative_path),
            metadata=meta,
            geometry=geometry,
            atlas_integrity_status=atlas_meta.atlas_integrity_status,
            warnings=warnings,
            failures=failures,
        )
        result.overlay_status = VerificationStatus.NOT_APPLICABLE
        result.overall_status = status_aggregate(
            [
                result.metadata.tensor_contract_status,
                result.metadata.numerical_status,
                result.atlas_integrity_status,
                result.geometry.physical_geometry_status,
                result.geometry.array_grid_status,
            ]
        )
        result._image_array = image_array  # type: ignore[attr-defined]
        results.append(result)
    sample = select_overlay_sample(results, cfg.overlay_sample_size, cfg.overlay_seed)
    if cfg.generate_overlays and atlas_array is not None:
        sample_hashes = {r.subject_hash for r in sample}
        for result in results:
            if result.subject_hash not in sample_hashes:
                result.overlay_status = VerificationStatus.NOT_APPLICABLE
                continue
            image_array = getattr(result, "_image_array", None)
            if image_array is None or result.geometry.array_grid_status != VerificationStatus.PASSED:
                result.overlay_status = VerificationStatus.FAILED
                continue
            result.overlay_status = generate_subject_overlays(
                image_array=np.asarray(image_array),
                atlas_array=np.asarray(atlas_array),
                result=result,
                output_dir=overlays_dir,
                slices_per_axis=cfg.overlay_slices_per_axis,
            )
    for result in results:
        if hasattr(result, "_image_array"):
            delattr(result, "_image_array")
    save_reports(output, results, atlas_meta, cfg, inventory_csv, atlas_path, sample)
    return results, atlas_meta


def _optional_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value)
    return text if text else None


def _json_ready(value: Any) -> Any:
    if isinstance(value, VerificationStatus):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    return value


def result_to_row(result: VerificationResult, atlas: AtlasMetadata) -> dict[str, Any]:
    m = result.metadata
    g = result.geometry
    return {
        "subject_hash": result.subject_hash,
        "cohort": result.cohort,
        "class_label": result.class_label,
        "derivative_path": result.derivative_path,
        "file_format": m.file_format,
        "original_shape": json.dumps(m.shape),
        "spatial_shape": json.dumps(m.spatial_shape),
        "channels": json.dumps(m.channel_shape),
        "dtype": m.dtype,
        "finite_fraction": m.numerical.finite_fraction,
        "nonzero_fraction": m.numerical.nonzero_fraction,
        "minimum": m.numerical.minimum,
        "maximum": m.numerical.maximum,
        "mean": m.numerical.mean,
        "standard_deviation": m.numerical.standard_deviation,
        "image_orientation": json.dumps(m.orientation),
        "image_spacing": json.dumps(m.spacing),
        "atlas_orientation": json.dumps(atlas.orientation),
        "atlas_spacing": json.dumps(atlas.spacing),
        "shape_match": g.shape_match,
        "spacing_match": g.spacing_match,
        "orientation_match": g.orientation_match,
        "affine_match": g.affine_match,
        "bounding_box_match": g.bounding_box_match,
        "tensor_contract_status": m.tensor_contract_status.value,
        "numerical_status": m.numerical_status.value,
        "atlas_integrity_status": result.atlas_integrity_status.value,
        "physical_geometry_status": g.physical_geometry_status.value,
        "array_grid_status": g.array_grid_status.value,
        "overlay_status": result.overlay_status.value,
        "overall_status": result.overall_status.value,
        "warnings": " | ".join(result.warnings),
        "failures": " | ".join(result.failures),
    }


def save_atlas_report(output_dir: Path, atlas: AtlasMetadata) -> None:
    with (output_dir / "atlas_report.json").open("w", encoding="utf-8") as stream:
        json.dump(_json_ready(asdict(atlas)), stream, indent=2, sort_keys=True)


def save_reports(
    output_dir: Path,
    results: list[VerificationResult],
    atlas: AtlasMetadata,
    cfg: VerificationConfig,
    inventory_csv: str | Path,
    atlas_path: str | Path,
    sample: list[VerificationResult],
) -> None:
    rows = [result_to_row(result, atlas) for result in results]
    pd.DataFrame(rows).to_csv(output_dir / "subjects.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame([r for r in rows if r["overall_status"] == VerificationStatus.FAILED.value]).to_csv(
        output_dir / "failures.csv", index=False
    )
    pd.DataFrame([r for r in rows if r["warnings"]]).to_csv(output_dir / "warnings.csv", index=False)
    pd.DataFrame(
        [r for r in rows if VerificationStatus.INSUFFICIENT_METADATA.value in str(r.values())]
    ).to_csv(output_dir / "insufficient_metadata.csv", index=False)
    pd.DataFrame([{"subject_hash": r.subject_hash, "cohort": r.cohort, "class_label": r.class_label} for r in sample]).to_csv(
        output_dir / "overlay_sample.csv", index=False
    )
    save_atlas_report(output_dir, atlas)
    summary = build_summary(results, atlas)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(_json_ready(summary), stream, indent=2, sort_keys=True)
    (output_dir / "summary.md").write_text(summary_markdown(summary), encoding="utf-8")
    with (output_dir / "configuration_resolved.yaml").open("w", encoding="utf-8") as stream:
        yaml.safe_dump(_json_ready(asdict(cfg)), stream, sort_keys=True)
    metadata = {
        "inventory_csv": str(inventory_csv),
        "atlas_path": str(atlas_path),
        "output_dir": str(output_dir),
        "method": "Option A - verify existing derivatives only",
    }
    with (output_dir / "verification_metadata.json").open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, sort_keys=True)


def build_summary(results: list[VerificationResult], atlas: AtlasMetadata) -> dict[str, Any]:
    formats = Counter(r.metadata.file_format for r in results)
    cohorts = Counter(r.cohort or "UNKNOWN" for r in results)
    overall = Counter(r.overall_status.value for r in results)
    tensor = Counter(r.metadata.tensor_contract_status.value for r in results)
    physical = Counter(r.geometry.physical_geometry_status.value for r in results)
    warnings = Counter(msg for r in results for msg in r.warnings)
    failures = Counter(msg for r in results for msg in r.failures)
    return {
        "inventory_rows": len(results),
        "readable_derivatives": sum(not r.failures for r in results),
        "count_by_file_format": dict(sorted(formats.items())),
        "count_by_cohort": dict(sorted(cohorts.items())),
        "count_by_overall_status": dict(sorted(overall.items())),
        "count_by_tensor_contract_status": dict(sorted(tensor.items())),
        "count_by_physical_geometry_status": dict(sorted(physical.items())),
        "insufficient_physical_metadata": physical.get(VerificationStatus.INSUFFICIENT_METADATA.value, 0),
        "atlas_integrity_status": atlas.atlas_integrity_status.value,
        "atlas_non_background_labels": len(atlas.non_background_labels),
        "most_frequent_warnings": warnings.most_common(10),
        "most_frequent_failures": failures.most_common(10),
        "overlays_generated": sum(r.overlay_status == VerificationStatus.PASSED for r in results),
    }


def summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Derivative Verification Summary",
        "",
        f"- Inventory rows processed: {summary['inventory_rows']}",
        f"- Readable derivatives without subject-level failures: {summary['readable_derivatives']}",
        f"- Count by file format: {summary['count_by_file_format']}",
        f"- Count by cohort: {summary['count_by_cohort']}",
        f"- Count by overall status: {summary['count_by_overall_status']}",
        f"- Count by tensor-contract status: {summary['count_by_tensor_contract_status']}",
        f"- Count by physical-geometry status: {summary['count_by_physical_geometry_status']}",
        f"- Insufficient physical metadata: {summary['insufficient_physical_metadata']}",
        f"- Atlas integrity status: {summary['atlas_integrity_status']}",
        f"- Atlas non-background labels: {summary['atlas_non_background_labels']}",
        f"- Overlays generated: {summary['overlays_generated']}",
        "",
        "## Frequent Warnings",
        "",
    ]
    lines.extend(f"- {msg}: {count}" for msg, count in summary["most_frequent_warnings"][:5])
    lines.extend(["", "## Frequent Failures", ""])
    lines.extend(f"- {msg}: {count}" for msg, count in summary["most_frequent_failures"][:5])
    lines.extend(
        [
            "",
            "## Methodological Conclusion",
            "",
            "Array-grid and physical-space compatibility were reported separately. "
            "Plain tensor derivatives without affine metadata cannot establish physical-space compatibility. "
            "No registration, resampling, interpolation, normalization, skull stripping or derivative repair was performed.",
            "",
        ]
    )
    return "\n".join(lines)
