from __future__ import annotations

import pytest
import torch
from torch import nn

from pada3dacb.models.baselines.common import (
    BaselineSpec,
    Small3DBackbone,
    parameter_metadata,
    reproducibility_hash,
    validate_baseline_output,
    validate_mri_input,
)


def test_baseline_spec_has_required_contract_fields() -> None:
    assert tuple(BaselineSpec.__dataclass_fields__) == (
        "id",
        "display_name",
        "class_name",
        "notebook_provenance",
        "input_contract",
        "requires_roi_masks",
        "optional_dependencies",
        "default_config",
        "output_classes",
    )


def test_validate_mri_input_accepts_only_finite_single_channel_5d_tensors() -> None:
    x = torch.zeros(2, 1, 8, 10, 12)
    assert validate_mri_input(x) is x

    for invalid in (torch.zeros(1, 8, 8, 8), torch.zeros(1, 2, 8, 8, 8)):
        with pytest.raises(ValueError, match=r"\[B, 1, D, H, W\]"):
            validate_mri_input(invalid)
    x[0, 0, 0, 0, 0] = torch.nan
    with pytest.raises(ValueError, match="finite"):
        validate_mri_input(x)


def test_validate_baseline_output_enforces_mapping_and_three_logits() -> None:
    logits = torch.zeros(2, 3)
    output = {"logits": logits, "features": torch.ones(2, 4)}
    assert validate_baseline_output(output, batch_size=2) is output

    with pytest.raises(ValueError, match=r"\[B, 3\]"):
        validate_baseline_output({"logits": torch.zeros(2, 2)}, batch_size=2)
    with pytest.raises(TypeError, match="mapping"):
        validate_baseline_output(logits, batch_size=2)  # type: ignore[arg-type]


def test_backbone_preserves_batch_and_produces_requested_channels() -> None:
    output = Small3DBackbone(out_ch=12)(torch.randn(2, 1, 16, 16, 16))
    assert output.shape[0] == 2
    assert output.shape[1] == 12


def test_metadata_and_hash_are_deterministic_and_sensitive_to_canonical_id() -> None:
    model = nn.Linear(4, 3)
    assert parameter_metadata(model) == {"total_parameters": 15, "trainable_parameters": 15}
    config = {"n_classes": 3, "shape": (8, 8, 8)}
    assert reproducibility_hash("aagn", config) == reproducibility_hash("aagn", config)
    assert reproducibility_hash("aagn", config) != reproducibility_hash("faster_snn", config)


def test_hash_is_independent_of_mapping_insertion_order() -> None:
    assert reproducibility_hash("aagn", {"b": 2, "a": 1}) == reproducibility_hash(
        "aagn", {"a": 1, "b": 2}
    )
