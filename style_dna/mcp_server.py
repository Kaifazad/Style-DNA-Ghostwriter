"""MCP server exposing Style DNA Ghostwriter as tools, resources, and prompts
for any MCP-compatible coding agent (Claude Code, Cursor, and others that
speak the Model Context Protocol).

Run it directly:
    style-dna mcp

Or point an MCP host at it via stdio:
    style-dna mcp

P1: Adds MCP Resource (``style-dna://profile``) and Prompt (``/ghostwrite``)
so the style profile is *passively* attached to the agent context — no
explicit ``analyze_repo`` call required on every session.

P1.2: Adds ``check_code_style`` tool so agents can verify generated code
against the extracted conventions before presenting it to the user.

Upgrades:
- Scoped Resources: ``style-dna://rules/python``, ``style-dna://rules/web``,
  and ``style-dna://rules/compact`` to eliminate context-window token waste.
- Stale Profile Detection: Alerts when a profile was generated >30 days ago.
"""

import json
import os
from pathlib import Path

# NOTE: FastMCP is NOT imported at module level — doing so would crash any
# CLI subcommand when the user hasn't installed the [mcp] optional extra.
# The import is deferred into run_server() below.

from .analyzer import analyze_codebase
from .profile import StyleProfile

DEFAULT_PROFILE_PATH = ".style-dna/style_profile.json"


# ── Shared implementation helpers ─────────────────────────────────────────────

def _load_or_analyze(path: str = ".") -> StyleProfile:
    """Load a cached profile if one exists, otherwise analyze fresh."""
    cached = Path(path) / DEFAULT_PROFILE_PATH
    if cached.exists():
        return StyleProfile.load(cached)
    return analyze_codebase(path)


def _analyze_repo_impl(path: str = ".", save: bool = True, force: bool = False) -> str:
    """Core implementation for analyze_repo."""
    cached = Path(path) / DEFAULT_PROFILE_PATH
    if not force and cached.exists():
        profile = StyleProfile.load(cached)
        advisory = (
            "[ADVISORY] Style profile is >30 days old. Run with force=True to re-sync.\n\n"
            if profile.is_stale(30)
            else ""
        )
        return (
            f"{advisory}Loaded cached profile from '{cached}' "
            f"({profile.total_files_analyzed} files analyzed).\n\n"
            f"{profile.as_prompt_rules()}"
        )

    profile = analyze_codebase(path)
    if profile.total_files_analyzed == 0:
        return (
            f"No supported source files found under '{path}' "
            "(Python, JS/TS, React, Next.js, CSS, HTML)."
        )

    if save:
        out = Path(path) / DEFAULT_PROFILE_PATH
        out.parent.mkdir(parents=True, exist_ok=True)
        profile.save(out)

    return (
        f"Analyzed {profile.total_files_analyzed} files from '{path}'.\n\n"
        f"{profile.as_prompt_rules()}"
    )


def _get_style_rules_impl(path: str = ".", scope: str = "all") -> str:
    """Core implementation for get_style_rules."""
    cached = Path(path) / DEFAULT_PROFILE_PATH
    advisory = ""
    if cached.exists():
        profile = StyleProfile.load(cached)
        if profile.is_stale(30):
            advisory = (
                "[ADVISORY] Style profile is >30 days old. "
                "Run 'refresh_style_profile' to re-sync with recent code.\n\n"
            )
        return advisory + profile.as_prompt_rules(scope=scope)

    profile = analyze_codebase(path)
    if profile.total_files_analyzed == 0:
        return (
            f"No supported source files found under '{path}'. "
            "No style rules available."
        )
    return profile.as_prompt_rules(scope=scope)


def _refresh_style_profile_impl(path: str = ".") -> str:
    """Core implementation for refresh_style_profile."""
    profile = analyze_codebase(path)
    out = Path(path) / DEFAULT_PROFILE_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    profile.save(out)
    return f"Refreshed profile from {profile.total_files_analyzed} files.\n\n{profile.as_prompt_rules()}"


def _check_code_style_impl(code: str, path: str = ".", language: str = "auto") -> str:
    """Core implementation for check_code_style (P1.2)."""
    from .verifier import check_code_style, StyleViolation  # deferred

    try:
        profile = _load_or_analyze(path)
    except Exception as e:
        return f"Could not load style profile: {e}"

    if profile.total_files_analyzed == 0:
        return (
            "No style profile available for this path. "
            "Run analyze_repo first to extract conventions."
        )

    advisory = (
        "[ADVISORY] Cached profile is >30 days old; verify against current patterns.\n\n"
        if profile.is_stale(30)
        else ""
    )

    violations = check_code_style(code, profile, language=language)

    if not violations:
        return f"{advisory}No style violations found. Code matches repo conventions."

    lines = [
        f"{advisory}Found {len(violations)} style violation(s):\n"
    ]
    for v in violations:
        loc = f"Line {v.line}" if v.line > 0 else "File"
        lines.append(f"  [{v.severity.upper()}] {loc} - {v.rule}: {v.message}")

    return "\n".join(lines)


# ── Standalone callable wrappers (importable without MCP) ────────────────────

def analyze_repo(path: str = ".", save: bool = True, force: bool = False) -> str:
    return _analyze_repo_impl(path=path, save=save, force=force)


def get_style_rules(path: str = ".", scope: str = "all") -> str:
    return _get_style_rules_impl(path=path, scope=scope)


def refresh_style_profile(path: str = ".") -> str:
    return _refresh_style_profile_impl(path=path)


# ── MCP server builder ────────────────────────────────────────────────────────

def _build_mcp() -> "FastMCP":  # type: ignore[name-defined]  # noqa: F821
    """Import FastMCP and register all tools, resources, and prompts."""
    from mcp.server.fastmcp import FastMCP  # deferred: only required with [mcp]

    mcp = FastMCP(
        "style-dna-ghostwriter",
        instructions=(
            "Style DNA Ghostwriter analyzes your codebase's real coding "
            "conventions (naming, docstrings, typing, error handling, imports, "
            "styling) and provides rules so every line you write looks like it "
            "was written by the same team. Use `analyze_repo` once to build a "
            "profile, then `get_style_rules` or the `style-dna://rules` resource "
            "before writing any new code."
        ),
    )

    # ── Tools ─────────────────────────────────────────────────────

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def analyze_repo(path: str = ".", save: bool = True, force: bool = False) -> str:
        """Analyze a codebase's real coding conventions and return them as rules.

        Args:
            path: Path to the codebase root to analyze. Defaults to the current directory.
            save: If true, saves the profile to .style-dna/style_profile.json for reuse.
            force: If true, re-analyzes even when a cached profile already exists.

        Returns:
            Plain-English style rules extracted from real source examples.
        """
        return _analyze_repo_impl(path=path, save=save, force=force)

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def get_style_rules(path: str = ".", scope: str = "all") -> str:
        """Get the style rules for a codebase, using a cached profile if one
        exists at .style-dna/style_profile.json, otherwise analyzing fresh.

        Args:
            path: Path to the codebase root.
            scope: "all" (default), "python", "web", or "compact" (token-dense summary).

        Returns:
            Plain-English style rules to follow when writing new code in this repo.
        """
        return _get_style_rules_impl(path=path, scope=scope)

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def refresh_style_profile(path: str = ".") -> str:
        """Re-analyze a codebase and overwrite its cached style profile.
        Call this after significant new code has been merged.

        Args:
            path: Path to the codebase root.

        Returns:
            Confirmation message with the updated rules.
        """
        return _refresh_style_profile_impl(path=path)

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def check_code_style(
        code: str,
        path: str = ".",
        language: str = "auto",
    ) -> str:
        """Verify that a code snippet matches this repo's extracted conventions.

        Run this *after* generating code and *before* presenting it to the user.

        Args:
            code: The code snippet to check (Python, JS, TS, TSX, or JSX).
            path: Path to the codebase root (to load its style profile).
            language: "python", "js", "ts", "tsx", "jsx", or "auto" (default).

        Returns:
            "No violations" message, or a list of violations with line numbers.
        """
        return _check_code_style_impl(code=code, path=path, language=language)

    # ── Resources (P1.1 & Scoped Resources) ────────────────────────

    @mcp.resource("style-dna://profile")
    def resource_profile() -> str:
        """Full style profile JSON for the current workspace."""
        try:
            cached = Path(".") / DEFAULT_PROFILE_PATH
            if cached.exists():
                return cached.read_text(encoding="utf-8")
            profile = analyze_codebase(".")
            return profile.to_json()
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.resource("style-dna://rules")
    def resource_rules() -> str:
        """Full plain-English style rules for the current workspace."""
        return _get_style_rules_impl(path=".", scope="all")

    @mcp.resource("style-dna://rules/python")
    def resource_rules_python() -> str:
        """Python-specific style rules only (saves context tokens)."""
        return _get_style_rules_impl(path=".", scope="python")

    @mcp.resource("style-dna://rules/web")
    def resource_rules_web() -> str:
        """Web/TypeScript/React style rules only (saves context tokens)."""
        return _get_style_rules_impl(path=".", scope="web")

    @mcp.resource("style-dna://rules/compact")
    def resource_rules_compact() -> str:
        """Ultra-dense 1-line summary of rules (saves ~65% context tokens)."""
        return _get_style_rules_impl(path=".", scope="compact")

    # ── Prompt ────────────────────────────────────────────────────

    @mcp.prompt()
    def ghostwrite(task: str, path: str = ".", scope: str = "all") -> str:
        """Generate a ghostwrite system prompt for the given coding task.

        Args:
            task: Description of the code to write.
            path: Path to the codebase root.
            scope: "all" (default), "python", "web", or "compact".

        Returns:
            A ready-to-use system prompt string.
        """
        rules = _get_style_rules_impl(path=path, scope=scope)
        return (
            "You are a ghostwriter for this codebase. "
            "Your goal is to write code that is completely indistinguishable "
            "from code already in the repository — same naming, same structure, "
            "same patterns, same style.\n\n"
            "CODING CONVENTIONS (extracted automatically from real source):\n\n"
            f"{rules}\n\n"
            "IMPORTANT:\n"
            "- Follow the conventions above strictly.\n"
            "- Do not introduce patterns, libraries, or styles not already used.\n"
            "- Match the exact quote style, semicolon usage, and import style.\n"
            "- After generating code, verify it against the conventions using "
            "the check_code_style tool.\n\n"
            f"TASK:\n{task}"
        )

    return mcp


def run_server() -> None:
    """Entry point used by `style-dna mcp`."""
    mcp = _build_mcp()
    mcp.run(transport=os.environ.get("STYLE_DNA_MCP_TRANSPORT", "stdio"))


if __name__ == "__main__":
    run_server()
