"""Extracts HTML conventions from source files.

Detects: indentation style, attribute quote style, and semantic HTML usage.
Uses regex-based parsing (no external HTML parser dependency).
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


# ── Semantic HTML elements ────────────────────────────────────────
_SEMANTIC_TAGS = {
    "header", "footer", "main", "nav", "section", "article",
    "aside", "figure", "figcaption", "details", "summary",
    "mark", "time", "dialog",
}

_NON_SEMANTIC_TAGS = {
    "div", "span",
}

_HTML_TAG = re.compile(r"<(/?)(\w+)(?:\s|>|/>)")

# Attribute quote detection
_ATTR_DOUBLE = re.compile(r'\w+=("[^"]*")')
_ATTR_SINGLE = re.compile(r"\w+=('[^']*')")


def extract_html(
    sources: list[str],
    paths: list[Path],
) -> dict:
    """Extract HTML conventions from source files.

    Args:
        sources: Raw HTML file contents.
        paths: Corresponding file paths.

    Returns:
        Dict of HTML-related StyleProfile fields.
    """
    indent_counts: Counter[str] = Counter()
    attr_double = 0
    attr_single = 0
    semantic_tags = 0
    non_semantic_tags = 0

    for src in sources:
        # ── Indent style ──
        for line in src.splitlines():
            if line and line[0] in (" ", "\t"):
                leading = len(line) - len(line.lstrip())
                raw = line[:leading]
                if "\t" in raw:
                    indent_counts["tabs"] += 1
                elif leading % 4 == 0 and leading > 0:
                    indent_counts["spaces_4"] += 1
                elif leading % 2 == 0 and leading > 0:
                    indent_counts["spaces_2"] += 1

        # ── Attribute quote style ──
        attr_double += len(_ATTR_DOUBLE.findall(src))
        attr_single += len(_ATTR_SINGLE.findall(src))

        # ── Semantic tags ──
        for match in _HTML_TAG.finditer(src):
            closing, tag = match.groups()
            tag_lower = tag.lower()
            if tag_lower in _SEMANTIC_TAGS:
                semantic_tags += 1
            elif tag_lower in _NON_SEMANTIC_TAGS:
                non_semantic_tags += 1

    # ── Determine values ──

    # Indent style
    if indent_counts:
        html_indent_style = indent_counts.most_common(1)[0][0]
    else:
        html_indent_style = "unknown"

    # Attribute quotes
    total_attrs = attr_double + attr_single
    if total_attrs > 3:
        html_attr_quote_style = "double" if attr_double >= attr_single else "single"
    else:
        html_attr_quote_style = "unknown"

    # Semantic usage
    total_semantic_relevant = semantic_tags + non_semantic_tags
    html_semantic_usage = (
        semantic_tags / total_semantic_relevant if total_semantic_relevant > 3 else 0.0
    )

    return {
        "html_indent_style": html_indent_style,
        "html_attr_quote_style": html_attr_quote_style,
        "html_semantic_usage": round(html_semantic_usage, 2),
    }
