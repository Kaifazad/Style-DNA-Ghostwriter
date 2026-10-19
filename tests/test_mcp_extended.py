"""Tests for MCP server primitives: Resources, Prompts, and check_code_style tool (P1)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from style_dna.mcp_server import (
    _check_code_style_impl,
    _build_mcp,
    DEFAULT_PROFILE_PATH,
)
from style_dna.profile import StyleProfile


class TestCheckCodeStyleTool:
    def test_check_code_style_reports_clean_when_no_violations(self, tmp_path: Path):
        profile_path = tmp_path / DEFAULT_PROFILE_PATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile = StyleProfile(files_analyzed=1, function_naming="snake_case", quote_style="double")
        profile.save(profile_path)

        code = 'def compute_total(a: int, b: int) -> int:\n    return a + b\n'
        result = _check_code_style_impl(code, path=str(tmp_path), language="python")
        assert "No style violations found" in result

    def test_check_code_style_reports_violations_with_line_numbers(self, tmp_path: Path):
        profile_path = tmp_path / DEFAULT_PROFILE_PATH
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile = StyleProfile(files_analyzed=1, function_naming="snake_case")
        profile.save(profile_path)

        code = 'def calculateTotal(price, tax):\n    return price + tax\n'
        result = _check_code_style_impl(code, path=str(tmp_path), language="python")
        assert "Found 1 style violation" in result
        assert "Line 1" in result
        assert "naming.function" in result

    def test_check_code_style_handles_empty_or_missing_profile(self, tmp_path: Path):
        result = _check_code_style_impl("x = 1", path=str(tmp_path))
        assert "No style profile available" in result or "No supported source files" in result


class TestFastMCPRegistration:
    def test_build_mcp_registers_all_primitives(self):
        """Verify FastMCP registers tools, resources, and prompts when mcp is installed."""
        try:
            mcp = _build_mcp()
        except ImportError:
            pytest.skip("mcp extra is not installed in the current environment")

        # Check tool registration names
        tools = [t.name for t in mcp._tool_manager.list_tools()]
        assert "analyze_repo" in tools
        assert "get_style_rules" in tools
        assert "refresh_style_profile" in tools
        assert "check_code_style" in tools
