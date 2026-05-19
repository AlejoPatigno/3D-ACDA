
"""
trainer.py
==========
Section O of the Materials and Methods.

Two-stage optimization:
  - Stage I : source pretraining
  - Stage II: source-target adaptation

Design choice:
  The concept head p_tilde is used as the operative classifier during
  training and inference. This is the cleaner interpretation-preserving
  option described in Section J of the M&M.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

import torch
from torch.utils.data import DataLoader

from atlas_utils import AtlasROIManager


@dataclass
class TrainConfig:
    n_epochs_stage1: int = 20
    n_epochs_stage2: int = 30
    lr: float = 3e-4
    weight_decay: float = 1e-4
    grad_clip_norm: float = 5.0
    device: str = "cuda"
    log_every: int = 10
    use_amp: bool = True


def _move_batch(batch: dict, device: torch.device) -> dict:
    out = {}
    for k, v in batch.items():
        if torch.is_tensor(v):
            out[k] = v.to(device, non_blocking=True)
        else:
            out[k] = v
    return out


def _require_keys(batch: dict, keys: Iterable[str]) -> None:
    missing = [k for k in keys if k not in batch]
    if missing:
        raise KeyError(f"Batch is missing required keys: {missing}")


class DomainAdaptationTrainer:
    def __init__(
        self,
        model,
        loss_fn,
        atlas_mgr: AtlasROIManager,
        input_shape=(128, 128, 128),
        cfg: Optional[TrainConfig] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        self.model = model
        self.loss_fn = loss_fn
        self.atlas_mgr = atlas_mgr
        self.cfg = cfg or TrainConfig()

        self.device = torch.device(self.cfg.device if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        if optimizer is None:
            optimizer = torch.optim.AdamW(
                self.model.parameters(),
                lr=self.cfg.lr,
                weight_decay=self.cfg.weight_decay,
            )
        self.optimizer = optimizer
        self.scaler = torch.cuda.amp.GradScaler(enabled=self.cfg.use_amp and self.device.type == "cuda")

        self.roi_masks = self._build_feature_space_roi_masks(input_shape)

    def _build_feature_space_roi_masks(self, input_shape):
        with torch.no_grad():
            dummy = torch.zeros(1, 1, *input_shape, device=self.device)
            feat = self.model.encoder(dummy)
            feature_shape = feat.shape[-3:]
        self.atlas_mgr.maybe_validate_K(self.model.K)
        return self.atlas_mgr.get_masks(feature_shape, normalize=True, device=self.device)

    def _forward(self, x: torch.Tensor) -> dict:
        return self.model(x, self.roi_masks)

    def train_stage1_epoch(self, source_loader: DataLoader, epoch: int) -> dict:
        self.model.train()
        meter = {"loss": 0.0, "n": 0}

        for step, batch in enumerate(source_loader):
            _require_keys(batch, ["x", "y", "c_target", "g_bar"])
            batch = _move_batch(batch, self.device)

            self.optimizer.zero_grad(set_to_none=True)

            with torch.cuda.amp.autocast(enabled=self.scaler.is_enabled()):
                out_src = self._forward(batch["x"])
                # Use cbm_logits as the operative classifier for interpretability
                loss, info = self.loss_fn.forward_stage1(
                    logits_src=out_src["cbm_logits"],
                    labels_src=batch["y"],
                    c_src=out_src["c"],
                    c_target=batch["c_target"],
                    g_bar_src=batch["g_bar"],
                )

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip_norm)
            self.scaler.step(self.optimizer)
            self.scaler.update()

            meter["loss"] += float(loss.item())
            meter["n"] += 1

            if step % self.cfg.log_every == 0:
                print(f"[Stage I][Epoch {epoch:03d}][Step {step:04d}] "
                      f"loss={loss.item():.4f} "
                      f"L_cls={info['L_cls']:.4f} "
                      f"L_concept={info['L_concept']:.4f} "
                      f"L_anat={info['L_anat']:.4f}")

        meter["loss"] /= max(meter["n"], 1)
        return meter

    def train_stage2_epoch(self, source_loader: DataLoader, target_loader: DataLoader, epoch: int) -> dict:
        self.model.train()
        meter = {"loss": 0.0, "n": 0}
        tgt_iter = iter(target_loader)

        for step, src_batch in enumerate(source_loader):
            try:
                tgt_batch = next(tgt_iter)
            except StopIteration:
                tgt_iter = iter(target_loader)
                tgt_batch = next(tgt_iter)

            _require_keys(src_batch, ["x", "y", "c_target", "g_bar"])
            _require_keys(tgt_batch, ["x", "g_bar"])

            src_batch = _move_batch(src_batch, self.device)
            tgt_batch = _move_batch(tgt_batch, self.device)

            self.optimizer.zero_grad(set_to_none=True)

            with torch.cuda.amp.autocast(enabled=self.scaler.is_enabled()):
                out_src = self._forward(src_batch["x"])
                out_tgt = self._forward(tgt_batch["x"])

                loss, info = self.loss_fn.forward_stage2(
                    logits_src=out_src["cbm_logits"],
                    labels_src=src_batch["y"],
                    z_src=out_src["z"],
                    c_src=out_src["c"],
                    c_target=src_batch["c_target"],
                    g_bar_src=src_batch["g_bar"],
                    logits_tgt=out_tgt["cbm_logits"],
                    z_tgt=out_tgt["z"],
                    c_tgt=out_tgt["c"],
                    g_bar_tgt=tgt_batch["g_bar"],
                )

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip_norm)
            self.scaler.step(self.optimizer)
            self.scaler.update()

            meter["loss"] += float(loss.item())
            meter["n"] += 1

            if step % self.cfg.log_every == 0:
                print(f"[Stage II][Epoch {epoch:03d}][Step {step:04d}] "
                      f"loss={loss.item():.4f} "
                      f"L_cls={info['L_cls']:.4f} "
                      f"L_proto={info['L_proto']:.4f} "
                      f"L_pl={info['L_pl']:.4f} "
                      f"L_concept={info['L_concept']:.4f} "
                      f"L_anat={info['L_anat']:.4f} "
                      f"n_conf_T={info['n_confident_T']}")

        meter["loss"] /= max(meter["n"], 1)
        return meter

    @torch.no_grad()
    def evaluate(self, loader: DataLoader) -> dict:
        self.model.eval()
        y_true = []
        y_pred = []

        for batch in loader:
            _require_keys(batch, ["x", "y"])
            batch = _move_batch(batch, self.device)
            out = self._forward(batch["x"])
            probs = torch.softmax(out["cbm_logits"], dim=-1)
            pred = probs.argmax(dim=-1)

            y_true.append(batch["y"].cpu())
            y_pred.append(pred.cpu())

        y_true = torch.cat(y_true)
        y_pred = torch.cat(y_pred)

        acc = float((y_true == y_pred).float().mean().item())
        return {"accuracy": acc}

    def fit(
        self,
        source_loader: DataLoader,
        target_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
    ) -> dict:
        history = {"stage1": [], "stage2": []}

        for epoch in range(1, self.cfg.n_epochs_stage1 + 1):
            train_info = self.train_stage1_epoch(source_loader, epoch)
            eval_info = self.evaluate(val_loader) if val_loader is not None else {}
            history["stage1"].append({**train_info, **eval_info})

        for epoch in range(1, self.cfg.n_epochs_stage2 + 1):
            train_info = self.train_stage2_epoch(source_loader, target_loader, epoch)
            eval_info = self.evaluate(val_loader) if val_loader is not None else {}
            history["stage2"].append({**train_info, **eval_info})

        return history
