import torch

from acda3d.adaptation.prototype import PrototypeLoss


def test_prototype_loss_backpropagates_through_selected_source_and_target_embeddings():
    z_src = torch.tensor([[1.0, 1.0], [2.0, 1.0], [50.0, 50.0]], requires_grad=True)
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.tensor([[1.0, 2.0], [3.0, 1.0], [99.0, 99.0]], requires_grad=True)
    logits_c_tgt = torch.tensor([[6.0, 0.0, 0.0], [0.0, 6.0, 0.0], [0.0, 0.0, 0.0]], requires_grad=True)

    output = PrototypeLoss(lambda_sep=0.0)(z_src, y_src, z_tgt, logits_c_tgt)
    output.total.backward()

    assert z_src.grad is not None
    assert z_tgt.grad is not None
    assert z_src.grad[0].abs().sum() > 0
    assert z_src.grad[1].abs().sum() > 0
    assert z_src.grad[2].abs().sum() == 0
    assert z_tgt.grad[0].abs().sum() > 0
    assert z_tgt.grad[1].abs().sum() > 0
    assert z_tgt.grad[2].abs().sum() == 0
    assert logits_c_tgt.grad is None


def test_source_separation_backpropagates_through_valid_source_prototypes_only():
    z_src = torch.tensor([[1.0, 0.0], [0.8, 0.6], [-1.0, 0.0]], requires_grad=True)
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.zeros(1, 2, requires_grad=True)
    logits_c_tgt = torch.zeros(1, 3, requires_grad=True)

    output = PrototypeLoss(lambda_sep=1.0)(z_src, y_src, z_tgt, logits_c_tgt)
    output.separation.backward()

    assert z_src.grad is not None
    assert z_src.grad[0].abs().sum() > 0
    assert z_src.grad[1].abs().sum() > 0
    assert z_src.grad[2].abs().sum() == 0
    assert z_tgt.grad is None
    assert logits_c_tgt.grad is None
