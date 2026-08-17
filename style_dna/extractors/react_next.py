"""Extracts React and Next.js conventions from source files and project structure.

Detects: App Router vs Pages Router, Server/Client Components, component
style, hooks patterns, state management libraries, and framework detection.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


# ── Regex patterns ────────────────────────────────────────────────

_USE_CLIENT = re.compile(r"""^['"]use client['"];?\s*$""", re.MULTILINE)
_USE_SERVER = re.compile(r"""^['"]use server['"];?\s*$""", re.MULTILINE)

# Component definitions
_ARROW_COMPONENT = re.compile(
    r"(?:export\s+)?(?:default\s+)?(?:const|let)\s+([A-Z]\w+)\s*"
    r"(?::\s*React\.FC\w*(?:<[^>]*>)?\s*)?=\s*(?:\([^)]*\)|[a-zA-Z_$]\w*)\s*=>"
)
_FUNC_COMPONENT = re.compile(
    r"(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)\s*\("
)

# Custom hooks
_CUSTOM_HOOK = re.compile(r"(?:export\s+)?(?:const|function)\s+(use[A-Z]\w+)")

# State management imports
_STATE_MGMT_PATTERNS = {
    "zustand": re.compile(r"""from\s+['"]zustand['"]"""),
    "redux": re.compile(r"""from\s+['"](?:react-redux|@reduxjs/toolkit)['"]"""),
    "context": re.compile(r"(?:createContext|useContext)\s*(?:\(|<)"),
    "tanstack_query": re.compile(r"""from\s+['"]@tanstack/react-query['"]"""),
    "swr": re.compile(r"""from\s+['"]swr['"]"""),
    "jotai": re.compile(r"""from\s+['"]jotai['"]"""),
    "recoil": re.compile(r"""from\s+['"]recoil['"]"""),
}

# Framework detection via package.json dependencies
_FRAMEWORK_KEYS = {
    "next": "Next.js",
    "react": "React",
    "react-dom": "React DOM",
    "vue": "Vue.js",
    "nuxt": "Nuxt.js",
    "@angular/core": "Angular",
    "svelte": "Svelte",
    "astro": "Astro",
    "tailwindcss": "Tailwind CSS",
    "styled-components": "Styled Components",
    "@emotion/react": "Emotion",
    "typescript": "TypeScript",
    "prisma": "Prisma",
    "drizzle-orm": "Drizzle ORM",
    "@trpc/server": "tRPC",
    "express": "Express",
    "fastify": "Fastify",
    "vite": "Vite",
    "webpack": "Webpack",
}


def _detect_frameworks(root: Path) -> list[str]:
    """Read package.json to detect frameworks and tools."""
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return []

    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return []

    all_deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        all_deps.update(data.get(key, {}))

    detected = []
    for pkg, label in _FRAMEWORK_KEYS.items():
        if pkg in all_deps:
            detected.append(label)
    return detected


def _detect_nextjs_router(root: Path) -> str:
    """Detect whether a Next.js project uses App Router or Pages Router."""
    # App Router: presence of app/ directory with layout or page files
    app_dir = root / "app"
    src_app_dir = root / "src" / "app"
    pages_dir = root / "pages"
    src_pages_dir = root / "src" / "pages"

    has_app = (
        (app_dir.is_dir() and any(app_dir.rglob("page.*")))
        or (src_app_dir.is_dir() and any(src_app_dir.rglob("page.*")))
    )
    has_pages = (
        (pages_dir.is_dir() and any(pages_dir.rglob("*.tsx")))
        or (pages_dir.is_dir() and any(pages_dir.rglob("*.jsx")))
        or (src_pages_dir.is_dir() and any(src_pages_dir.rglob("*.tsx")))
    )

    if has_app:
        return "app_router"
    if has_pages:
        return "pages_router"
    return "none"


def _detect_component_file_naming(paths: list[Path]) -> str:
    """Detect how component files are named (PascalCase, kebab-case, etc.)."""
    pascal = 0
    kebab = 0
    index_files = 0

    for p in paths:
        stem = p.stem
        if stem == "index":
            index_files += 1
            continue
        if re.match(r"^[A-Z][a-zA-Z0-9]*$", stem):
            pascal += 1
        elif re.match(r"^[a-z]+(-[a-z]+)+$", stem):
            kebab += 1

    if pascal > kebab and pascal > index_files:
        return "PascalCase"
    if kebab > pascal:
        return "kebab-case"
    if index_files > pascal:
        return "index.tsx barrels"
    return "unknown"


def extract_react_next(
    sources: list[str],
    paths: list[Path],
    root: Path,
) -> dict:
    """Extract React and Next.js conventions.

    Args:
        sources: Raw source contents of .jsx/.tsx/.js/.ts files.
        paths: Corresponding file paths.
        root: Project root directory.

    Returns:
        Dict of React/Next.js-related StyleProfile fields.
    """
    use_client_count = 0
    use_server_count = 0
    total_components = 0
    arrow_components = 0
    func_components = 0
    custom_hooks: list[str] = []
    state_mgmt_hits: Counter[str] = Counter()

    component_paths: list[Path] = []

    for src, path in zip(sources, paths):
        # Only analyze JSX/TSX or JS/TS files
        if path.suffix not in (".jsx", ".tsx", ".js", ".ts"):
            continue

        # ── use client / use server ──
        if _USE_CLIENT.search(src):
            use_client_count += 1
        if _USE_SERVER.search(src):
            use_server_count += 1

        # ── Component definitions ──
        arrow_matches = _ARROW_COMPONENT.findall(src)
        func_matches = _FUNC_COMPONENT.findall(src)
        arrow_components += len(arrow_matches)
        func_components += len(func_matches)
        if arrow_matches or func_matches:
            total_components += 1
            component_paths.append(path)

        # ── Custom hooks ──
        for hook in _CUSTOM_HOOK.findall(src):
            if hook not in custom_hooks:
                custom_hooks.append(hook)

        # ── State management ──
        for name, pattern in _STATE_MGMT_PATTERNS.items():
            if pattern.search(src):
                state_mgmt_hits[name] += 1

    # ── Derive values ──
    total_cmp_defs = arrow_components + func_components
    if total_cmp_defs > 2:
        ratio = arrow_components / total_cmp_defs
        react_component_style = "arrow" if ratio > 0.65 else ("function" if ratio < 0.35 else "mixed")
    else:
        react_component_style = "unknown"

    total_files = len(sources)
    react_use_client_rate = use_client_count / total_files if total_files > 0 else 0.0
    react_use_server_rate = use_server_count / total_files if total_files > 0 else 0.0

    # Component file naming
    react_component_naming = _detect_component_file_naming(component_paths)

    # State management: pick the most-used
    react_state_management = state_mgmt_hits.most_common(1)[0][0] if state_mgmt_hits else "none"

    # Hooks patterns (limit to top 10)
    react_hooks_patterns = custom_hooks[:10]

    # Frameworks
    web_frameworks = _detect_frameworks(root)

    # Next.js router
    nextjs_router = "none"
    if any("Next" in f for f in web_frameworks):
        nextjs_router = _detect_nextjs_router(root)

    return {
        "nextjs_router": nextjs_router,
        "react_component_style": react_component_style,
        "react_component_naming": react_component_naming,
        "react_use_client_rate": round(react_use_client_rate, 2),
        "react_use_server_rate": round(react_use_server_rate, 2),
        "react_hooks_patterns": react_hooks_patterns,
        "react_state_management": react_state_management,
        "web_frameworks": web_frameworks,
    }
