"""Walks a codebase and builds a StyleProfile from real source examples."""

from __future__ import annotations

import ast
from pathlib import Path

from .profile import StyleProfile
from .extractors import (
    extract_naming,
    extract_docstrings,
    extract_error_handling,
    extract_formatting,
    extract_imports,
    extract_structure,
    extract_type_hints,
    extract_common_patterns,
)

DEFAULT_IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".tox",
}


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in DEFAULT_IGNORE_DIRS for part in path.parts):
            continue
        yield path


def analyze_codebase(path: str, max_files: int | None = 300) -> StyleProfile:
    """Analyze a directory of Python source and return its StyleProfile.

    Args:
        path: Path to the root of the codebase to analyze.
        max_files: Optional cap on number of files parsed (for speed on huge repos).

    Returns:
        A populated StyleProfile.
    """
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"No such path: {path}")

    files = list(_iter_python_files(root))
    if max_files:
        files = files[:max_files]

    trees: list[ast.AST] = []
    sources: list[str] = []

    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src, filename=str(f))
        except (SyntaxError, UnicodeDecodeError):
            continue
        trees.append(tree)
        sources.append(src)

    if not trees:
        return StyleProfile(source_path=str(root), files_analyzed=0)

    fields: dict = {"source_path": str(root), "files_analyzed": len(trees)}
    fields.update(extract_naming(trees))
    fields.update(extract_docstrings(trees))
    fields.update(extract_error_handling(trees))
    fields.update(extract_formatting(sources))
    fields.update(extract_imports(trees))
    fields.update(extract_structure(trees))
    fields.update(extract_type_hints(trees))
    fields.update(extract_common_patterns(trees))

    return StyleProfile(**fields)
