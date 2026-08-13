"""Deterministic synthetic lifecycle and contract coverage for Phase 17."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

import pada3dacb.experiments.ablations as ablations
from pada3dacb.experiments.ablations import (
    APPROVED_ABLATIONS,
    MONITORING_LABEL,
    build_equivalence_reference,
    execute,
    load_ablation_config,
    planned_run_path,
)
from pada3dacb.experiments.prediction_export import (
    export_ablation_predictions,
    validate_ablation_prediction_records,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "experiments" / "ablations.yaml"


def test_all_approved_candidates_have_single_synthetic_dry_run_plan(tmp_path: Path) -> None:
    config = load_ablation_config(CONFIG, output_root=tmp_path / "results")

    payload = execute(
        config,
        requested_names=APPROVED_ABLATIONS,
        both_directions=True,
        all_folds=True,
        all_seeds=True,
        dry_run=True,
    )

    assert payload["mode"] == "dry-run"
    assert payload["approved_ids"] == list(APPROVED_ABLATIONS)
    assert len(payload["plans"]) == len(APPROVED_ABLATIONS) * 2 * 5
    assert all(plan["target_loader_use"] == "unlabeled_target_adaptation" for plan in payload["plans"])
    assert all(plan["forward_executed"] is False for plan in payload["plans"])
    assert all(plan["real_data_run"] is False for plan in payload["plans"])
    assert all(plan["publication_metrics_present"] is False for plan in payload["plans"])
    assert not (tmp_path / "results").exists()


def test_dry_run_covers_both_directions_and_complete_five_fold_matrix(tmp_path: Path) -> None:
    config = load_ablation_config(CONFIG, output_root=tmp_path / "results")

    payload = execute(
        config,
        requested_names=("no_proto",),
        both_directions=True,
        all_folds=True,
        all_seeds=True,
        dry_run=True,
    )

    assert {plan["direction"] for plan in payload["plans"]} == {
        "ADNI_to_OASIS",
        "OASIS_to_ADNI",
    }
    assert {plan["fold"] for plan in payload["plans"]} == set(range(5))
    assert {plan["seed"] for plan in payload["plans"]} == {42}
    assert all(plan["target_label_firewall"]["target_labels_in_adaptation"] is False for plan in payload["plans"])
    assert all(
        Path(plan["output_dir"]).parts[-2] == "seed_42"
        and Path(plan["output_dir"]).parts[-1].startswith("fold_")
        for plan in payload["plans"]
    )
    assert not (tmp_path / "results").exists()


def test_validate_only_is_no_grad_no_optimizer_step_and_preserves_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_ablation_config(CONFIG, output_root=tmp_path / "results")
    observed_grad_modes: list[bool] = []
    original_forward = ablations.ComposedCoreLoss.forward

    def probe_forward(*args: object, **kwargs: object) -> object:
        observed_grad_modes.append(torch.is_grad_enabled())
        return original_forward(*args, **kwargs)  # type: ignore[arg-type]

    def fail_backward(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("validate-only must not call backward")

    def fail_step(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("validate-only must not step an optimizer")

    monkeypatch.setattr(ablations.ComposedCoreLoss, "forward", probe_forward)
    monkeypatch.setattr(torch.Tensor, "backward", fail_backward)
    monkeypatch.setattr(torch.optim.Optimizer, "step", fail_step)

    payload = execute(
        config,
        requested_names=APPROVED_ABLATIONS,
        source_domain="ADNI",
        target_domain="OASIS",
        fold=0,
        seed=42,
        validate_only=True,
    )

    assert len(payload["plans"]) == len(APPROVED_ABLATIONS)
    assert observed_grad_modes and not any(observed_grad_modes)
    assert all(plan["validated"] is True for plan in payload["plans"])
    assert all(plan["backward_executed"] is False for plan in payload["plans"])
    assert all(plan["optimizer_step_executed"] is False for plan in payload["plans"])
    assert all(plan["target_batch_keys"] == ["cohort", "subject_hash", "subject_id", "x"] for plan in payload["plans"])
    assert all(plan["target_labels_in_adaptation"] is False for plan in payload["plans"])
    assert all(plan["target_monitoring_label"] == MONITORING_LABEL for plan in payload["plans"])
    assert all("ContextualROIEncoder" not in plan["model_variant"] for plan in payload["plans"])
    assert not (tmp_path / "results").exists()


def test_validate_only_reports_disabled_terms_and_mean_pool_variant(tmp_path: Path) -> None:
    config = load_ablation_config(CONFIG, output_root=tmp_path / "results")

    payload = execute(
        config,
        requested_names=APPROVED_ABLATIONS,
        source_domain="OASIS",
        target_domain="ADNI",
        fold=4,
        seed=42,
        validate_only=True,
    )
    plans = {plan["ablation_id"]: plan for plan in payload["plans"]}

    assert plans["no_cons"]["validated"] is True
    assert plans["no_concept"]["validated"] is True
    assert plans["no_anat"]["validated"] is True
    assert plans["mean_pool"]["model_variant"] == "PADA-3DACB+MeanPoolAggregator"
    assert all(plan["model_variant"] == "PADA-3DACB" for name, plan in plans.items() if name != "mean_pool")
    assert all(plan["target_monitoring_enabled"] is True for plan in plans.values())


def test_supported_output_path_prediction_and_equivalence_schemas(tmp_path: Path) -> None:
    config = load_ablation_config(CONFIG, output_root=tmp_path / "results")
    path = planned_run_path(config, "no_proto", "ADNI_to_OASIS", 42, 3)
    assert path == tmp_path / "results" / "ablations" / "no_proto" / "ADNI_to_OASIS" / "seed_42" / "fold_3"

    reference = build_equivalence_reference("no_domain_adaptation")
    assert reference["canonical_id"] is None
    assert reference["disposition"] == "BLOCKED_NOT_PROVEN"
    assert reference["real_data_run"] is False
    assert reference["publication_metrics_present"] is False
    assert reference["equivalence_manifest_hash"]

    identity = "a" * 64
    records = [
        {
            "schema_version": "phase17.prediction.v1",
            "subject_id": "synthetic-target-adaptation-0",
            "subject_hash": "synthetic-target-adaptation-hash-0",
            "cohort": "OASIS",
            "dataset_role": "target_adaptation",
            "target_labels_present": False,
            "target_label_usage": "forbidden",
            "direction": "ADNI_to_OASIS",
            "method": "ablation",
            "model": "PADA-3DACB",
            "fold": 0,
            "seed": 42,
            "checkpoint_name": "checkpoint_last.pt",
            "checkpoint_epoch": 1,
            "split": "target_adaptation",
            "experiment_hash": identity,
            "predicted_class_z": 0,
            "predicted_class_c": 0,
        },
        {
            "schema_version": "phase17.prediction.v1",
            "subject_id": "synthetic-target-evaluation-0",
            "subject_hash": "synthetic-target-evaluation-hash-0",
            "cohort": "OASIS",
            "dataset_role": "target_evaluation",
            "target_labels_present": True,
            "target_label_usage": "monitoring_only",
            "direction": "ADNI_to_OASIS",
            "method": "ablation",
            "model": "PADA-3DACB",
            "fold": 0,
            "seed": 42,
            "checkpoint_name": "checkpoint_best_source_f1.pt",
            "checkpoint_epoch": 1,
            "split": "target_evaluation",
            "experiment_hash": identity,
            "predicted_class_z": 0,
            "predicted_class_c": 0,
        },
    ]
    validate_ablation_prediction_records(records)
    output = export_ablation_predictions(records, tmp_path / "predictions.jsonl")
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
    assert all(json.loads(line)["dataset_role"] != "target_adaptation" or not json.loads(line)["target_labels_present"] for line in output.read_text(encoding="utf-8").splitlines())


def _artifact_snapshot(run_dir: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(run_dir).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in run_dir.rglob("*")
        if path.is_file()
    }


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == len(lines)
    assert all(isinstance(record, dict) for record in records)
    return records


def test_complete_lifecycle_resume_and_completed_fold_reuse_contract(tmp_path: Path) -> None:
    config = load_ablation_config(CONFIG, output_root=tmp_path / "interrupted-results")
    expected_total_epochs = config.payload["epochs"]["warm"] + config.payload["epochs"]["full"]

    interrupted = ablations.run_synthetic_lifecycle(
        config,
        "no_proto",
        direction="ADNI_to_OASIS",
        seed=42,
        fold=0,
        interrupt_after=2,
    )
    run_dir = interrupted.output_dir
    assert interrupted.status == "INTERRUPTED"
    assert interrupted.completed_epochs == 2
    assert interrupted.total_epochs == expected_total_epochs == 55
    assert (run_dir / "checkpoint_last.pt").exists()
    assert (run_dir / "checkpoint_best_source_f1.pt").exists()
    assert (run_dir / "training_history.json").exists()
    assert (run_dir / "artifact_index.json").exists()
    assert not (run_dir / "target_adaptation_predictions.jsonl").exists()

    validation = ablations.validate_resume_identity(
        config,
        run_dir,
        requested_name="no_proto",
        direction="ADNI_to_OASIS",
        seed=42,
        fold=0,
    )
    assert validation.valid, validation.mismatches

    interrupted_history = json.loads((run_dir / "training_history.json").read_text(encoding="utf-8"))
    assert [row["epoch"] for row in interrupted_history["rows"]] == [1, 2]

    resumed = ablations.resume_synthetic_lifecycle(
        config,
        run_dir,
        requested_name="no_proto",
        direction="ADNI_to_OASIS",
        seed=42,
        fold=0,
    )
    assert resumed.status == "COMPLETED"
    assert resumed.reused is False
    assert resumed.completed_epochs == resumed.total_epochs == expected_total_epochs

    identity_payload = json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))
    outer_identity = identity_payload["identity"]
    resolved_config = json.loads((run_dir / "config_resolved.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(run_dir / "checkpoint_last.pt", map_location="cpu", weights_only=False)
    history = json.loads((run_dir / "training_history.json").read_text(encoding="utf-8"))
    equivalence_manifest = json.loads(
        (run_dir / "equivalence_manifest.json").read_text(encoding="utf-8")
    )
    artifact_index = json.loads((run_dir / "artifact_index.json").read_text(encoding="utf-8"))
    prediction_lines = (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
    rows = history["rows"]
    assert [row["epoch"] for row in rows] == list(range(1, expected_total_epochs + 1))
    assert len({row["epoch"] for row in rows}) == expected_total_epochs
    assert history["history_hash"]

    predictions = _read_jsonl(run_dir / "predictions.jsonl")

    assignment_hash_fields = (
        "source_split_assignment_hash",
        "target_adaptation_assignment_hash",
        "target_evaluation_assignment_hash",
    )
    expected_assignment_hashes = {
        field: outer_identity[field] for field in assignment_hash_fields
    }
    expected_assignments = outer_identity["assignments"]
    embedded_identities = {
        "identity.json": identity_payload["identity"],
        "config_resolved.json": resolved_config["identity"],
        "checkpoint_last.pt": checkpoint["identity"],
        "training_history.json": history["identity"],
        "equivalence_manifest.json": equivalence_manifest["identity"],
        "artifact_index.json": artifact_index["identity"],
        **{
            f"predictions.jsonl[{index}]": record["identity"]
            for index, record in enumerate(predictions)
        },
    }
    for artifact_name, embedded_identity in embedded_identities.items():
        assert {
            field: embedded_identity[field] for field in assignment_hash_fields
        } == expected_assignment_hashes, artifact_name
        assert embedded_identity["assignments"] == expected_assignments, artifact_name

    resolved_identity = resolved_config["resolved"]
    assert {
        field: resolved_identity[field] for field in assignment_hash_fields
    } == expected_assignment_hashes
    assert resolved_identity["assignments"] == expected_assignments
    assert len(prediction_lines) == len(predictions)

    assert predictions
    assert all(record["dataset_role"] != "target_adaptation" for record in predictions)
    assert all(
        record["target_labels_present"] is False
        for record in predictions
        if record["dataset_role"] == "source_validation"
    )
    assert all(
        record["target_labels_present"] is True
        for record in predictions
        if record["dataset_role"] == "target_evaluation"
    )
    assert not (run_dir / "target_adaptation_predictions.jsonl").exists()

    checkpoint = torch.load(run_dir / "checkpoint_last.pt", map_location="cpu", weights_only=False)
    best_checkpoint = torch.load(run_dir / "checkpoint_best_source_f1.pt", map_location="cpu", weights_only=False)
    assert checkpoint["target_checkpoint_selection_state"] == {}
    assert best_checkpoint["target_checkpoint_selection_state"] == {}
    assert checkpoint["best_source_validation_macro_f1"] == max(
        row["source_metrics"]["macro_f1"] for row in rows
    )
    assert all(row["target_monitoring"]["enabled"] is True for row in rows)
    assert all(row["target_monitoring"]["label"] == MONITORING_LABEL for row in rows)

    fresh_config = load_ablation_config(CONFIG, output_root=tmp_path / "fresh-results")
    fresh = ablations.run_synthetic_lifecycle(
        fresh_config,
        "no_proto",
        direction="ADNI_to_OASIS",
        seed=42,
        fold=0,
    )
    assert fresh.status == "COMPLETED"
    assert fresh.reused is False
    fresh_dir = fresh.output_dir
    for name in ("identity.json", "training_history.json", "predictions.jsonl"):
        assert (run_dir / name).read_bytes() == (fresh_dir / name).read_bytes()

    identity = json.loads((run_dir / "identity.json").read_text(encoding="utf-8"))
    fresh_identity = json.loads((fresh_dir / "identity.json").read_text(encoding="utf-8"))
    assert identity == fresh_identity
    artifact_index = json.loads((run_dir / "artifact_index.json").read_text(encoding="utf-8"))
    fresh_artifact_index = json.loads((fresh_dir / "artifact_index.json").read_text(encoding="utf-8"))
    assert artifact_index == fresh_artifact_index
    assert all(entry["content_hash"] for entry in artifact_index["entries"])

    completed_snapshot = _artifact_snapshot(run_dir)
    reused = ablations.run_synthetic_lifecycle(
        config,
        "no_proto",
        direction="ADNI_to_OASIS",
        seed=42,
        fold=0,
    )
    assert reused.status == "COMPLETED"
    assert reused.reused is True
    assert _artifact_snapshot(run_dir) == completed_snapshot

    mismatch_cases = (
        {"requested_name": "no_pl", "direction": "ADNI_to_OASIS", "seed": 42, "fold": 0},
        {"requested_name": "no_proto", "direction": "OASIS_to_ADNI", "seed": 42, "fold": 0},
        {"requested_name": "no_proto", "direction": "ADNI_to_OASIS", "seed": 42, "fold": 1},
        {"requested_name": "no_proto", "direction": "ADNI_to_OASIS", "seed": 43, "fold": 0},
    )
    for case in mismatch_cases:
        with pytest.raises(ablations.SyntheticLifecycleError):
            ablations.resume_synthetic_lifecycle(config, run_dir, **case)
        assert _artifact_snapshot(run_dir) == completed_snapshot

    mismatched_config_path = tmp_path / "mismatched-ablations.yaml"
    mismatched_config_path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(
            "synthetic-jacobian-artifact-v1", "synthetic-jacobian-artifact-v2"
        ),
        encoding="utf-8",
    )
    mismatched_config = load_ablation_config(
        mismatched_config_path,
        output_root=tmp_path / "mismatched-config-results",
    )
    with pytest.raises(ablations.SyntheticLifecycleError):
        ablations.resume_synthetic_lifecycle(
            mismatched_config,
            run_dir,
            requested_name="no_proto",
            direction="ADNI_to_OASIS",
            seed=42,
            fold=0,
        )
    assert _artifact_snapshot(run_dir) == completed_snapshot
