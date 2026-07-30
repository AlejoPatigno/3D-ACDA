from __future__ import annotations

from pathlib import Path

import pytest

from pada3dacb.experiments import (
    load_cdan_config,
    load_coral_config,
    load_mmd_config,
    load_source_only_config,
)
from pada3dacb.experiments.prototype_pseudo import load_prototype_pseudo_config
from pada3dacb.models.baselines import get_baseline_spec, list_baselines


def test_phase14_registry_does_not_duplicate_or_alias_approved_pada_methods() -> None:
    assert list_baselines() == ("aagn", "faster_snn")
    for name in (
        "source_only",
        "coral",
        "mmd",
        "cdan",
        "prototype_pseudo",
        "pada-3dacb",
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
        root / "src" / "pada3dacb" / "evaluation" / "statistics.py",
        root / "src" / "pada3dacb" / "evaluation" / "concept_interventions.py",
        root / "src" / "pada3dacb" / "evaluation" / "roi_stability.py",
        root / "src" / "pada3dacb" / "experiments" / "phase15.py",
    )
    assert not any(path.exists() for path in forbidden)
