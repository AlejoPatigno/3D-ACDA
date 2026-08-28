import torch
from torch.nn import functional as F

from acda3d.adaptation.pseudo_label import PseudoLabelLoss


def test_pseudo_label_loss_gradients_flow_through_accepted_logits_only():
    logits_c_tgt = torch.tensor(
        [
            [6.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 7.0, 0.0],
        ],
        requires_grad=True,
    )

    output = PseudoLabelLoss(tau_p=0.95)(logits_c_tgt)
    output.loss.backward()

    reference_logits = logits_c_tgt.detach().clone().requires_grad_(True)
    reference_loss = F.cross_entropy(reference_logits[[0, 2]], torch.tensor([0, 1]))
    reference_loss.backward()
    expected_grad = reference_logits.grad

    assert output.accepted.tolist() == [True, False, True]
    assert logits_c_tgt.grad is not None
    torch.testing.assert_close(logits_c_tgt.grad, expected_grad)
    assert logits_c_tgt.grad[0].abs().sum() > 0
    assert logits_c_tgt.grad[1].abs().sum() == 0
    assert logits_c_tgt.grad[2].abs().sum() > 0


def test_pseudo_label_loss_has_no_gradient_contribution_when_all_rows_rejected():
    logits_c_tgt = torch.zeros(2, 3, requires_grad=True)

    output = PseudoLabelLoss(tau_p=0.95)(logits_c_tgt)
    output.loss.backward()

    assert output.accepted.tolist() == [False, False]
    assert output.accepted_count == 0
    assert logits_c_tgt.grad is not None
    torch.testing.assert_close(logits_c_tgt.grad, torch.zeros_like(logits_c_tgt))
