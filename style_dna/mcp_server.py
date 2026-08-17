"""MCP server exposing Style DNA Ghostwriter as tools for any MCP-compatible
coding agent (Claude Code, Cursor, and others that speak the Model Context
Protocol).

Run it directly:
    style-dna mcp

Or point an MCP host at it via stdio using the console script:
    style-dna mcp
"""

import os
from pathlib import Path

# NOTE: FastMCP is NOT imported at module level — doing so would crash any
# CLI subcommand when the user hasn't installed the [mcp] optional extra.
# The import is deferred into run_server() below.

from .analyzer import analyze_codebase
from .profile import StyleProfile

DEFAULT_PROFILE_PATH = ".style-dna/style_profile.json"


def _build_mcp() -> "FastMCP":  # type: ignore[name-defined]  # noqa: F821
    """Import FastMCP and register all tools. Called once inside run_server()."""
    from mcp.server.fastmcp import FastMCP  # deferred: only required with [mcp]

    mcp = FastMCP("style-dna-ghostwriter")

    @mcp.tool()
    def analyze_repo(path: str = ".", save: bool = True, force: bool = False) -> str:
        """Analyze a codebase's real coding conventions (naming, docstrings,
        error handling, typing, formatting, imports) and return them as rules.

        Args:
            path: Path to the codebase root to analyze. Defaults to the current directory.
            save: If true, saves the profile to .style-dna/style_profile.json for reuse.
            force: If true, re-analyzes even when a cached profile already exists.

        Returns:
            Plain-English style rules extracted from real source examples.
        """
        cached = Path(path) / DEFAULT_PROFILE_PATH
        if not force and cached.exists():
            profile = StyleProfile.load(cached)
            return (
                f"Loaded cached profile from '{cached}' "
                f"({profile.total_files_analyzed} files analyzed).\n\n"
                f"{profile.as_prompt_rules()}"
            )

        profile = analyze_codebase(path)
        if profile.total_files_analyzed == 0:
            return f"No supported source files found under '{path}' (Python, JS/TS, React, Next.js, CSS, HTML)."

        if save:
            out = Path(path) / DEFAULT_PROFILE_PATH
            out.parent.mkdir(parents=True, exist_ok=True)
            profile.save(out)

        return (
            f"Analyzed {profile.total_files_analyzed} files from '{path}'.\n\n"
            f"{profile.as_prompt_rules()}"
        )

    @mcp.tool()
    def get_style_rules(path: str = ".") -> str:
        """Get the style rules for a codebase, using a cached profile if one
        exists at .style-dna/style_profile.json, otherwise analyzing fresh.

        Args:
            path: Path to the codebase root.

        Returns:
            Plain-English style rules to follow when writing new code in this repo.
        """
        cached = Path(path) / DEFAULT_PROFILE_PATH
        if cached.exists():
            profile = StyleProfile.load(cached)
            return profile.as_prompt_rules()

        profile = analyze_codebase(path)
        if profile.total_files_analyzed == 0:
            return f"No supported source files found under '{path}'. No style rules available."
        return profile.as_prompt_rules()

    @mcp.tool()
    def refresh_style_profile(path: str = ".") -> str:
        """Re-analyze a codebase and overwrite its cached style profile.
        Call this after significant new code has been merged, so the learned
        conventions stay current.

        Args:
            path: Path to the codebase root.

        Returns:
            Confirmation message with the updated rules.
        """
        profile = analyze_codebase(path)
        out = Path(path) / DEFAULT_PROFILE_PATH
        out.parent.mkdir(parents=True, exist_ok=True)
        profile.save(out)
        return f"Refreshed profile from {profile.total_files_analyzed} files.\n\n{profile.as_prompt_rules()}"

    return mcp


def run_server() -> None:
    """Entry point used by `style-dna mcp`."""
    mcp = _build_mcp()
    mcp.run(transport=os.environ.get("STYLE_DNA_MCP_TRANSPORT", "stdio"))


if __name__ == "__main__":
    run_server()
