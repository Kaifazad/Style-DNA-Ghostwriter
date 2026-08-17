"""Data model for a codebase's extracted 'style DNA'."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class StyleProfile:
    """A structured fingerprint of a codebase's conventions.

    Every field is derived from real examples in the target codebase,
    never from a declared style guide.  Covers Python, JavaScript,
    TypeScript, React, Next.js, CSS/SCSS, Tailwind, and HTML.
    """

    source_path: str = ""
    files_analyzed: int = 0
    web_files_analyzed: int = 0   # JS/TS/JSX/TSX/CSS/HTML files

    # ── Python: Naming ────────────────────────────────────────────
    function_naming: str = "unknown"       # snake_case | camelCase | PascalCase | mixed
    variable_naming: str = "unknown"
    private_prefix_rate: float = 0.0
    getter_setter_style: str = "unknown"   # get_x/set_x | property | direct

    # ── Python: Docstrings ────────────────────────────────────────
    docstring_style: str = "none"          # google | numpy | rest | plain | none
    docstring_coverage: float = 0.0

    # ── Python: Typing ────────────────────────────────────────────
    type_hint_coverage: float = 0.0

    # ── Python: Error handling ────────────────────────────────────
    error_handling_pattern: str = "unknown"
    uses_custom_exceptions: bool = False
    logs_on_exception_rate: float = 0.0

    # ── Python: Formatting ────────────────────────────────────────
    quote_style: str = "unknown"           # single | double | mixed
    avg_line_length: float = 0.0
    max_observed_line_length: int = 0
    indent_style: str = "spaces_4"

    # ── Python: Imports ───────────────────────────────────────────
    import_style: str = "unknown"
    prefers_relative_imports: bool = False

    # ── Python: Structure ─────────────────────────────────────────
    avg_function_length: float = 0.0
    common_decorators: list[str] = field(default_factory=list)
    common_patterns: list[str] = field(default_factory=list)

    # ── JavaScript / TypeScript ───────────────────────────────────
    js_quote_style: str = "unknown"        # single | double | backtick | mixed
    js_semicolons: str = "unknown"         # always | never | mixed
    js_function_style: str = "unknown"     # arrow | declaration | mixed
    js_export_style: str = "unknown"       # named | default | mixed
    js_import_alias_style: str = "unknown" # alias_at (@/...) | relative | mixed
    ts_type_style: str = "unknown"         # interface | type | mixed
    ts_strict_rate: float = 0.0            # fraction of typed params/returns

    # ── React / Next.js ───────────────────────────────────────────
    nextjs_router: str = "unknown"         # app_router | pages_router | none
    react_component_style: str = "unknown" # arrow | function | mixed
    react_component_naming: str = "unknown"  # PascalCase file names pattern
    react_use_client_rate: float = 0.0     # fraction of components with 'use client'
    react_use_server_rate: float = 0.0     # fraction with 'use server'
    react_hooks_patterns: list[str] = field(default_factory=list)
    react_state_management: str = "unknown"  # zustand | redux | context | tanstack_query | none
    web_frameworks: list[str] = field(default_factory=list)

    # ── CSS / Styling ─────────────────────────────────────────────
    styling_approach: str = "unknown"      # tailwind | css_modules | css_in_js | vanilla_css | mixed
    css_class_naming: str = "unknown"      # BEM | kebab-case | camelCase | mixed
    css_variables_usage: bool = False
    css_color_format: str = "unknown"      # hex | hsl | rgb | mixed

    # ── HTML ──────────────────────────────────────────────────────
    html_indent_style: str = "unknown"     # spaces_2 | spaces_4 | tabs
    html_attr_quote_style: str = "unknown" # single | double
    html_semantic_usage: float = 0.0       # fraction of semantic elements

    # ── JS / TS comment style ─────────────────────────────────────
    js_comment_style: str = "unknown"      # jsdoc | inline | block | none

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "StyleProfile":
        try:
            data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(
                f"Could not load style profile from '{path}': {e}. "
                "Re-run 'style-dna analyze' to regenerate it."
            ) from e
        # Silently drop fields that no longer exist in the dataclass so
        # older profiles remain loadable after upgrades.
        valid_fields = {f.name for f in StyleProfile.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        try:
            return cls(**filtered)
        except TypeError as e:
            raise ValueError(
                f"Style profile at '{path}' is outdated or corrupted: {e}. "
                "Re-run 'style-dna analyze' to regenerate it."
            ) from e

    # ── Prompt rendering ──────────────────────────────────────────

    def as_prompt_rules(self) -> str:
        """Render the profile as plain-English rules for an LLM system prompt."""
        sections: list[str] = []

        # Detect which stacks are present
        has_python = self.files_analyzed > 0 and self.function_naming != "unknown"
        has_web = self.web_files_analyzed > 0

        if has_python:
            sections.append(self._python_rules())
        if has_web:
            sections.append(self._web_rules())

        # Common patterns apply to the whole codebase
        if self.common_patterns:
            pattern_lines = [f"- {note}" for note in self.common_patterns]
            sections.append("## General Patterns\n" + "\n".join(pattern_lines))

        # Fallback: if nothing was detected, still output the basics
        if not sections:
            return self._python_rules()

        return "\n\n".join(sections)

    def _python_rules(self) -> str:
        """Render Python-specific conventions."""
        rules: list[str] = []
        rules.append(
            f"- Name functions and variables in {self.function_naming} "
            f"(observed in {self.files_analyzed} files from {self.source_path or 'this codebase'})."
        )
        if self.private_prefix_rate > 0.15:
            rules.append(
                f"- Prefix internal/private names with a leading underscore "
                f"(observed in ~{self.private_prefix_rate:.0%} of internal names)."
            )
        if self.docstring_style != "none" and self.docstring_coverage > 0.2:
            rules.append(
                f"- Write {self.docstring_style}-style docstrings on public functions/classes "
                f"(coverage ~{self.docstring_coverage:.0%} in this codebase)."
            )
        else:
            rules.append("- This codebase rarely uses docstrings; do not over-document.")
        if self.type_hint_coverage > 0.3:
            rules.append(
                f"- Use type hints (observed in ~{self.type_hint_coverage:.0%} of function signatures)."
            )
        if self.error_handling_pattern != "unknown":
            rules.append(f"- Error handling convention: {self.error_handling_pattern.replace('_', ' ')}.")
        if self.uses_custom_exceptions:
            rules.append("- Prefer raising custom/domain-specific exception classes over generic ones.")
        if self.quote_style in ("single", "double"):
            rules.append(f"- Use {self.quote_style} quotes for strings, matching the rest of the codebase.")
        if self.avg_function_length:
            rules.append(
                f"- Keep functions close to the codebase's typical length "
                f"(~{self.avg_function_length:.0f} lines on average); avoid sprawling functions."
            )
        if self.common_decorators:
            rules.append(f"- Common decorators in this codebase: {', '.join(self.common_decorators)}.")
        if self.indent_style and self.indent_style != "spaces_4":
            rules.append(f"- Use {self.indent_style.replace('_', ' ')} for indentation.")
        if self.import_style != "unknown":
            rules.append(f"- Import ordering convention: {self.import_style.replace('_', ' ')}.")

        header = "## Python Conventions" if self.web_files_analyzed > 0 else ""
        body = "\n".join(rules)
        return f"{header}\n{body}".strip() if header else body

    def _web_rules(self) -> str:
        """Render JavaScript / TypeScript / React / Next.js / CSS / HTML conventions."""
        sections: list[str] = []

        # ── Frameworks detected ──
        if self.web_frameworks:
            sections.append(f"- Detected frameworks/tools: {', '.join(self.web_frameworks)}.")

        # ── JS / TS ──
        js_rules: list[str] = []
        if self.js_quote_style in ("single", "double"):
            js_rules.append(f"- Use {self.js_quote_style} quotes for JS/TS strings.")
        if self.js_semicolons in ("always", "never"):
            js_rules.append(
                f"- {'Always use' if self.js_semicolons == 'always' else 'Omit'} semicolons at end of statements."
            )
        if self.js_function_style in ("arrow", "declaration"):
            label = "arrow functions (`const fn = () => {}`)" if self.js_function_style == "arrow" else "function declarations (`function fn() {}`)"
            js_rules.append(f"- Prefer {label}.")
        if self.js_export_style in ("named", "default"):
            js_rules.append(f"- Prefer {self.js_export_style} exports.")
        if self.js_import_alias_style == "alias_at":
            js_rules.append("- Use path aliases (`@/...`) for imports instead of deep relative paths.")
        elif self.js_import_alias_style == "relative":
            js_rules.append("- Use relative imports (`./`, `../`) — no path aliases.")
        if self.ts_type_style in ("interface", "type"):
            js_rules.append(f"- Prefer `{self.ts_type_style}` over `{'type' if self.ts_type_style == 'interface' else 'interface'}` for object shapes in TypeScript.")
        if self.ts_strict_rate > 0.3:
            js_rules.append(f"- TypeScript typing coverage: ~{self.ts_strict_rate:.0%} of function signatures are typed.")
        if self.js_comment_style != "unknown":
            labels = {"jsdoc": "JSDoc (`/** ... */`)", "inline": "inline (`// ...`)", "block": "block (`/* ... */`)"}
            js_rules.append(f"- Comment style: {labels.get(self.js_comment_style, self.js_comment_style)}.")
        if js_rules:
            sections.append("### JavaScript / TypeScript\n" + "\n".join(js_rules))

        # ── React / Next.js ──
        react_rules: list[str] = []
        if self.nextjs_router in ("app_router", "pages_router"):
            label = "App Router (`app/`)" if self.nextjs_router == "app_router" else "Pages Router (`pages/`)"
            react_rules.append(f"- Next.js routing: {label}.")
        if self.react_component_style in ("arrow", "function"):
            label = "arrow functions (`const Button = () => ...`)" if self.react_component_style == "arrow" else "function declarations (`function Button() ...`)"
            react_rules.append(f"- Define React components as {label}.")
        if self.react_component_naming != "unknown":
            react_rules.append(f"- Component file naming: {self.react_component_naming}.")
        if self.react_use_client_rate > 0.05:
            react_rules.append(f"- ~{self.react_use_client_rate:.0%} of components use `'use client'` directive.")
        if self.react_use_server_rate > 0.05:
            react_rules.append(f"- ~{self.react_use_server_rate:.0%} of modules use `'use server'` directive (Server Actions).")
        if self.react_hooks_patterns:
            react_rules.append(f"- Custom hook patterns in use: {', '.join(self.react_hooks_patterns)}.")
        if self.react_state_management != "unknown" and self.react_state_management != "none":
            react_rules.append(f"- State management: {self.react_state_management.replace('_', ' ')}.")
        if react_rules:
            sections.append("### React / Next.js\n" + "\n".join(react_rules))

        # ── CSS / Styling ──
        css_rules: list[str] = []
        if self.styling_approach != "unknown":
            labels = {
                "tailwind": "Tailwind CSS utility classes",
                "css_modules": "CSS Modules (`*.module.css`)",
                "css_in_js": "CSS-in-JS (styled-components / Emotion)",
                "vanilla_css": "Vanilla CSS (plain `.css` files)",
                "mixed": "Mixed styling approaches",
            }
            css_rules.append(f"- Styling approach: {labels.get(self.styling_approach, self.styling_approach)}.")
        if self.css_class_naming != "unknown":
            css_rules.append(f"- CSS class naming convention: {self.css_class_naming}.")
        if self.css_variables_usage:
            css_rules.append("- Uses CSS custom properties (`var(--token-name)`) for design tokens.")
        if self.css_color_format != "unknown":
            css_rules.append(f"- Preferred color format: {self.css_color_format.upper()}.")
        if css_rules:
            sections.append("### CSS / Styling\n" + "\n".join(css_rules))

        # ── HTML ──
        html_rules: list[str] = []
        if self.html_indent_style != "unknown":
            html_rules.append(f"- HTML indentation: {self.html_indent_style.replace('_', ' ')}.")
        if self.html_attr_quote_style in ("single", "double"):
            html_rules.append(f"- HTML attribute quotes: {self.html_attr_quote_style}.")
        if self.html_semantic_usage > 0.3:
            html_rules.append(f"- Uses semantic HTML elements (~{self.html_semantic_usage:.0%} semantic tag rate). Prefer `<header>`, `<main>`, `<section>`, `<nav>`, etc.")
        if html_rules:
            sections.append("### HTML\n" + "\n".join(html_rules))

        header = "## Web Conventions"
        body = "\n\n".join(sections)
        return f"{header}\n{body}" if sections else ""
