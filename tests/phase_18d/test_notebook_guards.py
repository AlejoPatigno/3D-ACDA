from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_ROOT = Path(__file__).resolve().parents[2] / "notebooks" / "kaggle"
REQUIRED = (
    "00_kaggle_input_binding.ipynb",
    "01_kaggle_binary_artifact_preparation.ipynb",
    "02_kaggle_real_run_readiness.ipynb",
)
FORBIDDEN_TERMS = (
    "placeholder",
    "real model training",
    "publication analysis",
    "phase 19",
    "optimizer.step",
    ".fit(",
)


def notebook_source(path: Path) -> str:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["nbformat"] >= 4
    return "\n".join("".join(cell.get("source", [])) for cell in document["cells"])


def test_required_notebooks_are_valid_json() -> None:
    for name in REQUIRED:
        path = NOTEBOOK_ROOT / name
        assert path.is_file(), name
        source = notebook_source(path)
        assert "PADA3DACB_SUBJECT_HMAC_KEY" in source
        assert "/kaggle/input" in source
        if name.startswith("02_"):
            assert "KAGGLE_READINESS_EVIDENCE_PRODUCED" in source


def test_notebooks_have_no_placeholder_or_training_code() -> None:
    for name in REQUIRED:
        source = notebook_source(NOTEBOOK_ROOT / name).lower()
        assert "placeholder" not in source
        assert "optimizer.step" not in source
        assert ".fit(" not in source


def test_notebooks_preserve_authorization_boundary() -> None:
    for name in REQUIRED:
        source = notebook_source(NOTEBOOK_ROOT / name)
        assert "real_execution_authorized" in source
        assert "publication_authorized" in source
        assert "phase_19_forbidden" in source
