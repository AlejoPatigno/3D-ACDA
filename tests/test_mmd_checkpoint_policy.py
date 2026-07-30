from pathlib import Path

import torch

from tests.phase8_helpers import make_loader
from tests.phase11_helpers import make_mmd_target_loader, make_mmd_trainer


def test_mmd_checkpoint_uses_source_f1_and_stores_complete_provenance(tmp_path: Path):
    trainer = make_mmd_trainer(tmp_path, warmup_epochs=1, full_epochs=2)
    history = trainer.fit(
        make_loader(), make_loader(), target_adaptation_loader=make_mmd_target_loader()
    )
    checkpoint = torch.load(
        tmp_path / "checkpoint_best_source_f1.pt", map_location="cpu", weights_only=False
    )
    expected_epoch = max(
        history.rows, key=lambda row: row["source_validation/macro_f1"]
    )["epoch"]
    assert checkpoint["epoch"] == expected_epoch
    assert checkpoint["adaptation_method"] == "mmd"
    assert checkpoint["mmd_weight"] == 1.0
    assert checkpoint["mmd_feature"] == "z"
    assert checkpoint["mmd_estimator"] == "biased"
    assert checkpoint["mmd_include_diagonal"] is True
    assert checkpoint["mmd_kernel_name"] == "gaussian_rbf_mixture"
    assert checkpoint["mmd_bandwidths"] == [0.5, 1.0, 2.0]
    assert sorted(checkpoint["loader_generator_states"]) == [
        "source_train", "target_adaptation"
    ]
