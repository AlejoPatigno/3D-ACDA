from __future__ import annotations

import pytest
import torch

from acda3d.ablations import resolve_ablation_config
from acda3d.exceptions import ModelContractError
from acda3d.models.ablations import (
    MEAN_POOL_MODEL_VARIANT,
    MeanPoolACDA3D,
    build_mean_pool_model,
    mean_pool_model_variant_hash,
)

PRIMARY_LOSSES = {
    "lambda_z": 1.0,
    "lambda_c": 1.0,
    "lambda_cons": 0.1,
    "lambda_cbm": 0.5,
    "lambda_anat": 0.2,
    "lambda_proto": 1.0,
    "lambda_pl": 0.1,
    "tau_p": 0.95,
    "proto_margin": 1.0,
    "lambda_sep": 0.1,
    "label_smoothing": 0.1,
    "warm_lambda_z": 0.1,
    "warm_lambda_c": 1.0,
    "warm_lambda_cbm": 1.0,
    "warm_lambda_anat": 1.0,
    "warm_lambda_cons": 0.0,
}


def base_config() -> dict[str, object]:
    return {
        "base_method": "3D-ACDA",
        "model": {"name": "3D-ACDA", "contextual_encoder": False},
        "losses": PRIMARY_LOSSES,
        "approval": {"status": "approved", "approval_id": "maintainer-phase17"},
        "epochs": {"warm": 1, "full": 1},
        "matrix": {
            "directions": ["ADNI_to_OASIS", "OASIS_to_ADNI"],
            "folds": [0],
            "seeds": [42],
        },
        "assignments": {
            "source": ["source-0"],
            "target_adaptation": ["target-adapt-0"],
            "target_evaluation": ["target-eval-0"],
        },
        "precomputed_artifacts": {"concepts": "fixture-concepts", "jacobians": "fixture-jacobians"},
    }


def fixture_inputs(*, dtype: torch.dtype = torch.float32) -> tuple[torch.Tensor, torch.Tensor]:
    torch.manual_seed(17)
    x = torch.randn(2, 1, 16, 16, 16, dtype=dtype)
    roi_masks = torch.zeros(3, 2, 2, 2, dtype=dtype)
    roi_masks[0, 0, 0, 0] = 1
    roi_masks[1, 0, 0, 1] = 1
    roi_masks[2, 1, 1, 1] = 1
    return x, roi_masks


def build_fixture_model() -> MeanPoolACDA3D:
    return build_mean_pool_model(
        num_rois=3,
        feature_dim=8,
        token_dim=6,
        base_channels=2,
        concept_hidden_dim=4,
        token_dropout=0.0,
        concept_dropout=0.0,
    )


def test_mean_pool_matches_notebook_operation_and_uniform_alpha() -> None:
    model = build_fixture_model().eval()
    x, roi_masks = fixture_inputs()

    output = model(x, roi_masks)
    expected_z = output.U.mean(dim=1)
    expected_alpha = torch.full((x.shape[0], roi_masks.shape[0]), 1 / roi_masks.shape[0])

    assert torch.equal(output.z, expected_z)
    assert torch.equal(output.alpha, expected_alpha)
    assert torch.equal(output.alpha.sum(dim=1), torch.ones(x.shape[0]))


def test_mean_pool_preserves_output_contract_device_dtype_and_gradients() -> None:
    model = build_fixture_model().train()
    x, roi_masks = fixture_inputs()
    x.requires_grad_()

    output = model(x, roi_masks)
    assert output.F.device == x.device
    assert output.F.dtype == x.dtype
    assert output.T.shape == (2, 3, 6)
    assert output.U.shape == (2, 3, 6)
    assert output.z.shape == (2, 6)
    assert output.alpha.shape == (2, 3)
    assert output.latent_logits.shape == (2, 3)
    assert output.concept_logits.shape == (2, 3)
    assert torch.isfinite(output.z).all()

    output.latent_logits.sum().backward()
    assert x.grad is not None
    assert torch.isfinite(x.grad).all()
    assert any(parameter.grad is not None for parameter in model.parameters())


def test_mean_pool_output_is_deterministic_in_eval_mode() -> None:
    model = build_fixture_model().eval()
    x, roi_masks = fixture_inputs()

    first = model(x, roi_masks)
    second = model(x, roi_masks)
    assert torch.equal(first.z, second.z)
    assert torch.equal(first.alpha, second.alpha)
    assert torch.equal(first.latent_logits, second.latent_logits)
    assert torch.equal(first.concept_logits, second.concept_logits)


@pytest.mark.parametrize(
    ("x", "roi_masks"),
    [
        (torch.zeros(1, 16, 16, 16), fixture_inputs()[1]),
        (torch.zeros(1, 1, 16, 16, 16, dtype=torch.float64), fixture_inputs()[1]),
        (torch.full((1, 1, 16, 16, 16), float("nan")), fixture_inputs()[1]),
        (fixture_inputs()[0], torch.zeros(3, 3, 2, 2)),
        (fixture_inputs()[0], torch.full((3, 2, 2, 2), float("nan"))),
        (fixture_inputs()[0], torch.zeros(3, 2, 2, 2)),
    ],
)
def test_mean_pool_rejects_invalid_inputs(x: torch.Tensor, roi_masks: torch.Tensor) -> None:
    with pytest.raises(ModelContractError):
        build_fixture_model()(x, roi_masks)


def test_mean_pool_has_no_contextual_encoder_or_runtime_switch() -> None:
    model = build_fixture_model()
    assert not hasattr(model, "ctx_enc")
    assert not hasattr(model, "contextual_encoder")
    assert not hasattr(model, "runtime_variant_switch")
    assert not hasattr(model, "variant_switch")
    assert "ContextualROIEncoder" not in type(model).__name__


def test_mean_pool_variant_identity_matches_registry_and_differs_from_base() -> None:
    resolved = resolve_ablation_config(base_config(), "mean_pool")

    assert MEAN_POOL_MODEL_VARIANT.name == "3D-ACDA+MeanPoolAggregator"
    assert MEAN_POOL_MODEL_VARIANT.aggregator == "MeanPoolAggregator"
    assert mean_pool_model_variant_hash() == resolved.model_variant_hash
    assert resolved.model_variant_hash != resolve_ablation_config(base_config(), "no_proto").model_variant_hash


def test_mean_pooling_alias_remains_blocked_without_resolver_approval() -> None:
    with pytest.raises(Exception) as error:
        resolve_ablation_config(base_config(), "mean_pooling")
    assert getattr(error.value, "reason", None) == "alias_not_approved"
