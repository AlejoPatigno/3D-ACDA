
"""
dataset_contract.py
===================
Minimal dataset contract for the already-created dataloaders.

Required keys for Stage I source batches:
    x        : (B,1,H,W,D)
    y        : (B,)
    c_target : (B,K)
    g_bar    : (B,K)

Required keys for Stage II target batches:
    x        : (B,1,H,W,D)
    g_bar    : (B,K)

Optional metadata:
    subject_id, source_path, label_name
"""

from __future__ import annotations

from typing import Mapping

import torch


def validate_source_batch(batch: Mapping, K: int) -> None:
    for key in ["x", "y", "c_target", "g_bar"]:
        if key not in batch:
            raise KeyError(f"Missing key '{key}' in source batch.")
    if batch["x"].ndim != 5:
        raise ValueError(f"Expected x shape (B,1,H,W,D), got {tuple(batch['x'].shape)}.")
    if batch["c_target"].shape[-1] != K or batch["g_bar"].shape[-1] != K:
        raise ValueError("Concept targets or Jacobian summaries do not match K.")

def validate_target_batch(batch: Mapping, K: int) -> None:
    for key in ["x", "g_bar"]:
        if key not in batch:
            raise KeyError(f"Missing key '{key}' in target batch.")
    if batch["x"].ndim != 5:
        raise ValueError(f"Expected x shape (B,1,H,W,D), got {tuple(batch['x'].shape)}.")
    if batch["g_bar"].shape[-1] != K:
        raise ValueError("Jacobian summaries do not match K.")
