from pathlib import Path

import pytest
import torch

from pada3dacb.data.datasets import LabeledSourceDataset
from pada3dacb.data.records import SubjectRecord
from pada3dacb.exceptions import ConfigurationError, ModelContractError
from pada3dacb.models import PADA3DACB, PADA3DACBOutput, build_pada3dacb


def masks(k: int, spatial: int = 2) -> torch.Tensor:
    value = torch.ones(k, spatial, spatial, spatial)
    return value / value[0].numel()


@pytest.mark.parametrize("batch_size", [1, 2])
def test_complete_forward_contract_and_backward(batch_size):
    model = PADA3DACB(3, 8, 6, base_channels=4, concept_hidden_dim=4)
    output = model(torch.randn(batch_size, 1, 16, 16, 16), masks(3))
    assert isinstance(output, PADA3DACBOutput)
    assert output.F.shape == (batch_size, 8, 2, 2, 2)
    assert output.T.shape == output.U.shape == (batch_size, 3, 6)
    assert output.z.shape == (batch_size, 6)
    assert output.alpha.shape == output.concepts.shape == (batch_size, 3)
    assert output.latent_logits.shape == output.concept_logits.shape == (batch_size, 3)
    assert torch.allclose(output.latent_probabilities.sum(-1), torch.ones(batch_size))
    assert torch.allclose(output.concept_probabilities.sum(-1), torch.ones(batch_size))
    assert output["logits"] is output.latent_logits
    assert set(output.to_legacy_dict()) == {
        "F", "T", "U", "z", "alpha", "logits", "c", "cbm_logits"
    }
    (output.latent_logits.sum() + output.concept_logits.sum() + output.concepts.sum()).backward()
    assert model.encoder.stem[0].weight.grad is not None


def test_input_validation_and_no_contextual_architecture():
    model = PADA3DACB(2, 8, 6, base_channels=4, concept_hidden_dim=4)
    with pytest.raises(ModelContractError, match="float32"):
        model(torch.ones(1, 1, 16, 16, 16, dtype=torch.float64), masks(2))
    with pytest.raises(ModelContractError, match="finite"):
        model(torch.full((1, 1, 16, 16, 16), float("nan")), masks(2))
    assert "ctx_enc" not in dict(model.named_modules())
    assert not any(key.startswith(("ctx_enc.", "contextual_encoder.")) for key in model.state_dict())
    assert model.class_order == ("CN", "MCI", "AD")


def test_builder_rejects_excluded_architecture_and_validates_roi_count():
    with pytest.raises(ConfigurationError):
        build_pada3dacb({"name": "PADA-3DACB-Full"})
    with pytest.raises(ConfigurationError):
        build_pada3dacb({"name": "PADA-3DACB", "contextual_encoder": True})
    with pytest.raises(ConfigurationError, match="K=3"):
        build_pada3dacb({"name": "PADA-3DACB", "num_rois": 3}, torch.ones(2, 2, 2, 2))


def test_phase6_source_dataset_batch_integrates_with_model(tmp_path: Path):
    derivative = tmp_path / "x.pt"
    concept = tmp_path / "c.pt"
    jacobian = tmp_path / "g.pt"
    torch.save(torch.randn(1, 16, 16, 16), derivative)
    torch.save(torch.tensor([0.2, 0.8]), concept)
    torch.save(torch.tensor([0.4, 0.6]), jacobian)
    record = SubjectRecord(
        subject_hash="hash", cohort="ADNI", class_label="CN", label_index=0,
        derivative_path=derivative, concept_path=concept, jacobian_path=jacobian,
        concept_status="COMPUTED", jacobian_status="COMPUTED",
    )
    dataset = LabeledSourceDataset(
        [record], expected_spatial_shape=(16, 16, 16), expected_num_rois=2
    )
    batch = dataset[0]
    output = PADA3DACB(2, 8, 6, base_channels=4, concept_hidden_dim=4)(
        batch["x"].unsqueeze(0), masks(2)
    )
    assert output.concepts.shape[-1] == batch["c_target"].shape[-1]
    assert output.concepts.shape[-1] == batch["g_bar"].shape[-1]


def test_production_configuration_builds_102_roi_model():
    model = build_pada3dacb({
        "model": {
            "name": "PADA-3DACB", "contextual_encoder": False, "num_rois": 102,
            "encoder": {"base_channels": 4, "output_channels": 8},
            "tokenizer": {"feature_dim": 8, "token_dim": 6},
            "concept_bottleneck": {"hidden_dim": 4},
        }
    })
    assert model.num_rois == 102
