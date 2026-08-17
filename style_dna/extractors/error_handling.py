"""Extracts error-handling and exception conventions from parsed ASTs."""

from __future__ import annotations

import ast
from collections import Counter


def extract_error_handling(trees: list[ast.AST]) -> dict:
    broad_except = 0
    specific_except = 0
    custom_exception_classes = 0
    total_excepts = 0
    excepts_with_logging = 0

    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                if any("Error" in b or "Exception" in b for b in bases):
                    custom_exception_classes += 1

            if isinstance(node, ast.ExceptHandler):
                total_excepts += 1
                if node.type is None:
                    broad_except += 1
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    broad_except += 1
                else:
                    specific_except += 1

                has_log_call = False
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        func = sub.func
                        name = getattr(func, "attr", None) or getattr(func, "id", None)
                        if name in ("error", "exception", "warning", "critical", "log"):
                            has_log_call = True
                if has_log_call:
                    excepts_with_logging += 1

    pattern = "unknown"
    if total_excepts:
        pattern = "specific_except" if specific_except >= broad_except else "broad_except"
    if custom_exception_classes >= 1:
        pattern = "custom_exceptions"

    return {
        "error_handling_pattern": pattern,
        "uses_custom_exceptions": custom_exception_classes > 0,
        "logs_on_exception_rate": (excepts_with_logging / total_excepts) if total_excepts else 0.0,
    }
