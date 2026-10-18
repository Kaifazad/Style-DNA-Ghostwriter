"""Optional tree-sitter based AST extraction for JavaScript / TypeScript.

P2: More accurate than regex — no false positives from strings or comments,
accurate scope handling, proper JSX support.

Falls back gracefully to the existing regex extractors when tree-sitter or
the grammar wheels are not installed.

Install the extras to enable::

    pip install "style-dna-ghostwriter[treesitter]"
    # or individually:
    pip install tree-sitter>=0.23.0 tree-sitter-typescript>=0.23.0

Check availability at runtime::

    from style_dna.extractors.ts_ast import is_available
    if is_available():
        ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ── Availability check ────────────────────────────────────────────────────────

_TS_AVAILABLE = False
_TSX_AVAILABLE = False

try:
    import tree_sitter_typescript as _tsl  # noqa: F401
    from tree_sitter import Language, Parser  # noqa: F401
    _TS_AVAILABLE = True
    _TSX_AVAILABLE = True
except ImportError:
    pass


def is_available() -> bool:
    """Return ``True`` if tree-sitter with TypeScript grammar is installed."""
    return _TS_AVAILABLE


# ── Public API ────────────────────────────────────────────────────────────────

def extract_ts_signatures(source: str, tsx: bool = False) -> list[dict]:
    """Extract function/component signatures from TypeScript source.

    Args:
        source: Raw TypeScript (or TSX) source text.
        tsx: If ``True``, use the TSX grammar (needed for files with JSX).

    Returns:
        A list of dicts, each with keys:

        * ``name`` (str): identifier name, or ``"<anonymous>"``.
        * ``kind`` (str): tree-sitter node type.
        * ``line`` (int): 1-indexed starting line.
        * ``typed`` (bool): has TypeScript type annotations.
        * ``is_component`` (bool): PascalCase name, likely a React component.
        * ``is_hook`` (bool): starts with ``use``, likely a React hook.

        Returns an empty list when tree-sitter is not installed.
    """
    if not _TS_AVAILABLE:
        return []

    try:
        import tree_sitter_typescript as tsl
        from tree_sitter import Language, Parser

        lang_fn = tsl.language_tsx if tsx else tsl.language_typescript
        lang = Language(lang_fn())
        parser = Parser(lang)
        tree = parser.parse(source.encode("utf-8", errors="replace"))

        results: list[dict] = []
        _walk(tree.root_node, results, source)
        return results
    except Exception:
        return []


def ts_strict_rate(sources: list[str], paths: list | None = None) -> float:
    """Compute the fraction of function signatures that are typed.

    Augments or replaces the regex-based ``ts_strict_rate`` from
    :mod:`style_dna.extractors.js_ts` when tree-sitter is available.

    Args:
        sources: List of raw source strings (JS/TS/TSX).
        paths: Optional list of corresponding file paths (used to pick grammar).

    Returns:
        Float in ``[0.0, 1.0]``, or ``0.0`` if nothing could be parsed.
    """
    if not _TS_AVAILABLE:
        return 0.0

    total = typed = 0
    for i, src in enumerate(sources):
        p = paths[i] if paths else None
        tsx = str(p).endswith((".tsx", ".jsx")) if p else False
        for sig in extract_ts_signatures(src, tsx=tsx):
            total += 1
            if sig["typed"]:
                typed += 1

    return typed / total if total > 0 else 0.0


# ── Tree-walker ───────────────────────────────────────────────────────────────

_FUNCTION_KINDS = frozenset({
    "function_declaration",
    "function_expression",
    "arrow_function",
    "method_definition",
})


def _walk(node, results: list[dict], source: str) -> None:
    """Recursively collect function/component nodes from the syntax tree."""
    if node.type in _FUNCTION_KINDS:
        name = _resolve_name(node, source)
        typed_flag = _has_types(node)
        results.append({
            "name": name,
            "kind": node.type,
            "line": node.start_point[0] + 1,
            "typed": typed_flag,
            "is_component": name[0].isupper() if name and name != "<anonymous>" else False,
            "is_hook": name.startswith("use") if name else False,
        })

    for child in node.children:
        _walk(child, results, source)


def _resolve_name(node, source: str) -> str:
    """Extract the identifier for a function node.

    For named functions, returns the identifier text.
    For arrow functions assigned to variables (``const Foo = () => {}``),
    looks at the parent variable declarator.
    """
    # Named function declarations have an 'identifier' child
    for child in node.children:
        if child.type == "identifier":
            return source[child.start_byte:child.end_byte]

    # Arrow function assigned to a variable: walk up via the parent chain
    parent = node.parent
    if parent and parent.type == "variable_declarator":
        for child in parent.children:
            if child.type == "identifier":
                return source[child.start_byte:child.end_byte]

    return "<anonymous>"


def _has_types(node) -> bool:
    """Return ``True`` if the function node carries TypeScript type annotations."""
    for child in node.children:
        if child.type in ("type_annotation", "type_parameters"):
            return True
        if child.type in ("formal_parameters", "parameters"):
            for param in child.children:
                if _node_has_type(param):
                    return True
    return False


def _node_has_type(node) -> bool:
    """Recursively check if a parameter node contains a type annotation."""
    if node.type == "type_annotation":
        return True
    for child in node.children:
        if _node_has_type(child):
            return True
    return False
