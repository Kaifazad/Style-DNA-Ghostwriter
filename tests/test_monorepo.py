"""Tests for style_dna.monorepo (P2.2)."""

from __future__ import annotations

import json
from pathlib import Path
from style_dna.monorepo import detect_packages, analyze_monorepo, MonorepoProfile


class TestMonorepoDetection:
    def test_npm_workspaces_detected(self, tmp_path: Path):
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(json.dumps({"workspaces": ["packages/*"]}))

        pkg_a = tmp_path / "packages" / "ui"
        pkg_a.mkdir(parents=True)
        (pkg_a / "package.json").write_text(json.dumps({"name": "@repo/ui"}))

        pkg_b = tmp_path / "packages" / "api"
        pkg_b.mkdir(parents=True)
        (pkg_b / "package.json").write_text(json.dumps({"name": "@repo/api"}))

        pkgs = detect_packages(tmp_path)
        names = [name for name, _ in pkgs]
        assert "@repo/ui" in names
        assert "@repo/api" in names

    def test_pnpm_workspaces_detected(self, tmp_path: Path):
        pnpm_yaml = tmp_path / "pnpm-workspace.yaml"
        pnpm_yaml.write_text("packages:\n  - 'apps/*'\n")

        app_web = tmp_path / "apps" / "web"
        app_web.mkdir(parents=True)
        (app_web / "package.json").write_text(json.dumps({"name": "web-app"}))

        pkgs = detect_packages(tmp_path)
        names = [name for name, _ in pkgs]
        assert "web-app" in names

    def test_python_subprojects_detected(self, tmp_path: Path):
        service_a = tmp_path / "services" / "auth"
        service_a.mkdir(parents=True)
        (service_a / "pyproject.toml").write_text("[project]\nname='auth'\n")

        pkgs = detect_packages(tmp_path)
        names = [name for name, _ in pkgs]
        assert "services" in names or any("auth" in p.name for _, p in pkgs)

    def test_fallback_to_root(self, tmp_path: Path):
        pkgs = detect_packages(tmp_path)
        assert len(pkgs) == 1
        assert pkgs[0][1] == tmp_path


class TestAnalyzeMonorepo:
    def test_analyze_monorepo_builds_profiles(self, tmp_path: Path):
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(json.dumps({"workspaces": ["packages/*"]}))

        pkg_a = tmp_path / "packages" / "pkg-a"
        pkg_a.mkdir(parents=True)
        (pkg_a / "package.json").write_text(json.dumps({"name": "pkg-a"}))
        (pkg_a / "main.py").write_text("def hello_world():\n    pass\n")

        pkg_b = tmp_path / "packages" / "pkg-b"
        pkg_b.mkdir(parents=True)
        (pkg_b / "package.json").write_text(json.dumps({"name": "pkg-b"}))
        (pkg_b / "index.js").write_text("const calculate = () => 42;\n")

        mono = analyze_monorepo(str(tmp_path))
        assert isinstance(mono, MonorepoProfile)
        assert mono.total_packages >= 2
        assert mono.total_files_analyzed >= 2
        rules = mono.as_prompt_rules()
        assert "Package: pkg-a" in rules or "Package: pkg-b" in rules
        assert "Monorepo root:" in mono.summary()
