import pytest
import torch
from torch.nn import functional as F

from pada3dacb.adaptation.pseudo_label import PseudoLabelLoss, pseudo_label_cross_entropy
from pada3dacb.exceptions import LossContractError


def test_pseudo_label_loss_cross_entropy_matches_reference_for_one_accepted_sample():
    logits_c_tgt = torch.tensor(
        [
            [6.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=torch.float64,
    )

    output = PseudoLabelLoss(tau_p=0.95)(logits_c_tgt)

    expected = F.cross_entropy(logits_c_tgt[:1], torch.tensor([0]))
    torch.testing.assert_close(output.loss, expected)
    assert output.accepted_count == 1
    assert output.pseudo_labels.tolist() == [0, 0]
    assert output.accepted.tolist() == [True, False]


def test_pseudo_label_loss_mean_reduces_over_all_accepted_rows():
    logits_c_tgt = torch.tensor(
        [
            [6.0, 0.0, 0.0],
            [0.0, 7.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
    )

    output = pseudo_label_cross_entropy(logits_c_tgt, tau_p=0.95)

    expected = F.cross_entropy(logits_c_tgt[:2], torch.tensor([0, 1]))
    torch.testing.assert_close(output.loss, expected)
    assert output.accepted.tolist() == [True, True, False]
    assert output.accepted_count == 2


def test_pseudo_label_loss_returns_zero_scalar_when_no_target_rows_are_accepted():
    logits_c_tgt = torch.zeros(3, 3, dtype=torch.float64, requires_grad=True)

    output = PseudoLabelLoss(tau_p=0.95)(logits_c_tgt)

    assert output.loss.shape == torch.Size([])
    assert output.loss.device == logits_c_tgt.device
    assert output.loss.dtype == logits_c_tgt.dtype
    torch.testing.assert_close(output.loss, logits_c_tgt.sum() * 0.0)
    assert output.accepted_count == 0

    output.loss.backward()
    assert logits_c_tgt.grad is not None
    torch.testing.assert_close(logits_c_tgt.grad, torch.zeros_like(logits_c_tgt))


def test_pseudo_label_loss_api_does_not_accept_or_need_target_labels():
    logits_c_tgt = torch.tensor([[8.0, 0.0, 0.0]])
    target_labels = torch.tensor([2])

    with pytest.raises(TypeError):
        PseudoLabelLoss()(logits_c_tgt, target_labels)

    output = PseudoLabelLoss()(logits_c_tgt)
    assert output.accepted_count == 1
    assert output.pseudo_labels.tolist() == [0]


@pytest.mark.parametrize(
    ("logits_c_tgt", "tau_p"),
    [
        (torch.ones(2, 3, 1), 0.95),
        (torch.ones(2, 4), 0.95),
        (torch.ones(2, 3, dtype=torch.int64), 0.95),
        (torch.tensor([[1.0, float("nan"), 0.0], [2.0, 3.0, 4.0]]), 0.95),
        (torch.ones(2, 3), -0.1),
        (torch.ones(2, 3), 1.1),
    ],
)
def test_pseudo_label_loss_rejects_invalid_inputs(logits_c_tgt, tau_p):
    with pytest.raises(LossContractError):
        PseudoLabelLoss(tau_p=tau_p)(logits_c_tgt)
