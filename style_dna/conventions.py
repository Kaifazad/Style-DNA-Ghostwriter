"""Writes extracted style rules into the convention files that popular
coding agents automatically read at session start, so the rules apply
universally -- no MCP support required on the agent's side.
"""

from __future__ import annotations

from pathlib import Path

from .profile import StyleProfile

MARKER_START = "<!-- style-dna:start -->"
MARKER_END = "<!-- style-dna:end -->"

# Files various agents auto-read for project context/instructions.
TARGET_FILES = [
    "CLAUDE.md",       # Claude Code
    "AGENTS.md",        # Codex, OpenCode, and the emerging cross-tool convention
    ".cursorrules",      # Cursor
    ".github/copilot-instructions.md",  # GitHub Copilot
]


def _section(profile: StyleProfile) -> str:
    return (
        f"{MARKER_START}\n"
        f"## Style DNA (auto-generated -- do not hand-edit this section)\n\n"
        f"These conventions were extracted from this codebase's own source "
        f"({profile.total_files_analyzed} files analyzed). Follow them for any new "
        f"or modified code:\n\n"
        f"{profile.as_prompt_rules()}\n\n"
        f"Regenerate with: `style-dna init` (or `style-dna analyze .`)\n"
        f"{MARKER_END}"
    )


def _upsert(file_path: Path, section: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        if MARKER_START in content and MARKER_END in content:
            pre = content.split(MARKER_START)[0]
            post = content.split(MARKER_END)[1]
            content = pre + section + post
        else:
            content = content.rstrip() + "\n\n" + section + "\n"
    else:
        content = section + "\n"
    file_path.write_text(content, encoding="utf-8")


def write_convention_files(root: Path, profile: StyleProfile) -> list[Path]:
    """Write/update the style-DNA section in every known convention file.

    Returns the list of file paths that were written.
    """
    section = _section(profile)
    written = []
    for rel in TARGET_FILES:
        target = root / rel
        _upsert(target, section)
        written.append(target)
    return written


MCP_CONFIG_SNIPPET = """{
  "mcpServers": {
    "style-dna": {
      "command": "style-dna",
      "args": ["mcp"]
    }
  }
}"""
