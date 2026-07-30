import inspect
import math

import torch
from torch.nn import functional as F

from pada3dacb.adaptation.prototype_pseudo import (
    PrototypePseudoAdaptationConfig,
    PrototypePseudoAdaptationLoss,
    prototype_pseudo_adaptation_loss,
)


def test_hand_computed_prototype_and_weighted_objective_reference():
    z_src = torch.tensor(
        [
            [0.0, 0.0],
            [2.0, 0.0],
            [5.0, 0.0],
        ],
        dtype=torch.float64,
    )
    y_src = torch.tensor([0, 0, 1])
    z_tgt = torch.tensor(
        [
            [4.0, 0.0],
            [6.0, 0.0],
            [99.0, 99.0],
            [9.0, 0.0],
        ],
        dtype=torch.float64,
    )
    logits_c_tgt = torch.tensor(
        [
            [4.0, 0.0, 0.0],
            [5.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 4.0],
        ],
        dtype=torch.float64,
    )
    config = PrototypePseudoAdaptationConfig(
        lambda_proto=3.0,
        lambda_pl=0.5,
        lambda_sep=0.25,
        proto_margin=6.0,
        tau_p=0.8,
    )

    output = prototype_pseudo_adaptation_loss(
        z_src=z_src,
        y_src=y_src,
        z_tgt=z_tgt,
        logits_c_tgt=logits_c_tgt,
        stage="full",
        config=config,
    )

    expected_source_class_0 = torch.tensor([1.0, 0.0], dtype=torch.float64)
    expected_source_class_1 = torch.tensor([5.0, 0.0], dtype=torch.float64)
    expected_target_class_0 = torch.tensor([5.0, 0.0], dtype=torch.float64)
    expected_target_class_2 = torch.tensor([9.0, 0.0], dtype=torch.float64)
    expected_alignment = torch.tensor(16.0, dtype=torch.float64)
    expected_separation = torch.tensor(4.0, dtype=torch.float64)
    expected_proto = expected_alignment + 0.25 * expected_separation
    expected_pl = F.cross_entropy(logits_c_tgt[[0, 1, 3]], torch.tensor([0, 0, 2]))
    expected_total = 3.0 * expected_proto + 0.5 * expected_pl

    torch.testing.assert_close(output.source_prototypes[0], expected_source_class_0)
    torch.testing.assert_close(output.source_prototypes[1], expected_source_class_1)
    torch.testing.assert_close(output.source_prototypes[2], torch.zeros(2, dtype=torch.float64))
    torch.testing.assert_close(output.target_prototypes[0], expected_target_class_0)
    torch.testing.assert_close(output.target_prototypes[1], torch.zeros(2, dtype=torch.float64))
    torch.testing.assert_close(output.target_prototypes[2], expected_target_class_2)
    assert output.classes_with_source_prototypes == [0, 1]
    assert output.classes_with_target_prototypes == [0, 2]
    assert output.classes_with_both_prototypes == [0]
    torch.testing.assert_close(output.prototype_alignment, expected_alignment)
    torch.testing.assert_close(output.prototype_separation, expected_separation)
    torch.testing.assert_close(output.prototype_raw, expected_proto)
    torch.testing.assert_close(output.pseudo_label_raw, expected_pl)
    torch.testing.assert_close(output.prototype_weighted, 3.0 * expected_proto)
    torch.testing.assert_close(output.pseudo_label_weighted, 0.5 * expected_pl)
    torch.testing.assert_close(output.total, expected_total)


def test_pseudo_label_softmax_argmax_equation_and_equal_threshold_boundary():
    boundary_logit = math.log(2.0)
    logits_c_tgt = torch.tensor(
        [
            [boundary_logit, 0.0, 0.0],
            [0.0, boundary_logit, 0.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=torch.float64,
    )
    z_src = torch.tensor([[0.0], [2.0]], dtype=torch.float64)
    y_src = torch.tensor([0, 1])
    z_tgt = torch.tensor([[1.0], [3.0], [5.0]], dtype=torch.float64)
    config = PrototypePseudoAdaptationConfig(tau_p=0.5, lambda_proto=0.0, lambda_pl=1.0)

    output = PrototypePseudoAdaptationLoss(config)(z_src, y_src, z_tgt, logits_c_tgt, stage="full")

    probabilities = torch.softmax(logits_c_tgt, dim=-1)
    expected_confidence, expected_labels = probabilities.max(dim=-1)
    expected_accepted = torch.tensor([True, True, False])
    expected_loss = F.cross_entropy(logits_c_tgt[expected_accepted], expected_labels[expected_accepted])

    torch.testing.assert_close(output.pseudo_label_confidence, expected_confidence)
    assert output.target_pseudo_labels.tolist() == expected_labels.tolist()
    assert output.accepted_target.tolist() == expected_accepted.tolist()
    assert output.accepted_count == 2
    torch.testing.assert_close(output.pseudo_label_raw, expected_loss)
    torch.testing.assert_close(output.total, expected_loss)


def test_no_target_diagnosis_or_target_supervision_parameters_are_exposed():
    function_parameters = inspect.signature(prototype_pseudo_adaptation_loss).parameters
    forward_parameters = inspect.signature(PrototypePseudoAdaptationLoss.forward).parameters

    forbidden_names = {"y_tgt", "labels_tgt", "target_labels", "c_target_tgt", "g_bar_tgt"}
    assert forbidden_names.isdisjoint(function_parameters)
    assert forbidden_names.isdisjoint(forward_parameters)

    z_src = torch.tensor([[0.0, 0.0]])
    y_src = torch.tensor([0])
    z_tgt = torch.tensor([[1.0, 1.0]])
    logits_c_tgt = torch.tensor([[8.0, 0.0, 0.0]])
    target_diagnosis_labels = torch.tensor([2])

    try:
        prototype_pseudo_adaptation_loss(
            z_src=z_src,
            y_src=y_src,
            z_tgt=z_tgt,
            logits_c_tgt=logits_c_tgt,
            target_labels=target_diagnosis_labels,
            stage="full",
        )
    except TypeError as exc:
        assert "target_labels" in str(exc)
    else:  # pragma: no cover - this would be a target-label firewall breach.
        raise AssertionError("target diagnosis labels must not be accepted by the adaptation API")
