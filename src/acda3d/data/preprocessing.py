"""Model-ready MRI preprocessing extracted from the canonical notebook."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml
from nibabel.orientations import aff2axcodes

from acda3d import __version__
from acda3d.data.derivative_verification import numerical_summary
from acda3d.data.inventories import SelectedScan, discover_and_select, sanitize_id
from acda3d.exceptions import ConfigurationError, InvalidPathError
from acda3d.paths import ensure_directory, resolve_path


@dataclass
class PreprocessingConfig:
    target_shape: tuple[int, int, int] = (128, 128, 128)
    output_channels: int = 1
    normalization: str = "robust"
    interpolation_mode: str = "trilinear"
    align_corners: bool = False
    output_dtype: str = "float32"
    overwrite: bool = False
    resume: bool = True
    continue_on_error: bool = True
    save_provenance: bool = True
    save_qc_summary: bool = True
    dry_run: bool = False
    fail_on_subject_failure: bool = False
    compute_source_hash: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> PreprocessingConfig:
        cleaned = dict(data)
        if cleaned.get("target_shape") is not None:
            cleaned["target_shape"] = tuple(int(v) for v in cleaned["target_shape"])
        cfg = cls(**{k: v for k, v in cleaned.items() if k in cls.__dataclass_fields__})
        if cfg.normalization != "robust":
            raise ConfigurationError("Phase 4 only supports the canonical robust normalization.")
        if cfg.interpolation_mode != "trilinear" or cfg.align_corners is not False:
            raise ConfigurationError("Resize settings must match the canonical notebook behavior.")
        if cfg.output_channels != 1:
            raise ConfigurationError("The canonical preprocessing pipeline outputs one channel.")
        return cfg


@dataclass
class DiscoveryConfig:
    supported_extensions: tuple[str, ...] = (
        ".nii",
        ".nii.gz",
        ".img",
        ".hdr",
        ".mgz",
        ".mgh",
        ".pt",
        ".pth",
        ".npy",
        ".npz",
        ".dcm",
    )
    recursive: bool = True

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> DiscoveryConfig:
        cleaned = dict(data)
        if cleaned.get("supported_extensions") is not None:
            cleaned["supported_extensions"] = tuple(cleaned["supported_extensions"])
        return cls(**{k: v for k, v in cleaned.items() if k in cls.__dataclass_fields__})


@dataclass
class PreprocessingPaths:
    cohort: str | None = None
    input_root: Path | None = None
    metadata_csv: Path | None = None
    output_root: Path | None = None


@dataclass
class ExecutionConfig:
    seed: int = 42
    number_of_workers: int = 1
    progress_every: int = 10


@dataclass
class PreprocessingRunConfig:
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    data: PreprocessingPaths = field(default_factory=PreprocessingPaths)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    config_path: Path | None = None

    def validate(self) -> None:
        if self.data.cohort is None or self.data.cohort.upper() not in {"ADNI", "OASIS"}:
            raise ConfigurationError("preprocessing data.cohort must be ADNI or OASIS.")
        if self.data.input_root is None:
            raise InvalidPathError("preprocessing data.input_root is required.")
        if self.data.output_root is None:
            raise InvalidPathError("preprocessing data.output_root is required.")
        if self.data.cohort.upper() == "OASIS" and self.data.metadata_csv is None:
            raise InvalidPathError("OASIS preprocessing requires metadata_csv.")
        if self.execution.number_of_workers != 1:
            raise ConfigurationError("Phase 4 defaults to single-worker execution for reproducibility.")

    def to_dict(self) -> dict[str, Any]:
        def clean(value: Any) -> Any:
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, tuple):
                return list(value)
            if isinstance(value, dict):
                return {k: clean(v) for k, v in value.items()}
            if hasattr(value, "__dataclass_fields__"):
                return clean(asdict(value))
            return value

        return clean(
            {
                "preprocessing": self.preprocessing,
                "discovery": self.discovery,
                "data": self.data,
                "execution": self.execution,
            }
        )

    def sha256(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class LoadedMRI:
    tensor: torch.Tensor
    source_format: str
    original_shape: tuple[int, ...]
    original_dtype: str
    source_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PreprocessingRecord:
    subject_hash: str
    cohort: str
    class_label: str | None
    source_path: str
    selected_scan_path: str
    output_path: str
    original_shape: str | None
    final_shape: str | None
    original_dtype: str | None
    final_dtype: str | None
    selection_rule: str
    status: str
    skipped: bool
    skip_reason: str | None
    warnings: str
    errors: str
    runtime_seconds: float
    configuration_hash: str


def load_preprocessing_config(path: str | Path) -> PreprocessingRunConfig:
    config_path = Path(path).expanduser().resolve(strict=False)
    with config_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    base = config_path.parent
    data = payload.get("data") or {}
    cfg = PreprocessingRunConfig(
        preprocessing=PreprocessingConfig.from_mapping(payload.get("preprocessing") or {}),
        discovery=DiscoveryConfig.from_mapping(payload.get("discovery") or {}),
        data=PreprocessingPaths(
            cohort=data.get("cohort"),
            input_root=resolve_path(data.get("input_root"), base),
            metadata_csv=resolve_path(data.get("metadata_csv"), base),
            output_root=resolve_path(data.get("output_root"), base),
        ),
        execution=ExecutionConfig(**{k: v for k, v in (payload.get("execution") or {}).items() if k in ExecutionConfig.__dataclass_fields__}),
        config_path=config_path,
    )
    return cfg


def safe_torch_load(path: str | Path) -> Any:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def extract_tensor_from_object(obj: Any) -> Any:
    if torch.is_tensor(obj) or isinstance(obj, np.ndarray):
        return obj
    if isinstance(obj, dict):
        preferred_keys = ["image", "img", "x", "X", "tensor", "mri", "MRI", "volume", "vol", "data", "scan", "arr", "array"]
        for key in preferred_keys:
            if key in obj:
                return extract_tensor_from_object(obj[key])
        raise ValueError("Dictionary does not contain a supported MRI tensor key.")
    if isinstance(obj, (list, tuple)):
        for value in obj:
            try:
                return extract_tensor_from_object(value)
            except ValueError:
                continue
    raise ValueError("No tensor-like MRI volume was found inside the loaded object.")


def to_channel_first_3d(x: Any) -> torch.Tensor:
    if isinstance(x, np.ndarray):
        x = torch.from_numpy(x)
    if not torch.is_tensor(x):
        x = torch.as_tensor(x)
    tensor = x.detach().cpu().float()
    tensor = torch.nan_to_num(tensor, nan=0.0, posinf=0.0, neginf=0.0)
    while tensor.ndim > 4 and 1 in tensor.shape:
        tensor = tensor.squeeze(list(tensor.shape).index(1))
    if tensor.ndim == 5:
        tensor = tensor[0]
    if tensor.ndim == 4:
        if tensor.shape[0] <= 10:
            tensor = tensor[:1]
        elif tensor.shape[-1] <= 10:
            tensor = tensor.permute(3, 0, 1, 2)[:1]
        else:
            tensor = tensor[..., 0].unsqueeze(0)
    elif tensor.ndim == 3:
        tensor = tensor.unsqueeze(0)
    else:
        raise ValueError(f"Expected a 3D/4D MRI volume, but got shape {tuple(tensor.shape)}.")
    return tensor.contiguous()


def load_nifti_tensor(path: str | Path) -> LoadedMRI:
    img = nib.load(str(path))
    canonical = nib.as_closest_canonical(img)
    volume = canonical.get_fdata(dtype=np.float32)
    metadata = {
        "original_affine": np.asarray(img.affine).tolist(),
        "original_spacing": tuple(float(v) for v in img.header.get_zooms()[:3]),
        "original_orientation": tuple(str(v) for v in aff2axcodes(img.affine)),
    }
    return LoadedMRI(
        tensor=to_channel_first_3d(volume),
        source_format=Path(path).suffix.lower(),
        original_shape=tuple(int(v) for v in volume.shape),
        original_dtype=str(volume.dtype),
        source_metadata=metadata,
    )


def load_numpy_tensor(path: str | Path) -> LoadedMRI:
    loaded = np.load(path)
    if isinstance(loaded, np.lib.npyio.NpzFile):
        keys = sorted(loaded.keys(), key=lambda k: 0 if np.asarray(loaded[k]).ndim >= 3 else 1)
        if not keys:
            raise ValueError(".npz file contains no arrays.")
        arr = loaded[keys[0]]
    else:
        arr = np.asarray(loaded)
    if arr.dtype == object:
        raise ValueError("Object arrays are not supported for MRI preprocessing.")
    return LoadedMRI(to_channel_first_3d(arr), Path(path).suffix.lower(), tuple(arr.shape), str(arr.dtype))


def load_pt_tensor(path: str | Path) -> LoadedMRI:
    obj = safe_torch_load(path)
    tensor_like = extract_tensor_from_object(obj)
    original_shape = tuple(int(v) for v in tensor_like.shape)
    original_dtype = str(tensor_like.dtype)
    return LoadedMRI(to_channel_first_3d(tensor_like), ".pt", original_shape, original_dtype)


def load_dicom_series_tensor(path: str | Path) -> LoadedMRI:
    try:
        import SimpleITK as sitk  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("DICOM loading requires SimpleITK, matching the notebook implementation.") from exc
    directory = Path(path) if Path(path).is_dir() else Path(path).parent
    series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(directory))
    if not series_ids:
        raise RuntimeError(f"No DICOM series found in {directory}")
    best_files = max((sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(directory), sid) for sid in series_ids), key=len)
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(best_files)
    image = reader.Execute()
    arr = np.transpose(sitk.GetArrayFromImage(image).astype(np.float32), (1, 2, 0))
    return LoadedMRI(to_channel_first_3d(arr), ".dcm", tuple(arr.shape), str(arr.dtype))


def load_mri_tensor(path: str | Path) -> LoadedMRI:
    p = Path(path)
    name = str(p).lower()
    if p.is_dir() or name.endswith(".dcm"):
        return load_dicom_series_tensor(p)
    if name.endswith((".nii", ".nii.gz", ".img", ".hdr", ".mgz", ".mgh")):
        return load_nifti_tensor(p)
    if name.endswith((".pt", ".pth")):
        return load_pt_tensor(p)
    if name.endswith((".npy", ".npz")):
        return load_numpy_tensor(p)
    raise ValueError(f"Unsupported file extension: {p}")


def robust_intensity_normalization(x: torch.Tensor, pmin: float = 1.0, pmax: float = 99.0) -> torch.Tensor:
    vals = x[x > 0]
    if vals.numel() == 0:
        return x
    lo = torch.quantile(vals, pmin / 100.0)
    hi = torch.quantile(vals, pmax / 100.0)
    clipped = torch.clamp(x, lo, hi)
    mean = vals.mean()
    std = vals.std().clamp_min(1e-6)
    return (clipped - mean) / std


def resize_3d_tensor(x: torch.Tensor, target_shape: tuple[int, int, int] = (128, 128, 128)) -> torch.Tensor:
    x5 = x.unsqueeze(0)
    x5 = x5.permute(0, 1, 4, 2, 3)
    x5 = F.interpolate(
        x5,
        size=(target_shape[2], target_shape[0], target_shape[1]),
        mode="trilinear",
        align_corners=False,
    )
    x5 = x5.permute(0, 1, 3, 4, 2)
    return x5.squeeze(0)


def center_crop_or_pad_3d(x: torch.Tensor, target_shape: tuple[int, int, int]) -> torch.Tensor:
    _, height, width, depth = x.shape
    target_h, target_w, target_d = target_shape
    out = torch.zeros((1, target_h, target_w, target_d), dtype=x.dtype)
    h0_src = max((height - target_h) // 2, 0)
    w0_src = max((width - target_w) // 2, 0)
    d0_src = max((depth - target_d) // 2, 0)
    h1_src = min(h0_src + target_h, height)
    w1_src = min(w0_src + target_w, width)
    d1_src = min(d0_src + target_d, depth)
    crop = x[:, h0_src:h1_src, w0_src:w1_src, d0_src:d1_src]
    _, crop_h, crop_w, crop_d = crop.shape
    h0_dst = max((target_h - crop_h) // 2, 0)
    w0_dst = max((target_w - crop_w) // 2, 0)
    d0_dst = max((target_d - crop_d) // 2, 0)
    out[:, h0_dst : h0_dst + crop_h, w0_dst : w0_dst + crop_w, d0_dst : d0_dst + crop_d] = crop
    return out


def apply_mri_transforms(x: torch.Tensor, target_shape: tuple[int, int, int]) -> torch.Tensor:
    x = robust_intensity_normalization(x)
    x = resize_3d_tensor(x, target_shape=target_shape)
    x = center_crop_or_pad_3d(x, target_shape=target_shape)
    return x.to(torch.float32).contiguous()


def atomic_save_tensor(tensor: torch.Tensor, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    torch.save(tensor.detach().cpu(), tmp_path)
    os.replace(tmp_path, path)


def output_path_for(scan: SelectedScan, output_root: Path) -> Path:
    label = sanitize_id(scan.class_label or "unknown")
    return output_root / label / f"{sanitize_id(scan.subject_id)}_MRI.pt"


def validate_existing_output(path: Path, cfg: PreprocessingRunConfig) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "missing"
    try:
        loaded = load_pt_tensor(path)
        if tuple(loaded.tensor.shape[1:]) != cfg.preprocessing.target_shape:
            return False, "shape_mismatch"
        summary, status = numerical_summary(loaded.tensor.numpy(), cfg=_numerical_cfg())
        if status.value == "FAILED" or summary.finite_fraction < 1.0:
            return False, "non_finite"
        sidecar = path.with_suffix(path.suffix + ".json")
        if sidecar.exists():
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            if payload.get("configuration_hash") != cfg.sha256():
                return False, "configuration_hash_mismatch"
        return True, None
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return False, str(exc)


def _numerical_cfg() -> Any:
    from acda3d.data.derivative_verification import VerificationConfig

    return VerificationConfig()


def process_scan(scan: SelectedScan, cfg: PreprocessingRunConfig) -> PreprocessingRecord:
    start = time.time()
    output_root = cfg.data.output_root
    if output_root is None:
        raise InvalidPathError("Output root is required.")
    output_path = output_path_for(scan, output_root)
    warnings: list[str] = []
    errors: list[str] = []
    config_hash = cfg.sha256()
    subject_hash = hashlib.sha256(scan.subject_id.encode("utf-8")).hexdigest()[:16]
    if cfg.preprocessing.dry_run:
        return _record(scan, output_path, None, None, "DRY_RUN", False, None, warnings, errors, start, config_hash)
    if output_path.exists() and cfg.preprocessing.resume and not cfg.preprocessing.overwrite:
        valid, reason = validate_existing_output(output_path, cfg)
        if valid:
            return _record(scan, output_path, None, None, "SKIPPED_VALID", True, "valid_existing_output", warnings, errors, start, config_hash)
        errors.append(f"Existing output is invalid: {reason}")
        if not cfg.preprocessing.overwrite:
            return _record(scan, output_path, None, None, "FAILED", False, None, warnings, errors, start, config_hash)
    loaded = load_mri_tensor(scan.selected_path)
    transformed = apply_mri_transforms(loaded.tensor, cfg.preprocessing.target_shape)
    atomic_save_tensor(transformed, output_path)
    sidecar = {
        "safe_subject_id": subject_hash,
        "cohort": scan.cohort,
        "class_label": scan.class_label,
        "source_path": str(scan.selected_path),
        "selected_scan": str(scan.selected_path),
        "output_path": str(output_path),
        "original_format": loaded.source_format,
        "original_shape": list(loaded.original_shape),
        "final_shape": list(transformed.shape),
        "original_dtype": loaded.original_dtype,
        "final_dtype": str(transformed.dtype),
        "preprocessing_operations": ["to_channel_first_3d", "robust_intensity_normalization", "resize_3d_tensor", "center_crop_or_pad_3d"],
        "operation_order": ["load", "channel_first", "robust_normalize", "resize", "center_crop_or_pad", "save_tensor"],
        "configuration_hash": config_hash,
        "source_file_size": scan.selected_path.stat().st_size,
        "source_file_modified_time": scan.selected_path.stat().st_mtime,
        "source_physical_metadata": loaded.source_metadata,
        "software_version": __version__,
        "status": "PROCESSED",
        "warnings": warnings,
        "errors": errors,
    }
    if cfg.preprocessing.compute_source_hash:
        sidecar["source_file_hash"] = hashlib.sha256(scan.selected_path.read_bytes()).hexdigest()
    if cfg.preprocessing.save_provenance:
        output_path.with_suffix(output_path.suffix + ".json").write_text(json.dumps(sidecar, indent=2, sort_keys=True), encoding="utf-8")
    return _record(scan, output_path, loaded, transformed, "PROCESSED", False, None, warnings, errors, start, config_hash)


def _record(
    scan: SelectedScan,
    output_path: Path,
    loaded: LoadedMRI | None,
    tensor: torch.Tensor | None,
    status: str,
    skipped: bool,
    skip_reason: str | None,
    warnings: list[str],
    errors: list[str],
    start: float,
    config_hash: str,
) -> PreprocessingRecord:
    return PreprocessingRecord(
        subject_hash=hashlib.sha256(scan.subject_id.encode("utf-8")).hexdigest()[:16],
        cohort=scan.cohort,
        class_label=scan.class_label,
        source_path=str(scan.selected_path),
        selected_scan_path=str(scan.selected_path),
        output_path=str(output_path),
        original_shape=json.dumps(loaded.original_shape) if loaded else None,
        final_shape=json.dumps(tuple(tensor.shape)) if tensor is not None else None,
        original_dtype=loaded.original_dtype if loaded else None,
        final_dtype=str(tensor.dtype) if tensor is not None else None,
        selection_rule=scan.selection_rule,
        status=status,
        skipped=skipped,
        skip_reason=skip_reason,
        warnings=" | ".join(warnings),
        errors=" | ".join(errors),
        runtime_seconds=time.time() - start,
        configuration_hash=config_hash,
    )


def run_preprocessing(cfg: PreprocessingRunConfig, *, limit: int | None = None, subjects: set[str] | None = None) -> list[PreprocessingRecord]:
    cfg.validate()
    assert cfg.data.input_root is not None
    assert cfg.data.output_root is not None
    report_root = ensure_directory(cfg.data.output_root)
    scans = discover_and_select(
        cfg.data.cohort or "",
        cfg.data.input_root,
        cfg.discovery.supported_extensions,
        cfg.data.metadata_csv,
    )
    if subjects:
        scans = [scan for scan in scans if scan.subject_id in subjects]
    if limit is not None:
        scans = scans[:limit]
    records: list[PreprocessingRecord] = []
    for scan in scans:
        try:
            records.append(process_scan(scan, cfg))
        except (OSError, ValueError, RuntimeError) as exc:
            output_path = output_path_for(scan, report_root)
            records.append(
                _record(scan, output_path, None, None, "FAILED", False, None, [], [str(exc)], time.time(), cfg.sha256())
            )
            if not cfg.preprocessing.continue_on_error:
                break
    save_preprocessing_reports(report_root, cfg, records)
    return records


def save_preprocessing_reports(output_root: Path, cfg: PreprocessingRunConfig, records: list[PreprocessingRecord]) -> None:
    rows = [asdict(record) for record in records]
    manifest = pd.DataFrame(rows)
    manifest.to_csv(output_root / "preprocessing_manifest.csv", index=False)
    manifest[manifest["status"] == "FAILED"].to_csv(output_root / "failures.csv", index=False)
    manifest[manifest["skipped"]].to_csv(output_root / "skipped.csv", index=False)
    counts = manifest["status"].value_counts().to_dict() if len(manifest) else {}
    summary = {"n_records": len(records), "status_counts": counts, "configuration_hash": cfg.sha256()}
    (output_root / "preprocessing_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (output_root / "preprocessing_summary.md").write_text(
        "# Preprocessing Summary\n\n"
        f"- Records: {len(records)}\n"
        f"- Status counts: {counts}\n"
        "- No registration, atlas resampling, skull stripping or bias correction was performed.\n",
        encoding="utf-8",
    )
    (output_root / "configuration_resolved.yaml").write_text(yaml.safe_dump(cfg.to_dict(), sort_keys=True), encoding="utf-8")
    metadata = {"method": "canonical notebook preprocessing extraction", "software_version": __version__}
    (output_root / "preprocessing_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
