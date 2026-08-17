from __future__ import annotations

import ast
from pathlib import Path

PUBLICATION_RUNTIME = Path("src/pada3dacb/publication/binary_runtime.py")
FORBIDDEN_IMPORTS = {"torch", "nibabel", "pada3dacb.data", "pada3dacb.training"}


def test_publication_binary_runtime_is_a_thin_dependency_free_facade() -> None:
    tree = ast.parse(PUBLICATION_RUNTIME.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(
        module in FORBIDDEN_IMPORTS or module.startswith("pada3dacb.training")
        for module in imported
    )


def test_publication_binary_runtime_preserves_public_symbols() -> None:
    from pada3dacb.publication.binary_runtime import (
        BINARY_PUBLICATION_METHODS,
        BinaryPublicationRuntime,
        load_binary_publication_config,
    )

    assert BINARY_PUBLICATION_METHODS
    assert BinaryPublicationRuntime.from_path
    assert load_binary_publication_config
