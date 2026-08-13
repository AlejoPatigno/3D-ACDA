"""CPU-only tests for Phase 17 loss-component composition."""

from __future__ import annotations

import pytest
import torch

from pada3dacb.ablations.resolver import resolve_ablation_config
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
from pada3dacb.models.pada3dacb import PADA3DACBOutput
from pada3dacb.training.uda_trainer import ComposedCoreLoss

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


def _resolved(name: str):
    return resolve_ablation_config(
        AblationBaseConfig(
            base_method="PADA-3DACB",
            losses=_LOSSES,
            model=ModelVariant(name="PADA-3DACB", aggregator="AttentionAggregator"),
            approval=ApprovalRecord("phase17-test", ApprovalStatus.APPROVED),
            epochs_warm=1,
            epochs_full=1,
            matrix=RunMatrix(("ADNI_to_OASIS",), (0,), (1,)),
            assignments=AssignmentManifest(("src-1",), ("tgt-a",), ("tgt-e",)),
            precomputed_artifacts=("concept=synthetic", "jacobian=synthetic"),
        ),
        name,
    )


def _adaptation_tensors() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    z_src = torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], requires_grad=True)
    y_src = torch.tensor([0, 1, 2])
    z_tgt = torch.tensor([[0.9, 0.1], [0.1, 0.9], [0.8, 0.8]], requires_grad=True)
    logits = torch.tensor([[8.0, 0.0, 0.0], [0.0, 8.0, 0.0], [0.0, 0.0, 8.0]], requires_grad=True)
    return z_src, y_src, z_tgt, logits


@pytest.mark.parametrize("candidate,parameter", [("no_proto", "lambda_proto"), ("no_pl", "lambda_pl")])
def test_resolved_adaptation_component_is_exactly_disabled(candidate: str, parameter: str) -> None:
    contract = _resolved(candidate)
    z_src, y_src, z_tgt, logits = _adaptation_tensors()
    result = PrototypePseudoAdaptationLoss.from_resolved(contract)(
        z_src, y_src, z_tgt, logits, stage="full"
    )

    assert getattr(contract.losses, parameter) == 0.0
    assert result.total == result.prototype_weighted + result.pseudo_label_weighted
    if candidate == "no_proto":
        assert result.prototype_raw == 0
        assert result.prototype_weighted == 0
        assert result.prototype_active is False
        assert result.source_prototypes is None
    else:
        assert result.pseudo_label_raw == 0
        assert result.pseudo_label_weighted == 0
        assert result.pseudo_label_active is False
    result.total.backward()
    assert any(t.grad is not None for t in (z_src, z_tgt, logits))


@pytest.mark.parametrize("candidate", ["no_proto", "no_pl", "no_cons", "no_concept", "no_anat"])
def test_warm_adaptation_is_inactive_and_full_has_component_diagnostics(candidate: str) -> None:
    contract = _resolved(candidate)
    z_src, y_src, z_tgt, logits = _adaptation_tensors()
    adaptation = PrototypePseudoAdaptationLoss.from_resolved(contract)
    warm = adaptation(z_src, y_src, z_tgt, logits, stage="warm")
    assert warm.total == 0
    assert warm.adaptation_active is False
    assert warm.prototype_raw == 0 and warm.pseudo_label_raw == 0

    output = _synthetic_output()
    core = ComposedCoreLoss(
        CorePADA3DACBLoss(num_rois=2, label_smoothing=0.1), contract
    )
    source_y = torch.tensor([0, 1, 2])
    concept_targets = torch.zeros(3, 2)
    g_bar = torch.zeros(3, 2)
    full = core(output, source_y, concept_targets, g_bar, stage="full")
    if candidate in {"no_cons", "no_concept", "no_anat"}:
        disabled = {
            "no_cons": "L_cons",
            "no_concept": "L_concept",
            "no_anat": "L_anat",
        }[candidate]
        assert full.component_diagnostics[f"{disabled}_raw"] == 0.0
        assert full.component_diagnostics[f"{disabled}_weighted"] == 0.0
        assert full.component_diagnostics[f"{disabled}_active"] is False


def _synthetic_output() -> PADA3DACBOutput:
    latent = torch.tensor([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]], requires_grad=True)
    concept_logits = latent.clone().requires_grad_()
    concepts = torch.tensor([[0.2, 0.4], [0.3, 0.5], [0.6, 0.1]], requires_grad=True)
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


@pytest.mark.parametrize(
    "candidate,disabled_attribute",
    [("no_proto", "prototype_loss"), ("no_pl", "pseudo_label_loss")],
)
def test_disabled_adaptation_term_is_not_computed(candidate: str, disabled_attribute: str) -> None:
    loss = PrototypePseudoAdaptationLoss.from_resolved(_resolved(candidate))

    class ExplodingLoss:
        def __call__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("disabled adaptation component was computed")

    setattr(loss, disabled_attribute, ExplodingLoss())
    z_src, y_src, z_tgt, logits = _adaptation_tensors()
    result = loss(z_src, y_src, z_tgt, logits, stage="full")
    assert result.total.isfinite()


@pytest.mark.parametrize(
    "candidate,field,coefficient",
    [
        ("no_cons", "prediction_consistency", 0.1),
        ("no_concept", "concept_supervision", 0.5),
        ("no_anat", "anatomical_consistency", 0.2),
    ],
)
def test_core_objective_is_exact_base_minus_one_component(
    candidate: str, field: str, coefficient: float
) -> None:
    output = _synthetic_output()
    base = CorePADA3DACBLoss(num_rois=2, label_smoothing=0.1)
    labels = torch.tensor([0, 1, 2])
    concept_targets = torch.zeros(3, 2)
    g_bar = torch.zeros(3, 2)
    baseline = base(output, labels, concept_targets, g_bar, stage="full")
    composed = ComposedCoreLoss(base, _resolved(candidate))(
        output, labels, concept_targets, g_bar, stage="full"
    )
    expected = baseline.total - coefficient * getattr(baseline, field)
    torch.testing.assert_close(composed.total, expected)


def test_one_optimizer_step_receives_adaptation_gradient() -> None:
    contract = _resolved("no_pl")
    z_src, y_src, z_tgt, logits = _adaptation_tensors()
    optimizer = torch.optim.SGD([z_src, z_tgt, logits], lr=0.1)
    before = z_tgt.detach().clone()
    result = PrototypePseudoAdaptationLoss.from_resolved(contract)(
        z_src, y_src, z_tgt, logits, stage="full"
    )
    optimizer.zero_grad()
    result.total.backward()
    optimizer.step()
    assert not torch.equal(before, z_tgt.detach())


def test_target_adaptation_accepts_exact_metadata_contract() -> None:
    from pada3dacb.training.uda_trainer import UDATrainer

    UDATrainer._validate_target_batch(
        {
            "x": torch.zeros(2, 1),
            "subject_id": ["subject-1", "subject-2"],
            "subject_hash": ["hash-1", "hash-2"],
            "cohort": ["ADNI", "OASIS"],
        },
        strict=True,
    )


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "y",
        "label",
        "diagnosis",
        "concept_target",
        "concept_targets",
        "jacobian",
        "jacobian_target",
    ],
)
def test_target_adaptation_rejects_forbidden_fields(forbidden_key: str) -> None:
    from pada3dacb.training.uda_trainer import UDATrainer

    with pytest.raises(Exception, match="forbidden|unsupported"):
        UDATrainer._validate_target_batch(
            {
                "x": torch.zeros(2, 1),
                "subject_id": ["subject-1", "subject-2"],
                "subject_hash": ["hash-1", "hash-2"],
                "cohort": ["ADNI", "OASIS"],
                forbidden_key: torch.zeros(2),
            },
            strict=True,
        )


@pytest.mark.parametrize("missing_key", ["subject_id", "subject_hash", "cohort"])
def test_strict_target_adaptation_requires_all_metadata(missing_key: str) -> None:
    from pada3dacb.training.uda_trainer import UDATrainer

    batch = {
        "x": torch.zeros(2, 1),
        "subject_id": ["subject-1", "subject-2"],
        "subject_hash": ["hash-1", "hash-2"],
        "cohort": ["ADNI", "OASIS"],
    }
    del batch[missing_key]
    with pytest.raises(Exception, match="exactly|unsupported"):
        UDATrainer._validate_target_batch(batch, strict=True)



def test_strict_target_adaptation_rejects_any_extra_field() -> None:
    from pada3dacb.training.uda_trainer import UDATrainer

    with pytest.raises(Exception, match="unsupported"):
        UDATrainer._validate_target_batch(
            {
                "x": torch.zeros(2, 1),
                "subject_id": ["subject-1", "subject-2"],
                "subject_hash": ["hash-1", "hash-2"],
                "cohort": ["ADNI", "OASIS"],
                "extra": torch.zeros(2),
            },
            strict=True,
        )



def test_non_ablation_target_adaptation_keeps_x_only_compatibility() -> None:
    from pada3dacb.training.uda_trainer import UDATrainer

    UDATrainer._validate_target_batch({"x": torch.zeros(2, 1)}, strict=False)
