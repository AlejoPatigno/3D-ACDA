"""Source-only cross-cohort orchestration for approved architectural baselines."""

from __future__ import annotations

import hashlib
import json
import pickle
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd
import torch
import yaml
from sklearn.model_selection import StratifiedKFold
from torch.utils.data import DataLoader

from pada3dacb.data.baseline_dataset import ClassificationOnlyMRIDataset
from pada3dacb.exceptions import ConfigurationError
from pada3dacb.models.baselines import build_baseline, get_baseline_spec
from pada3dacb.training.baseline_trainer import BaselineTrainConfig, ClassificationOnlyTrainer

_COHORTS = {"ADNI", "OASIS"}
_REQUIRED_COLUMNS = {"x_path", "cohort"}


@dataclass(frozen=True)
class BaselineExperimentConfig:
    name: str
    baseline_names: tuple[str, ...]
    source_domain: str
    target_domain: str
    n_splits: int
    folds: tuple[int, ...]
    seeds: tuple[int, ...]
    artifact_index: Path
    output_root: Path
    roi_masks: Path | None
    baseline_configs: dict[str, dict[str, Any]]
    training: BaselineTrainConfig
    target_monitoring: bool = True
    sequential: bool = True
    overwrite: bool = False

    @property
    def direction(self) -> str:
        return f"{self.source_domain}_to_{self.target_domain}"

    def validate(self) -> None:
        if self.source_domain not in _COHORTS or self.target_domain not in _COHORTS:
            raise ConfigurationError("Baseline domains must be ADNI or OASIS.")
        if self.source_domain == self.target_domain:
            raise ConfigurationError("Source and target baseline domains must be different.")
        if self.n_splits < 2 or not self.folds or not self.seeds:
            raise ConfigurationError("Baseline folds, seeds, and n_splits must be non-empty.")
        if any(fold < 0 or fold >= self.n_splits for fold in self.folds):
            raise ConfigurationError("Baseline fold index is outside configured n_splits.")
        if not self.sequential:
            raise ConfigurationError("Phase 14 baseline execution must be sequential.")
        for name in self.baseline_names:
            try:
                spec = get_baseline_spec(name)
            except KeyError as error:
                raise ConfigurationError(f"Unknown or unapproved baseline: {name!r}.") from error
            if spec.id not in self.baseline_configs:
                raise ConfigurationError(f"Missing constructor configuration for {spec.id}.")
        self.training.validate()

    def with_direction(self, source: str, target: str) -> BaselineExperimentConfig:
        updated = replace(self, source_domain=source, target_domain=target)
        updated.validate()
        return updated

    def resolved_baseline_config(self, baseline_name: str) -> dict[str, Any]:
        baseline_id = get_baseline_spec(baseline_name).id
        resolved = dict(get_baseline_spec(baseline_id).default_config)
        resolved.update(self.baseline_configs[baseline_id])
        return resolved

    def roi_masks_hash(self, baseline_name: str) -> str | None:
        if not get_baseline_spec(baseline_name).requires_roi_masks:
            return None
        if self.roi_masks is None or not self.roi_masks.is_file():
            raise ConfigurationError("AAGN requires configured ROI-mask provenance.")
        return hashlib.sha256(self.roi_masks.read_bytes()).hexdigest()

    def run_dir(self, baseline_name: str, *, fold: int, seed: int) -> Path:
        baseline_id = get_baseline_spec(baseline_name).id
        return (
            self.output_root
            / "baselines"
            / baseline_id
            / self.direction
            / f"seed_{seed}"
            / f"fold_{fold}"
        )

    def sha256(self, baseline_name: str) -> str:
        baseline_id = get_baseline_spec(baseline_name).id
        payload = {
            "name": self.name,
            "method": "baseline",
            "baseline_id": baseline_id,
            "baseline_configuration": self.resolved_baseline_config(baseline_id),
            "roi_masks_hash": self.roi_masks_hash(baseline_id),
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "n_splits": self.n_splits,
            "folds": self.folds,
            "seeds": self.seeds,
            "training": asdict(self.training),
            "target_monitoring": self.target_monitoring,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class BaselineFoldPlan:
    baseline_id: str
    fold: int
    seed: int
    fold_seed: int
    source_train: pd.DataFrame
    source_validation: pd.DataFrame
    target_evaluation: pd.DataFrame
    input_shape: tuple[int, int, int]
    source_assignment_hash: str
    target_evaluation_assignment_hash: str
    experiment_hash: str
    target_adaptation_loader_constructed: bool = False

    @property
    def source_train_count(self) -> int:
        return len(self.source_train)

    @property
    def source_validation_count(self) -> int:
        return len(self.source_validation)

    @property
    def target_evaluation_count(self) -> int:
        return len(self.target_evaluation)


def _resolve_path(value: object, root: Path, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"Baseline path {field} must be configured.")
    path = Path(value)
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def load_baseline_config(
    path: str | Path, *, overrides: dict[str, Any] | None = None
) -> BaselineExperimentConfig:
    config_path = Path(path).resolve()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError("Baseline configuration root must be a mapping.")
    experiment = payload.get("experiment", {})
    paths = payload.get("paths", {})
    if overrides:
        for key in ("artifact_index", "output_root", "roi_masks"):
            if overrides.get(key) is not None:
                paths[key] = str(overrides[key])
        for key in ("source_domain", "target_domain"):
            if overrides.get(key) is not None:
                experiment[key] = overrides[key]
        if overrides.get("device") is not None:
            payload.setdefault("training", {})["device"] = overrides["device"]
        if overrides.get("overwrite") is not None:
            payload.setdefault("execution", {})["overwrite"] = overrides["overwrite"]
        if overrides.get("target_monitoring") is not None:
            payload.setdefault("evaluation", {})["target_monitoring"] = overrides[
                "target_monitoring"
            ]
    if experiment.get("method") != "baseline":
        raise ConfigurationError("Baseline configuration experiment.method must be 'baseline'.")
    names = tuple(experiment.get("baseline_names", ()))
    constructors: dict[str, dict[str, Any]] = {}
    for requested_name, relative in payload.get("baseline_configs", {}).items():
        try:
            baseline_id = get_baseline_spec(requested_name).id
        except KeyError as error:
            raise ConfigurationError(f"Unknown or unapproved baseline: {requested_name!r}.") from error
        baseline_path = _resolve_path(relative, config_path.parent, requested_name)
        baseline_payload = yaml.safe_load(baseline_path.read_text(encoding="utf-8"))
        section = baseline_payload.get("baseline", {})
        if section.get("id") != baseline_id or not isinstance(section.get("constructor"), dict):
            raise ConfigurationError(f"Invalid baseline constructor file for {baseline_id}.")
        constructors[baseline_id] = dict(section["constructor"])
    training_values = dict(payload.get("training", {}))
    if training_values.get("device") == "auto":
        training_values["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        training = BaselineTrainConfig(**training_values)
    except TypeError as error:
        raise ConfigurationError(f"Invalid baseline training configuration: {error}") from error
    config = BaselineExperimentConfig(
        name=str(experiment.get("name", "architectural_baselines")),
        baseline_names=names,
        source_domain=str(experiment.get("source_domain", "")),
        target_domain=str(experiment.get("target_domain", "")),
        n_splits=int(experiment.get("n_splits", 5)),
        folds=tuple(int(value) for value in experiment.get("folds", range(5))),
        seeds=tuple(int(value) for value in experiment.get("seeds", (42,))),
        artifact_index=_resolve_path(paths.get("artifact_index"), config_path.parent, "artifact_index"),
        output_root=_resolve_path(paths.get("output_root"), config_path.parent, "output_root"),
        roi_masks=(
            _resolve_path(paths.get("roi_masks"), config_path.parent, "roi_masks")
            if paths.get("roi_masks")
            else None
        ),
        baseline_configs=constructors,
        training=training,
        target_monitoring=bool(payload.get("evaluation", {}).get("target_monitoring", True)),
        sequential=bool(payload.get("execution", {}).get("sequential", True)),
        overwrite=bool(payload.get("execution", {}).get("overwrite", False)),
    )
    config.validate()
    return config


def _load_inventory(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise ConfigurationError(f"Baseline artifact index does not exist: {path}.")
    frame = pd.read_csv(path)
    if not _REQUIRED_COLUMNS.issubset(frame.columns) or not ({"label", "Label"} & set(frame.columns)):
        raise ConfigurationError("Baseline artifact index lacks x_path, cohort, or label columns.")
    if "label" not in frame:
        frame = frame.rename(columns={"Label": "label"})
    return frame


def plan_baseline_fold(
    config: BaselineExperimentConfig, baseline_name: str, *, fold: int, seed: int
) -> BaselineFoldPlan:
    config.validate()
    baseline_id = get_baseline_spec(baseline_name).id
    if baseline_id not in config.baseline_names:
        raise ConfigurationError(f"Baseline {baseline_id!r} is not selected by this experiment.")
    frame = _load_inventory(config.artifact_index)
    source = frame[frame["cohort"] == config.source_domain].reset_index(drop=True)
    target = frame[frame["cohort"] == config.target_domain].reset_index(drop=True)
    counts = source["label"].value_counts()
    if len(counts) != 3 or int(counts.min()) < config.n_splits:
        raise ConfigurationError("n_splits exceeds the smallest source class count.")
    splitter = StratifiedKFold(n_splits=config.n_splits, shuffle=True, random_state=42)
    splits = list(splitter.split(source, source["label"]))
    if fold < 0 or fold >= len(splits):
        raise ConfigurationError("Requested baseline fold is outside the split plan.")
    train_indices, validation_indices = splits[fold]
    source_train = source.iloc[train_indices].reset_index(drop=True)
    source_validation = source.iloc[validation_indices].reset_index(drop=True)

    def assignment_hash(*frames: pd.DataFrame) -> str:
        values: list[str] = []
        for selected in frames:
            key = "subject_hash" if "subject_hash" in selected else "x_path"
            values.extend(str(value) for value in selected[key])
        return hashlib.sha256("\n".join(values).encode()).hexdigest()

    sample = ClassificationOnlyMRIDataset(source_train)[0]["x"]
    input_shape = tuple(int(value) for value in sample.shape[1:])
    source_hash = assignment_hash(source_train, source_validation)
    target_hash = assignment_hash(target)
    experiment_hash = hashlib.sha256(
        f"{config.sha256(baseline_id)}:{source_hash}:{target_hash}:{fold}:{seed}".encode()
    ).hexdigest()
    return BaselineFoldPlan(
        baseline_id=baseline_id,
        fold=fold,
        seed=seed,
        fold_seed=seed + fold,
        source_train=source_train,
        source_validation=source_validation,
        target_evaluation=target,
        input_shape=input_shape,
        source_assignment_hash=source_hash,
        target_evaluation_assignment_hash=target_hash,
        experiment_hash=experiment_hash,
    )


@dataclass(frozen=True)
class BaselineFoldResult:
    baseline_id: str
    source_domain: str
    target_domain: str
    fold: int
    seed: int
    status: str
    run_dir: Path
    experiment_hash: str
    payload: dict[str, Any]
    reused: bool = False

    def summary_row(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "fold": self.fold,
            "seed": self.seed,
            "status": self.status,
            "experiment_hash": self.experiment_hash,
            "reused": self.reused,
            **self.payload,
        }


def _load_roi_masks(path: Path | None) -> torch.Tensor:
    if path is None or not path.is_file():
        raise ConfigurationError("AAGN requires a configured ROI-mask tensor.")
    value = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(value, dict):
        value = value.get("roi_masks")
    if not torch.is_tensor(value) or value.ndim != 4 or not torch.isfinite(value).all():
        raise ConfigurationError("ROI masks must be a finite tensor shaped [K,D,H,W].")
    return value.to(dtype=torch.float32)


def _build_model(config: BaselineExperimentConfig, plan: BaselineFoldPlan) -> torch.nn.Module:
    constructor = config.resolved_baseline_config(plan.baseline_id)
    if get_baseline_spec(plan.baseline_id).requires_roi_masks:
        constructor["roi_masks"] = _load_roi_masks(config.roi_masks)
    return build_baseline(plan.baseline_id, constructor)


def _loader(frame: pd.DataFrame, config: BaselineExperimentConfig, seed: int) -> DataLoader:
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        ClassificationOnlyMRIDataset(frame),
        batch_size=config.training.batch_size,
        shuffle=False,
        num_workers=config.training.num_workers,
        generator=generator,
    )


@torch.no_grad()
def _prediction_rows(
    model: torch.nn.Module,
    loader: DataLoader,
    *,
    split: str,
    checkpoint: str,
    model_name: str,
) -> list[dict[str, Any]]:
    model.eval()
    rows: list[dict[str, Any]] = []
    for batch in loader:
        output = model(batch["x"])
        logits = output["logits"] if isinstance(output, dict) else output
        probabilities = logits.softmax(dim=-1).cpu()
        for index in range(probabilities.shape[0]):
            rows.append(
                {
                    "subject_id": batch["subject_id"][index],
                    "subject_hash": batch["subject_hash"][index],
                    "cohort": batch["cohort"][index],
                    "label_name": batch["label_name"][index],
                    "label": int(batch["y"][index]),
                    "prediction": int(probabilities[index].argmax()),
                    "prob_cn": float(probabilities[index, 0]),
                    "prob_mci": float(probabilities[index, 1]),
                    "prob_ad": float(probabilities[index, 2]),
                    "split": split,
                    "checkpoint": checkpoint,
                    "method": "baseline",
                    "model": model_name,
                }
            )
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def train_baseline_cv_fold(
    config: BaselineExperimentConfig,
    baseline_name: str,
    fold: int,
    seed: int,
    *,
    dry_run: bool = False,
    validate_only: bool = False,
    resume_from: str | Path | None = None,
    interrupt_after_epoch: int | None = None,
) -> BaselineFoldResult:
    plan = plan_baseline_fold(config, baseline_name, fold=fold, seed=seed)
    run_dir = config.run_dir(plan.baseline_id, fold=fold, seed=seed)
    resolved_constructor = config.resolved_baseline_config(plan.baseline_id)
    base_payload: dict[str, Any] = {
        "fold_seed": plan.fold_seed,
        "input_shape": plan.input_shape,
        "source_train_count": plan.source_train_count,
        "source_validation_count": plan.source_validation_count,
        "target_evaluation_count": plan.target_evaluation_count,
        "source_assignment_hash": plan.source_assignment_hash,
        "target_evaluation_assignment_hash": plan.target_evaluation_assignment_hash,
        "target_adaptation_loader_constructed": False,
    }
    if dry_run:
        return BaselineFoldResult(
            plan.baseline_id, config.source_domain, config.target_domain, fold, seed,
            "PENDING", run_dir, plan.experiment_hash, base_payload,
        )

    model = _build_model(config, plan)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    source_train = _loader(plan.source_train, config, plan.fold_seed)
    source_validation = _loader(plan.source_validation, config, plan.fold_seed + 1)
    target_evaluation = _loader(plan.target_evaluation, config, plan.fold_seed + 2)
    first_batch = next(iter(source_train))
    with torch.no_grad():
        output = model(first_batch["x"])
        logits = output["logits"] if isinstance(output, dict) else output
    if logits.shape != (first_batch["x"].shape[0], 3) or not torch.isfinite(logits).all():
        raise ConfigurationError("Baseline validate-only forward must return finite [B,3] logits.")
    if validate_only:
        return BaselineFoldResult(
            plan.baseline_id, config.source_domain, config.target_domain, fold, seed,
            "VALIDATED", run_dir, plan.experiment_hash,
            {**base_payload, "parameter_count": parameter_count},
        )

    expected_identity = {
        "baseline_id": plan.baseline_id,
        "experiment_hash": plan.experiment_hash,
        "direction": config.direction,
        "fold": fold,
        "seed": seed,
        "source_assignment_hash": plan.source_assignment_hash,
        "target_evaluation_assignment_hash": plan.target_evaluation_assignment_hash,
        "baseline_configuration": resolved_constructor,
        "roi_masks_hash": config.roi_masks_hash(plan.baseline_id),
    }
    result_path = run_dir / "fold_result.json"
    if result_path.is_file() and not config.overwrite and resume_from is None:
        stored = json.loads(result_path.read_text(encoding="utf-8"))
        required = (
            run_dir / "weights.pt", run_dir / "last.pt",
            run_dir / "predictions.csv", run_dir / "run_manifest.json",
        )
        manifest = (
            json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            if (run_dir / "run_manifest.json").is_file()
            else {}
        )
        outputs_valid = False
        if all(path.is_file() for path in required):
            try:
                weights = torch.load(required[0], map_location="cpu", weights_only=True)
                last = torch.load(required[1], map_location="cpu", weights_only=True)
                predictions = pd.read_csv(required[2])
                required_prediction_columns = {
                    "subject_hash", "split", "checkpoint", "prob_cn", "prob_mci", "prob_ad",
                    "method", "model"
                }
                expected_splits = {"source_validation"}
                if config.target_monitoring:
                    expected_splits.add("target_monitoring")
                expected_counts = {
                    (split, checkpoint): (
                        plan.source_validation_count
                        if split == "source_validation"
                        else plan.target_evaluation_count
                    )
                    for split in expected_splits
                    for checkpoint in ("best_source_f1", "last")
                }
                actual_counts = predictions.groupby(["split", "checkpoint"]).size().to_dict()
                outputs_valid = (
                    isinstance(weights, dict)
                    and bool(weights)
                    and all(
                        torch.is_tensor(value) and torch.isfinite(value).all()
                        for value in weights.values()
                    )
                    and last.get("identity") == expected_identity
                    and not predictions.empty
                    and required_prediction_columns.issubset(predictions.columns)
                    and set(predictions["checkpoint"]) == {"best_source_f1", "last"}
                    and set(predictions["split"]) == expected_splits
                    and actual_counts == expected_counts
                    and set(predictions["method"]) == {"baseline"}
                    and set(predictions["model"])
                    == {get_baseline_spec(plan.baseline_id).display_name}
                )
            except (OSError, RuntimeError, ValueError, KeyError, pickle.UnpicklingError):
                outputs_valid = False
        if (
            stored.get("status") == "COMPLETED"
            and stored.get("experiment_hash") == plan.experiment_hash
            and manifest.get("experiment_hash") == plan.experiment_hash
            and manifest.get("baseline_id") == plan.baseline_id
            and manifest.get("direction") == config.direction
            and manifest.get("fold") == fold
            and manifest.get("seed") == seed
            and outputs_valid
        ):
            return BaselineFoldResult(
                plan.baseline_id, config.source_domain, config.target_domain, fold, seed,
                "COMPLETED", run_dir, plan.experiment_hash, stored["payload"], reused=True,
            )
        raise ConfigurationError("Existing baseline fold is incomplete or incompatible.")

    trainer = ClassificationOnlyTrainer(
        model, config.training, run_dir=run_dir, identity=expected_identity
    )
    started = time.perf_counter()
    training_result = trainer.fit(
        source_train, source_validation,
        target_evaluation if config.target_monitoring else None,
        resume_from=resume_from, interrupt_after_epoch=interrupt_after_epoch,
    )
    train_runtime = time.perf_counter() - started
    status = "COMPLETED" if trainer.completed_epoch == config.training.n_epochs else "INTERRUPTED"
    final_target = training_result.final_target_metrics or {}
    last_history = training_result.history[-1]
    payload = {
        **base_payload,
        "baseline_configuration": resolved_constructor,
        "training_configuration": asdict(config.training),
        "parameter_count": parameter_count,
        "best_source_epoch": training_result.best_source_epoch,
        "best_source_macro_f1": training_result.best_source_macro_f1,
        "last_source_macro_f1": last_history["source_validation/macro_f1"],
        "best_checkpoint_target_monitoring_macro_f1": final_target.get("target_evaluation/macro_f1"),
        "last_checkpoint_target_monitoring_macro_f1": last_history.get("target_evaluation/macro_f1"),
        "final_source_metrics": training_result.final_source_metrics,
        "final_target_metrics": training_result.final_target_metrics,
        "history": training_result.history,
        "train_runtime": train_runtime,
        "peak_memory": (
            int(torch.cuda.max_memory_allocated())
            if torch.cuda.is_available() and config.training.device == "cuda" else 0
        ),
        "checkpoint_paths": {
            "best_source_f1": str(run_dir / "weights.pt"),
            "last": str(run_dir / "last.pt"),
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    if status == "COMPLETED":
        best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        weights_temporary = run_dir / "weights.pt.tmp"
        torch.save(best_state, weights_temporary)
        weights_temporary.replace(run_dir / "weights.pt")
        display_name = get_baseline_spec(plan.baseline_id).display_name
        predictions = _prediction_rows(
            model, source_validation, split="source_validation",
            checkpoint="best_source_f1", model_name=display_name,
        )
        if config.target_monitoring:
            predictions += _prediction_rows(
                model, target_evaluation, split="target_monitoring",
                checkpoint="best_source_f1", model_name=display_name,
            )
        last_checkpoint = torch.load(run_dir / "last.pt", map_location="cpu", weights_only=True)
        model.load_state_dict(last_checkpoint["model"])
        predictions += _prediction_rows(
            model, source_validation, split="source_validation",
            checkpoint="last", model_name=display_name,
        )
        if config.target_monitoring:
            predictions += _prediction_rows(
                model, target_evaluation, split="target_monitoring",
                checkpoint="last", model_name=display_name,
            )
        model.load_state_dict(best_state)
        predictions_temporary = run_dir / "predictions.csv.tmp"
        pd.DataFrame(predictions).to_csv(predictions_temporary, index=False)
        predictions_temporary.replace(run_dir / "predictions.csv")
    _write_json(result_path, {"status": status, "experiment_hash": plan.experiment_hash, "payload": payload})
    _write_json(
        run_dir / "run_manifest.json",
        {
            "method": "baseline",
            "baseline_id": plan.baseline_id,
            "source_domain": config.source_domain,
            "target_domain": config.target_domain,
            "direction": config.direction,
            "fold": fold,
            "seed": seed,
            "baseline_display_name": get_baseline_spec(plan.baseline_id).display_name,
            "baseline_class": get_baseline_spec(plan.baseline_id).class_name,
            "baseline_configuration": resolved_constructor,
            "baseline_configuration_hash": config.sha256(plan.baseline_id),
            "registry_reproducibility_hash": getattr(model, "baseline_metadata", {}).get(
                "reproducibility_hash", config.sha256(plan.baseline_id)
            ),
            "notebook_provenance": get_baseline_spec(plan.baseline_id).notebook_provenance,
            "trainable_parameter_count": parameter_count,
            "optional_dependencies": get_baseline_spec(plan.baseline_id).optional_dependencies,
            "input_contract": get_baseline_spec(plan.baseline_id).input_contract,
            "requires_roi_masks": get_baseline_spec(plan.baseline_id).requires_roi_masks,
            "roi_masks_hash": config.roi_masks_hash(plan.baseline_id),
            "experiment_hash": plan.experiment_hash,
            **base_payload,
        },
    )
    return BaselineFoldResult(
        plan.baseline_id, config.source_domain, config.target_domain, fold, seed,
        status, run_dir, plan.experiment_hash, payload,
    )

def run_baseline_cv_for_cohort(
    config: BaselineExperimentConfig,
    baseline_name: str,
    *,
    dry_run: bool = False,
    validate_only: bool = False,
) -> list[BaselineFoldResult]:
    return [
        train_baseline_cv_fold(
            config,
            baseline_name,
            fold,
            seed,
            dry_run=dry_run,
            validate_only=validate_only,
        )
        for seed in config.seeds
        for fold in config.folds
    ]


def run_all_requested_baselines(
    config: BaselineExperimentConfig,
    *,
    baseline_names: tuple[str, ...] | None = None,
    dry_run: bool = False,
    validate_only: bool = False,
) -> dict[str, list[BaselineFoldResult]]:
    selected = baseline_names or config.baseline_names
    return {
        get_baseline_spec(name).id: run_baseline_cv_for_cohort(
            config, name, dry_run=dry_run, validate_only=validate_only
        )
        for name in selected
    }


def run_baseline_both_directions(
    config: BaselineExperimentConfig,
    *,
    baseline_names: tuple[str, ...] | None = None,
    dry_run: bool = False,
    validate_only: bool = False,
) -> dict[str, dict[str, list[BaselineFoldResult]]]:
    reverse = config.with_direction(config.target_domain, config.source_domain)
    return {
        config.direction: run_all_requested_baselines(
            config,
            baseline_names=baseline_names,
            dry_run=dry_run,
            validate_only=validate_only,
        ),
        reverse.direction: run_all_requested_baselines(
            reverse,
            baseline_names=baseline_names,
            dry_run=dry_run,
            validate_only=validate_only,
        ),
    }


def summarize_baseline_cv_results(
    results: list[BaselineFoldResult],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    per_fold = pd.DataFrame(result.summary_row() for result in results)
    metric_columns = [
        column
        for column in per_fold.columns
        if column.startswith(
            (
                "best_source_",
                "last_source_",
                "best_checkpoint_target_monitoring_",
                "last_checkpoint_target_monitoring_",
            )
        )
        and pd.api.types.is_numeric_dtype(per_fold[column])
    ]
    if per_fold.empty or not metric_columns:
        return per_fold, pd.DataFrame()
    grouped = (
        per_fold.groupby("baseline_id", sort=True)[metric_columns]
        .agg(["mean", "std"])
        .reset_index()
    )
    grouped.columns = [
        column if isinstance(column, str) else "_".join(part for part in column if part)
        for column in grouped.columns
    ]
    return per_fold, grouped


def build_task_scoped_binary_baseline(name: str, config: dict[str, Any]) -> torch.nn.Module:
    """Build one binary baseline without changing the historical experiment path."""
    from pada3dacb.binary import build_binary_baseline

    return build_binary_baseline(name, config)


def validate_task_scoped_binary_baseline(name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Validate one binary baseline on synthetic CPU tensors only."""
    from pada3dacb.binary import validate_binary_baseline

    return validate_binary_baseline(name, config)


def validate_task_scoped_binary_baselines(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate AAGN and FasterSNN under the explicit binary task contract."""
    from pada3dacb.binary import BINARY_BASELINES

    return {name: validate_task_scoped_binary_baseline(name, config) for name in BINARY_BASELINES}
