"""Report orchestration and output management for concept evaluation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .figures import (
    plot_anatomy_consistency_roi_heatmap,
    plot_class_conditional_profiles,
    plot_concept_fidelity_roi_heatmap,
    plot_head_agreement_matrix,
    plot_roi_stability_heatmap,
)
from .schemas import (
    CheckpointPolicy,
    Direction,
    MethodId,
)


@dataclass(frozen=True)
class ConceptEvaluationPlan:
    """Complete plan for concept evaluation output."""
    evaluation_identity: str
    analysis_mode: str
    methods: tuple[MethodId, ...]
    directions: tuple[Direction, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    intended_relative_paths: tuple[str, ...]


def build_concept_output_plan(
    evaluation_identity: str,
    analysis_mode: str,
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    checkpoint_policies: Sequence[CheckpointPolicy],
    included_methods: tuple[MethodId, ...],
    include_artifact_index: bool = True,
) -> ConceptEvaluationPlan:
    """Build exact output manifest for concept evaluation."""
    paths = [
        "evaluation_config_resolved.yaml",
        "provenance_report.json",
        "method_status.csv",
        "evaluation_log.txt",
    ]
    included_methods = tuple(dict.fromkeys(included_methods))
    concept_directions = directions if included_methods else ()

    for direction in concept_directions:
        for policy in checkpoint_policies:
            base = f"concepts/{direction.value}/{policy.logical_checkpoint}"
            paths.extend([
                f"{base}/subject_outputs/subject_outputs.csv",
                f"{base}/concept_fidelity/concept_fidelity_global.csv",
                f"{base}/concept_fidelity/concept_fidelity_per_subject.csv",
                f"{base}/concept_fidelity/concept_fidelity_per_roi.csv",
                f"{base}/concept_fidelity/correlations.csv",
                f"{base}/anatomy_consistency/anatomy_consistency_global.csv",
                f"{base}/anatomy_consistency/anatomy_consistency_per_subject.csv",
                f"{base}/anatomy_consistency/anatomy_consistency_per_roi.csv",
                f"{base}/anatomy_consistency/correlations.csv",
                f"{base}/anatomy_consistency/weighted_score.csv",
                f"{base}/head_agreement/latent_predictive.csv",
                f"{base}/head_agreement/concept_predictive.csv",
                f"{base}/head_agreement/top1_agreement.csv",
                f"{base}/head_agreement/js_divergence.csv",
                f"{base}/head_agreement/consistency_direction.csv",
                f"{base}/head_agreement/per_class_disagreement.csv",
                f"{base}/roi_stability/rank_correlations.csv",
                f"{base}/roi_stability/mean_pairwise_rho.csv",
                f"{base}/roi_stability/instance_std.csv",
                f"{base}/roi_stability/jaccard_overlap.csv",
                f"{base}/roi_stability/rank_dispersion.csv",
                f"{base}/class_profiles/cn_concepts.csv",
                f"{base}/class_profiles/mci_concepts.csv",
                f"{base}/class_profiles/ad_concepts.csv",
                f"{base}/class_profiles/cn_c_targets.csv",
                f"{base}/class_profiles/mci_c_targets.csv",
                f"{base}/class_profiles/ad_c_targets.csv",
                f"{base}/class_profiles/cn_g_bar.csv",
                f"{base}/class_profiles/mci_g_bar.csv",
                f"{base}/class_profiles/ad_g_bar.csv",
                f"{base}/paired_comparisons/concept_mae_paired.csv",
                f"{base}/paired_comparisons/anatomy_mae_paired.csv",
                f"{base}/paired_comparisons/js_divergence_paired.csv",
                f"{base}/paired_comparisons/holm_adjusted.csv",
                f"{base}/figures/concept_fidelity_roi_heatmap.png",
                f"{base}/figures/anatomy_consistency_roi_heatmap.png",
                f"{base}/figures/head_agreement_matrix.png",
                f"{base}/figures/roi_stability_heatmap.png",
                f"{base}/figures/class_conditional_concept_profiles.png",
                f"{base}/tables/concept_fidelity_global.csv",
                f"{base}/tables/concept_fidelity_per_subject.csv",
                f"{base}/tables/concept_fidelity_per_roi.csv",
                f"{base}/tables/anatomy_consistency_global.csv",
                f"{base}/tables/anatomy_consistency_per_subject.csv",
                f"{base}/tables/anatomy_consistency_per_roi.csv",
                f"{base}/tables/head_agreement.csv",
                f"{base}/tables/roi_stability.csv",
                f"{base}/tables/class_conditional_profiles.csv",
                f"{base}/tables/paired_method_comparisons.csv",
                f"{base}/tables/method_status.csv",
            ])

    paths = sorted(paths)
    if include_artifact_index:
        paths.append("artifact_index.json")

    paths.append("evaluation_manifest.json")

    return ConceptEvaluationPlan(
        evaluation_identity=evaluation_identity,
        analysis_mode=analysis_mode,
        methods=tuple(methods),
        directions=tuple(directions),
        checkpoint_policies=tuple(checkpoint_policies),
        intended_relative_paths=tuple(paths),
    )


def build_artifact_index(artifacts: Mapping[str, bytes]) -> bytes:
    """Build optional self-excluding artifact hash inventory."""
    if "artifact_index.json" in artifacts:
        raise ValueError("artifact index input must exclude itself")

    payload = {
        "schema_version": "1.0",
        "artifacts": {
            path: hashlib.sha256(artifacts[path]).hexdigest()
            for path in sorted(artifacts)
        },
    }
    return (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def build_completion_manifest(
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    identity_inputs: Mapping[str, Any],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    ci_policy: str,
    gate_states: Mapping[str, bool],
    created_utc: str,
    completed_utc: str,
    disposition: str = "completed",
) -> bytes:
    """Build identity-bound completion manifest over every non-manifest artifact."""
    expected = set(plan.intended_relative_paths)
    expected.discard("evaluation_manifest.json")
    expected.discard("artifact_index.json")

    ordinary_expected = {p for p in expected if p not in {"artifact_index.json"}}
    if set(artifacts.keys()) != ordinary_expected:
        raise ValueError("completed artifacts do not exactly match the evaluation plan")

    output_sha256s = {
        path: hashlib.sha256(artifacts[path]).hexdigest()
        for path in sorted(ordinary_expected)
    }

    required_gates = ("authorized_exports", "concept_normalizer", "atlas_hash", "protocol_approval")
    gates = dict.fromkeys(required_gates, False)
    gates.update(gate_states)

    config_hash = identity_inputs.get("configuration_sha256", "0" * 64)
    auth_hash = identity_inputs.get("authorization_sha256", "0" * 64)
    ordered_inputs = identity_inputs.get("ordered_input_sha256s", [])

    payload = {
        "schema_version": "1.0",
        "protocol_version": "1.0",
        "evaluation_identity": plan.evaluation_identity,
        "analysis_mode": plan.analysis_mode,
        "created_utc": created_utc,
        "completed_utc": completed_utc,
        "methods": [m.value for m in plan.methods],
        "directions": [d.value for d in plan.directions],
        "checkpoint_policies": [p.logical_checkpoint for p in plan.checkpoint_policies],
        "class_order": {"CN": 0, "MCI": 1, "AD": 2},
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "ci_policy": ci_policy,
        },
        "configuration_sha256": config_hash,
        "authorization_sha256": auth_hash,
        "gate_states": gates,
        "ordered_input_sha256s": ordered_inputs,
        "identity_inputs": dict(identity_inputs),
        "library_versions": dict(library_versions),
        "output_sha256s": output_sha256s,
        "disposition": disposition,
    }
    return (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def _csv_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    fieldnames = list(rows[0])
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _synthetic_status_rows(
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    policies: Sequence[CheckpointPolicy],
) -> list[dict[str, Any]]:
    not_applicable_methods = (MethodId.AAGN, MethodId.FASTER_SNN)
    selected_methods = tuple(dict.fromkeys(methods))
    status_methods = tuple(dict.fromkeys((*selected_methods, *not_applicable_methods)))
    rows = []
    for direction in directions:
        for policy in policies:
            for method in status_methods:
                is_not_applicable = method in not_applicable_methods
                rows.append({
                    "method": method.value,
                    "direction": direction.value,
                    "checkpoint_policy": policy.logical_checkpoint,
                    "status": (
                        "not_applicable_no_pada3dacb_concept_head"
                        if is_not_applicable else "included"
                    ),
                    "reason": (
                        "no_pada3dacb_concept_head"
                        if is_not_applicable else "fixture_only"
                    ),
                })
    return rows


def _synthetic_csv_artifact(
    relative_path: str,
    metrics: Mapping[str, Any],
    methods: Sequence[MethodId],
) -> bytes:
    parts = relative_path.split("/")
    direction = parts[1] if len(parts) > 3 and parts[0] == "concepts" else "all"
    policy = parts[2] if len(parts) > 3 and parts[0] == "concepts" else "all"
    name = Path(relative_path).name
    method = methods[0].value
    common = {"method": method, "direction": direction, "checkpoint_policy": policy}
    if name == "subject_outputs.csv":
        return _csv_bytes([{**common, "subject_hash": "1" * 64, "true_label": 0,
            "label_name": "CN", "predicted_concepts": "[0.1,0.3,0.5]",
            "concept_targets": "[0.05,0.25,0.45]", "anatomical_targets": "[0.2,0.4,0.6]"}])
    if "concept_fidelity" in name:
        rows = [{**common, "roi_index": roi, "n_subjects": 6,
            "mae": metrics["concept_mae"], "rmse": metrics.get("concept_rmse", 0.05), "bias": 0.05}
            for roi in range(3)]
    elif "anatomy_consistency" in name or name in {"weighted_score.csv", "correlations.csv"}:
        rows = [{**common, "roi_index": roi, "n_subjects": 6,
            "mae": metrics.get("anatomy_mae", 0.1), "rmse": metrics.get("anatomy_rmse", 0.1),
            "status": "available"} for roi in range(3)]
    elif name in {"head_agreement.csv", "latent_predictive.csv", "concept_predictive.csv",
                  "top1_agreement.csv", "js_divergence.csv", "consistency_direction.csv",
                  "per_class_disagreement.csv"}:
        rows = [{**common, "n_subjects": 6,
            "top1_agreement_rate": metrics.get("top1_agreement_rate", 1.0),
            "mean_js_divergence": metrics.get("mean_js_divergence", 0.0),
            "consistency_direction": "latent_supervises_concept"}]
    elif "roi_stability" in relative_path or name in {
        "rank_correlations.csv", "mean_pairwise_rho.csv", "instance_std.csv",
        "jaccard_overlap.csv", "rank_dispersion.csv",
    }:
        rows = [{**common, "profile": profile, "roi_index": roi, "k": 2,
            "metric": "profile_specific_stability", "value": 1.0}
            for profile in ("fidelity", "anatomy", "concept", "alpha") for roi in range(3)]
    elif "class" in name or "class_profiles" in relative_path:
        rows = [{**common, "class_label": label, "class_index": index, "support": 2,
            "roi_index": roi, "mean": 0.2 + 0.1 * index + 0.05 * roi,
            "ci_low": 0.1, "ci_high": 0.8}
            for index, label in enumerate(("CN", "MCI", "AD")) for roi in range(3)]
    elif "paired" in name or "holm" in name:
        rows = [{**common, "comparator_method": comparator.value,
            "metric": "concept_mae", "mean_difference": 0.0, "ci_low": 0.0,
            "ci_high": 0.0, "raw_p_value": 1.0, "adjusted_p_value": 1.0,
            "status": "available"}
            for comparator in (MethodId.SOURCE_ONLY, MethodId.CORAL, MethodId.MMD, MethodId.CDAN)]
    elif name == "method_status.csv":
        rows = [{**common, "status": "included", "reason": "fixture_only"}]
    else:
        rows = [{**common, "fixture_only": True, "status": "available"}]
    return _csv_bytes(rows)


def _synthetic_figure_payloads(methods: Sequence[MethodId]) -> dict[str, bytes]:
    method_names = [method.value for method in methods]
    fidelity = [{"method": method, "roi_index": roi, "mae": 0.05 + 0.01 * roi}
        for method in method_names for roi in range(3)]
    anatomy = [{"method": method, "roi_index": roi, "mae": 0.1 + 0.01 * roi}
        for method in method_names for roi in range(3)]
    profiles = [{"class_label": label, "roi_index": roi, "mean": 0.2 + 0.1 * index,
        "ci_low": 0.1, "ci_high": 0.8}
        for index, label in enumerate(("CN", "MCI", "AD")) for roi in range(3)]
    stability = SimpleNamespace(
        instance_std_fidelity=(0.01, 0.02, 0.03),
        instance_std_anatomy=(0.02, 0.03, 0.04),
        instance_std_concept=(0.03, 0.04, 0.05),
        instance_std_alpha=(0.01, 0.01, 0.02),
    )
    with tempfile.TemporaryDirectory(prefix="pada3dacb-concept-figures-") as directory:
        root = Path(directory)
        plot_concept_fidelity_roi_heatmap(fidelity, root / "concept_fidelity_roi_heatmap.png")
        plot_anatomy_consistency_roi_heatmap(anatomy, root / "anatomy_consistency_roi_heatmap.png")
        plot_head_agreement_matrix({"source_only": {
            "comparator_method": "source_only",
            "confusion_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        }}, root / "head_agreement_matrix.png")
        plot_roi_stability_heatmap(stability, root / "roi_stability_heatmap.png")
        plot_class_conditional_profiles(profiles, root / "class_conditional_concept_profiles.png")
        return {path.name: path.read_bytes() for path in root.glob("*.png")}


def build_synthetic_fixture_bundle(
    *,
    evaluation_identity: str,
    methods: Sequence[MethodId],
    directions: Sequence[Direction],
    checkpoint_policies: Sequence[CheckpointPolicy],
    metrics: Mapping[str, Any],
    resolved_config: Mapping[str, Any],
    identity_inputs: Mapping[str, Any],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> tuple[ConceptEvaluationPlan, dict[str, bytes]]:
    """Build the complete deterministic fixture-only report tree."""
    included_methods = tuple(
        method for method in methods
        if method not in {MethodId.AAGN, MethodId.FASTER_SNN}
    )
    plan = build_concept_output_plan(
        evaluation_identity,
        "synthetic_test_only",
        methods,
        directions,
        checkpoint_policies,
        included_methods,
    )
    ordinary: dict[str, bytes] = {
        "evaluation_config_resolved.yaml": (
            json.dumps(dict(resolved_config), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
        "evaluation_log.txt": b"fixture_only deterministic synthetic evaluation\n",
        "method_status.csv": _csv_bytes(
            _synthetic_status_rows(methods, directions, checkpoint_policies)
        ),
        "provenance_report.json": (
            json.dumps({"candidates": [], "excluded": [], "fixture_only": True,
                "ordered_input_sha256s": [], "real_data": False},
                sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
    }
    figures = _synthetic_figure_payloads(methods)
    for relative_path in plan.intended_relative_paths:
        if relative_path in ordinary or relative_path in {
            "artifact_index.json", "evaluation_manifest.json"
        }:
            continue
        ordinary[relative_path] = (
            figures[Path(relative_path).name]
            if relative_path.endswith(".png")
            else _synthetic_csv_artifact(relative_path, metrics, methods)
        )
    artifact_index = build_artifact_index(ordinary)
    manifest = build_completion_manifest(
        plan, ordinary, identity_inputs, library_versions,
        bootstrap_replicates, bootstrap_seed, "percentile_95_linear",
        {"authorized_exports": False, "concept_normalizer": False,
         "atlas_hash": False, "protocol_approval": False},
        "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
    )
    return plan, {**ordinary, "artifact_index.json": artifact_index,
        "evaluation_manifest.json": manifest}


def _default_output_writer(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _relative_entries(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    if root.is_symlink():
        raise ValueError("output root must not be a symlink")
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"output contains a symlink: {relative}")
        if path.is_file():
            files.add(relative)
        elif path.is_dir():
            directories.add(relative)
        else:
            raise ValueError(f"output contains an unsupported entry: {relative}")
    return files, directories


def _relative_files(root: Path) -> set[str]:
    return _relative_entries(root)[0]


def _safe_relative_path(relative_path: Any) -> bool:
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        return False
    path = Path(relative_path)
    return (
        not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in relative_path.split("/"))
    )


def _expected_directories(files: set[str]) -> set[str]:
    directories: set[str] = set()
    for relative_path in files:
        parts = relative_path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]))
    return directories


def _validate_allowlisted_tree(root: Path, expected_files: set[str]) -> None:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("recognized output exists and is not a directory")
    try:
        actual_files, actual_directories = _relative_entries(root)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    if actual_files != expected_files:
        unknown = sorted(actual_files - expected_files)
        missing = sorted(expected_files - actual_files)
        raise RuntimeError(
            f"unknown output paths block overwrite; unknown={unknown}, missing={missing}"
        )
    expected_directories = _expected_directories(expected_files)
    if actual_directories != expected_directories:
        unknown = sorted(actual_directories - expected_directories)
        raise RuntimeError(f"unknown output directories block overwrite: {unknown}")


def _validate_completed_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise ValueError("completed evaluation manifest is not an object")
    if manifest.get("schema_version") != "1.0" or manifest.get("protocol_version") != "1.0":
        raise ValueError("completed evaluation manifest version is unsupported")
    if not isinstance(manifest.get("evaluation_identity"), str) or not manifest["evaluation_identity"]:
        raise ValueError("completed evaluation identity is missing")
    if not isinstance(manifest.get("analysis_mode"), str) or not manifest["analysis_mode"]:
        raise ValueError("completed analysis mode is missing")
    if manifest.get("disposition") != "completed":
        raise ValueError("completed evaluation is not marked completed")
    output_hashes = manifest.get("output_sha256s")
    if not isinstance(output_hashes, Mapping):
        raise ValueError("completed output hashes are missing")
    for relative_path, expected_hash in output_hashes.items():
        if not _safe_relative_path(relative_path) or relative_path in {
            "artifact_index.json", "evaluation_manifest.json"
        }:
            raise ValueError("completed output contains an unsafe artifact path")
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or expected_hash != expected_hash.lower()
            or any(character not in "0123456789abcdef" for character in expected_hash)
        ):
            raise ValueError(f"invalid artifact hash: {relative_path}")
    return dict(manifest)


_OWNER_METADATA_NAME = ".pada3dacb-owner.json"
_STALE_CONTROLLED_AGE_SECONDS = 30.0


def _process_is_alive(pid: int) -> bool:
    """Return a conservative liveness result for a controlled owner PID."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _owner_metadata_path(entry: Path, kind: str) -> Path:
    return entry / _OWNER_METADATA_NAME


def _write_owner_metadata(entry: Path, *, kind: str, pid: int, token: str) -> None:
    metadata_path = _owner_metadata_path(entry, kind)
    metadata = json.dumps(
        {"schema_version": "1", "pid": pid, "token": token},
        separators=(",", ":"),
    ).encode("utf-8")
    temporary = metadata_path.with_name(f".{metadata_path.name}.{token}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(metadata)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, metadata_path)
    finally:
        with suppress(FileNotFoundError):
            temporary.unlink()


def _read_owner_metadata(entry: Path, *, kind: str) -> dict[str, Any] | None:
    metadata_path = _owner_metadata_path(entry, kind)
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version") != "1"
        or isinstance(payload.get("pid"), bool)
        or not isinstance(payload.get("pid"), int)
        or payload["pid"] <= 0
        or not isinstance(payload.get("token"), str)
        or not payload["token"]
    ):
        return {}
    return dict(payload)


def _controlled_entry_kind(name: str, output_name: str) -> tuple[str, str] | None:
    pattern = rf"\.{re.escape(output_name)}(?:\.v\d{{6}})?\.(stage|reserve|backup)\.([A-Za-z0-9_-]+)"
    match = re.fullmatch(pattern, name)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _controlled_destination(entry: Path, output_name: str) -> Path:
    name = entry.name
    destination_name = output_name
    version_prefix = f".{output_name}.v"
    if name.startswith(version_prefix):
        version = name[len(version_prefix):].split(".", maxsplit=1)[0]
        destination_name = f"{output_name}.v{version}"
    return entry.parent / destination_name


def _is_old_controlled_entry(entry: Path) -> bool:
    try:
        age = time.time() - entry.stat().st_mtime
    except OSError:
        return False
    return age >= _STALE_CONTROLLED_AGE_SECONDS


def _owner_is_stale(
    entry: Path,
    *,
    kind: str,
    token: str | None = None,
) -> bool:
    if entry.is_symlink() or not entry.is_dir():
        return False
    metadata = _read_owner_metadata(entry, kind=kind)
    if metadata is None and token is not None:
        encoded_pid = token.split("-", maxsplit=1)[0]
        if encoded_pid.isdigit() and int(encoded_pid) > 0:
            return not _process_is_alive(int(encoded_pid))
    if metadata is None:
        return _is_old_controlled_entry(entry)
    if not metadata:
        return False
    if token is not None and metadata["token"] != token:
        return False
    if _process_is_alive(metadata["pid"]):
        return False
    # Read twice: a writer racing an owner read is never reclaimed.
    return _read_owner_metadata(entry, kind=kind) == metadata


def _remove_controlled_entry(entry: Path, parent: Path) -> bool:
    if entry.parent != parent or entry.is_symlink() or not entry.is_dir():
        return False
    shutil.rmtree(entry)
    return True


def _recover_stale_backup(entry: Path, output_name: str) -> None:
    destination = _controlled_destination(entry, output_name)
    if not destination.exists() and not destination.is_symlink():
        try:
            verify_completed_output(entry)
        except (OSError, ValueError):
            pass
        else:
            os.replace(entry, destination)
            return
    _remove_controlled_entry(entry, entry.parent)


def _recover_stale_controlled_entries(parent: Path, output_name: str) -> None:
    for entry in tuple(parent.iterdir()):
        controlled = _controlled_entry_kind(entry.name, output_name)
        if controlled is None:
            continue
        kind, token = controlled
        if not _owner_is_stale(entry, kind=kind, token=token):
            continue
        if kind == "backup":
            _recover_stale_backup(entry, output_name)
        else:
            _remove_controlled_entry(entry, parent)


@contextmanager
def _allocation_lock(parent: Path, output_name: str, *, timeout_seconds: float = 5.0):
    lock = parent / f".{output_name}.allocation.lock"
    owner = {"pid": os.getpid(), "token": uuid.uuid4().hex}
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            lock.mkdir()
        except FileExistsError as error:
            if _owner_is_stale(lock, kind="lock"):
                _remove_controlled_entry(lock, parent)
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError("output allocation lock is busy") from error
            time.sleep(0.01)
        else:
            try:
                _write_owner_metadata(
                    lock, kind="lock", pid=owner["pid"], token=owner["token"]
                )
            except Exception:
                _remove_controlled_entry(lock, parent)
                raise
            break
    try:
        _recover_stale_controlled_entries(parent, output_name)
        yield owner
    finally:
        metadata = _read_owner_metadata(lock, kind="lock")
        if metadata is not None and metadata.get("token") == owner["token"]:
            _remove_controlled_entry(lock, parent)


def _reservation_glob(parent: Path, destination: Path) -> str:
    return f".{destination.name}.reserve.*"


def _reserve_destination(parent: Path, destination: Path, token: str) -> Path:
    reservation = parent / f".{destination.name}.reserve.{token}"
    reservation.mkdir()
    return reservation


def _find_non_overwrite_destination(
    output: Path,
    evaluation_identity: str,
    *,
    owner: Mapping[str, Any] | None = None,
) -> tuple[Path, Path | None]:
    if output.exists() or output.is_symlink():
        if not output.is_dir():
            raise ValueError("existing output is not a completed directory")
        try:
            manifest = verify_completed_output(output)
        except ValueError as error:
            raise ValueError(
                f"existing output is invalid and was not modified: {error}"
            ) from error
        if manifest["evaluation_identity"] == evaluation_identity:
            return output, None

    token = (
        f"{owner['pid']}-{owner['token']}"
        if owner is not None else f"{os.getpid()}-{uuid.uuid4().hex}"
    )
    if (
        not output.exists()
        and not output.is_symlink()
        and not list(output.parent.glob(_reservation_glob(output.parent, output)))
    ):
        return output, _reserve_destination(
            output.parent, output, token,
        )

    version = 1
    while True:
        destination = output.with_name(f"{output.name}.v{version:06d}")
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                try:
                    manifest = verify_completed_output(destination)
                except ValueError:
                    pass
                else:
                    if manifest["evaluation_identity"] == evaluation_identity:
                        return destination, None
            version += 1
            continue
        if list(output.parent.glob(_reservation_glob(output.parent, destination))):
            version += 1
            continue
        try:
            return destination, _reserve_destination(
                output.parent, destination, token,
            )
        except FileExistsError:
            version += 1


def _replace_with_permission_retry(
    replace: Any,
    source: str | Path,
    destination: str | Path,
    *,
    attempts: int = 10,
    delay_seconds: float = 0.02,
) -> None:
    for attempt in range(attempts):
        try:
            replace(source, destination)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(delay_seconds)


def _publish_output(
    destination: Path,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    overwrite: bool,
    write: Any,
    replace: Any,
    reservation: Path | None,
    owner: Mapping[str, Any],
) -> Path:
    stage: Path | None = None
    backup: Path | None = None
    moved_existing = False
    committed = False
    try:
        stage = destination.parent / (
            f".{destination.name}.stage.{owner['pid']}-{owner['token']}"
        )
        stage.mkdir()
        backup = destination.parent / (
            f".{destination.name}.backup.{owner['pid']}-{owner['token']}"
        )
        ordered_paths = [
            path for path in plan.intended_relative_paths
            if path != "evaluation_manifest.json"
        ]
        if "evaluation_manifest.json" in plan.intended_relative_paths:
            ordered_paths.append("evaluation_manifest.json")
        for relative_path in ordered_paths:
            write(stage / relative_path, artifacts[relative_path])
        if overwrite and destination.exists():
            if backup.exists():
                raise RuntimeError("controlled output backup already exists")
            _replace_with_permission_retry(replace, destination, backup)
            moved_existing = True
        elif destination.exists() or destination.is_symlink():
            raise RuntimeError("reserved output destination became occupied")

        _replace_with_permission_retry(replace, stage, destination)
        committed = True
        return destination
    except Exception as error:
        restored = False
        if (
            moved_existing
            and backup is not None
            and backup.exists()
            and not destination.exists()
        ):
            try:
                _replace_with_permission_retry(replace, backup, destination)
                restored = True
            except Exception as restore_error:
                raise RuntimeError(
                    f"output commit and restoration failed; backup remains at {backup}"
                ) from restore_error
        message = "output commit failed; previous tree restored" if restored else "output commit failed"
        raise RuntimeError(f"{message}: {error}") from error
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if reservation is not None and reservation.exists():
            _remove_controlled_entry(reservation, reservation.parent)
        if committed and backup is not None and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)


def commit_output(
    output_root: str | Path,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    overwrite: bool = False,
    writer: Any = None,
    replace: Any = os.replace,
) -> Path:
    """Publish an exact completed tree without destructive non-overwrite behavior."""
    output = Path(output_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    expected_files = set(plan.intended_relative_paths)
    if set(artifacts.keys()) != expected_files:
        raise ValueError("artifacts must exactly match the evaluation plan")

    write = writer or _default_output_writer
    if overwrite:
        with _allocation_lock(output.parent, output.name) as owner:
            if output.exists() or output.is_symlink():
                _validate_allowlisted_tree(output, expected_files)
                verify_completed_output(output)
            return _publish_output(
                output, plan, artifacts, overwrite=True, write=write,
                replace=replace, reservation=None, owner=owner,
            )

    with _allocation_lock(output.parent, output.name) as owner:
        destination, reservation = _find_non_overwrite_destination(
            output, plan.evaluation_identity, owner=owner
        )
        if reservation is None:
            return destination
    return _publish_output(
        destination, plan, artifacts, overwrite=False, write=write,
        replace=replace, reservation=reservation, owner=owner,
    )


def verify_completed_output(
    output_root: str | Path,
    *,
    expected_identity: str | None = None,
) -> dict[str, Any]:
    """Verify any immutable completed output tree without writing to it."""
    root = Path(output_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("completed output root is not a directory")
    manifest_path = root / "evaluation_manifest.json"
    try:
        manifest = _validate_completed_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("completed evaluation manifest is unreadable") from error
    if expected_identity is not None and manifest["evaluation_identity"] != expected_identity:
        raise ValueError("evaluation identity mismatch")

    output_hashes = manifest["output_sha256s"]
    expected_files = set(output_hashes) | {"artifact_index.json", "evaluation_manifest.json"}
    try:
        actual_files, actual_directories = _relative_entries(root)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if actual_files != expected_files or actual_directories != _expected_directories(expected_files):
        raise ValueError("completed output file set mismatch")

    ordinary: dict[str, bytes] = {}
    for relative_path, expected_hash in output_hashes.items():
        payload = (root / relative_path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_hash:
            raise ValueError(f"artifact hash mismatch: {relative_path}")
        ordinary[str(relative_path)] = payload
    if (root / "artifact_index.json").read_bytes() != build_artifact_index(ordinary):
        raise ValueError("artifact index hash mismatch")
    return manifest


def generate_concept_report(
    output_root: str | Path,
    evaluation_identity: str,
    analysis_mode: str,
    methods: Sequence[Any],
    directions: Sequence[Any],
    checkpoint_policies: Sequence[Any],
    included_methods: Sequence[Any],
    canonical_tables: Mapping[Any, Any],
    report_statistics: Mapping[Any, Any],
    root_metadata: Mapping[str, Any],
    policy_metadata: Mapping[Any, Any],
    identity_inputs: Mapping[str, Any],
    library_versions: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    ci_policy: str,
    gate_states: Mapping[str, bool],
    created_utc: str,
    completed_utc: str,
    disposition: str = "completed",
    overwrite: bool = False,
    writer: Any = None,
    replace: Any = os.replace,
) -> Path:
    """
    Generate complete concept evaluation report.

    This is the main entry point for report generation.
    """
    plan = build_concept_output_plan(
        evaluation_identity, analysis_mode, methods, directions,
        checkpoint_policies, included_methods, include_artifact_index=True
    )

    required_metadata = {
        "resolved_config",
        "provenance_report",
        "method_status_rows",
        "evaluation_log",
    }
    missing_metadata = required_metadata - set(root_metadata)
    if missing_metadata:
        raise ValueError(f"missing root report metadata: {sorted(missing_metadata)}")
    artifacts: dict[str, bytes] = {
        "evaluation_config_resolved.yaml": (
            json.dumps(root_metadata["resolved_config"], sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
        "provenance_report.json": (
            json.dumps(root_metadata["provenance_report"], sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
        "method_status.csv": _csv_bytes(root_metadata["method_status_rows"]),
        "evaluation_log.txt": str(root_metadata["evaluation_log"]).encode("utf-8"),
    }
    figure_artifacts = report_statistics.get("figure_artifacts", {})
    for relative_path in plan.intended_relative_paths:
        if relative_path in artifacts or relative_path in {
            "artifact_index.json", "evaluation_manifest.json"
        }:
            continue
        if relative_path.endswith(".png"):
            payload = figure_artifacts.get(relative_path)
            if not isinstance(payload, bytes) or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"missing valid figure artifact: {relative_path}")
            artifacts[relative_path] = payload
            continue
        rows_or_payload = canonical_tables.get(relative_path)
        if isinstance(rows_or_payload, bytes):
            artifacts[relative_path] = rows_or_payload
        elif isinstance(rows_or_payload, Sequence) and rows_or_payload:
            artifacts[relative_path] = _csv_bytes(rows_or_payload)
        else:
            raise ValueError(f"missing canonical table artifact: {relative_path}")

    ordinary_artifacts = dict(artifacts)
    artifacts["artifact_index.json"] = build_artifact_index(ordinary_artifacts)
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, ordinary_artifacts, identity_inputs, library_versions,
        bootstrap_replicates, bootstrap_seed, ci_policy, gate_states,
        created_utc, completed_utc, disposition,
    )
    return commit_output(
        output_root, plan, artifacts, overwrite=overwrite,
        writer=writer, replace=replace,
    )