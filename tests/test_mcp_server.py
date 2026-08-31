"""Unit tests for Style DNA Ghostwriter MCP server tools.

Tests all exposed MCP tools:
- analyze_repo
- get_style_rules
- refresh_style_profile
"""

from pathlib import Path
import shutil
import sys
import pytest

# Allow running without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from style_dna.mcp_server import (
    analyze_repo,
    get_style_rules,
    refresh_style_profile,
    DEFAULT_PROFILE_PATH,
)
from style_dna.profile import StyleProfile

SAMPLE_REPO = Path(__file__).resolve().parents[1] / "examples" / "sample_repo"
SAMPLE_WEB_REPO = Path(__file__).resolve().parents[1] / "examples" / "sample_web_repo"


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary copy of sample_repo to test caching and profile mutations."""
    dst = tmp_path / "repo"
    shutil.copytree(SAMPLE_REPO, dst)
    return dst


class TestAnalyzeRepo:
    def test_analyze_repo_empty_dir(self, tmp_path):
        result = analyze_repo(str(tmp_path), save=False)
        assert "No supported source files found" in result

    def test_analyze_repo_runs_and_extracts_rules(self, temp_repo):
        result = analyze_repo(str(temp_repo), save=False)
        assert "Analyzed 2 files" in result
        assert "Name functions and variables in snake_case" in result

    def test_analyze_repo_saves_cache_profile(self, temp_repo):
        profile_path = temp_repo / DEFAULT_PROFILE_PATH
        assert not profile_path.exists()

        result = analyze_repo(str(temp_repo), save=True)
        assert profile_path.exists()
        assert "Analyzed 2 files" in result

    def test_analyze_repo_uses_cached_profile(self, temp_repo):
        profile_path = temp_repo / DEFAULT_PROFILE_PATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        fake_profile = StyleProfile(files_analyzed=99)
        fake_profile.save(profile_path)

        result = analyze_repo(str(temp_repo), force=False)
        assert "Loaded cached profile" in result
        assert "99 files analyzed" in result

    def test_analyze_repo_force_flag_bypasses_cache(self, temp_repo):
        profile_path = temp_repo / DEFAULT_PROFILE_PATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        fake_profile = StyleProfile(files_analyzed=99)
        fake_profile.save(profile_path)

        result = analyze_repo(str(temp_repo), force=True)
        assert "Analyzed 2 files" in result
        assert "Loaded cached profile" not in result


class TestGetStyleRules:
    def test_get_style_rules_empty_dir(self, tmp_path):
        result = get_style_rules(str(tmp_path))
        assert "No supported source files found" in result

    def test_get_style_rules_fresh_analysis(self, temp_repo):
        result = get_style_rules(str(temp_repo))
        assert "Name functions and variables in snake_case" in result

    def test_get_style_rules_uses_cached_profile(self, temp_repo):
        profile_path = temp_repo / DEFAULT_PROFILE_PATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        fake_profile = StyleProfile(files_analyzed=1, function_naming="camelCase")
        fake_profile.save(profile_path)

        result = get_style_rules(str(temp_repo))
        assert "Name functions and variables in camelCase" in result


class TestRefreshStyleProfile:
    def test_refresh_style_profile_creates_and_overwrites_cache(self, temp_repo):
        profile_path = temp_repo / DEFAULT_PROFILE_PATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        fake_profile = StyleProfile(files_analyzed=1)
        fake_profile.save(profile_path)

        result = refresh_style_profile(str(temp_repo))
        assert "Refreshed profile from 2 files" in result

        # Verify disk cache was overwritten with actual codebase analysis
        loaded = StyleProfile.load(profile_path)
        assert loaded.files_analyzed == 2
        assert loaded.function_naming == "snake_case"
