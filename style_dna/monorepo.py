"""Monorepo-aware analysis: detects sub-packages and analyzes each one.

P2: Supports common monorepo layouts so Style DNA profiles per-package
instead of forcing one flat profile for the whole tree.

Detected workspace configs:
  - npm/Yarn workspaces  (``package.json`` ``"workspaces"`` field)
  - pnpm                 (``pnpm-workspace.yaml``)
  - Lerna                (``lerna.json``)
  - Nx                   (``nx.json`` ``"projects"`` dict)
  - Python sub-packages  (any sub-dir with ``pyproject.toml`` or ``setup.py``)

Falls back to treating the root as a single "package" if nothing is detected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .analyzer import analyze_codebase
from .profile import StyleProfile


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PackageProfile:
    """A style profile for one package within a monorepo."""

    name: str
    path: str
    profile: StyleProfile


@dataclass
class MonorepoProfile:
    """An aggregate style profile across all packages in a monorepo."""

    root: str
    packages: list[PackageProfile] = field(default_factory=list)

    @property
    def total_packages(self) -> int:
        return len(self.packages)

    @property
    def total_files_analyzed(self) -> int:
        return sum(p.profile.total_files_analyzed for p in self.packages)

    def as_prompt_rules(self) -> str:
        """Render per-package rules, indented under their package name."""
        active = [p for p in self.packages if p.profile.total_files_analyzed > 0]
        if not active:
            return "No packages with source files found in this monorepo."
        sections = []
        for pkg in active:
            sections.append(f"### Package: {pkg.name}\n{pkg.profile.as_prompt_rules()}")
        return "\n\n".join(sections)

    def summary(self) -> str:
        active = sum(1 for p in self.packages if p.profile.total_files_analyzed > 0)
        return (
            f"Monorepo root: {self.root}\n"
            f"Packages detected: {self.total_packages} "
            f"({active} with source files, "
            f"{self.total_files_analyzed} total files analyzed)"
        )


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_monorepo(path: str, max_files_per_package: int = 300) -> MonorepoProfile:
    """Analyze all packages in a monorepo and return an aggregate profile.

    Args:
        path: Path to the monorepo root.
        max_files_per_package: Max files to parse per sub-package.

    Returns:
        A :class:`MonorepoProfile` with per-package :class:`StyleProfile`\\s.
    """
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"No such path: {path}")

    detected = detect_packages(root)
    package_profiles: list[PackageProfile] = []

    for name, pkg_path in detected:
        try:
            profile = analyze_codebase(str(pkg_path), max_files=max_files_per_package)
        except Exception:
            profile = StyleProfile(source_path=str(pkg_path), files_analyzed=0)
        package_profiles.append(
            PackageProfile(name=name, path=str(pkg_path), profile=profile)
        )

    return MonorepoProfile(root=str(root), packages=package_profiles)


def detect_packages(root: Path) -> list[tuple[str, Path]]:
    """Return ``(name, path)`` pairs for each detected sub-package.

    The list is de-duplicated by resolved path.  If no workspace config is
    found the function returns ``[(root.name, root)]`` so callers always get
    at least one package.

    Args:
        root: Resolved absolute path to the monorepo root.

    Returns:
        List of ``(package_name, package_path)`` tuples.
    """
    packages: list[tuple[str, Path]] = []
    seen: set[Path] = set()

    def _add(name: str, pkg_path: Path) -> None:
        resolved = pkg_path.resolve()
        if resolved not in seen and pkg_path.exists() and pkg_path.is_dir():
            seen.add(resolved)
            packages.append((name, pkg_path))

    from .analyzer import DEFAULT_IGNORE_DIRS

    # ── pnpm-workspace.yaml ───────────────────────────────────────
    pnpm_ws = root / "pnpm-workspace.yaml"
    if pnpm_ws.exists():
        globs = _read_pnpm_workspace(pnpm_ws)
        for pattern in globs:
            for p in root.glob(pattern):
                if p.is_dir():
                    _add(_pkg_name(p), p)

    # ── package.json workspaces ───────────────────────────────────
    root_pkg = root / "package.json"
    if root_pkg.exists():
        ws_globs = _read_npm_workspaces(root_pkg)
        for pattern in ws_globs:
            for p in root.glob(pattern):
                if p.is_dir():
                    _add(_pkg_name(p), p)

    # ── lerna.json ────────────────────────────────────────────────
    lerna = root / "lerna.json"
    if lerna.exists():
        try:
            data = json.loads(lerna.read_text(encoding="utf-8"))
            for pattern in data.get("packages", ["packages/*"]):
                for p in root.glob(pattern):
                    if p.is_dir():
                        _add(_pkg_name(p), p)
        except Exception:
            pass

    # ── nx.json ───────────────────────────────────────────────────
    nx_json = root / "nx.json"
    if nx_json.exists():
        try:
            data = json.loads(nx_json.read_text(encoding="utf-8"))
            for name, cfg in data.get("projects", {}).items():
                if isinstance(cfg, str):
                    _add(str(name), root / cfg)
                elif isinstance(cfg, dict):
                    _add(str(name), root / cfg.get("root", name))
        except Exception:
            pass

    # ── Python sub-packages ───────────────────────────────────────
    for manifest_name in ("pyproject.toml", "setup.py"):
        for manifest in root.glob(f"**/{manifest_name}"):
            parent = manifest.parent
            if parent == root:
                continue
            if any(part in DEFAULT_IGNORE_DIRS for part in parent.parts):
                continue
            _add(parent.name, parent)

    # ── Fallback: single-package repo ─────────────────────────────
    if not packages:
        _add(root.name or "root", root)

    return packages


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pkg_name(p: Path) -> str:
    """Get package name from ``package.json`` or directory name."""
    pkg_json = p / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            if name := data.get("name"):
                return str(name)
        except Exception:
            pass
    return p.name


def _read_pnpm_workspace(path: Path) -> list[str]:
    """Parse ``pnpm-workspace.yaml`` and return workspace glob patterns."""
    try:
        # Try PyYAML first, fall back to a naïve line-based parser
        import yaml  # type: ignore[import-untyped]
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data.get("packages", []) if isinstance(data, dict) else []
    except ImportError:
        pass
    except Exception:
        return []
    # Naïve YAML parser: handle simple list items under 'packages:'
    globs: list[str] = []
    in_packages = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "packages:":
            in_packages = True
            continue
        if in_packages:
            stripped = line.strip()
            if stripped.startswith("-"):
                globs.append(stripped.lstrip("- ").strip().strip("'\""))
            elif stripped and not stripped.startswith("#"):
                break  # new top-level key
    return globs


def _read_npm_workspaces(path: Path) -> list[str]:
    """Parse ``package.json`` and return workspace glob patterns."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ws = data.get("workspaces", [])
        if isinstance(ws, dict):
            ws = ws.get("packages", [])
        return ws if isinstance(ws, list) else []
    except Exception:
        return []
