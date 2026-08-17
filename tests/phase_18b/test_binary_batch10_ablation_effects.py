from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from pada3dacb.binary import (
    BINARY_ABLATIONS,
    apply_binary_ablation_loss_plan,
    binary_ablation_plan,
    build_binary_ablation,
)
from pada3dacb.publication.binary_runtime import BinaryPublicationRuntime
from pada3dacb.training.uda_trainer import ProposedPrototypePseudoAdaptationMethod

CONFIG_PATH = Path("configs/publication/phase18b_binary.yaml")
CANONICAL_COMPONENTS = {
    "L_cls_z": 1.0,
    "L_cls_c": 2.0,
    "L_cons": 3.0,
    "L_concept": 4.0,
    "L_anat": 5.0,
    "L_proto": 6.0,
    "L_pl": 7.0,
    "unrelated": 11.0,
}


@pytest.mark.parametrize(
    ("candidate", "disabled"),
    (
        ("no_proto", ("L_proto",)),
        ("no_pl", ("L_pl",)),
        ("no_cons", ("L_cons",)),
        ("no_concept", ("L_cls_c", "L_concept")),
        ("no_anat", ("L_anat",)),
    ),
)
def test_binary_loss_ablation_plan_changes_only_approved_components(
    candidate: str, disabled: tuple[str, ...]
) -> None:
    plan = binary_ablation_plan(candidate)
    effective = apply_binary_ablation_loss_plan(candidate, CANONICAL_COMPONENTS)

    assert plan.disabled_loss_components == disabled
    assert effective != CANONICAL_COMPONENTS
    assert all(effective[name] == 0.0 for name in disabled)
    assert effective["unrelated"] == CANONICAL_COMPONENTS["unrelated"]
    assert all(
        effective[name] == CANONICAL_COMPONENTS[name]
        for name in CANONICAL_COMPONENTS
        if name not in disabled
    )


def test_mean_pool_plan_preserves_losses_but_changes_model_architecture_identity() -> None:
    plan = binary_ablation_plan("mean_pool")
    assert apply_binary_ablation_loss_plan("mean_pool", CANONICAL_COMPONENTS) == CANONICAL_COMPONENTS
    assert plan.model_variant == "mean_pool"

    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    report = runtime.validate_all_ablations()
    assert report["mean_pool"]["model_architecture_identity"] != report["no_proto"]["model_architecture_identity"]
    assert report["mean_pool"]["effective_loss_components"] == {
        key: value for key, value in CANONICAL_COMPONENTS.items() if key != "unrelated"
    }


def test_validate_only_reports_effective_binary_ablation_interventions() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    report = runtime.validate_all_ablations()

    for candidate in BINARY_ABLATIONS:
        result = report[candidate]
        assert result["effective_loss_components"]
        assert result["classifier_cardinality"] == 2
        assert result["concept_classifier_cardinality"] == 2
        assert result["validate_only"] is True

    assert report["no_proto"]["effective_loss_components"]["L_proto"] == 0.0
    assert report["no_pl"]["effective_loss_components"]["L_pl"] == 0.0
    assert report["no_cons"]["effective_loss_components"]["L_cons"] == 0.0
    assert report["no_concept"]["effective_loss_components"]["L_cls_c"] == 0.0
    assert report["no_concept"]["effective_loss_components"]["L_concept"] == 0.0
    assert report["no_anat"]["effective_loss_components"]["L_anat"] == 0.0


def test_all_binary_ablation_models_keep_two_logit_paths() -> None:
    runtime = BinaryPublicationRuntime.from_path(CONFIG_PATH)
    for candidate in BINARY_ABLATIONS:
        model = build_binary_ablation(candidate, runtime._model_payload())
        output = model(torch.randn(2, 1, 16, 16, 16), torch.ones(2, 2, 2, 2))
        assert tuple(output.latent_logits.shape) == (2, 2)
        assert tuple(output.concept_logits.shape) == (2, 2)


def test_task_scoped_uda_adaptation_consumes_the_binary_loss_plan() -> None:
    method = ProposedPrototypePseudoAdaptationMethod(num_classes=2)
    method.binary_ablation_plan = binary_ablation_plan("no_proto")
    source = SimpleNamespace(z=torch.tensor([[1.0, 0.0], [0.0, 1.0]]))
    target = SimpleNamespace(
        z=torch.tensor([[1.0, 0.0], [0.0, 1.0]]),
        concept_logits=torch.tensor([[8.0, -8.0], [-8.0, 8.0]]),
    )

    result = method.compute(source, target, "full", labels_src=torch.tensor([0, 1]))

    assert result.components["L_proto_weighted"].item() == 0.0
    assert result.components["L_pl_weighted"].item() > 0.0
    assert result.total.item() == result.components["L_pl_weighted"].item()
