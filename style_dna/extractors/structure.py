"""Extracts formatting, import style, structural conventions, and common patterns."""

from __future__ import annotations

import ast
from collections import Counter


def extract_formatting(sources: list[str]) -> dict:
    single = 0
    double = 0
    line_lengths: list[int] = []
    indent_counts: Counter[str] = Counter()

    for src in sources:
        # --- Quote style: count via AST, not raw text ---
        try:
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    # Reconstruct the source snippet to detect the actual quote char used
                    try:
                        col = node.col_offset
                        lineno = node.lineno
                        line = src.splitlines()[lineno - 1]
                        char_at_col = line[col] if col < len(line) else None
                        if char_at_col == "'":
                            single += 1
                        elif char_at_col == '"':
                            double += 1
                    except (IndexError, AttributeError):
                        pass
        except SyntaxError:
            pass

        # --- Line lengths ---
        for line in src.splitlines():
            stripped = line.rstrip("\n")
            if stripped.strip():
                line_lengths.append(len(stripped))

        # --- Indent style detection ---
        for line in src.splitlines():
            if line and line[0] in (" ", "\t"):
                leading = len(line) - len(line.lstrip())
                raw = line[:leading]
                if "\t" in raw:
                    indent_counts["tabs"] += 1
                elif leading % 4 == 0:
                    indent_counts["spaces_4"] += 1
                elif leading % 2 == 0:
                    indent_counts["spaces_2"] += 1

    quote_style = "unknown"
    if single or double:
        ratio = single / (single + double) if (single + double) else 0
        if ratio > 0.65:
            quote_style = "single"
        elif ratio < 0.35:
            quote_style = "double"
        else:
            quote_style = "mixed"

    avg_len = sum(line_lengths) / len(line_lengths) if line_lengths else 0.0
    max_len = max(line_lengths) if line_lengths else 0

    indent_style = indent_counts.most_common(1)[0][0] if indent_counts else "spaces_4"

    return {
        "quote_style": quote_style,
        "avg_line_length": round(avg_len, 1),
        "max_observed_line_length": max_len,
        "indent_style": indent_style,
    }


def extract_imports(trees: list[ast.AST]) -> dict:
    relative = 0
    absolute = 0
    grouped_like = 0
    total_files_with_imports = 0

    for tree in trees:
        import_lines = [n.lineno for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        if not import_lines:
            continue
        total_files_with_imports += 1

        # crude "grouped" heuristic: import block(s) not scattered across whole file
        span = max(import_lines) - min(import_lines)
        if span <= len(import_lines) + 5:
            grouped_like += 1

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    relative += 1
                else:
                    absolute += 1
            elif isinstance(node, ast.Import):
                absolute += 1

    import_style = "unknown"
    if total_files_with_imports:
        import_style = "grouped_stdlib_first" if grouped_like / total_files_with_imports > 0.6 else "ungrouped"

    return {
        "import_style": import_style,
        "prefers_relative_imports": relative > absolute,
    }


def extract_structure(trees: list[ast.AST]) -> dict:
    func_lengths: list[int] = []
    decorator_counts: Counter[str] = Counter()

    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, "end_lineno") and node.end_lineno:
                    func_lengths.append(node.end_lineno - node.lineno + 1)
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name):
                        decorator_counts[dec.id] += 1
                    elif isinstance(dec, ast.Attribute):
                        decorator_counts[dec.attr] += 1
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                        decorator_counts[dec.func.id] += 1

    avg_len = sum(func_lengths) / len(func_lengths) if func_lengths else 0.0
    common_decorators = [name for name, _ in decorator_counts.most_common(5)]

    return {
        "avg_function_length": round(avg_len, 1),
        "common_decorators": common_decorators,
    }


def extract_type_hints(trees: list[ast.AST]) -> dict:
    total_args = 0
    hinted_args = 0
    total_returns = 0
    hinted_returns = 0

    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a for a in node.args.args if a.arg != "self"]
                total_args += len(args)
                hinted_args += sum(1 for a in args if a.annotation is not None)
                total_returns += 1
                if node.returns is not None:
                    hinted_returns += 1

    total = total_args + total_returns
    hinted = hinted_args + hinted_returns
    return {"type_hint_coverage": (hinted / total) if total else 0.0}


def extract_common_patterns(trees: list[ast.AST]) -> dict:
    """Detect high-level patterns in the codebase and emit free-text notes for the LLM."""
    patterns: list[str] = []

    uses_dataclasses = False
    uses_protocol = False
    uses_contextmanager = False
    uses_async = False
    uses_slots = False
    uses_abstract = False
    uses_namedtuple = False
    uses_typing_overload = False

    for tree in trees:
        for node in ast.walk(tree):
            # Check imports for dataclasses, typing, contextlib
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = {alias.name for alias in node.names}
                if mod == "dataclasses" and "dataclass" in names:
                    uses_dataclasses = True
                if mod == "typing" and "Protocol" in names:
                    uses_protocol = True
                if mod == "contextlib" and "contextmanager" in names:
                    uses_contextmanager = True
                if mod == "typing" and "overload" in names:
                    uses_typing_overload = True
                if mod == "abc" and ("ABC" in names or "abstractmethod" in names):
                    uses_abstract = True
                if mod in ("typing", "collections") and (
                    "NamedTuple" in names or "namedtuple" in names
                ):
                    uses_namedtuple = True

            # Detect async functions
            if isinstance(node, ast.AsyncFunctionDef):
                uses_async = True

            # Detect __slots__
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "__slots__"
                    for t in node.targets
                )
            ):
                uses_slots = True

    if uses_dataclasses:
        patterns.append("Codebase uses @dataclass for data models.")
    if uses_protocol:
        patterns.append("Uses typing.Protocol for structural subtyping (duck-typed interfaces).")
    if uses_abstract:
        patterns.append("Uses ABCs (abc.ABC / abstractmethod) for interfaces.")
    if uses_contextmanager:
        patterns.append("Uses contextlib.contextmanager for context managers.")
    if uses_async:
        patterns.append("Codebase has async/await patterns; prefer async-compatible code where relevant.")
    if uses_slots:
        patterns.append("Uses __slots__ on classes for memory efficiency.")
    if uses_namedtuple:
        patterns.append("Uses NamedTuple/namedtuple for lightweight immutable records.")
    if uses_typing_overload:
        patterns.append("Uses typing.overload for multiple call signatures.")

    return {"common_patterns": patterns}
