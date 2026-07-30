"""Report orchestration and output management for concept evaluation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import time
from collections.abc import Mapping, Sequence
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

    for direction in directions:
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

    if include_artifact_index:
        paths.append("artifact_index.json")

    paths.append("evaluation_manifest.json")

    return ConceptEvaluationPlan(
        evaluation_identity=evaluation_identity,
        analysis_mode=analysis_mode,
        methods=tuple(methods),
        directions=tuple(directions),
        checkpoint_policies=tuple(checkpoint_policies),
        intended_relative_paths=tuple(sorted(paths)),
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
    rows = []
    for direction in directions:
        for policy in policies:
            for method in methods:
                rows.append({
                    "method": method.value,
                    "direction": direction.value,
                    "checkpoint_policy": policy.logical_checkpoint,
                    "status": "included",
                    "reason": "fixture_only",
                })
            for method in (MethodId.AAGN, MethodId.FASTER_SNN):
                rows.append({
                    "method": method.value,
                    "direction": direction.value,
                    "checkpoint_policy": policy.logical_checkpoint,
                    "status": "not_applicable_no_pada3dacb_concept_head",
                    "reason": "no_pada3dacb_concept_head",
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
    plan = build_concept_output_plan(
        evaluation_identity,
        "synthetic_test_only",
        methods,
        directions,
        checkpoint_policies,
        tuple(methods),
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


def _relative_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


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


def commit_output(
    output_root: str | Path,
    plan: ConceptEvaluationPlan,
    artifacts: Mapping[str, bytes],
    *,
    overwrite: bool = False,
    writer: Any = None,
    replace: Any = os.replace,
) -> Path:
    """Stage a complete allowlisted tree and publish it with the manifest written last."""
    output = Path(output_root)
    output.parent.mkdir(parents=True, exist_ok=True)

    if set(artifacts.keys()) != set(plan.intended_relative_paths):
        raise ValueError("artifacts must exactly match the evaluation plan")

    write = writer or _default_output_writer

    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage.", dir=output.parent))
    token = stage.name.rsplit(".", maxsplit=1)[-1]
    backup = output.parent / f".{output.name}.backup.{token}"

    moved_existing = False
    try:
        ordered_paths = [
            path for path in plan.intended_relative_paths
            if path != "evaluation_manifest.json"
        ]
        if "evaluation_manifest.json" in plan.intended_relative_paths:
            ordered_paths.append("evaluation_manifest.json")
        for relative_path in ordered_paths:
            write(stage / relative_path, artifacts[relative_path])

        if output.exists():
            if not output.is_dir():
                raise RuntimeError("recognized output exists and is not a directory")
            unknown = _relative_files(output) - set(plan.intended_relative_paths)
            if unknown and not overwrite:
                raise RuntimeError(f"unknown output paths block overwrite: {sorted(unknown)}")
            _replace_with_permission_retry(replace, output, backup)
            moved_existing = True

        _replace_with_permission_retry(replace, stage, output)

        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)

        return output

    except Exception as error:
        restored = False
        if moved_existing and backup.exists() and not output.exists():
            try:
                _replace_with_permission_retry(replace, backup, output)
                restored = True
            except Exception as restore_error:
                raise RuntimeError(
                    f"output commit and restoration failed; backup remains at {backup}"
                ) from restore_error
        message = "output commit failed; previous tree restored" if restored else "output commit failed"
        raise RuntimeError(message) from error
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if backup.exists() and output.exists():
            shutil.rmtree(backup, ignore_errors=True)


def verify_completed_output(
    output_root: str | Path,
    *,
    expected_identity: str | None = None,
) -> dict[str, Any]:
    """Verify an immutable completed synthetic bundle without writing to it."""
    root = Path(output_root)
    manifest_path = root / "evaluation_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("completed evaluation manifest is unreadable") from error
    if manifest.get("analysis_mode") != "synthetic_test_only":
        raise ValueError("completed output is not fixture-only")
    if expected_identity is not None and manifest.get("evaluation_identity") != expected_identity:
        raise ValueError("evaluation identity mismatch")

    output_hashes = manifest.get("output_sha256s")
    if not isinstance(output_hashes, Mapping):
        raise ValueError("completed output hashes are missing")
    expected_files = set(output_hashes) | {"artifact_index.json", "evaluation_manifest.json"}
    if _relative_files(root) != expected_files:
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