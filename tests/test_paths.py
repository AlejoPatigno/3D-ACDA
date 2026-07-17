from __future__ import annotations

from pathlib import Path

import pytest

from pada3dacb.exceptions import InvalidPathError
from pada3dacb.paths import ensure_directory, is_forbidden_hardcoded_path, resolve_path


def test_environment_variable_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("PADA_TEST_ROOT", str(tmp_path))
    assert resolve_path("$PADA_TEST_ROOT/example") == (tmp_path / "example").resolve()


def test_user_home_expansion():
    assert resolve_path("~") == Path.home().resolve()


def test_relative_path_resolution(tmp_path):
    assert resolve_path("child", base_dir=tmp_path) == (tmp_path / "child").resolve()


def test_optional_existence_check(tmp_path):
    with pytest.raises(InvalidPathError):
        resolve_path(tmp_path / "missing", must_exist=True)


def test_output_directory_creation(tmp_path):
    target = ensure_directory(tmp_path / "new" / "nested")
    assert target.exists()
    assert target.is_dir()


@pytest.mark.parametrize(
    "value",
    [
        "/kaggle/input/example",
        "/content/data",
        "/home/specific-user/data",
        r"C:\Users\Someone\data",
    ],
)
def test_forbidden_hardcoded_paths(value):
    assert is_forbidden_hardcoded_path(value)


def test_empty_required_path_is_rejected():
    with pytest.raises(InvalidPathError):
        resolve_path("")
