import torch

from acda3d.models import ACDA3D
from acda3d.models.model_summary import (
    count_parameters_by_module,
    count_trainable_parameters,
    infer_output_shapes,
    summarize_model,
)


def test_parameter_counts_match_manual_calculation():
    model = ACDA3D(2, 8, 6, base_channels=4, concept_hidden_dim=4)
    manual = sum(parameter.numel() for parameter in model.parameters())
    assert count_trainable_parameters(model) == manual
    by_module = count_parameters_by_module(model)
    assert sum(by_module.values()) == manual
    assert by_module["token_dropout"] == 0


def test_summary_and_output_shapes_are_complete_and_restore_mode():
    model = ACDA3D(2, 8, 6, base_channels=4, concept_hidden_dim=4).train()
    masks = torch.ones(2, 2, 2, 2) / 8
    shapes = infer_output_shapes(model, torch.zeros(1, 1, 16, 16, 16), masks)
    assert shapes["F"] == (1, 8, 2, 2, 2)
    assert shapes["U"] == (1, 2, 6)
    assert shapes["concept_logits"] == (1, 3)
    assert model.training
    summary = summarize_model(model, (1, 1, 16, 16, 16), masks)
    assert summary["model_name"] == "3D-ACDA"
    assert summary["total_parameters"] == sum(p.numel() for p in model.parameters())
    assert summary["non_trainable_parameters"] == 0
