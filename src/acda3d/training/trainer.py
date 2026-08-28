"""Fixed-epoch core training engine for synthetic and future experiment wiring."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
import yaml

from acda3d.exceptions import TrainingRuntimeError
from acda3d.losses import CoreACDA3DLoss
from acda3d.training.checkpointing import (
    load_training_checkpoint,
    restore_training_checkpoint,
    save_training_checkpoint,
)
from acda3d.training.history import TrainingHistory
from acda3d.training.monitoring import evaluate_labeled_loader
from acda3d.training.runtime import (
    loader_generator_state,
    move_batch,
    require_batch_keys,
    restore_loader_generator_state,
    validate_nonempty_loader,
)


@dataclass(frozen=True)
class FixedEpochTrainingConfig:
    warmup_epochs: int = 20
    full_epochs: int = 30
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    gradient_clip_norm: float = 5.0
    mixed_precision: bool = False
    fail_on_nonfinite_loss: bool = True
    checkpoint_every: int = 5
    source_evaluation_every: int = 1
    target_monitoring_every: int = 1
    target_monitoring_enabled: bool = True
    save_last: bool = True
    save_best_source_f1: bool = True
    device: str = "cpu"
    seed: int = 42

    def validate(self) -> None:
        if self.warmup_epochs < 0 or self.full_epochs < 0:
            raise TrainingRuntimeError("Fixed epoch counts must be non-negative.")
        if self.warmup_epochs + self.full_epochs <= 0:
            raise TrainingRuntimeError("At least one fixed training epoch is required.")
        if self.learning_rate <= 0 or self.weight_decay < 0:
            raise TrainingRuntimeError("Invalid AdamW learning rate or weight decay.")
        if self.gradient_clip_norm <= 0:
            raise TrainingRuntimeError("gradient_clip_norm must be positive.")
        if min(self.checkpoint_every, self.source_evaluation_every, self.target_monitoring_every) <= 0:
            raise TrainingRuntimeError("Checkpoint and evaluation frequencies must be positive.")

    @property
    def total_epochs(self) -> int:
        return self.warmup_epochs + self.full_epochs


def build_optimizer(model: torch.nn.Module, config: FixedEpochTrainingConfig) -> torch.optim.AdamW:
    return torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )


class BaseFixedEpochTrainer:
    def __init__(
        self,
        model: torch.nn.Module,
        loss_fn: CoreACDA3DLoss,
        feature_roi_masks: torch.Tensor,
        run_dir: str | Path,
        *,
        config: FixedEpochTrainingConfig | None = None,
        optimizer: torch.optim.Optimizer | None = None,
        scheduler: Any = None,
        split_assignment_hash: str = "synthetic-split",
        atlas_hash: str = "synthetic-atlas",
        roi_order_hash: str = "synthetic-roi-order",
    ):
        self.config = config or FixedEpochTrainingConfig()
        self.config.validate()
        self.device = torch.device(self.config.device)
        self.model = model.to(self.device)
        self.loss_fn = loss_fn.to(self.device)
        self.roi_masks = feature_roi_masks.to(self.device)
        self.optimizer = optimizer or build_optimizer(self.model, self.config)
        self.scheduler = scheduler
        self.scaler = torch.amp.GradScaler(
            "cuda", enabled=self.config.mixed_precision and self.device.type == "cuda"
        )
        self.run_dir = Path(run_dir)
        self.split_assignment_hash = split_assignment_hash
        self.atlas_hash = atlas_hash
        self.roi_order_hash = roi_order_hash
        self.global_step = 0
        self.best_source_macro_f1 = float("-inf")
        self.completed_epoch = 0
        self.history = TrainingHistory()
        self.resolved_configuration = {
            "model_name": "3D-ACDA",
            "num_rois": getattr(model, "num_rois", None),
            "num_classes": getattr(model, "num_classes", None),
            "training": asdict(self.config),
        }

    def _stage(self, epoch: int) -> str:
        return "warm" if epoch <= self.config.warmup_epochs else "full"

    def _train_epoch(self, loader: Any, stage: str) -> dict[str, float]:
        self.model.train()
        sums: dict[str, float] = {}
        batches = 0
        for raw_batch in loader:
            require_batch_keys(raw_batch, ["x", "y", "c_target", "g_bar"])
            batch = move_batch(raw_batch, self.device)
            self.optimizer.zero_grad(set_to_none=True)
            with torch.autocast(
                device_type=self.device.type,
                enabled=self.config.mixed_precision and self.device.type == "cuda",
            ):
                output = self.model(batch["x"], self.roi_masks)
                losses = self.loss_fn(
                    output, batch["y"], batch["c_target"], batch["g_bar"], stage=stage
                )
            if self.config.fail_on_nonfinite_loss and not torch.isfinite(losses.total):
                raise TrainingRuntimeError("Non-finite total loss detected before backward.")
            if self.scaler.is_enabled():
                self.scaler.scale(losses.total).backward()
                self.scaler.unscale_(self.optimizer)
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.config.gradient_clip_norm
                )
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                losses.total.backward()
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.config.gradient_clip_norm
                )
                self.optimizer.step()
            values = losses.detached()
            values["gradient_norm"] = float(gradient_norm.detach().cpu())
            for key, value in values.items():
                sums[key] = sums.get(key, 0.0) + value
            batches += 1
            self.global_step += 1
        return {key: value / batches for key, value in sums.items()}

    def _validate_adaptation_loader(self, target_adaptation_loader: Any | None) -> None:
        if target_adaptation_loader is not None:
            raise TrainingRuntimeError("Source-only training does not accept target adaptation.")

    def _train_epoch_for_stage(
        self, source_loader: Any, target_adaptation_loader: Any | None, stage: str
    ) -> dict[str, float]:
        return self._train_epoch(source_loader, stage)

    def _loader_states(
        self, source_loader: Any, target_adaptation_loader: Any | None
    ) -> dict[str, torch.Tensor | None]:
        return {"source_train": loader_generator_state(source_loader)}

    def _checkpoint_extra(self) -> dict[str, Any]:
        return {}

    def _validate_resume_extra(self, checkpoint: dict[str, Any]) -> None:
        return None

    def _restore_extra_loader_states(
        self, target_adaptation_loader: Any | None, states: dict[str, Any]
    ) -> None:
        return None

    def _history_metadata(self, stage: str) -> dict[str, Any]:
        return {}

    def _checkpoint(
        self,
        filename: str,
        epoch: int,
        stage: str,
        source_loader: Any,
        target_adaptation_loader: Any | None = None,
    ) -> Path:
        return save_training_checkpoint(
            self.run_dir / filename,
            model=self.model,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            scaler=self.scaler,
            epoch=epoch,
            global_step=self.global_step,
            best_source_macro_f1=self.best_source_macro_f1,
            stage=stage,
            resolved_configuration=self.resolved_configuration,
            split_assignment_hash=self.split_assignment_hash,
            atlas_hash=self.atlas_hash,
            roi_order_hash=self.roi_order_hash,
            random_seed=self.config.seed,
            history_rows=self.history.rows,
            loader_generator_states=self._loader_states(
                source_loader, target_adaptation_loader
            ),
            extra_payload=self._checkpoint_extra(),
        )

    def _resume(
        self,
        checkpoint_path: str | Path,
        source_loader: Any,
        target_adaptation_loader: Any | None = None,
    ) -> None:
        checkpoint = load_training_checkpoint(checkpoint_path)
        self._validate_resume_extra(checkpoint)
        restore_training_checkpoint(
            checkpoint,
            model=self.model,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            scaler=self.scaler,
            resolved_configuration=self.resolved_configuration,
            split_assignment_hash=self.split_assignment_hash,
            atlas_hash=self.atlas_hash,
            roi_order_hash=self.roi_order_hash,
        )
        self.completed_epoch = int(checkpoint["epoch"])
        self.global_step = int(checkpoint["global_step"])
        self.best_source_macro_f1 = float(checkpoint["best_source_macro_f1"])
        self.history = TrainingHistory(list(checkpoint.get("history_rows", [])))
        restore_loader_generator_state(
            source_loader, checkpoint.get("loader_generator_states", {}).get("source_train")
        )
        self._restore_extra_loader_states(
            target_adaptation_loader, checkpoint.get("loader_generator_states", {})
        )

    def fit(
        self,
        source_train_loader: Any,
        source_validation_loader: Any,
        target_monitoring_loader: Any | None = None,
        *,
        target_adaptation_loader: Any | None = None,
        resume_from: str | Path | None = None,
        interrupt_after_epoch: int | None = None,
    ) -> TrainingHistory:
        validate_nonempty_loader(source_train_loader, "source_train_loader")
        validate_nonempty_loader(source_validation_loader, "source_validation_loader")
        if target_monitoring_loader is not None:
            validate_nonempty_loader(target_monitoring_loader, "target_monitoring_loader")
        self._validate_adaptation_loader(target_adaptation_loader)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "config_resolved.yaml").write_text(
            yaml.safe_dump(self.resolved_configuration, sort_keys=True), encoding="utf-8"
        )
        (self.run_dir / "reproducibility_metadata.json").write_text(
            json.dumps(
                {
                    "seed": self.config.seed,
                    "split_assignment_hash": self.split_assignment_hash,
                    "atlas_hash": self.atlas_hash,
                    "roi_order_hash": self.roi_order_hash,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        if resume_from is not None:
            self._resume(resume_from, source_train_loader, target_adaptation_loader)
        final_epoch = self.config.total_epochs
        if interrupt_after_epoch is not None:
            if not self.completed_epoch < interrupt_after_epoch <= final_epoch:
                raise TrainingRuntimeError("interrupt_after_epoch is outside the remaining run.")
            final_epoch = interrupt_after_epoch
        for epoch in range(self.completed_epoch + 1, final_epoch + 1):
            stage = self._stage(epoch)
            started = time.perf_counter()
            train = self._train_epoch_for_stage(
                source_train_loader, target_adaptation_loader, stage
            )
            train_seconds = time.perf_counter() - started
            validation_started = time.perf_counter()
            source_metrics: dict[str, float | str] = {}
            if epoch % self.config.source_evaluation_every == 0:
                source_metrics = evaluate_labeled_loader(
                    self.model,
                    source_validation_loader,
                    self.roi_masks,
                    self.device,
                    loss_fn=self.loss_fn,
                    stage=stage,
                    namespace="source_validation",
                )
            validation_seconds = time.perf_counter() - validation_started
            target_started = time.perf_counter()
            target_metrics: dict[str, float | str] = {}
            if (
                self.config.target_monitoring_enabled
                and target_monitoring_loader is not None
                and epoch % self.config.target_monitoring_every == 0
            ):
                target_metrics = evaluate_labeled_loader(
                    self.model,
                    target_monitoring_loader,
                    self.roi_masks,
                    self.device,
                    namespace="target_monitoring",
                )
            target_seconds = time.perf_counter() - target_started
            source_f1 = source_metrics.get("source_validation/macro_f1")
            improved = source_f1 is not None and float(source_f1) > self.best_source_macro_f1
            if improved:
                self.best_source_macro_f1 = float(source_f1)
            row: dict[str, Any] = {
                "epoch": epoch,
                "stage": stage,
                "global_step": self.global_step,
                "learning_rate": self.optimizer.param_groups[0]["lr"],
                "epoch_train_seconds": train_seconds,
                "source_validation_seconds": validation_seconds,
                "target_monitoring_seconds": target_seconds,
                "peak_cuda_memory": (
                    int(torch.cuda.max_memory_allocated()) if self.device.type == "cuda" else 0
                ),
                **{f"train/{key}": value for key, value in train.items()},
                **self._history_metadata(stage),
                **source_metrics,
                **target_metrics,
            }
            self.history.append(row)
            self.completed_epoch = epoch
            self.history.flush(self.run_dir)
            if self.scheduler is not None:
                self.scheduler.step()
            checkpoint_started = time.perf_counter()
            if improved and self.config.save_best_source_f1:
                self._checkpoint(
                    "checkpoint_best_source_f1.pt",
                    epoch,
                    stage,
                    source_train_loader,
                    target_adaptation_loader,
                )
            if epoch % self.config.checkpoint_every == 0:
                self._checkpoint(
                    f"checkpoint_epoch_{epoch:03d}.pt",
                    epoch,
                    stage,
                    source_train_loader,
                    target_adaptation_loader,
                )
            if self.config.save_last:
                self._checkpoint(
                    "checkpoint_last.pt",
                    epoch,
                    stage,
                    source_train_loader,
                    target_adaptation_loader,
                )
            row["checkpoint_seconds"] = time.perf_counter() - checkpoint_started
            self.history.flush(self.run_dir)
        return self.history
