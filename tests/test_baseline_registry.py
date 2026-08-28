from __future__ import annotations

import sys
from types import ModuleType

import pytest
import torch
from torch import nn

from acda3d.models.baselines import (
    build_baseline,
    get_baseline_spec,
    list_baselines,
)


class _FakeBaseline(nn.Module):
    def __init__(self, **config: object) -> None:
        super().__init__()
        self.config = config
        self.weight = nn.Parameter(torch.ones(2))

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"logits": x.new_zeros((x.shape[0], 3))}


def _install_fake_model(monkeypatch: pytest.MonkeyPatch, module_name: str, class_name: str) -> None:
    module = ModuleType(module_name)
    setattr(module, class_name, _FakeBaseline)
    monkeypatch.setitem(sys.modules, module_name, module)


def test_registry_inventory_is_approved_and_deterministic() -> None:
    assert list_baselines() == ("aagn", "faster_snn")
    assert list_baselines() is list_baselines()
    assert {get_baseline_spec(name).class_name for name in list_baselines()} == {
        "ROIAwareGatingBaseline",
        "FasterSNNBaseline",
    }
    assert all(spec.output_classes == 3 for spec in map(get_baseline_spec, list_baselines()))


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("aagn", "aagn"),
        ("roiawaregating", "aagn"),
        ("aagnstyle", "aagn"),
        ("roi-aware-gating", "aagn"),
        ("roi_gating", "aagn"),
        ("faster_snn", "faster_snn"),
        ("fastersnn", "faster_snn"),
        ("faster-snn", "faster_snn"),
    ],
)
def test_only_explicit_aliases_resolve(name: str, expected: str) -> None:
    assert get_baseline_spec(name).id == expected


@pytest.mark.parametrize(
    "name",
    ["AAGN", "aag", "vit", "longformer", "AlzheimerSupervisedMRIModel", "3d-acda"],
)
def test_unknown_blocked_fuzzy_and_proposed_names_fail(name: str) -> None:
    with pytest.raises(KeyError, match="Unknown or unapproved baseline"):
        get_baseline_spec(name)


def test_build_is_lazy_validated_and_records_deterministic_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = "acda3d.models.baselines.faster_snn"
    _install_fake_model(monkeypatch, module_name, "FasterSNNBaseline")

    first = build_baseline("faster_snn", {"base_ch": 8})
    second = build_baseline("fastersnn", {"base_ch": 8})

    assert isinstance(first, _FakeBaseline)
    assert first.config["n_classes"] == 3
    assert first.baseline_metadata == second.baseline_metadata
    assert first.baseline_metadata["canonical_id"] == "faster_snn"
    assert first.baseline_metadata["resolved_config"]["base_ch"] == 8
    assert first.baseline_metadata["total_parameters"] == 2


@pytest.mark.parametrize(
    ("config", "message"),
    [({"unknown": 1}, "Unsupported constructor keys"), ({"n_classes": 2}, "exactly 3")],
)
def test_build_rejects_invalid_constructor_config(config: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_baseline("faster_snn", config)


def test_faster_snn_default_matches_notebook_factory_width() -> None:
    model = build_baseline("faster_snn", {})

    assert get_baseline_spec("faster_snn").default_config["base_ch"] == 16
    assert model.baseline_metadata["resolved_config"]["base_ch"] == 16
    assert sum(parameter.numel() for parameter in model.parameters()) == 291_603


def test_faster_snn_explicit_width_override_remains_literal() -> None:
    model = build_baseline("faster_snn", {"base_ch": 2})

    assert model.baseline_metadata["resolved_config"]["base_ch"] == 2
    assert sum(parameter.numel() for parameter in model.parameters()) == 4_701
