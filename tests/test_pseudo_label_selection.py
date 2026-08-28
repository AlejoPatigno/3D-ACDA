import math

import pytest
import torch
from torch.nn import functional as F

from acda3d.adaptation.pseudo_label import (
    DEFAULT_PSEUDO_LABEL_CLASS_COUNT,
    DEFAULT_TAU_P,
    PseudoLabelLoss,
    select_pseudo_labels,
)
from acda3d.exceptions import LossContractError


def test_select_pseudo_labels_uses_concept_logits_softmax_argmax_confidence():
    logits_c_tgt = torch.tensor(
        [
            [3.0, 1.0, -2.0],
            [0.0, 5.0, 1.0],
            [-1.0, 0.5, 2.5],
        ]
    )

    selection = select_pseudo_labels(logits_c_tgt, tau_p=0.0)

    probabilities = F.softmax(logits_c_tgt, dim=-1)
    expected_confidence, expected_pseudo = probabilities.max(dim=-1)
    torch.testing.assert_close(selection.probabilities, probabilities)
    torch.testing.assert_close(selection.confidence, expected_confidence)
    assert selection.pseudo_labels.tolist() == expected_pseudo.tolist()
    assert selection.accepted.tolist() == [True, True, True]


def test_select_pseudo_labels_accepts_confidence_equal_to_tau_p_boundary():
    tau = 0.95
    boundary_logit = math.log((2.0 * tau) / (1.0 - tau))
    logits_c_tgt = torch.tensor(
        [
            [boundary_logit, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
    )

    selection = select_pseudo_labels(logits_c_tgt, tau_p=tau)

    torch.testing.assert_close(selection.confidence[0], torch.tensor(tau))
    assert selection.pseudo_labels.tolist() == [0, 0]
    assert selection.accepted.tolist() == [True, False]
    assert selection.accepted_count == 1


def test_select_pseudo_labels_reports_accepted_and_rejected_masks_counts():
    logits_c_tgt = torch.tensor(
        [
            [6.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 6.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
    )

    selection = select_pseudo_labels(logits_c_tgt, tau_p=0.95)

    assert selection.accepted.tolist() == [True, False, True, False]
    assert selection.rejected.tolist() == [False, True, False, True]
    assert selection.accepted_count == 2
    assert selection.rejected_count == 2


@pytest.mark.parametrize(
    "logits_c_tgt",
    [
        torch.ones(2, 3, 1),
        torch.ones(0, 3),
        torch.ones(2, 0),
        torch.ones(2, 3, dtype=torch.int64),
        torch.tensor([[1.0, float("nan"), 0.0], [2.0, 3.0, 4.0]]),
        torch.tensor([[1.0, float("inf"), 0.0], [2.0, 3.0, 4.0]]),
    ],
)
def test_select_pseudo_labels_rejects_invalid_logits_contracts(logits_c_tgt):
    with pytest.raises(LossContractError):
        select_pseudo_labels(logits_c_tgt)


@pytest.mark.parametrize("tau_p", [-0.01, 1.01, float("nan"), float("inf")])
def test_select_pseudo_labels_rejects_invalid_tau_threshold(tau_p):
    with pytest.raises(LossContractError):
        select_pseudo_labels(torch.ones(1, 3), tau_p=tau_p)


def test_select_pseudo_labels_rejects_invalid_class_count():
    with pytest.raises(LossContractError):
        select_pseudo_labels(torch.ones(1, 3), class_count=0)
    with pytest.raises(LossContractError):
        select_pseudo_labels(torch.ones(1, 4), class_count=DEFAULT_PSEUDO_LABEL_CLASS_COUNT)


def test_pseudo_label_loss_has_fixed_threshold_and_no_temperature_schedule_balancing_state():
    loss_fn = PseudoLabelLoss()

    assert vars(loss_fn) == {"tau_p": DEFAULT_TAU_P, "class_count": DEFAULT_PSEUDO_LABEL_CLASS_COUNT}
    assert not hasattr(loss_fn, "temperature")
    assert not hasattr(loss_fn, "schedule")
    assert not hasattr(loss_fn, "class_balancing")
    assert not hasattr(loss_fn, "quota")
