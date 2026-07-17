"""Deterministic input discovery and scan selection for preprocessing."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from pada3dacb.exceptions import ConfigurationError

ADNI_SUBJECT_RE = re.compile(r"\d{3}_S_\d{4}")
OASIS_ID_RE = re.compile(r"OASIS\d+_\d+", re.IGNORECASE)
CLASS_NAMES = ("CN", "MCI", "AD")
CLASS_TO_IDX = {"CN": 0, "MCI": 1, "AD": 2}


@dataclass(frozen=True)
class DiscoveredScan:
    subject_id: str
    cohort: str
    class_label: str | None
    path: Path


@dataclass
class SelectedScan:
    subject_id: str
    cohort: str
    class_label: str | None
    selected_path: Path
    all_paths: list[Path]
    selection_rule: str
    excluded_paths: list[Path] = field(default_factory=list)


def lower_name(path: str | Path) -> str:
    return str(path).lower()


def strip_medical_suffix(path: str | Path) -> str:
    name = Path(path).name
    for suffix in [".nii.gz", ".nii", ".img", ".hdr", ".mgz", ".mgh", ".pt", ".pth", ".npy", ".npz", ".dcm"]:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return Path(path).stem


def sanitize_id(text: object) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text))
    value = re.sub(r"_+", "_", value).strip("_")
    return value if value else "unknown"


def is_supported_file(path: str | Path, supported_extensions: Iterable[str]) -> bool:
    name = lower_name(path)
    return any(name.endswith(ext.lower()) for ext in supported_extensions)


def extract_adni_subject_id(path: str | Path) -> str:
    match = ADNI_SUBJECT_RE.search(str(path))
    if match:
        return sanitize_id(match.group(0))
    return sanitize_id(strip_medical_suffix(path))


def extract_oasis_base_id(text: str | Path) -> str | None:
    match = OASIS_ID_RE.search(str(text))
    return match.group(0).upper() if match else None


def find_class_dirs(root: str | Path) -> dict[str, Path]:
    root_path = Path(root)
    found: dict[str, Path] = {}
    for candidate in sorted(root_path.rglob("*")):
        if candidate.is_dir() and candidate.name.upper() in CLASS_TO_IDX:
            found[candidate.name.upper()] = candidate
    return found


def iter_adni_files_by_label(root: str | Path, supported_extensions: Iterable[str]) -> list[DiscoveredScan]:
    class_dirs = find_class_dirs(root)
    if not class_dirs:
        raise FileNotFoundError(f"No CN/MCI/AD directories were found under {root}.")
    scans: list[DiscoveredScan] = []
    for label, class_dir in sorted(class_dirs.items()):
        for path in sorted(class_dir.rglob("*")):
            if path.is_file() and is_supported_file(path, supported_extensions):
                scans.append(
                    DiscoveredScan(
                        subject_id=extract_adni_subject_id(path),
                        cohort="ADNI",
                        class_label=label,
                        path=path,
                    )
                )
    return scans


def find_adni_mprage_series_dirs(root: str | Path) -> list[Path]:
    candidates = []
    for directory in sorted(Path(root).rglob("*")):
        if not directory.is_dir():
            continue
        low = str(directory).lower()
        if ("mp-rage" in low or "mprage" in low) and any(p.suffix.lower() == ".dcm" for p in directory.iterdir() if p.is_file()):
            candidates.append(directory)
    return sorted(set(candidates))


def choose_oasis_scan(files: list[Path]) -> Path:
    def score(path: Path) -> tuple[int, str]:
        name = lower_name(path)
        value = 0
        for token in ["mpr", "t1", "brain", "struc", "processed", "masked", "talairach"]:
            if token in name:
                value -= 1
        return value, str(path)

    return sorted(files, key=score)[0]


def load_oasis_label_map(metadata_csv: str | Path) -> dict[str, str]:
    df = pd.read_csv(metadata_csv)
    columns = {name.lower(): name for name in df.columns}
    id_col = next((columns[key] for key in ["id", "subject id", "subject_id", "subject"] if key in columns), None)
    cdr_col = columns.get("cdr")
    if id_col is None or cdr_col is None:
        raise ConfigurationError("OASIS metadata must contain ID and CDR columns.")
    labels: dict[str, str] = {}
    for _, row in df.iterrows():
        base_id = extract_oasis_base_id(row[id_col])
        if base_id is None:
            continue
        cdr = row[cdr_col]
        if pd.isna(cdr):
            continue
        label = "CN" if float(cdr) == 0 else "AD"
        labels[base_id] = label
    return labels


def discover_oasis_scans(
    root: str | Path,
    metadata_csv: str | Path,
    supported_extensions: Iterable[str],
) -> list[DiscoveredScan]:
    labels = load_oasis_label_map(metadata_csv)
    scans: list[DiscoveredScan] = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or not is_supported_file(path, supported_extensions):
            continue
        base_id = extract_oasis_base_id(path)
        if base_id is None or base_id not in labels:
            continue
        scans.append(DiscoveredScan(base_id, "OASIS", labels[base_id], path))
    return scans


def select_one_scan_per_subject(scans: list[DiscoveredScan], cohort: str) -> list[SelectedScan]:
    grouped: dict[tuple[str, str | None], list[Path]] = {}
    for scan in scans:
        grouped.setdefault((scan.subject_id, scan.class_label), []).append(scan.path)
    selected: list[SelectedScan] = []
    for (subject_id, label), paths in sorted(grouped.items()):
        ordered = sorted(paths)
        if cohort.upper() == "OASIS":
            chosen = choose_oasis_scan(ordered)
            rule = "oasis_priority_tokens_then_path"
        else:
            chosen = ordered[0]
            rule = "sorted_path_first"
        selected.append(
            SelectedScan(
                subject_id=subject_id,
                cohort=cohort.upper(),
                class_label=label,
                selected_path=chosen,
                all_paths=ordered,
                selection_rule=rule,
                excluded_paths=[p for p in ordered if p != chosen],
            )
        )
    return selected


def discover_and_select(
    cohort: str,
    input_root: str | Path,
    supported_extensions: Iterable[str],
    metadata_csv: str | Path | None = None,
) -> list[SelectedScan]:
    cohort_name = cohort.upper()
    if cohort_name == "ADNI":
        scans = iter_adni_files_by_label(input_root, supported_extensions)
    elif cohort_name == "OASIS":
        if metadata_csv is None:
            raise ConfigurationError("OASIS preprocessing requires metadata_csv.")
        scans = discover_oasis_scans(input_root, metadata_csv, supported_extensions)
    else:
        raise ConfigurationError(f"Unsupported preprocessing cohort: {cohort}")
    return select_one_scan_per_subject(scans, cohort_name)
