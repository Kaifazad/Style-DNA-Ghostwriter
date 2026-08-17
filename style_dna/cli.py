"""Command-line interface for Style DNA Ghostwriter.

Usage:
    style-dna analyze <path_to_codebase> [--out profile.json]
    style-dna show <profile.json>
    style-dna generate <profile.json> "<task description>" [--out result.py]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import analyze_codebase
from .profile import StyleProfile


def cmd_init(args: argparse.Namespace) -> None:
    from .conventions import write_convention_files, MCP_CONFIG_SNIPPET

    root = Path(args.path)
    profile = analyze_codebase(str(root))
    if profile.total_files_analyzed == 0:
        print(
            f"No supported source files found under '{root}' (Python, JS/TS, React, Next.js, CSS, HTML). Nothing to write.",
            file=sys.stderr,
        )
        sys.exit(1)

    profile_path = root / ".style-dna" / "style_profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile.save(profile_path)

    written = write_convention_files(root, profile)

    print(
        f"Analyzed {profile.total_files_analyzed} files from '{root}' "
        f"({profile.files_analyzed} Python, {profile.web_files_analyzed} Web)."
    )
    print(f"Profile saved to: {profile_path}\n")
    print("Style rules written into (auto-read by most coding agents):")
    for f in written:
        print(f"  - {f}")
    print(
        "\nFor agents that speak MCP (Claude Code, etc.), add this server to "
        "their MCP config so they can pull live rules instead of a static file:\n"
    )
    print(MCP_CONFIG_SNIPPET)


def cmd_mcp(args: argparse.Namespace) -> None:
    from .mcp_server import run_server

    run_server()


def cmd_analyze(args: argparse.Namespace) -> None:
    profile = analyze_codebase(args.path, max_files=args.max_files)
    out_path = args.out or "style_profile.json"
    profile.save(out_path)
    print(
        f"Analyzed {profile.total_files_analyzed} files from '{args.path}' "
        f"({profile.files_analyzed} Python, {profile.web_files_analyzed} Web)."
    )
    print(f"Style profile saved to: {out_path}\n")
    print(profile.as_prompt_rules())


def cmd_show(args: argparse.Namespace) -> None:
    profile = StyleProfile.load(args.profile)
    if args.format == "json":
        print(profile.to_json())
    else:
        print(profile.as_prompt_rules())


def cmd_generate(args: argparse.Namespace) -> None:
    from .generator import generate_code  # deferred import: anthropic is optional

    profile = StyleProfile.load(args.profile)
    code = generate_code(profile, args.task, model=args.model)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Generated code written to: {args.out}")
    else:
        print(code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="style-dna", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help="One-shot setup: analyze the repo and write rules into CLAUDE.md/AGENTS.md/.cursorrules/etc.",
    )
    p_init.add_argument("path", nargs="?", default=".", help="Path to the project root (default: cwd)")
    p_init.set_defaults(func=cmd_init)

    p_mcp = sub.add_parser("mcp", help="Run as an MCP server (stdio) for MCP-compatible agents")
    p_mcp.set_defaults(func=cmd_mcp)

    p_analyze = sub.add_parser("analyze", help="Analyze a codebase and build a style profile")
    p_analyze.add_argument("path", help="Path to the codebase root")
    p_analyze.add_argument("--out", help="Where to save the style_profile.json", default=None)
    p_analyze.add_argument("--max-files", type=int, default=300, help="Max files to parse")
    p_analyze.set_defaults(func=cmd_analyze)

    p_show = sub.add_parser("show", help="Print a saved style profile as plain-English rules")
    p_show.add_argument("profile", help="Path to style_profile.json")
    p_show.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default) for plain-English rules, 'json' for raw profile data",
    )
    p_show.set_defaults(func=cmd_show)

    p_generate = sub.add_parser("generate", help="Generate code matching a style profile")
    p_generate.add_argument("profile", help="Path to style_profile.json")
    p_generate.add_argument("task", help="Description of the code to generate")
    p_generate.add_argument("--out", help="Write generated code to this file", default=None)
    p_generate.add_argument("--model", default="claude-sonnet-4-6", help="Model to use")
    p_generate.set_defaults(func=cmd_generate)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # noqa: BLE001 - top-level CLI error boundary
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
