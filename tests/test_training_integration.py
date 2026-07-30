from pathlib import Path

import torch

from pada3dacb.data.datasets import LabeledSourceDataset
from pada3dacb.data.records import SubjectRecord
from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.models import PADA3DACB, prepare_feature_grid_roi_masks


def test_phase6_phase7_phase8_forward_loss_backward(tmp_path: Path):
    derivative = tmp_path / "x.pt"
    concept = tmp_path / "c.pt"
    jacobian = tmp_path / "g.pt"
    torch.save(torch.randn(1, 16, 16, 16), derivative)
    torch.save(torch.tensor([0.25, 0.75]), concept)
    torch.save(torch.tensor([0.4, 0.6]), jacobian)
    record = SubjectRecord(
        subject_hash="hash", cohort="ADNI", class_label="MCI", label_index=1,
        derivative_path=derivative, concept_path=concept, jacobian_path=jacobian,
        concept_status="COMPUTED", jacobian_status="COMPUTED",
    )
    batch = LabeledSourceDataset(
        [record], expected_spatial_shape=(16, 16, 16), expected_num_rois=2
    )[0]
    atlas_masks = torch.zeros(2, 16, 16, 16)
    atlas_masks[0, :8] = 1
    atlas_masks[1, 8:] = 1
    feature_masks = prepare_feature_grid_roi_masks(atlas_masks, (2, 2, 2))
    model = PADA3DACB(2, 8, 6, base_channels=4, concept_hidden_dim=4)
    output = model(batch["x"].unsqueeze(0), feature_masks)
    result = CorePADA3DACBLoss(2)(
        output,
        batch["y"].unsqueeze(0),
        batch["c_target"].unsqueeze(0),
        batch["g_bar"].unsqueeze(0),
    )
    result.total.backward()
    assert torch.isfinite(result.total)
    assert model.encoder.stem[0].weight.grad is not None
