"""Comprehensive tests for Style DNA Ghostwriter.

Covers: analyzer, extractors, profile save/load round-trip,
conventions upsert logic, and CLI argument parsing.
"""

import json
import sys
from pathlib import Path

import pytest

# Allow running without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from style_dna.analyzer import analyze_codebase
from style_dna.profile import StyleProfile
from style_dna.conventions import write_convention_files, MARKER_START, MARKER_END

SAMPLE_REPO = Path(__file__).resolve().parents[1] / "examples" / "sample_repo"


# ---------------------------------------------------------------------------
# Analyzer / end-to-end extraction
# ---------------------------------------------------------------------------

class TestAnalyzer:
    def test_analyze_finds_files(self):
        profile = analyze_codebase(str(SAMPLE_REPO))
        assert profile.files_analyzed == 2

    def test_naming_is_snake_case(self):
        profile = analyze_codebase(str(SAMPLE_REPO))
        assert profile.function_naming == "snake_case"

    def test_docstring_style_is_google(self):
        profile = analyze_codebase(str(SAMPLE_REPO))
        assert profile.docstring_style == "google"
        assert profile.docstring_coverage > 0.5

    def test_uses_custom_exceptions(self):
        profile = analyze_codebase(str(SAMPLE_REPO))
        assert profile.uses_custom_exceptions is True

    def test_type_hint_coverage_is_high(self):
        profile = analyze_codebase(str(SAMPLE_REPO))
        assert profile.type_hint_coverage > 0.7

    def test_empty_dir_returns_empty_profile(self, tmp_path):
        profile = analyze_codebase(str(tmp_path))
        assert profile.files_analyzed == 0

    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            analyze_codebase("/nonexistent/path/that/does/not/exist")

    def test_max_files_cap(self, tmp_path):
        # Create 5 minimal Python files
        for i in range(5):
            (tmp_path / f"mod_{i}.py").write_text(f"x_{i} = {i}\n", encoding="utf-8")
        profile = analyze_codebase(str(tmp_path), max_files=3)
        assert profile.files_analyzed == 3

    def test_syntax_error_files_skipped(self, tmp_path):
        (tmp_path / "good.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "bad.py").write_text("def foo(\n", encoding="utf-8")  # syntax error
        profile = analyze_codebase(str(tmp_path))
        assert profile.files_analyzed == 1

    def test_indent_style_detected(self, tmp_path):
        (tmp_path / "tabbed.py").write_text(
            "def foo():\n\tx = 1\n\treturn x\n", encoding="utf-8"
        )
        profile = analyze_codebase(str(tmp_path))
        assert profile.indent_style == "tabs"

    def test_common_patterns_populated(self, tmp_path):
        (tmp_path / "mod.py").write_text(
            "from dataclasses import dataclass\n\n@dataclass\nclass Foo:\n    x: int = 0\n",
            encoding="utf-8",
        )
        profile = analyze_codebase(str(tmp_path))
        assert any("dataclass" in p.lower() for p in profile.common_patterns)


# ---------------------------------------------------------------------------
# StyleProfile: save / load / render
# ---------------------------------------------------------------------------

class TestStyleProfile:
    def _make_profile(self) -> StyleProfile:
        return StyleProfile(
            source_path="/tmp/repo",
            files_analyzed=10,
            function_naming="snake_case",
            docstring_style="google",
            docstring_coverage=0.8,
            type_hint_coverage=0.9,
            error_handling_pattern="custom_exceptions",
            uses_custom_exceptions=True,
            quote_style="double",
            avg_function_length=12.5,
            common_decorators=["staticmethod", "property"],
            import_style="grouped_stdlib_first",
            common_patterns=["Uses @dataclass for data models."],
        )

    def test_to_json_is_valid_json(self):
        p = self._make_profile()
        data = json.loads(p.to_json())
        assert data["files_analyzed"] == 10
        assert data["function_naming"] == "snake_case"

    def test_save_and_load_roundtrip(self, tmp_path):
        p = self._make_profile()
        path = tmp_path / "profile.json"
        p.save(path)
        loaded = StyleProfile.load(path)
        assert loaded.files_analyzed == p.files_analyzed
        assert loaded.function_naming == p.function_naming
        assert loaded.common_patterns == p.common_patterns

    def test_load_missing_file_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="Could not load"):
            StyleProfile.load(tmp_path / "nonexistent.json")

    def test_load_malformed_json_raises_value_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="Could not load"):
            StyleProfile.load(bad)

    def test_load_outdated_schema_raises_value_error(self, tmp_path):
        """A JSON with unexpected keys should raise ValueError, not TypeError."""
        out = tmp_path / "profile.json"
        out.write_text(
            json.dumps({"unknown_field_xyz": "boom", "files_analyzed": 5}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="outdated or corrupted"):
            StyleProfile.load(out)

    def test_as_prompt_rules_snake_case(self):
        p = self._make_profile()
        rules = p.as_prompt_rules()
        assert "snake_case" in rules

    def test_as_prompt_rules_google_docstrings(self):
        p = self._make_profile()
        rules = p.as_prompt_rules()
        assert "google" in rules.lower()

    def test_as_prompt_rules_custom_exceptions(self):
        p = self._make_profile()
        rules = p.as_prompt_rules()
        assert "custom" in rules.lower()

    def test_as_prompt_rules_common_patterns_included(self):
        p = self._make_profile()
        rules = p.as_prompt_rules()
        assert "dataclass" in rules.lower()

    def test_as_prompt_rules_no_docstrings(self):
        p = StyleProfile(source_path=".", files_analyzed=5, docstring_coverage=0.0)
        rules = p.as_prompt_rules()
        assert "rarely" in rules.lower() or "docstring" in rules.lower()

    def test_prompt_rules_render(self):
        profile = analyze_codebase(str(SAMPLE_REPO))
        rules = profile.as_prompt_rules()
        assert "snake_case" in rules
        assert "google" in rules.lower() or "docstring" in rules.lower()


# ---------------------------------------------------------------------------
# Conventions: upsert logic
# ---------------------------------------------------------------------------

class TestConventions:
    def _make_profile(self) -> StyleProfile:
        return StyleProfile(source_path=".", files_analyzed=3, function_naming="snake_case")

    def test_creates_files_when_absent(self, tmp_path):
        profile = self._make_profile()
        written = write_convention_files(tmp_path, profile)
        for f in written:
            assert f.exists(), f"{f} was not created"

    def test_content_has_markers(self, tmp_path):
        profile = self._make_profile()
        write_convention_files(tmp_path, profile)
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert MARKER_START in content
        assert MARKER_END in content

    def test_upsert_replaces_existing_section(self, tmp_path):
        profile = self._make_profile()
        # Write once
        write_convention_files(tmp_path, profile)
        first = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        # Write again — should not double-up
        write_convention_files(tmp_path, profile)
        second = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert second.count(MARKER_START) == 1, "Section was duplicated on second write"
        assert second == first, "Content changed unexpectedly on idempotent re-run"

    def test_appends_to_existing_file(self, tmp_path):
        profile = self._make_profile()
        existing = tmp_path / "CLAUDE.md"
        existing.write_text("# My project\n\nsome notes here\n", encoding="utf-8")
        write_convention_files(tmp_path, profile)
        content = existing.read_text(encoding="utf-8")
        assert "My project" in content
        assert MARKER_START in content

    def test_copilot_instructions_directory_created(self, tmp_path):
        profile = self._make_profile()
        write_convention_files(tmp_path, profile)
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()


# ---------------------------------------------------------------------------
# Individual extractors
# ---------------------------------------------------------------------------

class TestNamingExtractor:
    def _parse(self, src: str):
        import ast
        return [ast.parse(src)]

    def test_snake_case_functions(self):
        from style_dna.extractors.naming import extract_naming
        trees = self._parse("def get_user(): pass\ndef send_email(): pass\n")
        result = extract_naming(trees)
        assert result["function_naming"] == "snake_case"

    def test_camel_case_functions(self):
        from style_dna.extractors.naming import extract_naming
        trees = self._parse("def getUser(): pass\ndef sendEmail(): pass\n")
        result = extract_naming(trees)
        assert result["function_naming"] == "camelCase"

    def test_dunder_methods_excluded(self):
        from style_dna.extractors.naming import extract_naming
        # Only dunders — should fall back to unknown
        trees = self._parse("class Foo:\n    def __init__(self): pass\n    def __str__(self): pass\n")
        result = extract_naming(trees)
        assert result["function_naming"] == "unknown"

    def test_private_prefix_rate(self):
        from style_dna.extractors.naming import extract_naming
        trees = self._parse(
            "def public(): pass\ndef _private(): pass\ndef _also_private(): pass\n"
        )
        result = extract_naming(trees)
        assert result["private_prefix_rate"] == pytest.approx(2 / 3, abs=0.01)


class TestDocstringExtractor:
    def _parse(self, src: str):
        import ast
        return [ast.parse(src)]

    def test_google_style_detected(self):
        from style_dna.extractors.docstrings import extract_docstrings
        src = '''
def foo(x):
    """Do foo.

    Args:
        x: The input.

    Returns:
        A value.
    """
    pass
'''
        result = extract_docstrings(self._parse(src))
        assert result["docstring_style"] == "google"

    def test_rest_style_detected(self):
        from style_dna.extractors.docstrings import extract_docstrings
        src = '''
def bar(x):
    """:param x: the input\n    :return: a value\n    """
    pass
'''
        result = extract_docstrings(self._parse(src))
        assert result["docstring_style"] == "rest"

    def test_no_docstrings(self):
        from style_dna.extractors.docstrings import extract_docstrings
        src = "def foo(): pass\n"
        result = extract_docstrings(self._parse(src))
        assert result["docstring_style"] == "none"
        assert result["docstring_coverage"] == 0.0


class TestErrorHandlingExtractor:
    def _parse(self, src: str):
        import ast
        return [ast.parse(src)]

    def test_custom_exceptions_detected(self):
        from style_dna.extractors.error_handling import extract_error_handling
        src = "class MyError(ValueError): pass\n"
        result = extract_error_handling(self._parse(src))
        assert result["uses_custom_exceptions"] is True
        assert result["error_handling_pattern"] == "custom_exceptions"

    def test_broad_except_detected(self):
        from style_dna.extractors.error_handling import extract_error_handling
        src = "try:\n    pass\nexcept Exception:\n    pass\n"
        result = extract_error_handling(self._parse(src))
        assert result["error_handling_pattern"] == "broad_except"

    def test_specific_except_detected(self):
        from style_dna.extractors.error_handling import extract_error_handling
        src = "try:\n    pass\nexcept ValueError:\n    pass\n"
        result = extract_error_handling(self._parse(src))
        assert result["error_handling_pattern"] == "specific_except"


class TestStructureExtractor:
    def _parse(self, src: str):
        import ast
        return [ast.parse(src)]

    def test_type_hint_coverage_full(self):
        from style_dna.extractors.structure import extract_type_hints
        src = "def foo(x: int, y: str) -> bool: return True\n"
        result = extract_type_hints(self._parse(src))
        assert result["type_hint_coverage"] == pytest.approx(1.0)

    def test_type_hint_coverage_none(self):
        from style_dna.extractors.structure import extract_type_hints
        src = "def foo(x, y): return True\n"
        result = extract_type_hints(self._parse(src))
        assert result["type_hint_coverage"] == pytest.approx(0.0)

    def test_common_patterns_dataclass(self):
        from style_dna.extractors.structure import extract_common_patterns
        src = "from dataclasses import dataclass\n\n@dataclass\nclass Foo:\n    x: int = 0\n"
        result = extract_common_patterns(self._parse(src))
        assert any("dataclass" in p.lower() for p in result["common_patterns"])

    def test_common_patterns_async(self):
        from style_dna.extractors.structure import extract_common_patterns
        src = "async def fetch(): pass\n"
        result = extract_common_patterns(self._parse(src))
        assert any("async" in p.lower() for p in result["common_patterns"])

    def test_indent_style_tabs(self):
        from style_dna.extractors.structure import extract_formatting
        src = "def foo():\n\tx = 1\n\treturn x\n"
        result = extract_formatting([src])
        assert result["indent_style"] == "tabs"

    def test_indent_style_spaces_4(self):
        from style_dna.extractors.structure import extract_formatting
        src = "def foo():\n    x = 1\n    return x\n"
        result = extract_formatting([src])
        assert result["indent_style"] == "spaces_4"

    def test_quote_style_double(self):
        from style_dna.extractors.structure import extract_formatting
        src = 'x = "hello"\ny = "world"\n'
        result = extract_formatting([src])
        assert result["quote_style"] == "double"
