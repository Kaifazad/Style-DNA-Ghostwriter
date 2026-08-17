"""Extracts naming conventions from parsed ASTs."""

from __future__ import annotations

import ast
import re
from collections import Counter

SNAKE_RE = re.compile(r"^_{0,2}[a-z0-9]+(_[a-z0-9]+)*_{0,2}$")
CAMEL_RE = re.compile(r"^_{0,2}[a-z]+([A-Z][a-z0-9]*)+_{0,2}$")
PASCAL_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")


def _classify(name: str) -> str:
    if not name or (name.startswith("__") and name.endswith("__")):
        return "dunder"
    if PASCAL_RE.match(name):
        return "PascalCase"
    if SNAKE_RE.match(name):
        return "snake_case"
    if CAMEL_RE.match(name):
        return "camelCase"
    return "other"


def extract_naming(trees: list[ast.AST]) -> dict:
    func_styles: Counter[str] = Counter()
    var_styles: Counter[str] = Counter()
    total_internal = 0
    private_prefixed = 0
    getter_setter_hits = Counter()

    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                func_styles[_classify(node.name)] += 1
                total_internal += 1
                if node.name.startswith("_"):
                    private_prefixed += 1
                if node.name.startswith("get_") or node.name.startswith("set_"):
                    getter_setter_hits["get_set"] += 1
                elif any(
                    isinstance(d, ast.Name) and d.id == "property"
                    for d in getattr(node, "decorator_list", [])
                ):
                    getter_setter_hits["property"] += 1
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_styles[_classify(target.id)] += 1

    func_naming = func_styles.most_common(1)[0][0] if func_styles else "unknown"
    var_naming = var_styles.most_common(1)[0][0] if var_styles else "unknown"
    getter_setter_style = (
        getter_setter_hits.most_common(1)[0][0] if getter_setter_hits else "direct"
    )
    getter_setter_style = {"get_set": "get_x/set_x", "property": "property"}.get(
        getter_setter_style, "direct"
    )

    return {
        "function_naming": func_naming,
        "variable_naming": var_naming,
        "private_prefix_rate": (private_prefixed / total_internal) if total_internal else 0.0,
        "getter_setter_style": getter_setter_style,
    }
