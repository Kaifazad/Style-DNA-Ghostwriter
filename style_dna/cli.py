"""Command-line interface for Style DNA Ghostwriter.

Usage:
    style-dna init [path]                         # analyze + write convention files
    style-dna analyze <path> [--out profile.json]
    style-dna show <profile.json> [--format text|json]
    style-dna generate <profile.json> "<task>"    # AI ghostwriter (needs anthropic)
    style-dna check <file> [--profile profile.json] [--lang auto]  # P1.2
    style-dna monorepo <path> [--out dir]         # P2.2
    style-dna mcp                                 # MCP stdio server
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
            f"No supported source files found under '{root}' "
            "(Python, JS/TS, React, Next.js, CSS, HTML). Nothing to write.",
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


def cmd_check(args: argparse.Namespace) -> None:
    """P1.2: Verify a source file against extracted style conventions."""
    from .verifier import check_code_style  # deferred

    # Load code
    source_path = Path(args.file)
    try:
        code = source_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        print(f"Error reading '{args.file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Load profile
    if args.profile:
        try:
            profile = StyleProfile.load(args.profile)
        except ValueError as e:
            print(f"Error loading profile: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Auto-discover: walk up from the file looking for .style-dna/
        search_root = source_path.resolve().parent
        found = None
        for ancestor in [search_root, *search_root.parents]:
            candidate = ancestor / ".style-dna" / "style_profile.json"
            if candidate.exists():
                found = candidate
                break
        if found is None:
            print(
                "No style profile found. Run 'style-dna init' or pass --profile.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            profile = StyleProfile.load(found)
        except ValueError as e:
            print(f"Error loading profile: {e}", file=sys.stderr)
            sys.exit(1)

    # Detect language from extension if not provided
    language = args.lang
    if language == "auto":
        ext_map = {
            ".py": "python",
            ".js": "js", ".jsx": "jsx", ".mjs": "js", ".cjs": "js",
            ".ts": "ts", ".tsx": "tsx",
        }
        language = ext_map.get(source_path.suffix.lower(), "auto")

    violations = check_code_style(code, profile, language=language)

    if not violations:
        print(f"PASS: {source_path.name} - No style violations found.")
        sys.exit(0)

    print(f"FAIL: {source_path.name} - {len(violations)} violation(s) found:\n")
    for v in violations:
        loc = f"line {v.line}" if v.line > 0 else "file"
        tag = {"error": "[ERROR]", "warning": "[WARN] ", "info": "[INFO] "}.get(v.severity, "[INFO] ")
        print(f"  {tag} {loc} [{v.rule}] {v.message}")

    sys.exit(1 if any(v.severity == "error" for v in violations) else 0)


def cmd_monorepo(args: argparse.Namespace) -> None:
    """P2.2: Analyze all packages in a monorepo."""
    from .monorepo import analyze_monorepo  # deferred

    mono = analyze_monorepo(args.path)

    print(mono.summary())
    print()

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for pkg in mono.packages:
            if pkg.profile.total_files_analyzed == 0:
                continue
            safe_name = pkg.name.replace("/", "__").replace("@", "")
            out_file = out_dir / f"{safe_name}.json"
            pkg.profile.save(out_file)
            print(f"  Saved {pkg.name} → {out_file}")
        print(f"\nAll profiles written to: {args.out}")
    else:
        print(mono.as_prompt_rules())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="style-dna", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    # ── init ──────────────────────────────────────────────────────
    p_init = sub.add_parser(
        "init",
        help="One-shot setup: analyze the repo and write rules into CLAUDE.md/AGENTS.md/.cursorrules/etc.",
    )
    p_init.add_argument("path", nargs="?", default=".", help="Path to the project root (default: cwd)")
    p_init.set_defaults(func=cmd_init)

    # ── mcp ───────────────────────────────────────────────────────
    p_mcp = sub.add_parser("mcp", help="Run as an MCP server (stdio) for MCP-compatible agents")
    p_mcp.set_defaults(func=cmd_mcp)

    # ── analyze ───────────────────────────────────────────────────
    p_analyze = sub.add_parser("analyze", help="Analyze a codebase and build a style profile")
    p_analyze.add_argument("path", help="Path to the codebase root")
    p_analyze.add_argument("--out", help="Where to save the style_profile.json", default=None)
    p_analyze.add_argument("--max-files", type=int, default=300, help="Max files to parse")
    p_analyze.set_defaults(func=cmd_analyze)

    # ── show ──────────────────────────────────────────────────────
    p_show = sub.add_parser("show", help="Print a saved style profile as plain-English rules")
    p_show.add_argument("profile", help="Path to style_profile.json")
    p_show.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default) for plain-English rules, 'json' for raw profile data",
    )
    p_show.set_defaults(func=cmd_show)

    # ── generate ──────────────────────────────────────────────────
    p_generate = sub.add_parser("generate", help="Generate code matching a style profile")
    p_generate.add_argument("profile", help="Path to style_profile.json")
    p_generate.add_argument("task", help="Description of the code to generate")
    p_generate.add_argument("--out", help="Write generated code to this file", default=None)
    p_generate.add_argument("--model", default="claude-sonnet-4-6", help="Model to use")
    p_generate.set_defaults(func=cmd_generate)

    # ── check (P1.2) ──────────────────────────────────────────────
    p_check = sub.add_parser(
        "check",
        help="Check a source file against extracted style conventions (P1)",
    )
    p_check.add_argument("file", help="Path to the source file to check")
    p_check.add_argument(
        "--profile",
        default=None,
        help="Path to style_profile.json (auto-discovered if omitted)",
    )
    p_check.add_argument(
        "--lang",
        default="auto",
        choices=["auto", "python", "js", "ts", "tsx", "jsx"],
        help="Language of the file (default: auto-detect from extension)",
    )
    p_check.set_defaults(func=cmd_check)

    # ── monorepo (P2.2) ───────────────────────────────────────────
    p_mono = sub.add_parser(
        "monorepo",
        help="Analyze all packages in a monorepo and print per-package style rules (P2)",
    )
    p_mono.add_argument("path", nargs="?", default=".", help="Path to monorepo root (default: cwd)")
    p_mono.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help="Save per-package style_profile.json files into this directory",
    )
    p_mono.set_defaults(func=cmd_monorepo)

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
