import pytest
import torch

from pada3dacb.adaptation.prototype import (
    DEFAULT_PROTOTYPE_CLASS_COUNT,
    build_source_prototypes,
    build_target_prototypes,
)
from pada3dacb.exceptions import LossContractError


def test_source_prototypes_are_current_batch_per_class_means_with_absent_mask():
    z_src = torch.tensor(
        [
            [1.0, 2.0],
            [3.0, 4.0],
            [10.0, 20.0],
        ]
    )
    y_src = torch.tensor([0, 0, 2])

    prototypes, valid = build_source_prototypes(z_src, y_src, class_count=DEFAULT_PROTOTYPE_CLASS_COUNT)

    expected = torch.tensor(
        [
            [2.0, 3.0],
            [0.0, 0.0],
            [10.0, 20.0],
        ]
    )
    torch.testing.assert_close(prototypes, expected)
    assert valid.tolist() == [True, False, True]


def test_target_prototypes_use_softmax_argmax_and_confidence_threshold_boundary():
    z_tgt = torch.tensor(
        [
            [1.0, 1.0],
            [3.0, 5.0],
            [8.0, 13.0],
            [21.0, 34.0],
        ]
    )
    tau = 0.95
    boundary_logit = torch.log(torch.tensor(tau / (1.0 - tau)))
    logits_c_tgt = torch.tensor(
        [
            [boundary_logit, 0.0, -100.0],
            [0.0, 5.0, 0.0],
            [0.0, 0.0, 6.0],
            [0.0, 0.0, 0.0],
        ]
    )

    prototypes, valid, pseudo, accepted = build_target_prototypes(
        z_tgt,
        logits_c_tgt,
        tau_p=tau,
        class_count=DEFAULT_PROTOTYPE_CLASS_COUNT,
    )

    assert accepted.tolist() == [True, True, True, False]
    assert pseudo.tolist() == [0, 1, 2, 0]
    torch.testing.assert_close(prototypes, z_tgt[:3])
    assert valid.tolist() == [True, True, True]


def test_target_prototypes_mark_absent_accepted_classes_zero_invalid():
    z_tgt = torch.tensor([[2.0, 4.0], [4.0, 8.0]])
    logits_c_tgt = torch.tensor([[6.0, 0.0, 0.0], [5.0, 0.0, 0.0]])

    prototypes, valid, _pseudo, accepted = build_target_prototypes(z_tgt, logits_c_tgt, tau_p=0.95)

    assert accepted.tolist() == [True, True]
    torch.testing.assert_close(prototypes[0], torch.tensor([3.0, 6.0]))
    torch.testing.assert_close(prototypes[1:], torch.zeros(2, 2))
    assert valid.tolist() == [True, False, False]


@pytest.mark.parametrize(
    ("z_src", "y_src"),
    [
        (torch.ones(2, 3, 1), torch.tensor([0, 1])),
        (torch.ones(2, 3, dtype=torch.int64), torch.tensor([0, 1])),
        (torch.tensor([[1.0, float("nan")], [2.0, 3.0]]), torch.tensor([0, 1])),
        (torch.ones(2, 3), torch.tensor([[0], [1]])),
        (torch.ones(2, 3), torch.tensor([0, 3])),
        (torch.ones(2, 3), torch.tensor([0, -1])),
        (torch.ones(2, 3), torch.tensor([0.0, 1.0])),
    ],
)
def test_source_prototype_contract_rejects_invalid_inputs(z_src, y_src):
    with pytest.raises(LossContractError):
        build_source_prototypes(z_src, y_src)


@pytest.mark.parametrize(
    ("z_tgt", "logits_c_tgt"),
    [
        (torch.ones(2, 3, 1), torch.ones(2, 3)),
        (torch.ones(2, 3), torch.ones(2, 4)),
        (torch.ones(2, 3), torch.ones(3, 3)),
        (torch.ones(2, 3, dtype=torch.int64), torch.ones(2, 3)),
        (torch.ones(2, 3), torch.ones(2, 3, dtype=torch.int64)),
        (torch.tensor([[1.0, float("inf")], [2.0, 3.0]]), torch.ones(2, 3)),
        (torch.ones(2, 3), torch.tensor([[1.0, float("nan"), 0.0], [2.0, 3.0, 4.0]])),
    ],
)
def test_target_prototype_contract_rejects_invalid_inputs(z_tgt, logits_c_tgt):
    with pytest.raises(LossContractError):
        build_target_prototypes(z_tgt, logits_c_tgt)


def test_prototype_construction_rejects_invalid_hyperparameters():
    with pytest.raises(LossContractError):
        build_source_prototypes(torch.ones(1, 2), torch.tensor([0]), class_count=0)
    with pytest.raises(LossContractError):
        build_target_prototypes(torch.ones(1, 2), torch.ones(1, 3), tau_p=float("nan"))
