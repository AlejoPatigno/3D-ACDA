import torch
from torch.nn import functional as F

from acda3d.adaptation.prototype_pseudo import (
    PrototypePseudoAdaptationConfig,
    PrototypePseudoAdaptationLoss,
)


def test_warm_stage_is_exact_zero_and_backpropagates_zero_gradients():
    z_src = torch.tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[5.0, 6.0]], requires_grad=True)
    logits_c_tgt = torch.tensor([[9.0, 0.0, 0.0]], requires_grad=True)

    output = PrototypePseudoAdaptationLoss()(z_src, y_src, z_tgt, logits_c_tgt, stage="warm")
    output.total.backward()

    torch.testing.assert_close(output.total, torch.tensor(0.0))
    torch.testing.assert_close(output.prototype_raw, torch.tensor(0.0))
    torch.testing.assert_close(output.pseudo_label_raw, torch.tensor(0.0))
    assert output.adaptation_active is False
    assert output.accepted_count == 0
    assert output.rejected_count == 0
    torch.testing.assert_close(z_src.grad, torch.zeros_like(z_src))
    torch.testing.assert_close(z_tgt.grad, torch.zeros_like(z_tgt))
    torch.testing.assert_close(logits_c_tgt.grad, torch.zeros_like(logits_c_tgt))


def test_absent_source_and_absent_target_classes_do_not_contribute_to_alignment():
    z_src = torch.tensor([[0.0, 0.0], [10.0, 0.0]], dtype=torch.float64)
    y_src = torch.tensor([0, 0])
    z_tgt = torch.tensor([[2.0, 0.0], [50.0, 50.0]], dtype=torch.float64)
    logits_c_tgt = torch.tensor(
        [
            [0.0, 0.0, 8.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=torch.float64,
    )
    config = PrototypePseudoAdaptationConfig(tau_p=0.95, lambda_proto=1.0, lambda_pl=0.0)

    output = PrototypePseudoAdaptationLoss(config)(z_src, y_src, z_tgt, logits_c_tgt, stage="full")

    assert output.classes_with_source_prototypes == [0]
    assert output.classes_with_target_prototypes == [2]
    assert output.classes_with_both_prototypes == []
    assert output.prototype_distance_mean is None
    torch.testing.assert_close(output.prototype_alignment, torch.tensor(0.0, dtype=torch.float64))
    torch.testing.assert_close(output.prototype_separation, torch.tensor(0.0, dtype=torch.float64))
    torch.testing.assert_close(output.prototype_raw, torch.tensor(0.0, dtype=torch.float64))
    torch.testing.assert_close(output.total, torch.tensor(0.0, dtype=torch.float64))


def test_no_accepted_target_rows_zero_target_terms_but_keep_source_separation_equation():
    z_src = torch.tensor([[0.0], [0.5]], dtype=torch.float64)
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[100.0], [200.0]], dtype=torch.float64)
    logits_c_tgt = torch.zeros(2, 3, dtype=torch.float64)
    config = PrototypePseudoAdaptationConfig(
        tau_p=0.95,
        proto_margin=1.0,
        lambda_sep=0.2,
        lambda_proto=2.0,
        lambda_pl=3.0,
    )

    output = PrototypePseudoAdaptationLoss(config)(z_src, y_src, z_tgt, logits_c_tgt, stage="full")

    expected_separation = torch.tensor((1.0 - 0.5) ** 2, dtype=torch.float64)
    expected_proto = 0.2 * expected_separation
    assert output.accepted_count == 0
    assert output.rejected_count == 2
    assert output.classes_with_target_prototypes == []
    assert output.classes_with_both_prototypes == []
    torch.testing.assert_close(output.prototype_alignment, torch.tensor(0.0, dtype=torch.float64))
    torch.testing.assert_close(output.pseudo_label_raw, torch.tensor(0.0, dtype=torch.float64))
    torch.testing.assert_close(output.prototype_separation, expected_separation)
    torch.testing.assert_close(output.prototype_raw, expected_proto)
    torch.testing.assert_close(output.total, 2.0 * expected_proto)


def test_gradients_match_independent_references_and_rejected_logits_get_no_ce_gradient():
    z_src = torch.tensor([[0.0], [2.0], [5.0]], dtype=torch.float64, requires_grad=True)
    y_src = torch.tensor([0, 0, 1])
    z_tgt = torch.tensor([[4.0], [6.0], [100.0]], dtype=torch.float64, requires_grad=True)
    logits_c_tgt = torch.tensor(
        [
            [4.0, 0.0, 0.0],
            [5.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=torch.float64,
        requires_grad=True,
    )
    config = PrototypePseudoAdaptationConfig(
        tau_p=0.8,
        lambda_proto=2.0,
        lambda_pl=0.25,
        lambda_sep=0.0,
    )

    output = PrototypePseudoAdaptationLoss(config)(z_src, y_src, z_tgt, logits_c_tgt, stage="full")
    output.total.backward()

    z_src_ref = z_src.detach().clone().requires_grad_(True)
    z_tgt_ref = z_tgt.detach().clone().requires_grad_(True)
    logits_ref = logits_c_tgt.detach().clone().requires_grad_(True)
    src_mu_0 = z_src_ref[[0, 1]].mean(dim=0)
    tgt_mu_0 = z_tgt_ref[[0, 1]].mean(dim=0)
    reference_proto = (src_mu_0 - tgt_mu_0).square().sum()
    reference_ce = F.cross_entropy(logits_ref[[0, 1]], torch.tensor([0, 0]))
    reference_total = 2.0 * reference_proto + 0.25 * reference_ce
    reference_total.backward()

    torch.testing.assert_close(output.total, reference_total.detach())
    torch.testing.assert_close(z_src.grad, z_src_ref.grad)
    torch.testing.assert_close(z_tgt.grad, z_tgt_ref.grad)
    torch.testing.assert_close(logits_c_tgt.grad, logits_ref.grad)
    assert z_src.grad.abs().sum().item() > 0.0
    assert z_tgt.grad[:2].abs().sum().item() > 0.0
    torch.testing.assert_close(z_tgt.grad[2], torch.zeros_like(z_tgt.grad[2]))
    assert logits_c_tgt.grad[:2].abs().sum().item() > 0.0
    torch.testing.assert_close(logits_c_tgt.grad[2], torch.zeros_like(logits_c_tgt.grad[2]))
