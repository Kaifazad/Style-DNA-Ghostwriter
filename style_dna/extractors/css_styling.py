"""Extracts CSS, SCSS, and Tailwind styling conventions from source files.

Detects: styling approach (Tailwind / CSS Modules / CSS-in-JS / Vanilla),
class naming convention (BEM / kebab-case / camelCase), CSS variable usage,
and color format preferences.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


# ── Regex patterns ────────────────────────────────────────────────

# CSS class selectors in .css/.scss files
_CSS_CLASS_SELECTOR = re.compile(r"\.([a-zA-Z_][\w-]*)\s*[{,:]")

# BEM pattern: block__element--modifier
_BEM_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:__[a-z][a-z0-9]*)?(?:--[a-z][a-z0-9]*)?$")
_KEBAB_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)+$")
_CAMEL_PATTERN = re.compile(r"^[a-z][a-zA-Z0-9]*$")

# CSS custom properties
_CSS_VAR_DECL = re.compile(r"--[\w-]+\s*:")
_CSS_VAR_USAGE = re.compile(r"var\(\s*--[\w-]+")

# Color formats
_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3,4}){1,2}\b")
_HSL_COLOR = re.compile(r"hsla?\s*\(")
_RGB_COLOR = re.compile(r"rgba?\s*\(")

# Tailwind detection: className with utility-like strings
_TAILWIND_CLASSNAME = re.compile(r'className\s*=\s*[{"\'].*?(?:flex|grid|p-|m-|w-|h-|text-|bg-|rounded|shadow|border)')
_TAILWIND_IMPORT = re.compile(r"""@tailwind\s+(?:base|components|utilities)""")
_TAILWIND_CONFIG = re.compile(r"tailwind\.config\.")

# CSS Modules: import styles from '*.module.css'
_CSS_MODULE_IMPORT = re.compile(r"""import\s+\w+\s+from\s+['"][^'"]*\.module\.(?:css|scss|sass)['"]""")

# CSS-in-JS: styled-components / Emotion
_STYLED_COMPONENTS = re.compile(r"styled\.\w+`|styled\(\w+\)`|css`")


def extract_css_styling(
    css_sources: list[str],
    css_paths: list[Path],
    js_sources: list[str],
    js_paths: list[Path],
    root: Path,
) -> dict:
    """Extract CSS and styling conventions.

    Args:
        css_sources: Raw contents of .css/.scss files.
        css_paths: Corresponding CSS file paths.
        js_sources: Raw contents of .js/.jsx/.ts/.tsx files (for Tailwind/CSS-in-JS detection).
        js_paths: Corresponding JS/TS file paths.
        root: Project root directory.

    Returns:
        Dict of CSS/styling-related StyleProfile fields.
    """
    # ── Detect styling approach ──
    tailwind_signals = 0
    css_module_signals = 0
    css_in_js_signals = 0
    vanilla_css_files = 0

    # Check for tailwind config
    tailwind_config_exists = any(
        f.name.startswith("tailwind.config") for f in root.iterdir() if f.is_file()
    )
    if tailwind_config_exists:
        tailwind_signals += 5

    for src in js_sources:
        if _TAILWIND_CLASSNAME.search(src):
            tailwind_signals += 1
        if _CSS_MODULE_IMPORT.search(src):
            css_module_signals += 1
        if _STYLED_COMPONENTS.search(src):
            css_in_js_signals += 1

    for src in css_sources:
        if _TAILWIND_IMPORT.search(src):
            tailwind_signals += 3

    # Count CSS module files vs plain CSS files
    for p in css_paths:
        if ".module." in p.name:
            css_module_signals += 1
        else:
            vanilla_css_files += 1

    # Determine approach
    signals = {
        "tailwind": tailwind_signals,
        "css_modules": css_module_signals,
        "css_in_js": css_in_js_signals,
        "vanilla_css": vanilla_css_files,
    }
    max_signal = max(signals.values()) if signals else 0
    if max_signal == 0:
        styling_approach = "unknown"
    else:
        winners = [k for k, v in signals.items() if v == max_signal]
        styling_approach = winners[0] if len(winners) == 1 else "mixed"

    # ── Class naming convention ──
    class_names: list[str] = []
    for src in css_sources:
        class_names.extend(_CSS_CLASS_SELECTOR.findall(src))

    bem_count = 0
    kebab_count = 0
    camel_count = 0
    other_count = 0

    for name in class_names:
        if "__" in name or "--" in name:
            bem_count += 1
        elif _KEBAB_PATTERN.match(name):
            kebab_count += 1
        elif _CAMEL_PATTERN.match(name):
            camel_count += 1
        else:
            other_count += 1

    total_classes = bem_count + kebab_count + camel_count + other_count
    if total_classes > 3:
        counts = {"BEM": bem_count, "kebab-case": kebab_count, "camelCase": camel_count}
        css_class_naming = max(counts, key=counts.get)  # type: ignore[arg-type]
    else:
        css_class_naming = "unknown"

    # ── CSS variables ──
    css_var_decls = 0
    css_var_usages = 0
    for src in css_sources:
        css_var_decls += len(_CSS_VAR_DECL.findall(src))
        css_var_usages += len(_CSS_VAR_USAGE.findall(src))
    css_variables_usage = (css_var_decls + css_var_usages) > 3

    # ── Color format ──
    hex_count = 0
    hsl_count = 0
    rgb_count = 0
    for src in css_sources:
        hex_count += len(_HEX_COLOR.findall(src))
        hsl_count += len(_HSL_COLOR.findall(src))
        rgb_count += len(_RGB_COLOR.findall(src))

    total_colors = hex_count + hsl_count + rgb_count
    if total_colors > 3:
        color_counts = {"hex": hex_count, "hsl": hsl_count, "rgb": rgb_count}
        css_color_format = max(color_counts, key=color_counts.get)  # type: ignore[arg-type]
    else:
        css_color_format = "unknown"

    return {
        "styling_approach": styling_approach,
        "css_class_naming": css_class_naming,
        "css_variables_usage": css_variables_usage,
        "css_color_format": css_color_format,
    }
