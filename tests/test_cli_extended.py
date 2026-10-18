"""Tests for CLI check and monorepo commands (P1.2, P2.2)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from style_dna.cli import main
from style_dna.profile import StyleProfile


class TestCliCheck:
    def test_cli_check_success_exits_0(self, tmp_path: Path, capsys):
        # Create profile
        profile_dir = tmp_path / ".style-dna"
        profile_dir.mkdir()
        profile = StyleProfile(function_naming="snake_case")
        profile.save(profile_dir / "style_profile.json")

        # Create valid source
        src = tmp_path / "valid.py"
        src.write_text("def my_func():\n    pass\n")

        with pytest.raises(SystemExit) as excinfo:
            main(["check", str(src)])
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "No style violations found" in captured.out

    def test_cli_check_with_explicit_profile(self, tmp_path: Path, capsys):
        custom_prof = tmp_path / "my_profile.json"
        profile = StyleProfile(function_naming="snake_case")
        profile.save(custom_prof)

        src = tmp_path / "component.js"
        src.write_text("const a = 1;\n")

        with pytest.raises(SystemExit) as excinfo:
            main(["check", str(src), "--profile", str(custom_prof), "--lang", "js"])
        assert excinfo.value.code == 0


class TestCliMonorepo:
    def test_cli_monorepo_prints_summary(self, tmp_path: Path, capsys):
        pkg = tmp_path / "packages" / "core"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text(json.dumps({"name": "core"}))
        (pkg / "util.py").write_text("def run_util():\n    pass\n")

        root_pkg = tmp_path / "package.json"
        root_pkg.write_text(json.dumps({"workspaces": ["packages/*"]}))

        main(["monorepo", str(tmp_path)])
        captured = capsys.readouterr()
        assert "Monorepo root:" in captured.out
        assert "Packages detected:" in captured.out
