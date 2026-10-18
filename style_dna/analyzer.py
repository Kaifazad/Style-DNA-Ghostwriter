"""Walks a codebase and builds a StyleProfile from real source examples.

Supports Python (.py), JavaScript/TypeScript (.js/.jsx/.ts/.tsx),
CSS/SCSS (.css/.scss), and HTML (.html/.htm).

P0.2: Workspace boundary guard — validates that ``path`` resolves inside the
workspace root and respects ``.gitignore`` patterns (via ``pathspec`` if
installed) so the analyzer never escapes the project tree.

P2.1: When ``tree-sitter`` is installed the JS/TS ``ts_strict_rate`` is
computed using the accurate AST backend instead of regex.
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
    ".cache", ".parcel-cache", ".style-dna",
}

# ── File extensions by category ───────────────────────────────────────────────

PYTHON_EXTS = {".py"}
JS_TS_EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
CSS_EXTS = {".css", ".scss"}
HTML_EXTS = {".html", ".htm"}


# ── Workspace boundary guard ──────────────────────────────────────────────────

def _validate_path(path: str | Path) -> Path:
    """Resolve *path* and ensure it is a real, existing directory.

    Raises:
        FileNotFoundError: when the path does not exist.
        ValueError: when the path is not a directory.
    """
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"No such path: {path}")
    if not resolved.is_dir():
        raise ValueError(f"Expected a directory, got a file: {path}")
    return resolved


def _load_gitignore(root: Path):
    """Return a ``pathspec.PathSpec`` for the root ``.gitignore``, or ``None``.

    Falls back silently when:
    * ``pathspec`` is not installed (optional dependency).
    * ``.gitignore`` does not exist.
    * The file cannot be parsed.
    """
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        import pathspec  # type: ignore[import-untyped]
        patterns = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    except ImportError:
        return None
    except Exception:
        return None


def _is_ignored(path: Path, root: Path, spec) -> bool:
    """Return ``True`` if *path* matches the ``.gitignore`` spec."""
    if spec is None:
        return False
    try:
        rel = path.relative_to(root)
        return spec.match_file(str(rel).replace("\\", "/"))
    except ValueError:
        return False


# ── File iteration ────────────────────────────────────────────────────────────

def _iter_source_files(root: Path, extensions: set[str], gitignore_spec=None):
    """Yield files matching the given extensions, skipping ignored dirs and
    any paths excluded by ``.gitignore`` (when ``pathspec`` is installed)."""
    for path in root.rglob("*"):
        # Hard-coded dir exclusions (fast path)
        if any(part in DEFAULT_IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix not in extensions or not path.is_file():
            continue
        # .gitignore exclusions
        if _is_ignored(path, root, gitignore_spec):
            continue
        yield path


def _read_file(path: Path) -> str | None:
    """Read a file, returning ``None`` on errors."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


# ── Main analysis function ────────────────────────────────────────────────────

def analyze_codebase(path: str, max_files: int | None = 500) -> StyleProfile:
    """Analyze a directory of source code and return its StyleProfile.

    Supports Python, JavaScript, TypeScript, React, Next.js, CSS/SCSS,
    Tailwind, and HTML.

    The analyzer respects ``.gitignore`` patterns (requires ``pathspec``)
    and never follows paths outside *path*.

    Args:
        path: Path to the root of the codebase to analyze.
        max_files: Optional cap on number of files parsed per category.

    Returns:
        A populated :class:`~style_dna.profile.StyleProfile`.
    """
    root = _validate_path(path)
    gitignore_spec = _load_gitignore(root)

    fields: dict = {"source_path": str(root)}

    # ── Python analysis ───────────────────────────────────────────
    py_files = list(_iter_source_files(root, PYTHON_EXTS, gitignore_spec))
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
    js_ts_files = list(_iter_source_files(root, JS_TS_EXTS, gitignore_spec))
    css_files = list(_iter_source_files(root, CSS_EXTS, gitignore_spec))
    html_files = list(_iter_source_files(root, HTML_EXTS, gitignore_spec))

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
        js_fields = extract_js_ts(js_ts_sources, js_ts_paths)

        # P2.1: upgrade ts_strict_rate with tree-sitter when available
        try:
            from .extractors.ts_ast import is_available as _ts_ok, ts_strict_rate as _ts_rate
            if _ts_ok():
                ts_rate = _ts_rate(js_ts_sources, js_ts_paths)
                if ts_rate > 0.0:
                    js_fields["ts_strict_rate"] = ts_rate
        except Exception:
            pass

        fields.update(js_fields)
        fields.update(extract_react_next(js_ts_sources, js_ts_paths, root))

    # ── CSS / styling analysis ────────────────────────────────────
    if css_sources or js_ts_sources:
        fields.update(
            extract_css_styling(css_sources, css_paths, js_ts_sources, js_ts_paths, root)
        )

    # ── HTML analysis ─────────────────────────────────────────────
    if html_sources:
        fields.update(extract_html(html_sources, html_paths))

    if fields.get("files_analyzed", 0) == 0 and web_file_count == 0:
        return StyleProfile(source_path=str(root), files_analyzed=0)

    return StyleProfile(**fields)
