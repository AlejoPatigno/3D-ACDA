"""Independent CPU reference checks for Phase 17 mathematical contracts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from pada3dacb.ablations import resolve_ablation_config
from pada3dacb.ablations.schemas import (
    AblationBaseConfig,
    ApprovalRecord,
    ApprovalStatus,
    AssignmentManifest,
    LossCoefficients,
    ModelVariant,
    RunMatrix,
)
from pada3dacb.adaptation.prototype_pseudo import PrototypePseudoAdaptationLoss
from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.models.ablations import MeanPoolAggregator, build_mean_pool_model
from pada3dacb.models.pada3dacb import PADA3DACBOutput
from pada3dacb.training import trainer as trainer_module
from pada3dacb.training.uda_trainer import ComposedCoreLoss, UDATrainer

_LOSSES = LossCoefficients(
    lambda_z=1.0,
    lambda_c=1.0,
    lambda_cons=0.1,
    lambda_cbm=0.5,
    lambda_anat=0.2,
    lambda_proto=1.0,
    lambda_pl=0.1,
    tau_p=0.95,
    proto_margin=1.0,
    lambda_sep=0.1,
    label_smoothing=0.1,
    warm_lambda_z=0.1,
    warm_lambda_c=1.0,
    warm_lambda_cbm=1.0,
    warm_lambda_anat=1.0,
    warm_lambda_cons=0.0,
)


def _base_config() -> AblationBaseConfig:
    return AblationBaseConfig(
        base_method="PADA-3DACB",
        losses=_LOSSES,
        model=ModelVariant(name="PADA-3DACB", aggregator="AttentionAggregator"),
        approval=ApprovalRecord("phase17-math", ApprovalStatus.APPROVED),
        epochs_warm=1,
        epochs_full=2,
        matrix=RunMatrix(("ADNI_to_OASIS",), (0,), (17,)),
        assignments=AssignmentManifest(("source",), ("target-adaptation",), ("target-evaluation",)),
        precomputed_artifacts=("concept=synthetic", "jacobian=synthetic"),
    )


def _resolved(candidate: str):
    return resolve_ablation_config(_base_config(), candidate)


def _output() -> PADA3DACBOutput:
    latent = torch.tensor(
        [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]], requires_grad=True
    )
    concept_logits = torch.tensor(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], requires_grad=True
    )
    concepts = torch.tensor(
        [[0.2, 0.4], [0.3, 0.5], [0.6, 0.1]], requires_grad=True
    )
    return PADA3DACBOutput(
        F=torch.zeros(3, 1),
        T=torch.zeros(3, 2, 2),
        U=torch.zeros(3, 2, 2),
        z=torch.zeros(3, 2, requires_grad=True),
        alpha=torch.zeros(3, 2),
        latent_logits=latent,
        latent_probabilities=torch.softmax(latent, dim=-1),
        concepts=concepts,
        concept_logits=concept_logits,
        concept_probabilities=torch.softmax(concept_logits, dim=-1),
    )


def _adaptation_inputs() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    return (
        torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], requires_grad=True),
        torch.tensor([0, 1, 2]),
        torch.tensor([[0.9, 0.1], [0.1, 0.9], [0.8, 0.8]], requires_grad=True),
        torch.tensor(
            [[8.0, 0.0, 0.0], [0.0, 8.0, 0.0], [0.0, 0.0, 8.0]], requires_grad=True
        ),
    )


def test_warm_reference_excludes_adaptation_and_logs_zero() -> None:
    output = _output()
    labels = torch.tensor([0, 1, 2])
    concept_targets = torch.zeros(3, 2)
    g_bar = torch.zeros(3, 2)
    core = CorePADA3DACBLoss(num_rois=2, label_smoothing=0.1)
    warm = core(output, labels, concept_targets, g_bar, stage="warm")
    expected = (
        0.1 * warm.classification
        + warm.concept_classification
        + warm.concept_supervision * 0.5
        + warm.anatomical_consistency * 0.2
    )
    torch.testing.assert_close(warm.total, expected)

    z_src, y_src, z_tgt, logits = _adaptation_inputs()
    adaptation = PrototypePseudoAdaptationLoss.from_resolved(_resolved("no_proto"))

    class ExplodingLoss:
        def __call__(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("warm stage computed an adaptation term")

    adaptation.prototype_loss = ExplodingLoss()  # type: ignore[assignment]
    adaptation.pseudo_label_loss = ExplodingLoss()  # type: ignore[assignment]
    inactive = adaptation(z_src, y_src, z_tgt, logits, stage="warm")
    assert inactive.adaptation_active is False
    assert inactive.prototype_raw.item() == 0.0
    assert inactive.pseudo_label_raw.item() == 0.0
    trainer = object.__new__(UDATrainer)
    trainer.adaptation_method = SimpleNamespace(name="prototype_pseudo")
    logged = trainer._warm_metrics([1])
    assert logged["L_proto_raw"] == logged["L_proto_weighted"] == 0.0
    assert logged["L_pl_raw"] == logged["L_pl_weighted"] == 0.0


@pytest.mark.parametrize(
    ("candidate", "term", "coefficient"),
    [
        ("no_proto", "prototype", 1.0),
        ("no_pl", "pseudo", 0.1),
    ],
)
def test_full_adaptation_reference_disables_exactly_one_weighted_term(
    candidate: str, term: str, coefficient: float
) -> None:
    inputs = _adaptation_inputs()
    canonical = PrototypePseudoAdaptationLoss()
    reference = canonical(*inputs, stage="full")
    result = PrototypePseudoAdaptationLoss.from_resolved(_resolved(candidate))(
        *inputs, stage="full"
    )
    if term == "prototype":
        expected = reference.total - coefficient * reference.prototype_raw
        assert result.prototype_active is False
        assert result.prototype_raw.item() == 0.0
        assert result.prototype_weighted.item() == 0.0
    else:
        expected = reference.total - coefficient * reference.pseudo_label_raw
        assert result.pseudo_label_active is False
        assert result.pseudo_label_raw.item() == 0.0
        assert result.pseudo_label_weighted.item() == 0.0
    torch.testing.assert_close(result.total, expected)


@pytest.mark.parametrize(
    ("candidate", "field", "coefficient"),
    [
        ("no_cons", "prediction_consistency", 0.1),
        ("no_concept", "concept_supervision", 0.5),
        ("no_anat", "anatomical_consistency", 0.2),
    ],
)
def test_full_core_reference_disables_exactly_one_weighted_term(
    candidate: str, field: str, coefficient: float
) -> None:
    output = _output()
    labels = torch.tensor([0, 1, 2])
    concept_targets = torch.zeros(3, 2)
    g_bar = torch.zeros(3, 2)
    baseline = CorePADA3DACBLoss(num_rois=2, label_smoothing=0.1)(
        output, labels, concept_targets, g_bar, stage="full"
    )
    result = ComposedCoreLoss(CorePADA3DACBLoss(num_rois=2), _resolved(candidate))(
        output, labels, concept_targets, g_bar, stage="full"
    )
    expected = baseline.total - coefficient * getattr(baseline, field)
    torch.testing.assert_close(result.total, expected)
    term_name = {"prediction_consistency": "L_cons", "concept_supervision": "L_concept", "anatomical_consistency": "L_anat"}[field]
    assert result.component_diagnostics[f"{term_name}_active"] is False
    assert result.component_diagnostics[f"{term_name}_raw"] == 0.0
    assert result.component_diagnostics[f"{term_name}_weighted"] == 0.0


@pytest.mark.parametrize(
    ("candidate", "attribute"),
    [
        ("no_cons", "prediction_consistency"),
        ("no_concept", "concept_supervision"),
        ("no_anat", "anatomical_consistency"),
    ],
)
def test_disabled_core_component_is_not_computed(candidate: str, attribute: str) -> None:
    base = CorePADA3DACBLoss(num_rois=2)

    class ExplodingLoss(nn.Module):
        def forward(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("disabled core component was computed")

    setattr(base, attribute, ExplodingLoss())
    result = ComposedCoreLoss(base, _resolved(candidate))(
        _output(), torch.tensor([0, 1, 2]), torch.zeros(3, 2), torch.zeros(3, 2)
    )
    assert torch.isfinite(result.total)


@pytest.mark.parametrize("candidate", ["no_proto", "no_pl"])
def test_enabled_adaptation_component_has_gradient_and_optimizer_step(candidate: str) -> None:
    z_src, y_src, z_tgt, logits = _adaptation_inputs()
    optimizer = torch.optim.SGD([z_src, z_tgt, logits], lr=0.05)
    before = tuple(value.detach().clone() for value in (z_src, z_tgt, logits))
    result = PrototypePseudoAdaptationLoss.from_resolved(_resolved(candidate))(
        z_src, y_src, z_tgt, logits, stage="full"
    )
    result.total.backward()
    assert any(value.grad is not None and torch.isfinite(value.grad).all() for value in (z_src, z_tgt, logits))
    optimizer.step()
    assert any(not torch.equal(previous, current.detach()) for previous, current in zip(before, (z_src, z_tgt, logits), strict=True))


def test_mean_pool_is_exact_uniform_mean_and_has_no_contextual_variant() -> None:
    U = torch.arange(24, dtype=torch.float32).reshape(2, 3, 4).requires_grad_()
    z, alpha = MeanPoolAggregator()(U)
    assert torch.equal(z, U.mean(dim=1))
    assert torch.equal(alpha, torch.full((2, 3), 1 / 3))
    z.sum().backward()
    assert torch.equal(U.grad, torch.full_like(U, 1 / 3))

    model = build_mean_pool_model(
        num_rois=3,
        feature_dim=8,
        token_dim=6,
        base_channels=2,
        concept_hidden_dim=4,
        token_dropout=0.0,
        concept_dropout=0.0,
    )
    assert not hasattr(model, "ctx_enc")
    assert not hasattr(model, "contextual_encoder")
    assert not hasattr(model, "runtime_variant_switch")


def test_source_only_and_contextual_equivalences_remain_blocked() -> None:
    for candidate in ("no_domain_adaptation", "full", "no_ctx_encoder", "identity_ctx"):
        with pytest.raises(Exception) as error:
            resolve_ablation_config(_base_config(), candidate)
        assert getattr(error.value, "reason", None) in {
            "source_only_not_proven",
            "architecture_disposition_blocked",
        }


class _EpochProbe(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.tensor(1.0))

    def forward(self, _x: torch.Tensor, _masks: torch.Tensor) -> object:
        return SimpleNamespace(concept_probabilities=torch.tensor([[1.0, 0.0, 0.0]]))


class _ProbeTrainer(trainer_module.BaseFixedEpochTrainer):
    def _train_epoch_for_stage(self, _source: object, _target: object, _stage: str) -> dict[str, float]:
        return {"total": 1.0}


def test_fixed_epochs_and_source_macro_f1_selection_ignore_target_monitoring(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_scores = iter((0.25, 0.75, 0.50))
    target_scores = iter((0.99, 0.01, 0.99))

    def fake_evaluate(*_args: object, namespace: str = "source_validation", **_kwargs: object) -> dict[str, float | str]:
        score = next(target_scores if namespace == "target_monitoring" else source_scores)
        return {f"{namespace}/macro_f1": score, f"{namespace}/accuracy": score}

    monkeypatch.setattr(trainer_module, "evaluate_labeled_loader", fake_evaluate)
    config = trainer_module.FixedEpochTrainingConfig(
        warmup_epochs=1,
        full_epochs=2,
        checkpoint_every=1,
        device="cpu",
        target_monitoring_enabled=True,
    )
    trainer = _ProbeTrainer(
        _EpochProbe(),
        nn.Identity(),
        torch.zeros(1),
        tmp_path,
        config=config,
    )
    loader = [{"x": torch.zeros(1)}]
    history = trainer.fit(loader, loader, loader)
    assert len(history.rows) == 3
    assert [row["stage"] for row in history.rows] == ["warm", "full", "full"]
    assert trainer.best_source_macro_f1 == 0.75
    assert history.rows[0]["target_monitoring/macro_f1"] == 0.99
    assert history.rows[1]["target_monitoring/macro_f1"] == 0.01
    assert (tmp_path / "checkpoint_best_source_f1.pt").exists()
    assert (tmp_path / "checkpoint_last.pt").exists()
    assert not any("target_monitoring/macro_f1" in key for key in trainer.resolved_configuration)


def test_target_monitoring_is_observational_and_namespaced() -> None:
    parameter = nn.Parameter(torch.tensor(1.0))

    class MonitorModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.scale = parameter

        def forward(self, x: torch.Tensor, _masks: torch.Tensor) -> object:
            logits = torch.stack((self.scale.expand(x.shape[0]), torch.zeros(x.shape[0]), torch.zeros(x.shape[0])), dim=1)
            return SimpleNamespace(concept_probabilities=torch.softmax(logits, dim=-1))

    metrics = trainer_module.evaluate_labeled_loader(
        MonitorModel(),
        [{"x": torch.zeros(2, 1), "y": torch.tensor([0, 0])}],
        torch.zeros(1),
        torch.device("cpu"),
        namespace="target_monitoring",
    )
    assert metrics["target_monitoring/label"] == "MONITORING ONLY — NOT A TRAINING LOSS"
    assert parameter.grad is None

