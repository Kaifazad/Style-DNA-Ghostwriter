"""Extracts JavaScript and TypeScript conventions from source files.

Uses lexical / regex-based analysis (no Node.js dependency required).
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


# ── Regex patterns ────────────────────────────────────────────────

# Semicolons: match lines that end with a statement-like construct
_STMT_END_SEMI = re.compile(r"[^;{}\s]\s*;\s*$")
_STMT_END_NO_SEMI = re.compile(r"[^;{}\s/\*]\s*$")

# Quote styles
_SINGLE_Q = re.compile(r"(?<![\\])\'(?:[^\'\\]|\\.)*\'")
_DOUBLE_Q = re.compile(r'(?<![\\])\"(?:[^\"\\]|\\.)*\"')
_BACKTICK_Q = re.compile(r"(?<![\\])`(?:[^`\\]|\\.)*`")

# Function styles
_ARROW_FN = re.compile(r"(?:const|let|var)\s+\w+\s*=\s*(?:\([^)]*\)|[a-zA-Z_$]\w*)\s*=>")
_FUNC_DECL = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+\w+", re.MULTILINE)

# Export styles
_NAMED_EXPORT = re.compile(r"^export\s+(?:const|let|var|function|class|async\s+function)\s+", re.MULTILINE)
_DEFAULT_EXPORT = re.compile(r"^export\s+default\s+", re.MULTILINE)

# Import aliases
_ALIAS_IMPORT = re.compile(r"""from\s+['"]@/""")
_RELATIVE_IMPORT = re.compile(r"""from\s+['"]\.\.?/""")

# TypeScript: interface vs type
_TS_INTERFACE = re.compile(r"^(?:export\s+)?interface\s+\w+", re.MULTILINE)
_TS_TYPE_ALIAS = re.compile(r"^(?:export\s+)?type\s+\w+\s*=", re.MULTILINE)

# TypeScript: typed params/returns
_TS_TYPED_PARAM = re.compile(r"\w+\s*:\s*\w+")
_TS_RETURN_TYPE = re.compile(r"\)\s*:\s*\w+")

# Comment styles
_JSDOC_COMMENT = re.compile(r"/\*\*[\s\S]*?\*/")
_BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")
_INLINE_COMMENT = re.compile(r"//[^\n]*")


def extract_js_ts(sources: list[str], paths: list[Path]) -> dict:
    """Extract JS/TS conventions from a list of source strings.

    Args:
        sources: Raw file contents.
        paths: Corresponding file paths (used to detect .ts/.tsx).

    Returns:
        Dict of JS/TS-related StyleProfile fields.
    """
    semi_yes = 0
    semi_no = 0
    q_single = 0
    q_double = 0
    q_backtick = 0
    arrow_fns = 0
    func_decls = 0
    named_exports = 0
    default_exports = 0
    alias_imports = 0
    relative_imports = 0
    ts_interfaces = 0
    ts_type_aliases = 0
    ts_typed = 0
    ts_untyped = 0
    jsdoc_count = 0
    inline_count = 0
    block_count = 0

    ts_extensions = {".ts", ".tsx"}

    for src, path in zip(sources, paths):
        is_ts = path.suffix in ts_extensions

        # ── Semicolons ──
        for line in src.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            if _STMT_END_SEMI.search(stripped):
                semi_yes += 1
            elif _STMT_END_NO_SEMI.search(stripped):
                # Only count lines that look like statements, not blocks
                if not stripped.endswith("{") and not stripped.endswith("}") and not stripped.endswith(","):
                    semi_no += 1

        # ── Quote style ──
        q_single += len(_SINGLE_Q.findall(src))
        q_double += len(_DOUBLE_Q.findall(src))
        q_backtick += len(_BACKTICK_Q.findall(src))

        # ── Function style ──
        arrow_fns += len(_ARROW_FN.findall(src))
        func_decls += len(_FUNC_DECL.findall(src))

        # ── Export style ──
        named_exports += len(_NAMED_EXPORT.findall(src))
        default_exports += len(_DEFAULT_EXPORT.findall(src))

        # ── Import aliases ──
        alias_imports += len(_ALIAS_IMPORT.findall(src))
        relative_imports += len(_RELATIVE_IMPORT.findall(src))

        # ── TypeScript: interface vs type ──
        if is_ts:
            ts_interfaces += len(_TS_INTERFACE.findall(src))
            ts_type_aliases += len(_TS_TYPE_ALIAS.findall(src))
            ts_typed += len(_TS_TYPED_PARAM.findall(src))
            ts_untyped_lines = sum(
                1 for line in src.splitlines()
                if re.match(r"^\s*(?:const|let|var)\s+\w+\s*=", line) and ":" not in line.split("=")[0]
            )
            ts_untyped += ts_untyped_lines

        # ── Comment style ──
        jsdoc_count += len(_JSDOC_COMMENT.findall(src))
        # Block comments that are NOT jsdoc
        all_blocks = len(_BLOCK_COMMENT.findall(src))
        block_count += max(0, all_blocks - jsdoc_count)
        inline_count += len(_INLINE_COMMENT.findall(src))

    # ── Determine values ──
    total_semi = semi_yes + semi_no
    if total_semi > 5:
        semi_ratio = semi_yes / total_semi
        js_semicolons = "always" if semi_ratio > 0.7 else ("never" if semi_ratio < 0.3 else "mixed")
    else:
        js_semicolons = "unknown"

    total_quotes = q_single + q_double + q_backtick
    if total_quotes > 3:
        if q_single > q_double and q_single > q_backtick:
            js_quote_style = "single"
        elif q_double > q_single and q_double > q_backtick:
            js_quote_style = "double"
        elif q_backtick > q_single and q_backtick > q_double:
            js_quote_style = "backtick"
        else:
            js_quote_style = "mixed"
    else:
        js_quote_style = "unknown"

    total_fns = arrow_fns + func_decls
    if total_fns > 2:
        fn_ratio = arrow_fns / total_fns
        js_function_style = "arrow" if fn_ratio > 0.65 else ("declaration" if fn_ratio < 0.35 else "mixed")
    else:
        js_function_style = "unknown"

    total_exports = named_exports + default_exports
    if total_exports > 2:
        export_ratio = named_exports / total_exports
        js_export_style = "named" if export_ratio > 0.65 else ("default" if export_ratio < 0.35 else "mixed")
    else:
        js_export_style = "unknown"

    total_imports = alias_imports + relative_imports
    if total_imports > 2:
        alias_ratio = alias_imports / total_imports
        js_import_alias_style = "alias_at" if alias_ratio > 0.5 else "relative"
    else:
        js_import_alias_style = "unknown"

    total_ts_types = ts_interfaces + ts_type_aliases
    if total_ts_types > 2:
        ts_type_style = "interface" if ts_interfaces > ts_type_aliases else ("type" if ts_type_aliases > ts_interfaces else "mixed")
    else:
        ts_type_style = "unknown"

    total_ts_sigs = ts_typed + ts_untyped
    ts_strict_rate = ts_typed / total_ts_sigs if total_ts_sigs > 5 else 0.0

    total_comments = jsdoc_count + inline_count + block_count
    if total_comments > 3:
        comment_max = max(jsdoc_count, inline_count, block_count)
        if comment_max == jsdoc_count:
            js_comment_style = "jsdoc"
        elif comment_max == inline_count:
            js_comment_style = "inline"
        else:
            js_comment_style = "block"
    else:
        js_comment_style = "unknown" if total_comments == 0 else "none"

    return {
        "js_quote_style": js_quote_style,
        "js_semicolons": js_semicolons,
        "js_function_style": js_function_style,
        "js_export_style": js_export_style,
        "js_import_alias_style": js_import_alias_style,
        "ts_type_style": ts_type_style,
        "ts_strict_rate": round(ts_strict_rate, 2),
        "js_comment_style": js_comment_style,
    }
