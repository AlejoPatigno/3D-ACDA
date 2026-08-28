from __future__ import annotations

from pathlib import Path

import pytest

from acda3d.experiments import (
    load_cdan_config,
    load_coral_config,
    load_mmd_config,
    load_source_only_config,
)
from acda3d.experiments.prototype_pseudo import load_prototype_pseudo_config
from acda3d.models.baselines import get_baseline_spec, list_baselines


def test_phase14_registry_does_not_duplicate_or_alias_approved_acda_methods() -> None:
    assert list_baselines() == ("aagn", "faster_snn")
    for name in (
        "source_only",
        "coral",
        "mmd",
        "cdan",
        "prototype_pseudo",
        "3d-acda",
        "AlzheimerSupervisedMRIModel",
    ):
        with pytest.raises(KeyError):
            get_baseline_spec(name)


def test_previous_method_config_loaders_remain_importable() -> None:
    assert all(
        callable(loader)
        for loader in (
            load_source_only_config,
            load_coral_config,
            load_mmd_config,
            load_cdan_config,
            load_prototype_pseudo_config,
        )
    )


def test_phase15_does_not_add_unapproved_evaluation_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = (
        root / "src" / "acda3d" / "evaluation" / "statistics.py",
        root / "src" / "acda3d" / "evaluation" / "concept_interventions.py",
        root / "src" / "acda3d" / "evaluation" / "roi_stability.py",
        root / "src" / "acda3d" / "experiments" / "phase15.py",
    )
    assert not any(path.exists() for path in forbidden)
