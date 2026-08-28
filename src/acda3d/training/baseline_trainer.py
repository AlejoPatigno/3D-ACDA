"""Fixed-epoch classification-only training for architectural baselines."""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from torch import nn

from acda3d.exceptions import TrainingRuntimeError


@dataclass(frozen=True)
class BaselineTrainConfig:
    n_epochs: int = 25
    lr: float = 1e-4
    weight_decay: float = 1e-4
    batch_size: int = 2
    num_workers: int = 0
    use_amp: bool = True
    grad_clip_norm: float = 1.0
    device: str = "auto"
    scheduler: str | None = "cosine"
    label_smoothing: float = 0.0
    seed: int = 42

    def validate(self) -> None:
        if self.n_epochs <= 0:
            raise TrainingRuntimeError("n_epochs must be a positive fixed count.")
        if self.lr <= 0 or self.weight_decay < 0:
            raise TrainingRuntimeError("Invalid AdamW learning rate or weight decay.")
        if self.grad_clip_norm <= 0 or not 0 <= self.label_smoothing < 1:
            raise TrainingRuntimeError("Invalid gradient clipping or label smoothing value.")
        if self.scheduler not in (None, "cosine"):
            raise TrainingRuntimeError(f"Unsupported baseline scheduler: {self.scheduler!r}.")


class ClassificationOnlyLoss(nn.Module):
    def __init__(self, label_smoothing: float = 0.0) -> None:
        super().__init__()
        self.label_smoothing = float(label_smoothing)

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        return torch.nn.functional.cross_entropy(
            logits, labels, label_smoothing=self.label_smoothing
        )


@dataclass(frozen=True)
class BaselineTrainingResult:
    history: list[dict[str, float | int]]
    best_source_epoch: int
    best_source_macro_f1: float
    final_source_metrics: dict[str, float]
    final_target_metrics: dict[str, float] | None


def _logits(output: object) -> torch.Tensor:
    value = output.get("logits") if isinstance(output, dict) else output
    if not torch.is_tensor(value) or value.ndim != 2 or value.shape[1] != 3:
        raise TrainingRuntimeError("Baseline output must contain raw logits shaped [B,3].")
    if not torch.isfinite(value).all():
        raise TrainingRuntimeError("Baseline logits contain non-finite values.")
    return value


class ClassificationOnlyTrainer:
    """Train on source labels only; target evaluation is read-only monitoring."""

    uses_target_adaptation = False

    def __init__(
        self,
        model: nn.Module,
        config: BaselineTrainConfig | None = None,
        *,
        run_dir: str | Path | None = None,
        identity: dict[str, Any] | None = None,
    ) -> None:
        self.config = config or BaselineTrainConfig()
        self.config.validate()
        device = self.config.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.loss_fn = ClassificationOnlyLoss(self.config.label_smoothing).to(self.device)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.config.lr, weight_decay=self.config.weight_decay
        )
        self.scheduler = (
            torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer, T_max=self.config.n_epochs
            )
            if self.config.scheduler == "cosine"
            else None
        )
        self.scaler = torch.amp.GradScaler(
            "cuda", enabled=self.config.use_amp and self.device.type == "cuda"
        )
        self.run_dir = Path(run_dir) if run_dir is not None else None
        self.identity = dict(identity or {})
        self.history: list[dict[str, float | int]] = []
        self.completed_epoch = 0
        self.best_source_epoch = 0
        self.best_source_macro_f1 = float("-inf")
        self._best_state: dict[str, torch.Tensor] | None = None

    def train_epoch(self, loader: Any) -> float:
        self.model.train()
        total = 0.0
        batches = 0
        for batch in loader:
            if not isinstance(batch, dict) or not {"x", "y"}.issubset(batch):
                raise TrainingRuntimeError("Baseline training batches require x and y.")
            x = batch["x"].to(self.device)
            y = batch["y"].to(self.device)
            self.optimizer.zero_grad(set_to_none=True)
            with torch.autocast(
                device_type=self.device.type,
                enabled=self.config.use_amp and self.device.type == "cuda",
            ):
                loss = self.loss_fn(_logits(self.model(x)), y)
            if not torch.isfinite(loss):
                raise TrainingRuntimeError("Non-finite baseline loss detected before backward.")
            if self.scaler.is_enabled():
                self.scaler.scale(loss).backward()
                self.scaler.unscale_(self.optimizer)
                nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip_norm)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip_norm)
                self.optimizer.step()
            total += float(loss.detach().cpu())
            batches += 1
        if batches == 0:
            raise TrainingRuntimeError("Baseline training loader cannot be empty.")
        return total / batches

    @torch.no_grad()
    def evaluate(self, loader: Any, prefix: str) -> dict[str, float]:
        self.model.eval()
        labels: list[torch.Tensor] = []
        probabilities: list[torch.Tensor] = []
        losses: list[float] = []
        for batch in loader:
            x = batch["x"].to(self.device)
            y = batch["y"].to(self.device)
            logits = _logits(self.model(x))
            labels.append(y.cpu())
            probabilities.append(logits.softmax(dim=-1).cpu())
            losses.append(float(self.loss_fn(logits, y).cpu()))
        if not labels:
            raise TrainingRuntimeError(f"{prefix} loader cannot be empty.")
        truth = torch.cat(labels).numpy()
        probs = torch.cat(probabilities).numpy()
        prediction = probs.argmax(axis=1)
        metrics = {
            f"{prefix}/loss": float(np.mean(losses)),
            f"{prefix}/accuracy": float(accuracy_score(truth, prediction)),
            f"{prefix}/macro_f1": float(f1_score(truth, prediction, average="macro", zero_division=0)),
            f"{prefix}/macro_recall": float(recall_score(truth, prediction, average="macro", zero_division=0)),
            f"{prefix}/macro_precision": float(precision_score(truth, prediction, average="macro", zero_division=0)),
        }
        try:
            metrics[f"{prefix}/macro_auc"] = float(
                roc_auc_score(truth, probs, labels=[0, 1, 2], multi_class="ovr", average="macro")
            )
        except ValueError:
            metrics[f"{prefix}/macro_auc"] = float("nan")
        return metrics

    def _save_last(self, source_train_loader: Any) -> None:
        if self.run_dir is None:
            return
        self.run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "scheduler": self.scheduler.state_dict() if self.scheduler else None,
            "scaler": self.scaler.state_dict(),
            "epoch": self.completed_epoch,
            "history": self.history,
            "best_epoch": self.best_source_epoch,
            "best_f1": self.best_source_macro_f1,
            "best_state": self._best_state,
            "config": asdict(self.config),
            "identity": self.identity,
            "torch_rng_state": torch.get_rng_state(),
            "cuda_rng_state": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            "python_rng_state": random.getstate(),
            "numpy_rng_state": {
                "name": np.random.get_state()[0],
                "keys": torch.from_numpy(np.random.get_state()[1].copy()),
                "position": np.random.get_state()[2],
                "has_gauss": np.random.get_state()[3],
                "cached_gaussian": np.random.get_state()[4],
            },
            "source_loader_generator_state": (
                source_train_loader.generator.get_state()
                if getattr(source_train_loader, "generator", None) is not None
                else None
            ),
        }
        temporary = self.run_dir / "last.pt.tmp"
        torch.save(payload, temporary)
        temporary.replace(self.run_dir / "last.pt")

    def _resume(self, path: str | Path) -> None:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        if checkpoint.get("config") != asdict(self.config):
            raise TrainingRuntimeError("Baseline resume configuration mismatch.")
        if checkpoint.get("identity", {}) != self.identity:
            raise TrainingRuntimeError("Baseline resume identity mismatch.")
        self.model.load_state_dict(checkpoint["model"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        if self.scheduler and checkpoint["scheduler"] is not None:
            self.scheduler.load_state_dict(checkpoint["scheduler"])
        self.scaler.load_state_dict(checkpoint["scaler"])
        self.completed_epoch = int(checkpoint["epoch"])
        self.history = list(checkpoint["history"])
        self.best_source_epoch = int(checkpoint["best_epoch"])
        self.best_source_macro_f1 = float(checkpoint["best_f1"])
        self._best_state = checkpoint["best_state"]
        torch.set_rng_state(checkpoint["torch_rng_state"])
        if torch.cuda.is_available() and checkpoint.get("cuda_rng_state"):
            torch.cuda.set_rng_state_all(checkpoint["cuda_rng_state"])
        random.setstate(checkpoint["python_rng_state"])
        numpy_state = checkpoint["numpy_rng_state"]
        np.random.set_state(
            (
                numpy_state["name"],
                numpy_state["keys"].numpy(),
                numpy_state["position"],
                numpy_state["has_gauss"],
                numpy_state["cached_gaussian"],
            )
        )

    def fit(
        self,
        source_train_loader: Any,
        source_validation_loader: Any,
        target_evaluation_loader: Any | None = None,
        *,
        target_adaptation_loader: Any | None = None,
        resume_from: str | Path | None = None,
        interrupt_after_epoch: int | None = None,
    ) -> BaselineTrainingResult:
        if target_adaptation_loader is not None:
            raise TrainingRuntimeError("Baseline training does not accept target adaptation.")
        if resume_from is not None:
            self._resume(resume_from)
            loader_state = torch.load(
                resume_from, map_location="cpu", weights_only=True
            ).get("source_loader_generator_state")
            if loader_state is not None and getattr(source_train_loader, "generator", None) is not None:
                source_train_loader.generator.set_state(loader_state)
        stop_epoch = interrupt_after_epoch or self.config.n_epochs
        if not self.completed_epoch < stop_epoch <= self.config.n_epochs:
            raise TrainingRuntimeError("interrupt_after_epoch is outside the remaining run.")
        for epoch in range(self.completed_epoch + 1, stop_epoch + 1):
            train_loss = self.train_epoch(source_train_loader)
            source = self.evaluate(source_validation_loader, "source_validation")
            target = (
                self.evaluate(target_evaluation_loader, "target_evaluation")
                if target_evaluation_loader is not None
                else {}
            )
            score = source["source_validation/macro_f1"]
            if np.isfinite(score) and score > self.best_source_macro_f1:
                self.best_source_macro_f1 = score
                self.best_source_epoch = epoch
                self._best_state = copy.deepcopy(self.model.state_dict())
            self.completed_epoch = epoch
            self.history.append({"epoch": epoch, "train/loss": train_loss, **source, **target})
            if self.scheduler is not None:
                self.scheduler.step()
            self._save_last(source_train_loader)
        complete = self.completed_epoch == self.config.n_epochs
        if complete and self._best_state is not None:
            self.model.load_state_dict(self._best_state)
        final_source = self.evaluate(source_validation_loader, "source_validation")
        final_target = (
            self.evaluate(target_evaluation_loader, "target_evaluation")
            if target_evaluation_loader is not None
            else None
        )
        return BaselineTrainingResult(
            history=list(self.history),
            best_source_epoch=self.best_source_epoch,
            best_source_macro_f1=self.best_source_macro_f1,
            final_source_metrics=final_source,
            final_target_metrics=final_target,
        )
