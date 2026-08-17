"""Extracts docstring style and coverage from parsed ASTs."""

from __future__ import annotations

import ast
from collections import Counter


def _classify_docstring(doc: str) -> str:
    if "Args:" in doc or "Returns:" in doc or "Raises:" in doc:
        return "google"
    if "Parameters\n" in doc or "----------" in doc:
        return "numpy"
    if ":param" in doc or ":return:" in doc or ":raises:" in doc:
        return "rest"
    return "plain"


def extract_docstrings(trees: list[ast.AST]) -> dict:
    total_defs = 0
    documented = 0
    # Style is judged from FUNCTION docstrings only -- module/class docstrings
    # are usually short prose ("Raised when X.") and would drag a real
    # Args/Returns convention down to "plain" even when functions consistently
    # use a structured style.
    func_style_counts: Counter[str] = Counter()

    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_defs += 1
                doc = ast.get_docstring(node)
                if doc:
                    documented += 1
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_style_counts[_classify_docstring(doc)] += 1

    if documented == 0:
        return {"docstring_style": "none", "docstring_coverage": 0.0}

    style = func_style_counts.most_common(1)[0][0] if func_style_counts else "plain"
    return {
        "docstring_style": style,
        "docstring_coverage": documented / total_defs if total_defs else 0.0,
    }
