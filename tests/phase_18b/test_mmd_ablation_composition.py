from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch.utils.data import DataLoader

from acda3d.binary import build_binary_ablation
from acda3d.experiments.mmd_ablations import (
    binary_mmd_ablation_identity,
    binary_mmd_ablation_output_path,
    compose_binary_mmd_ablation,
)
from tests.phase11_helpers import make_mmd_target_loader


def make_binary_loader() -> DataLoader:
    rows = []
    for index in range(6):
        rows.append(
            {
                "x": torch.full((1, 2, 2, 2), float(index + 1) / 6),
                "y": torch.tensor(index % 2, dtype=torch.long),
                "c_target": torch.tensor([0.25, 0.75]),
                "g_bar": torch.tensor([0.4, 0.6]),
            }
        )
    return DataLoader(rows, batch_size=2)


@pytest.mark.parametrize(
    ("candidate", "changed", "expected"),
    (
        ("no_mmd", "mmd_weight", 0.0),
        ("no_cons", "prediction_consistency", 0.0),
        ("no_concept", "concept_supervision", 0.0),
        ("no_anat", "anatomical_consistency", 0.0),
    ),
)
def test_mmd_binary_composition_changes_only_its_approved_core_or_adaptation_value(
    candidate: str, changed: str, expected: float
) -> None:
    composition = compose_binary_mmd_ablation(candidate, num_rois=2, bandwidths=[0.5, 1.0])

    assert composition.base_method == "mmd"
    assert composition.candidate_id == candidate
    assert composition.requires_target_adaptation is True
    assert composition.requires_target_forward is True
    assert composition.core_loss_weights.concept_classification == 1.0
    if changed == "mmd_weight":
        assert composition.mmd_weight == expected
    else:
        assert getattr(composition.core_loss_weights, changed) == expected
        assert composition.mmd_weight == 1.0


def test_no_mmd_composition_keeps_target_loader_and_forward_but_reports_zero_weighted_mmd(
    tmp_path: Path,
) -> None:
    composition = compose_binary_mmd_ablation("no_mmd", num_rois=2, bandwidths=[0.5, 1.0])
    trainer = composition.build_trainer(
        model=build_binary_ablation(
            "no_mmd",
            {"task_id": "cn_vs_impaired", "model": {"num_rois": 2}},
            base_method="mmd",
        ),
        roi_masks=torch.ones(2, 1, 1, 1),
        run_dir=tmp_path,
        seed=17,
        warmup_epochs=0,
        full_epochs=1,
    )

    history = trainer.fit(
        make_binary_loader(),
        make_binary_loader(),
        target_adaptation_loader=make_mmd_target_loader(),
    )
    row = history.rows[0]
    assert row["adaptation/name"] == "mmd"
    assert row["train/target_batches_consumed"] == row["train/source_batches"]
    assert row["train/mmd_loss"] > 0.0
    assert row["train/weighted_mmd_loss"] == pytest.approx(0.0)


def test_mmd_binary_identity_and_output_path_are_candidate_and_run_bound() -> None:
    identity = binary_mmd_ablation_identity("mean_pool", "ADNI_to_OASIS", 3, 42)
    output = binary_mmd_ablation_output_path("runs", "mean_pool", "ADNI_to_OASIS", 3, 42)

    assert identity["candidate_id"] == "mean_pool"
    assert identity["base_method"] == "mmd"
    assert identity["direction"] == "ADNI_to_OASIS"
    assert identity["fold"] == 3
    assert identity["seed"] == 42
    assert output == Path("runs") / "mmd_ablations" / "mean_pool" / "ADNI_to_OASIS" / "seed_42" / "fold_3"


def test_mmd_composition_rejects_unapproved_weight_overrides() -> None:
    with pytest.raises(ValueError, match="unapproved MMD weight override"):
        compose_binary_mmd_ablation(
            "no_cons", num_rois=2, bandwidths=[0.5, 1.0], mmd_weight=0.0
        )
    with pytest.raises(ValueError, match="unapproved MMD weight override"):
        compose_binary_mmd_ablation(
            "no_mmd", num_rois=2, bandwidths=[0.5, 1.0], mmd_weight=1.0
        )


def test_mmd_identity_does_not_collide_with_historical_prototype_pseudo_identity() -> None:
    config = {"task_id": "cn_vs_impaired", "model": {"num_rois": 2}}
    prototype = build_binary_ablation("mean_pool", config)
    mmd = build_binary_ablation("mean_pool", config, base_method="mmd")

    assert prototype.binary_metadata["base_method"] == "prototype_pseudo"
    assert mmd.binary_metadata["base_method"] == "mmd"
    assert prototype.binary_metadata["identity_hash"] != mmd.binary_metadata["identity_hash"]


def test_mmd_identity_binds_accepted_runtime_configuration() -> None:
    base = binary_mmd_ablation_identity(
        "mean_pool",
        "ADNI_to_OASIS",
        3,
        42,
        bandwidths=[0.5, 1.0],
        mmd_weight=1.0,
    )
    changed = binary_mmd_ablation_identity(
        "mean_pool",
        "ADNI_to_OASIS",
        3,
        42,
        bandwidths=[0.5, 2.0],
        mmd_weight=1.0,
    )

    assert base["mmd_configuration"]["kernel"]["bandwidths"] == [0.5, 1.0]
    assert base["mmd_configuration_hash"]
    assert base["mmd_configuration_hash"] != changed["mmd_configuration_hash"]
    assert base["identity_hash"] != changed["identity_hash"]


def test_mmd_mean_pool_build_keeps_binary_heads_and_changes_only_aggregator() -> None:
    model = build_binary_ablation(
        "mean_pool",
        {"task_id": "cn_vs_impaired", "model": {"num_rois": 2}},
        base_method="mmd",
    )
    output = model(torch.randn(2, 1, 16, 16, 16), torch.ones(2, 2, 2, 2))

    assert tuple(output.latent_logits.shape) == (2, 2)
    assert tuple(output.concept_logits.shape) == (2, 2)
    assert model.binary_metadata["base_method"] == "mmd"
    assert model.binary_metadata["candidate_id"] == "mean_pool"
    assert model.binary_metadata["architecture_identity"] == "3D-ACDA+MeanPoolAggregator"
