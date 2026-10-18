"""Style convention verifier — checks a code snippet against an extracted StyleProfile.

P1: Closes the agent feedback loop.  The ``check_code_style`` MCP tool uses
this module to give coding agents instant, line-precise feedback on whether
generated code matches the real repo conventions extracted from source.

Usage (as a library)::

    from style_dna.verifier import check_code_style
    from style_dna import StyleProfile

    profile = StyleProfile.load(".style-dna/style_profile.json")
    violations = check_code_style(my_code, profile, language="python")
    for v in violations:
        print(f"Line {v.line}: [{v.rule}] {v.message}")
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class StyleViolation:
    """A single style convention violation."""

    line: int                  # 1-indexed; 0 means file-level
    rule: str                  # Short rule ID, e.g. "naming.snake_case"
    message: str               # Human-readable description
    severity: Literal["error", "warning", "info"] = "warning"

    def as_dict(self) -> dict:
        return {
            "line": self.line,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
        }


# ── Public entry point ────────────────────────────────────────────────────────

def check_code_style(
    code: str,
    profile,
    language: str = "auto",
) -> list[StyleViolation]:
    """Check *code* against the conventions in *profile*.

    Args:
        code: The source code snippet to verify.
        profile: A :class:`~style_dna.profile.StyleProfile` instance.
        language: ``"python"``, ``"js"``, ``"ts"``, ``"tsx"``, ``"jsx"``,
                  or ``"auto"`` (default) to auto-detect from the snippet.

    Returns:
        A list of :class:`StyleViolation` instances, empty when the snippet
        conforms to all extracted conventions.
    """
    lang = _detect_language(code) if language == "auto" else language.lower()

    if lang == "python":
        return _check_python(code, profile)
    if lang in ("js", "ts", "tsx", "jsx"):
        return _check_js_ts(code, profile)
    return []




# ── Language auto-detection ───────────────────────────────────────────────────

def _detect_language(code: str) -> str:
    py_signals = re.search(r"^\s*(def |import |from .+ import |@\w+\n)", code, re.MULTILINE)
    js_signals = re.search(r"^\s*(const |let |var |function |=>|export |import )", code, re.MULTILINE)
    if py_signals and not js_signals:
        return "python"
    if js_signals:
        return "js"
    return "python"


# ── Python checker ────────────────────────────────────────────────────────────

def _check_python(code: str, profile) -> list[StyleViolation]:
    violations: list[StyleViolation] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [StyleViolation(
            line=exc.lineno or 0,
            rule="syntax",
            message=str(exc),
            severity="error",
        )]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_py_function(node, profile, violations)
        if isinstance(node, ast.ClassDef):
            _check_py_class(node, profile, violations)

    _check_py_quotes(code, profile, violations)
    return violations


def _check_py_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    profile,
    out: list[StyleViolation],
) -> None:
    name = node.name
    lineno = node.lineno

    # --- Naming ---
    if profile.function_naming == "snake_case" and not _is_snake(name):
        out.append(StyleViolation(
            line=lineno,
            rule="naming.function",
            message=(
                f"Function '{name}' should be snake_case "
                f"(repo convention: snake_case)."
            ),
        ))
    elif profile.function_naming == "camelCase" and not _is_camel(name):
        out.append(StyleViolation(
            line=lineno,
            rule="naming.function",
            message=(
                f"Function '{name}' should be camelCase "
                f"(repo convention: camelCase)."
            ),
        ))

    # --- Type hints ---
    if profile.type_hint_coverage > 0.6:
        args = node.args
        all_args = args.args + args.posonlyargs + args.kwonlyargs
        meaningful = [a for a in all_args if a.arg not in ("self", "cls")]
        typed = sum(1 for a in meaningful if a.annotation is not None)
        has_return = node.returns is not None
        total = len(meaningful) + 1  # +1 for return
        annotated = typed + (1 if has_return else 0)
        if total > 1 and annotated / total < 0.5:
            out.append(StyleViolation(
                line=lineno,
                rule="typing.missing_hints",
                message=(
                    f"Function '{name}' has low type-hint coverage "
                    f"(repo annotates ~{profile.type_hint_coverage:.0%} of signatures)."
                ),
                severity="info",
            ))

    # --- Docstrings ---
    if profile.docstring_coverage > 0.5 and profile.docstring_style != "none":
        has_doc = (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )
        if not has_doc:
            out.append(StyleViolation(
                line=lineno,
                rule="docs.missing_docstring",
                message=(
                    f"'{name}' is missing a docstring "
                    f"(repo coverage: ~{profile.docstring_coverage:.0%})."
                ),
                severity="info",
            ))


def _check_py_class(node: ast.ClassDef, profile, out: list[StyleViolation]) -> None:
    if profile.docstring_coverage > 0.5 and profile.docstring_style != "none":
        has_doc = (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )
        if not has_doc:
            out.append(StyleViolation(
                line=node.lineno,
                rule="docs.missing_docstring",
                message=(
                    f"Class '{node.name}' is missing a docstring "
                    f"(repo coverage: ~{profile.docstring_coverage:.0%})."
                ),
                severity="info",
            ))


def _check_py_quotes(code: str, profile, out: list[StyleViolation]) -> None:
    if profile.quote_style not in ("single", "double"):
        return
    preferred = "'" if profile.quote_style == "single" else '"'
    wrong = '"' if profile.quote_style == "single" else "'"
    token_re = re.compile(
        rf"(?<!['\"])(?:{re.escape(wrong)})(?:[^{re.escape(wrong)}\\]|\\.)*{re.escape(wrong)}"
    )
    for i, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        if token_re.search(line):
            out.append(StyleViolation(
                line=i,
                rule="style.quotes",
                message=(
                    f"Prefer {profile.quote_style} quotes ({preferred!r}) "
                    f"to match repo convention."
                ),
                severity="info",
            ))


# ── JS/TS checker ─────────────────────────────────────────────────────────────

def _check_js_ts(code: str, profile) -> list[StyleViolation]:
    violations: list[StyleViolation] = []
    lines = code.splitlines()

    for i, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*") or stripped == "}":
            continue

        _check_js_semicolons(i, stripped, profile, violations)
        _check_js_quotes(i, stripped, profile, violations)
        _check_js_function_style(i, raw_line, profile, violations)
        _check_js_export_style(i, stripped, profile, violations)
        _check_js_imports(i, stripped, profile, violations)

    return violations


_STATEMENT_START = re.compile(
    r"^(const|let|var|return|throw|import|export|break|continue|yield)\b"
)
_BLOCK_ENDS = (";", "{", "}", ",", ")", "]", ":", "=>", "|", "&", "?", "/*", "*/")
_ARROW_FUNC = re.compile(
    r"^(?:export\s+)?const\s+\w+\s*=\s*(?:<[^>]*>\s*)?(?:\([^)]*\)|\w+)\s*=>"
)
_FUNC_DECL = re.compile(r"^(?:export\s+(?:default\s+)?)?function\s+\w*\s*\(")
_DEFAULT_EXPORT = re.compile(r"^export\s+default\s+")
_PATH_ALIAS = re.compile(r"""from\s+['"]@/""")
_RELATIVE_IMPORT = re.compile(r"""from\s+['"]\.{1,2}/""")


def _check_js_semicolons(
    lineno: int, stripped: str, profile, out: list[StyleViolation]
) -> None:
    if profile.js_semicolons == "never":
        if stripped.endswith(";") and not stripped.startswith("for"):
            out.append(StyleViolation(
                line=lineno,
                rule="style.semicolons",
                message="Remove trailing semicolon - this repo omits them.",
            ))
    elif profile.js_semicolons == "always":
        is_statement = bool(_STATEMENT_START.match(stripped))
        ends_cleanly = stripped.endswith(_BLOCK_ENDS)
        if is_statement and not ends_cleanly:
            out.append(StyleViolation(
                line=lineno,
                rule="style.semicolons",
                message="Add semicolon - this repo always uses semicolons.",
            ))


def _check_js_quotes(
    lineno: int, stripped: str, profile, out: list[StyleViolation]
) -> None:
    if profile.js_quote_style == "single":
        if '"' in stripped and "'" not in stripped and "`" not in stripped:
            out.append(StyleViolation(
                line=lineno,
                rule="style.quotes",
                message="Use single quotes - this repo uses single quotes.",
                severity="info",
            ))
    elif profile.js_quote_style == "double":
        if "'" in stripped and '"' not in stripped and "`" not in stripped:
            out.append(StyleViolation(
                line=lineno,
                rule="style.quotes",
                message="Use double quotes - this repo uses double quotes.",
                severity="info",
            ))


def _check_js_function_style(
    lineno: int, raw_line: str, profile, out: list[StyleViolation]
) -> None:
    s = raw_line.strip()
    if profile.js_function_style == "arrow":
        if _FUNC_DECL.match(s) and not _DEFAULT_EXPORT.match(s):
            out.append(StyleViolation(
                line=lineno,
                rule="style.function_style",
                message="Prefer arrow functions (`const fn = () => {}`) — repo convention.",
                severity="info",
            ))
    elif profile.js_function_style == "declaration":
        if _ARROW_FUNC.match(s):
            out.append(StyleViolation(
                line=lineno,
                rule="style.function_style",
                message="Prefer function declarations (`function fn() {}`) — repo convention.",
                severity="info",
            ))


def _check_js_export_style(
    lineno: int, stripped: str, profile, out: list[StyleViolation]
) -> None:
    if profile.js_export_style == "named" and re.match(r"^export\s+default\s+", stripped):
        out.append(StyleViolation(
            line=lineno,
            rule="style.exports",
            message="Prefer named exports - this repo uses named exports.",
            severity="info",
        ))
    elif profile.js_export_style == "default" and re.match(r"^export\s+\{", stripped):
        out.append(StyleViolation(
            line=lineno,
            rule="style.exports",
            message="Prefer default exports - this repo uses default exports.",
            severity="info",
        ))


def _check_js_imports(
    lineno: int, stripped: str, profile, out: list[StyleViolation]
) -> None:
    if profile.js_import_alias_style == "alias_at":
        if _RELATIVE_IMPORT.search(stripped):
            out.append(StyleViolation(
                line=lineno,
                rule="style.imports",
                message="Use path aliases (`@/...`) instead of relative paths — repo convention.",
                severity="info",
            ))
    elif profile.js_import_alias_style == "relative":
        if _PATH_ALIAS.search(stripped):
            out.append(StyleViolation(
                line=lineno,
                rule="style.imports",
                message="Use relative imports - this repo avoids path aliases.",
                severity="info",
            ))


# ── Naming helpers ────────────────────────────────────────────────────────────

_RE_SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
_RE_CAMEL = re.compile(r"^[a-z][a-zA-Z0-9]*$")


def _is_snake(name: str) -> bool:
    return bool(_RE_SNAKE.match(name)) or name.startswith("__")


def _is_camel(name: str) -> bool:
    return bool(_RE_CAMEL.match(name))


# Direct language aliases
check_python_style = _check_python
check_js_ts_style = _check_js_ts
