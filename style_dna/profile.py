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
    never from a declared style guide.
    """

    source_path: str = ""
    files_analyzed: int = 0

    # Naming
    function_naming: str = "unknown"       # snake_case | camelCase | PascalCase | mixed
    variable_naming: str = "unknown"
    private_prefix_rate: float = 0.0        # fraction of internal names using _leading_underscore
    getter_setter_style: str = "unknown"    # get_x/set_x | property | direct

    # Docstrings
    docstring_style: str = "none"           # google | numpy | rest | plain | none
    docstring_coverage: float = 0.0         # fraction of functions/classes with docstrings

    # Typing
    type_hint_coverage: float = 0.0

    # Error handling
    error_handling_pattern: str = "unknown"  # broad_except | specific_except | custom_exceptions | result_type
    uses_custom_exceptions: bool = False
    logs_on_exception_rate: float = 0.0

    # Formatting
    quote_style: str = "unknown"            # single | double | mixed
    avg_line_length: float = 0.0
    max_observed_line_length: int = 0
    indent_style: str = "spaces_4"

    # Imports
    import_style: str = "unknown"           # grouped_stdlib_first | alphabetical | ungrouped
    prefers_relative_imports: bool = False

    # Structure
    avg_function_length: float = 0.0
    common_decorators: list[str] = field(default_factory=list)
    common_patterns: list[str] = field(default_factory=list)  # free-text notes for the LLM

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
        try:
            return cls(**data)
        except TypeError as e:
            raise ValueError(
                f"Style profile at '{path}' is outdated or corrupted: {e}. "
                "Re-run 'style-dna analyze' to regenerate it."
            ) from e

    def as_prompt_rules(self) -> str:
        """Render the profile as plain-English rules for an LLM system prompt."""
        rules = [
            f"- Name functions and variables in {self.function_naming} "
            f"(observed in {self.files_analyzed} files from {self.source_path or 'this codebase'}).",
        ]
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
        for note in self.common_patterns:
            rules.append(f"- {note}")
        return "\n".join(rules)
