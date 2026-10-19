"""Tests for scoped rules, stale profile detection, and pre-commit hook commands."""

from __future__ import annotations

import datetime
from pathlib import Path
import pytest

from style_dna.cli import main
from style_dna.profile import StyleProfile


class TestScopedRules:
    def test_scope_compact_renders_dense_summary(self):
        profile = StyleProfile(
            files_analyzed=10,
            web_files_analyzed=15,
            function_naming="snake_case",
            type_hint_coverage=0.8,
            nextjs_router="app_router",
            react_component_style="arrow",
            react_state_management="zustand",
            styling_approach="tailwind",
            js_quote_style="single",
            js_semicolons="never",
            ts_type_style="interface",
        )
        compact = profile.as_prompt_rules(scope="compact")
        assert "Style DNA (Compact)" in compact
        assert "Python: snake_case" in compact
        assert "Next.js App Router" in compact
        assert "prefer interface" in compact
        # Should be very short (under 600 characters)
        assert len(compact) < 600

    def test_scope_python_omits_web(self):
        profile = StyleProfile(
            files_analyzed=5,
            web_files_analyzed=10,
            function_naming="snake_case",
            nextjs_router="app_router",
        )
        py_rules = profile.as_prompt_rules(scope="python")
        assert "snake_case" in py_rules
        assert "App Router" not in py_rules

    def test_scope_web_omits_python(self):
        profile = StyleProfile(
            files_analyzed=5,
            web_files_analyzed=10,
            function_naming="snake_case",
            nextjs_router="app_router",
        )
        web_rules = profile.as_prompt_rules(scope="web")
        assert "App Router" in web_rules
        assert "Python Conventions" not in web_rules

    def test_mixed_resolution_provides_direction(self):
        profile = StyleProfile(
            web_files_analyzed=5,
            react_component_style="mixed",
            js_function_style="mixed",
            ts_type_style="mixed",
        )
        rules = profile.as_prompt_rules(scope="web")
        assert "prefer arrow functions" in rules
        assert "prefer `interface`" in rules


class TestStaleProfileDetection:
    def test_stale_profile_detected(self):
        # 40 days ago
        old_time = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=40)
        ).isoformat()
        profile = StyleProfile(created_at=old_time)
        assert profile.is_stale(max_days=30) is True

    def test_fresh_profile_not_stale(self):
        now_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        profile = StyleProfile(created_at=now_time)
        assert profile.is_stale(max_days=30) is False

    def test_missing_timestamp_not_stale(self):
        profile = StyleProfile(created_at="")
        assert profile.is_stale(max_days=30) is False


class TestGitHookCli:
    def test_hook_install_and_uninstall(self, tmp_path: Path, capsys):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Install
        main(["hook", "install", str(tmp_path)])
        captured = capsys.readouterr()
        assert "PASS: Style DNA pre-commit hook installed" in captured.out
        hook_path = git_dir / "hooks" / "pre-commit"
        assert hook_path.exists()
        content = hook_path.read_text(encoding="utf-8")
        assert "style-dna check" in content

        # Uninstall
        main(["hook", "uninstall", str(tmp_path)])
        captured = capsys.readouterr()
        assert "Uninstalled" in captured.out
        assert not hook_path.exists()

    def test_hook_install_fails_outside_git(self, tmp_path: Path, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(["hook", "install", str(tmp_path)])
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "not a git repository" in captured.err
