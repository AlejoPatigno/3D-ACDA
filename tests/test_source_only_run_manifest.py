import json
from pathlib import Path

import pytest

from acda3d.exceptions import ExperimentValidationError
from acda3d.experiments.run_manifest import (
    create_run_manifest,
    update_run_manifest,
)


def test_run_manifest_statuses_are_atomic_and_complete(tmp_path: Path):
    path = tmp_path / "run_manifest.json"
    manifest = create_run_manifest(experiment_hash="hash", fold=0, seed=42)
    update_run_manifest(path, manifest, "RUNNING")
    running = json.loads(path.read_text())
    assert running["status"] == "RUNNING" and running["start_time"]
    update_run_manifest(path, manifest, "COMPLETED", checkpoint_paths={"last": "last.pt"})
    completed = json.loads(path.read_text())
    assert completed["status"] == "COMPLETED" and completed["completion_time"]
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(ExperimentValidationError):
        update_run_manifest(path, manifest, "UNKNOWN")
