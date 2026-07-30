import inspect

import pytest
import torch
from torch.nn import functional as F

from pada3dacb.adaptation.prototype_pseudo import (
    PrototypePseudoAdaptationConfig,
    PrototypePseudoAdaptationLoss,
    prototype_pseudo_adaptation_loss,
)
from pada3dacb.exceptions import LossContractError


def _reference_tensors():
    z_src = torch.tensor(
        [
            [0.0, 0.0],
            [0.5, 0.0],
            [2.0, 0.0],
        ],
        requires_grad=True,
    )
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.tensor(
        [
            [1.0, 0.0],
            [2.5, 0.0],
            [4.0, 0.0],
            [7.0, 7.0],
        ],
        requires_grad=True,
    )
    logits_c_tgt = torch.tensor(
        [
            [6.0, 0.0, 0.0],
            [0.0, 7.0, 0.0],
            [0.0, 0.0, 8.0],
            [0.0, 0.0, 0.0],
        ],
        requires_grad=True,
    )
    return z_src, y_src, z_tgt, logits_c_tgt


def test_full_stage_weighted_objective_matches_reference_without_duplicate_weighting():
    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()
    config = PrototypePseudoAdaptationConfig(lambda_proto=2.0, lambda_pl=0.5, lambda_sep=0.25, tau_p=0.95)

    output = prototype_pseudo_adaptation_loss(
        z_src=z_src,
        y_src=y_src,
        z_tgt=z_tgt,
        logits_c_tgt=logits_c_tgt,
        stage="full",
        config=config,
    )

    expected_alignment = torch.tensor((1.0 + 4.0 + 4.0) / 3.0)
    expected_separation = torch.tensor((((1.0 - 0.5) ** 2) + 0.0 + 0.0) / 3.0)
    expected_proto_raw = expected_alignment + 0.25 * expected_separation
    expected_pl_raw = F.cross_entropy(logits_c_tgt[:3], torch.tensor([0, 1, 2]))
    expected_total = 2.0 * expected_proto_raw + 0.5 * expected_pl_raw

    torch.testing.assert_close(output.prototype_raw, expected_proto_raw)
    torch.testing.assert_close(output.prototype_alignment, expected_alignment)
    torch.testing.assert_close(output.prototype_separation, expected_separation)
    torch.testing.assert_close(output.pseudo_label_raw, expected_pl_raw)
    torch.testing.assert_close(output.prototype_weighted, 2.0 * expected_proto_raw)
    torch.testing.assert_close(output.pseudo_label_weighted, 0.5 * expected_pl_raw)
    torch.testing.assert_close(output.total, expected_total)


def test_warm_stage_is_inactive_and_reports_zero_diagnostics():
    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()

    output = PrototypePseudoAdaptationLoss()(z_src, y_src, z_tgt, logits_c_tgt, stage="warm")

    assert output.adaptation_active is False
    torch.testing.assert_close(output.total, z_src.sum() * 0.0 + z_tgt.sum() * 0.0 + logits_c_tgt.sum() * 0.0)
    torch.testing.assert_close(output.prototype_raw, output.total)
    torch.testing.assert_close(output.prototype_weighted, output.total)
    torch.testing.assert_close(output.pseudo_label_raw, output.total)
    torch.testing.assert_close(output.pseudo_label_weighted, output.total)
    assert output.accepted_count == 0
    assert output.rejected_count == 0
    assert output.acceptance_rate == 0.0
    assert output.confidence_mean_accepted is None
    assert output.classes_with_source_prototypes == []
    assert output.classes_with_target_prototypes == []
    assert output.classes_with_both_prototypes == []
    assert output.prototype_distance_mean is None


def test_diagnostics_report_accepted_rejected_and_prototype_classes():
    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()

    output = PrototypePseudoAdaptationLoss()(z_src, y_src, z_tgt, logits_c_tgt, stage="full")

    assert output.accepted_count == 3
    assert output.rejected_count == 1
    assert output.acceptance_rate == pytest.approx(0.75)
    assert output.confidence_mean_accepted == pytest.approx(output.pseudo_label_confidence[:3].mean().item())
    assert output.classes_with_source_prototypes == [0, 1, 2]
    assert output.classes_with_target_prototypes == [0, 1, 2]
    assert output.classes_with_both_prototypes == [0, 1, 2]
    assert output.prototype_distance_mean == pytest.approx(torch.tensor([1.0, 2.0, 2.0]).mean().item())
    assert output.adaptation_active is True


def test_no_accepted_target_rows_zeroes_target_alignment_and_pseudo_label_loss():
    z_src = torch.tensor([[0.0, 0.0], [1.0, 0.0]], requires_grad=True)
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[9.0, 9.0], [8.0, 8.0]], requires_grad=True)
    logits_c_tgt = torch.zeros(2, 3, requires_grad=True)
    config = PrototypePseudoAdaptationConfig(lambda_sep=0.0)

    output = PrototypePseudoAdaptationLoss(config)(z_src, y_src, z_tgt, logits_c_tgt, stage="full")

    assert output.accepted_count == 0
    assert output.rejected_count == 2
    assert output.acceptance_rate == 0.0
    assert output.confidence_mean_accepted is None
    assert output.classes_with_target_prototypes == []
    assert output.classes_with_both_prototypes == []
    assert output.prototype_distance_mean is None
    torch.testing.assert_close(output.prototype_alignment, torch.tensor(0.0))
    torch.testing.assert_close(output.pseudo_label_raw, torch.tensor(0.0))
    torch.testing.assert_close(output.total, torch.tensor(0.0))


def test_gradients_flow_through_expected_embeddings_and_accepted_target_logits():
    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()

    output = PrototypePseudoAdaptationLoss()(z_src, y_src, z_tgt, logits_c_tgt, stage="full")
    output.total.backward()

    assert z_src.grad is not None
    assert z_tgt.grad is not None
    assert logits_c_tgt.grad is not None
    assert z_src.grad.abs().sum().item() > 0.0
    assert z_tgt.grad[:3].abs().sum().item() > 0.0
    torch.testing.assert_close(z_tgt.grad[3], torch.zeros_like(z_tgt.grad[3]))
    assert logits_c_tgt.grad[:3].abs().sum().item() > 0.0
    torch.testing.assert_close(logits_c_tgt.grad[3], torch.zeros_like(logits_c_tgt.grad[3]))


def test_api_neither_needs_nor_accepts_target_labels():
    signature = inspect.signature(prototype_pseudo_adaptation_loss)
    assert "y_tgt" not in signature.parameters
    assert "target_labels" not in signature.parameters

    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()
    target_labels = torch.tensor([2, 2, 2, 2])

    with pytest.raises(TypeError):
        prototype_pseudo_adaptation_loss(z_src, y_src, z_tgt, logits_c_tgt, target_labels, stage="full")

    output = prototype_pseudo_adaptation_loss(z_src=z_src, y_src=y_src, z_tgt=z_tgt, logits_c_tgt=logits_c_tgt, stage="full")
    assert output.accepted_count == 3


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"lambda_proto": -0.1},
        {"lambda_pl": float("nan")},
        {"tau_p": 1.1},
        {"proto_margin": -1.0},
        {"lambda_sep": -0.1},
        {"num_classes": 0},
    ],
)
def test_invalid_config_is_rejected(config_kwargs):
    with pytest.raises(LossContractError):
        PrototypePseudoAdaptationConfig(**config_kwargs)


@pytest.mark.parametrize("stage", ["", "train", "FULL", None])
def test_invalid_stage_is_rejected(stage):
    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()

    with pytest.raises(LossContractError):
        PrototypePseudoAdaptationLoss()(z_src, y_src, z_tgt, logits_c_tgt, stage=stage)


@pytest.mark.parametrize(
    ("bad_tensor_name", "bad_value"),
    [
        ("z_src", torch.ones(3, 2, dtype=torch.int64)),
        ("y_src", torch.tensor([0, 1, 3])),
        ("z_tgt", torch.ones(4, 3)),
        ("logits_c_tgt", torch.ones(4, 4)),
        ("logits_c_tgt", torch.tensor([[float("inf"), 0.0, 0.0]] * 4)),
    ],
)
def test_invalid_full_stage_tensors_are_rejected(bad_tensor_name, bad_value):
    z_src, y_src, z_tgt, logits_c_tgt = _reference_tensors()
    tensors = {
        "z_src": z_src,
        "y_src": y_src,
        "z_tgt": z_tgt,
        "logits_c_tgt": logits_c_tgt,
    }
    tensors[bad_tensor_name] = bad_value

    with pytest.raises(LossContractError):
        PrototypePseudoAdaptationLoss()(**tensors, stage="full")
