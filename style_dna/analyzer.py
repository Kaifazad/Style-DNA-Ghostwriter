"""Walks a codebase and builds a StyleProfile from real source examples.

Supports Python (.py), JavaScript/TypeScript (.js/.jsx/.ts/.tsx),
CSS/SCSS (.css/.scss), and HTML (.html/.htm).
"""

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
    extract_js_ts,
    extract_react_next,
    extract_css_styling,
    extract_html,
)

DEFAULT_IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".tox",
    ".next", ".nuxt", "out", "coverage", ".turbo", ".vercel",
    ".cache", ".parcel-cache",
}

# ── File extensions by category ───────────────────────────────────

PYTHON_EXTS = {".py"}
JS_TS_EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
CSS_EXTS = {".css", ".scss"}
HTML_EXTS = {".html", ".htm"}
ALL_EXTS = PYTHON_EXTS | JS_TS_EXTS | CSS_EXTS | HTML_EXTS


def _iter_source_files(root: Path, extensions: set[str]):
    """Yield files matching the given extensions, skipping ignored dirs."""
    for path in root.rglob("*"):
        if any(part in DEFAULT_IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix in extensions and path.is_file():
            yield path


def _read_file(path: Path) -> str | None:
    """Read a file, returning None on errors."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def analyze_codebase(path: str, max_files: int | None = 500) -> StyleProfile:
    """Analyze a directory of source code and return its StyleProfile.

    Supports Python, JavaScript, TypeScript, React, Next.js, CSS/SCSS,
    Tailwind, and HTML.

    Args:
        path: Path to the root of the codebase to analyze.
        max_files: Optional cap on number of files parsed per category.

    Returns:
        A populated StyleProfile.
    """
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"No such path: {path}")

    fields: dict = {"source_path": str(root)}

    # ── Python analysis ───────────────────────────────────────────
    py_files = list(_iter_source_files(root, PYTHON_EXTS))
    if max_files:
        py_files = py_files[:max_files]

    trees: list[ast.AST] = []
    py_sources: list[str] = []

    for f in py_files:
        src = _read_file(f)
        if src is None:
            continue
        try:
            tree = ast.parse(src, filename=str(f))
        except SyntaxError:
            continue
        trees.append(tree)
        py_sources.append(src)

    fields["files_analyzed"] = len(trees)

    if trees:
        fields.update(extract_naming(trees))
        fields.update(extract_docstrings(trees))
        fields.update(extract_error_handling(trees))
        fields.update(extract_formatting(py_sources))
        fields.update(extract_imports(trees))
        fields.update(extract_structure(trees))
        fields.update(extract_type_hints(trees))
        fields.update(extract_common_patterns(trees))

    # ── Web file collection ───────────────────────────────────────
    js_ts_files = list(_iter_source_files(root, JS_TS_EXTS))
    css_files = list(_iter_source_files(root, CSS_EXTS))
    html_files = list(_iter_source_files(root, HTML_EXTS))

    if max_files:
        js_ts_files = js_ts_files[:max_files]
        css_files = css_files[:max_files]
        html_files = html_files[:max_files]

    # Read web sources
    js_ts_sources: list[str] = []
    js_ts_paths: list[Path] = []
    for f in js_ts_files:
        src = _read_file(f)
        if src is not None:
            js_ts_sources.append(src)
            js_ts_paths.append(f)

    css_sources: list[str] = []
    css_paths: list[Path] = []
    for f in css_files:
        src = _read_file(f)
        if src is not None:
            css_sources.append(src)
            css_paths.append(f)

    html_sources: list[str] = []
    html_paths: list[Path] = []
    for f in html_files:
        src = _read_file(f)
        if src is not None:
            html_sources.append(src)
            html_paths.append(f)

    web_file_count = len(js_ts_sources) + len(css_sources) + len(html_sources)
    fields["web_files_analyzed"] = web_file_count

    # ── JS / TS analysis ──────────────────────────────────────────
    if js_ts_sources:
        fields.update(extract_js_ts(js_ts_sources, js_ts_paths))
        fields.update(extract_react_next(js_ts_sources, js_ts_paths, root))

    # ── CSS / styling analysis ────────────────────────────────────
    if css_sources or js_ts_sources:
        fields.update(extract_css_styling(css_sources, css_paths, js_ts_sources, js_ts_paths, root))

    # ── HTML analysis ─────────────────────────────────────────────
    if html_sources:
        fields.update(extract_html(html_sources, html_paths))

    if fields.get("files_analyzed", 0) == 0 and web_file_count == 0:
        return StyleProfile(source_path=str(root), files_analyzed=0)

    return StyleProfile(**fields)
