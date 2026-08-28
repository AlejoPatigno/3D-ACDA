"""Path helpers for configuration and experiment outputs."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from acda3d.exceptions import InvalidPathError

_WINDOWS_SPECIFIC_RE = re.compile(r"^[A-Za-z]:\\Users\\[^\\]+\\")
_HOME_SPECIFIC_RE = re.compile("^" + "/" + "home" + r"/[^/]+/")
_KAGGLE_MARKER = "/" + "kaggle" + "/"
_CONTENT_MARKER = "/" + "content" + "/"


def is_forbidden_hardcoded_path(value: Any) -> bool:
    """Return whether a value contains a forbidden notebook-local path."""
    if value is None:
        return False
    text = str(value)
    if not text:
        return False
    return (
        _KAGGLE_MARKER in text
        or _CONTENT_MARKER in text
        or bool(_WINDOWS_SPECIFIC_RE.search(text))
        or bool(_HOME_SPECIFIC_RE.search(text))
    )


def resolve_path(
    value: str | os.PathLike[str] | None,
    base_dir: str | os.PathLike[str] | None = None,
    *,
    must_exist: bool = False,
    required: bool = False,
) -> Path | None:
    """Resolve a configured path without creating it."""
    if value is None:
        if required:
            raise InvalidPathError("A path value is required.")
        return None

    raw = str(value)
    if raw == "":
        raise InvalidPathError("Empty strings are not valid paths.")
    expanded = os.path.expandvars(os.path.expanduser(raw))
    path = Path(expanded)
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    path = path.resolve(strict=False)

    if must_exist and not path.exists():
        raise InvalidPathError(f"Configured path does not exist: {path}")
    return path


def ensure_directory(path: str | os.PathLike[str]) -> Path:
    """Create an output directory explicitly and return its resolved path."""
    resolved = resolve_path(path, required=True)
    if resolved is None:
        raise InvalidPathError("A directory path is required.")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
