"""Tests for style_dna.verifier (P1.2)."""

from __future__ import annotations

import pytest
from style_dna.profile import StyleProfile
from style_dna.verifier import (
    StyleViolation,
    check_code_style,
    check_python_style,
    check_js_ts_style,
)


class TestVerifierPython:
    def test_snake_case_violation(self):
        profile = StyleProfile(function_naming="snake_case")
        code = "def calculateTotal(price, tax):\n    return price + tax\n"
        violations = check_python_style(code, profile)
        assert any(v.rule == "naming.function" for v in violations)
        assert any("snake_case" in v.message for v in violations)

    def test_camel_case_violation(self):
        profile = StyleProfile(function_naming="camelCase")
        code = "def calculate_total(price, tax):\n    return price + tax\n"
        violations = check_python_style(code, profile)
        assert any(v.rule == "naming.function" for v in violations)
        assert any("camelCase" in v.message for v in violations)

    def test_conforming_snake_case(self):
        profile = StyleProfile(function_naming="snake_case")
        code = "def calculate_total(price: float, tax: float) -> float:\n    return price + tax\n"
        violations = check_python_style(code, profile)
        assert not any(v.rule == "naming.function" for v in violations)

    def test_missing_type_hints_when_high_coverage(self):
        profile = StyleProfile(type_hint_coverage=0.85)
        code = "def process_order(user, item, count):\n    return True\n"
        violations = check_python_style(code, profile)
        assert any(v.rule == "typing.missing_hints" for v in violations)

    def test_type_hints_not_flagged_when_low_coverage(self):
        profile = StyleProfile(type_hint_coverage=0.2)
        code = "def process_order(user, item, count):\n    return True\n"
        violations = check_python_style(code, profile)
        assert not any(v.rule == "typing.missing_hints" for v in violations)

    def test_missing_docstring_when_high_coverage(self):
        profile = StyleProfile(docstring_coverage=0.9, docstring_style="google")
        code = "def compute_hash(val):\n    return hash(val)\n"
        violations = check_python_style(code, profile)
        assert any(v.rule == "docs.missing_docstring" for v in violations)

    def test_syntax_error_reported(self):
        profile = StyleProfile()
        code = "def broken(:\n    pass\n"
        violations = check_python_style(code, profile)
        assert len(violations) == 1
        assert violations[0].rule == "syntax"
        assert violations[0].severity == "error"

    def test_quote_style_check(self):
        profile = StyleProfile(quote_style="double")
        code = "name = 'kaif'\n"
        violations = check_python_style(code, profile)
        assert any(v.rule == "style.quotes" for v in violations)


class TestVerifierJsTs:
    def test_semicolons_missing_when_always(self):
        profile = StyleProfile(js_semicolons="always")
        code = "const x = 10\nconst y = 20\n"
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.semicolons" for v in violations)

    def test_semicolons_forbidden_when_never(self):
        profile = StyleProfile(js_semicolons="never")
        code = "const x = 10;\n"
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.semicolons" for v in violations)

    def test_quote_style_single(self):
        profile = StyleProfile(js_quote_style="single")
        code = 'const msg = "hello world";\n'
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.quotes" for v in violations)

    def test_arrow_function_preference(self):
        profile = StyleProfile(js_function_style="arrow")
        code = "function renderHeader() {\n  return null;\n}\n"
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.function_style" for v in violations)

    def test_declaration_function_preference(self):
        profile = StyleProfile(js_function_style="declaration")
        code = "const renderHeader = () => {\n  return null;\n};\n"
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.function_style" for v in violations)

    def test_import_alias_preference(self):
        profile = StyleProfile(js_import_alias_style="alias_at")
        code = 'import { Button } from "../../components/Button";\n'
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.imports" for v in violations)

    def test_relative_import_preference(self):
        profile = StyleProfile(js_import_alias_style="relative")
        code = 'import { Button } from "@/components/Button";\n'
        violations = check_js_ts_style(code, profile)
        assert any(v.rule == "style.imports" for v in violations)


class TestCheckCodeStyleAutoDetect:
    def test_auto_detects_python(self):
        profile = StyleProfile(function_naming="snake_case")
        py_code = "def badFunc():\n    pass\n"
        violations = check_code_style(py_code, profile, language="auto")
        assert any(v.rule == "naming.function" for v in violations)

    def test_auto_detects_javascript(self):
        profile = StyleProfile(js_semicolons="never")
        js_code = "const val = 42;\n"
        violations = check_code_style(js_code, profile, language="auto")
        assert any(v.rule == "style.semicolons" for v in violations)

    def test_violation_as_dict(self):
        v = StyleViolation(line=10, rule="test.rule", message="Test msg", severity="warning")
        d = v.as_dict()
        assert d["line"] == 10
        assert d["rule"] == "test.rule"
        assert d["severity"] == "warning"
