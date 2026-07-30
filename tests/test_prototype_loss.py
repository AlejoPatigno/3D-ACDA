import torch

from pada3dacb.adaptation.prototype import (
    PrototypeLoss,
    prototype_alignment_loss,
    prototype_separation_loss,
)


def test_alignment_uses_mean_squared_euclidean_over_mutually_valid_classes():
    source = torch.tensor([[1.0, 2.0], [0.0, 0.0], [10.0, 20.0]])
    target = torch.tensor([[2.0, 4.0], [6.0, 7.0], [0.0, 0.0]])
    valid_source = torch.tensor([True, False, True])
    valid_target = torch.tensor([True, True, False])

    loss = prototype_alignment_loss(source, valid_source, target, valid_target)

    torch.testing.assert_close(loss, torch.tensor(5.0))


def test_alignment_is_zero_when_no_target_rows_are_accepted():
    loss_fn = PrototypeLoss(tau_p=0.95, proto_margin=1.0, lambda_sep=0.0)
    z_src = torch.tensor([[1.0, 2.0], [4.0, 5.0]])
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[10.0, 20.0], [30.0, 40.0]])
    logits_c_tgt = torch.zeros(2, 3)

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    torch.testing.assert_close(output.alignment, torch.tensor(0.0))
    assert output.accepted_target_count == 0


def test_separation_uses_unordered_valid_source_pairs_and_margin_l2_equation():
    prototypes = torch.tensor(
        [
            [0.0, 0.0],
            [0.5, 0.0],
            [2.0, 0.0],
        ]
    )
    valid = torch.tensor([True, True, True])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=1.0)

    expected = torch.tensor((((1.0 - 0.5) ** 2) + 0.0 + 0.0) / 3.0)
    torch.testing.assert_close(loss, expected)


def test_separation_is_zero_with_fewer_than_two_valid_source_classes():
    prototypes = torch.tensor([[0.0, 0.0], [9.0, 9.0], [0.0, 0.0]])
    valid = torch.tensor([False, True, False])

    loss = prototype_separation_loss(prototypes, valid, proto_margin=1.0)

    torch.testing.assert_close(loss, torch.tensor(0.0))


def test_combined_prototype_loss_matches_alignment_plus_weighted_separation():
    loss_fn = PrototypeLoss(tau_p=0.95, proto_margin=1.0, lambda_sep=0.1)
    z_src = torch.tensor([[0.0, 0.0], [0.5, 0.0], [2.0, 0.0]])
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.tensor([[1.0, 0.0], [2.5, 0.0], [4.0, 0.0]])
    logits_c_tgt = torch.tensor([[6.0, 0.0, 0.0], [0.0, 6.0, 0.0], [0.0, 0.0, 6.0]])

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    expected_alignment = torch.tensor((1.0 + 4.0 + 4.0) / 3.0)
    expected_separation = torch.tensor((((1.0 - 0.5) ** 2) + 0.0 + 0.0) / 3.0)
    torch.testing.assert_close(output.alignment, expected_alignment)
    torch.testing.assert_close(output.separation, expected_separation)
    torch.testing.assert_close(output.total, expected_alignment + 0.1 * expected_separation)


def test_prototype_loss_has_no_normalization_or_stateful_cache_ema_momentum():
    loss_fn = PrototypeLoss()
    assert vars(loss_fn) == {"tau_p": 0.95, "proto_margin": 1.0, "lambda_sep": 0.1, "class_count": 3}

    z_src = torch.tensor([[3.0, 4.0]])
    y_src = torch.tensor([0])
    z_tgt = torch.tensor([[0.0, 0.0]])
    logits_c_tgt = torch.tensor([[8.0, 0.0, 0.0]])

    output = loss_fn(z_src, y_src, z_tgt, logits_c_tgt)

    torch.testing.assert_close(output.source_prototypes[0], torch.tensor([3.0, 4.0]))
    assert not hasattr(loss_fn, "cache")
    assert not hasattr(loss_fn, "ema")
    assert not hasattr(loss_fn, "momentum")
