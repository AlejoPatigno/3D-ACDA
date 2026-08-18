"""Current-batch prototype alignment for canonical PADA-3DACB adaptation."""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from torch import Tensor
from torch.nn import functional as F

from pada3dacb.exceptions import LossContractError

DEFAULT_PROTOTYPE_CLASS_COUNT = 3
DEFAULT_TAU_P = 0.95
DEFAULT_PROTO_MARGIN = 1.0
DEFAULT_LAMBDA_SEP = 0.1


@dataclass(frozen=True)
class PrototypeConstruction:
    prototypes: Tensor
    valid: Tensor


@dataclass(frozen=True)
class TargetPrototypeConstruction(PrototypeConstruction):
    pseudo_labels: Tensor
    accepted: Tensor


@dataclass(frozen=True)
class PrototypeLossOutput:
    total: Tensor
    alignment: Tensor
    separation: Tensor
    source_prototypes: Tensor
    target_prototypes: Tensor
    valid_source: Tensor
    valid_target: Tensor
    target_pseudo_labels: Tensor
    accepted_target: Tensor

    @property
    def accepted_target_count(self) -> int:
        return int(self.accepted_target.sum().item())


def _validate_class_count(class_count: int) -> int:
    if not isinstance(class_count, int) or class_count <= 0:
        raise LossContractError("Prototype class_count must be a positive integer.")
    return class_count


def _validate_probability_threshold(tau_p: float) -> float:
    value = float(tau_p)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise LossContractError("Prototype tau_p must be finite and within [0, 1].")
    return value


def _validate_nonnegative_scalar(value: float, name: str) -> float:
    scalar = float(value)
    if not math.isfinite(scalar) or scalar < 0.0:
        raise LossContractError(f"{name} must be finite and non-negative.")
    return scalar


def _validate_features(features: Tensor, name: str) -> None:
    if not torch.is_tensor(features) or features.ndim != 2:
        shape = tuple(features.shape) if torch.is_tensor(features) else type(features).__name__
        raise LossContractError(f"{name} must be a rank-2 tensor, got {shape}.")
    if features.shape[0] == 0 or features.shape[1] == 0:
        raise LossContractError(f"{name} must have non-empty batch and feature dimensions.")
    if not features.is_floating_point():
        raise LossContractError(f"{name} must use a floating-point dtype.")
    if not torch.isfinite(features).all():
        raise LossContractError(f"{name} must contain only finite values.")


def _validate_logits(logits: Tensor, name: str, expected_batch: int, class_count: int) -> None:
    if not torch.is_tensor(logits) or logits.ndim != 2:
        shape = tuple(logits.shape) if torch.is_tensor(logits) else type(logits).__name__
        raise LossContractError(f"{name} must be a rank-2 tensor, got {shape}.")
    if logits.shape != (expected_batch, class_count):
        raise LossContractError(
            f"{name} must have shape ({expected_batch}, {class_count}), got {tuple(logits.shape)}."
        )
    if not logits.is_floating_point():
        raise LossContractError(f"{name} must use a floating-point dtype.")
    if not torch.isfinite(logits).all():
        raise LossContractError(f"{name} must contain only finite values.")


def _validate_labels(labels: Tensor, expected_batch: int, class_count: int) -> None:
    if not torch.is_tensor(labels) or labels.ndim != 1:
        shape = tuple(labels.shape) if torch.is_tensor(labels) else type(labels).__name__
        raise LossContractError(f"source labels must be a rank-1 tensor, got {shape}.")
    if labels.shape[0] != expected_batch:
        raise LossContractError("source labels batch size must match source embeddings.")
    if labels.dtype not in (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8):
        raise LossContractError("source labels must use an integer dtype.")
    if labels.device.type != "cpu" and labels.device != labels.device:
        raise LossContractError("source labels device is invalid.")
    if labels.numel() and ((labels < 0).any() or (labels >= class_count).any()):
        raise LossContractError("source labels must be within [0, class_count).")


def _validate_shared_device(*tensors: Tensor) -> None:
    devices = {tensor.device for tensor in tensors}
    if len(devices) != 1:
        raise LossContractError("Prototype tensors must share the same device.")


def _zero_scalar_like(reference: Tensor) -> Tensor:
    return reference.sum() * 0.0


def build_source_prototypes(
    z_src: Tensor,
    y_src: Tensor,
    *,
    class_count: int = DEFAULT_PROTOTYPE_CLASS_COUNT,
) -> tuple[Tensor, Tensor]:
    """Return per-class current-batch source means and validity mask."""
    class_count = _validate_class_count(class_count)
    _validate_features(z_src, "z_src")
    _validate_labels(y_src, z_src.shape[0], class_count)
    if y_src.device != z_src.device:
        raise LossContractError("source labels and source embeddings must share a device.")

    z_src_norm = F.normalize(z_src, p=2, dim=1)
    prototypes = []
    valid = []
    for class_index in range(class_count):
        mask = y_src == class_index
        valid.append(mask.any())
        if bool(mask.any()):
            prototypes.append(z_src_norm[mask].mean(dim=0))
        else:
            prototypes.append(z_src_norm.new_zeros(z_src_norm.shape[1]))
    return torch.stack(prototypes, dim=0), torch.stack(valid).to(device=z_src.device)


def build_target_prototypes(
    z_tgt: Tensor,
    logits_c_tgt: Tensor,
    *,
    tau_p: float = DEFAULT_TAU_P,
    class_count: int = DEFAULT_PROTOTYPE_CLASS_COUNT,
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    """Return accepted target prototypes from concept-head logits."""
    class_count = _validate_class_count(class_count)
    tau_p = _validate_probability_threshold(tau_p)
    _validate_features(z_tgt, "z_tgt")
    _validate_logits(logits_c_tgt, "logits_c_tgt", z_tgt.shape[0], class_count)
    _validate_shared_device(z_tgt, logits_c_tgt)

    probabilities = F.softmax(logits_c_tgt, dim=-1)
    if not torch.isfinite(probabilities).all():
        raise LossContractError("target pseudo-label probabilities must be finite.")
    confidence, pseudo_labels = probabilities.max(dim=-1)
    accepted = confidence >= tau_p

    z_tgt_norm = F.normalize(z_tgt, p=2, dim=1)
    prototypes = []
    valid = []
    for class_index in range(class_count):
        mask = accepted & (pseudo_labels == class_index)
        valid.append(mask.any())
        if bool(mask.any()):
            prototypes.append(z_tgt_norm[mask].mean(dim=0))
        else:
            prototypes.append(z_tgt_norm.new_zeros(z_tgt_norm.shape[1]))
    return torch.stack(prototypes, dim=0), torch.stack(valid).to(device=z_tgt.device), pseudo_labels, accepted


def _validate_prototype_inputs(source: Tensor, valid_source: Tensor, target: Tensor | None = None, valid_target: Tensor | None = None) -> None:
    _validate_features(source, "source_prototypes")
    if not torch.is_tensor(valid_source) or valid_source.ndim != 1 or valid_source.shape[0] != source.shape[0]:
        raise LossContractError("valid_source must be rank 1 and match source prototype classes.")
    if valid_source.dtype != torch.bool or valid_source.device != source.device:
        raise LossContractError("valid_source must be a boolean tensor on the prototype device.")
    if target is None or valid_target is None:
        return
    _validate_features(target, "target_prototypes")
    if source.shape != target.shape:
        raise LossContractError("source and target prototypes must share shape.")
    if not torch.is_tensor(valid_target) or valid_target.ndim != 1 or valid_target.shape[0] != target.shape[0]:
        raise LossContractError("valid_target must be rank 1 and match target prototype classes.")
    if valid_target.dtype != torch.bool or valid_target.device != target.device:
        raise LossContractError("valid_target must be a boolean tensor on the prototype device.")
    _validate_shared_device(source, target)


def prototype_alignment_loss(
    source_prototypes: Tensor,
    valid_source: Tensor,
    target_prototypes: Tensor,
    valid_target: Tensor,
) -> Tensor:
    """Mean squared Euclidean distance over mutually valid prototype classes, normalized to [0, 1]."""
    _validate_prototype_inputs(source_prototypes, valid_source, target_prototypes, valid_target)
    mutually_valid = valid_source & valid_target
    if not bool(mutually_valid.any()):
        return _zero_scalar_like(source_prototypes) + _zero_scalar_like(target_prototypes)
    distances = (source_prototypes[mutually_valid] - target_prototypes[mutually_valid]).square().sum(dim=1)
    num_valid = mutually_valid.sum().to(dtype=source_prototypes.dtype)
    loss = distances.sum() / (4.0 * num_valid)
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise LossContractError("Prototype alignment loss must be a finite scalar.")
    return loss


def prototype_separation_loss(
    source_prototypes: Tensor,
    valid_source: Tensor,
    *,
    proto_margin: float = DEFAULT_PROTO_MARGIN,
) -> Tensor:
    """Normalized margin penalty over unordered valid source prototype pairs, in [0, 1]."""
    proto_margin = _validate_nonnegative_scalar(proto_margin, "proto_margin")
    _validate_prototype_inputs(source_prototypes, valid_source)
    if proto_margin == 0:
        return _zero_scalar_like(source_prototypes)
    valid_prototypes = source_prototypes[valid_source]
    if valid_prototypes.shape[0] < 2:
        return _zero_scalar_like(source_prototypes)
    pair_i, pair_j = torch.triu_indices(valid_prototypes.shape[0], valid_prototypes.shape[0], offset=1, device=source_prototypes.device)
    distances = (valid_prototypes[pair_i] - valid_prototypes[pair_j]).norm(p=2, dim=1)
    margin = source_prototypes.new_tensor(proto_margin)
    loss = (torch.relu(margin - distances) / margin).square().mean()
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise LossContractError("Prototype separation loss must be a finite scalar.")
    return loss


class PrototypeLoss:
    """Stateless canonical prototype adaptation loss from current mini-batch tensors."""

    def __init__(
        self,
        *,
        tau_p: float = DEFAULT_TAU_P,
        proto_margin: float = DEFAULT_PROTO_MARGIN,
        lambda_sep: float = DEFAULT_LAMBDA_SEP,
        class_count: int = DEFAULT_PROTOTYPE_CLASS_COUNT,
    ) -> None:
        self.tau_p = _validate_probability_threshold(tau_p)
        self.proto_margin = _validate_nonnegative_scalar(proto_margin, "proto_margin")
        self.lambda_sep = _validate_nonnegative_scalar(lambda_sep, "lambda_sep")
        self.class_count = _validate_class_count(class_count)

    def __call__(self, z_src: Tensor, y_src: Tensor, z_tgt: Tensor, logits_c_tgt: Tensor) -> PrototypeLossOutput:
        return self.forward(z_src, y_src, z_tgt, logits_c_tgt)

    def forward(self, z_src: Tensor, y_src: Tensor, z_tgt: Tensor, logits_c_tgt: Tensor) -> PrototypeLossOutput:
        _validate_features(z_src, "z_src")
        _validate_features(z_tgt, "z_tgt")
        if z_src.shape[1] != z_tgt.shape[1]:
            raise LossContractError("source and target embedding dimensions must match.")
        _validate_shared_device(z_src, z_tgt, logits_c_tgt)
        source_prototypes, valid_source = build_source_prototypes(z_src, y_src, class_count=self.class_count)
        target_prototypes, valid_target, pseudo_labels, accepted = build_target_prototypes(
            z_tgt,
            logits_c_tgt,
            tau_p=self.tau_p,
            class_count=self.class_count,
        )
        alignment = prototype_alignment_loss(source_prototypes, valid_source, target_prototypes, valid_target)
        separation = prototype_separation_loss(source_prototypes, valid_source, proto_margin=self.proto_margin)
        total = alignment + source_prototypes.new_tensor(self.lambda_sep) * separation
        if total.ndim != 0 or not torch.isfinite(total):
            raise LossContractError("Prototype loss must be a finite scalar.")
        return PrototypeLossOutput(
            total=total,
            alignment=alignment,
            separation=separation,
            source_prototypes=source_prototypes,
            target_prototypes=target_prototypes,
            valid_source=valid_source,
            valid_target=valid_target,
            target_pseudo_labels=pseudo_labels,
            accepted_target=accepted,
        )
