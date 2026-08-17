"""Tests for web stack extractors (JS/TS, React/Next.js, CSS, HTML)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from style_dna.analyzer import analyze_codebase
from style_dna.extractors.js_ts import extract_js_ts
from style_dna.extractors.react_next import extract_react_next
from style_dna.extractors.css_styling import extract_css_styling
from style_dna.extractors.html_extractor import extract_html

SAMPLE_WEB_REPO = Path(__file__).resolve().parents[1] / "examples" / "sample_web_repo"


# ---------------------------------------------------------------------------
# Full analyzer on the sample web repo
# ---------------------------------------------------------------------------

class TestWebAnalyzer:
    def test_detects_web_files(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.web_files_analyzed > 0

    def test_detects_nextjs(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert "Next.js" in profile.web_frameworks

    def test_detects_react(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert "React" in profile.web_frameworks

    def test_detects_tailwind(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert "Tailwind CSS" in profile.web_frameworks

    def test_detects_typescript(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert "TypeScript" in profile.web_frameworks

    def test_detects_zustand(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.react_state_management == "zustand"

    def test_detects_app_router(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.nextjs_router == "app_router"

    def test_detects_arrow_components(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.react_component_style in ("arrow", "mixed")

    def test_detects_tailwind_styling(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.styling_approach == "tailwind"

    def test_detects_css_variables(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.css_variables_usage is True

    def test_detects_hsl_colors(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.css_color_format == "hsl"

    def test_detects_html_semantic_usage(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.html_semantic_usage > 0.3

    def test_detects_html_double_quotes(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert profile.html_attr_quote_style == "double"

    def test_prompt_rules_include_web_section(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        rules = profile.as_prompt_rules()
        assert "Web Conventions" in rules

    def test_prompt_rules_mention_nextjs(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        rules = profile.as_prompt_rules()
        assert "Next.js" in rules

    def test_prompt_rules_mention_tailwind(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        rules = profile.as_prompt_rules()
        assert "Tailwind" in rules

    def test_custom_hooks_detected(self):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        assert len(profile.react_hooks_patterns) >= 2
        hook_names = profile.react_hooks_patterns
        assert any("useCartStore" in h for h in hook_names)
        assert any("useProducts" in h for h in hook_names)


# ---------------------------------------------------------------------------
# JS/TS extractor unit tests
# ---------------------------------------------------------------------------

class TestJsTsExtractor:
    def _extract(self, src: str, filename: str = "test.ts") -> dict:
        return extract_js_ts([src], [Path(filename)])

    def test_semicolons_always(self):
        src = "const x = 1;\nconst y = 2;\nconst z = 3;\nlet a = 4;\nlet b = 5;\nlet c = 6;\n"
        result = self._extract(src)
        assert result["js_semicolons"] == "always"

    def test_semicolons_never(self):
        src = "const x = 1\nconst y = 2\nconst z = 3\nlet a = 4\nlet b = 5\nlet c = 6\n"
        result = self._extract(src)
        assert result["js_semicolons"] == "never"

    def test_single_quotes(self):
        src = "const x = 'hello'\nconst y = 'world'\nconst z = 'foo'\nconst w = 'bar'\n"
        result = self._extract(src)
        assert result["js_quote_style"] == "single"

    def test_double_quotes(self):
        src = 'const x = "hello"\nconst y = "world"\nconst z = "foo"\nconst w = "bar"\n'
        result = self._extract(src)
        assert result["js_quote_style"] == "double"

    def test_arrow_function_style(self):
        src = "const foo = () => {}\nconst bar = (x) => x\nconst baz = () => null\n"
        result = self._extract(src)
        assert result["js_function_style"] == "arrow"

    def test_declaration_function_style(self):
        src = "function foo() {}\nfunction bar() {}\nfunction baz() {}\n"
        result = self._extract(src)
        assert result["js_function_style"] == "declaration"

    def test_named_exports(self):
        src = "export const foo = 1\nexport function bar() {}\nexport const baz = 2\n"
        result = self._extract(src)
        assert result["js_export_style"] == "named"

    def test_alias_imports(self):
        src = "import { Foo } from '@/components/Foo'\nimport { Bar } from '@/lib/bar'\nimport { Baz } from '@/hooks/baz'\n"
        result = self._extract(src)
        assert result["js_import_alias_style"] == "alias_at"

    def test_relative_imports(self):
        src = "import { Foo } from './Foo'\nimport { Bar } from '../lib/bar'\nimport { Baz } from './hooks/baz'\n"
        result = self._extract(src)
        assert result["js_import_alias_style"] == "relative"

    def test_ts_interface_preferred(self):
        src = "interface Foo { x: number }\ninterface Bar { y: string }\ninterface Baz { z: boolean }\n"
        result = self._extract(src, "test.ts")
        assert result["ts_type_style"] == "interface"

    def test_ts_type_preferred(self):
        src = "type Foo = { x: number }\ntype Bar = { y: string }\ntype Baz = { z: boolean }\n"
        result = self._extract(src, "test.ts")
        assert result["ts_type_style"] == "type"


# ---------------------------------------------------------------------------
# React / Next.js extractor unit tests
# ---------------------------------------------------------------------------

class TestReactNextExtractor:
    def _extract(self, src: str, filename: str = "Component.tsx", root: Path | None = None) -> dict:
        return extract_react_next([src], [Path(filename)], root or Path("."))

    def test_use_client_detected(self):
        src = "'use client';\n\nexport const Foo = () => <div>Hello</div>\n"
        result = self._extract(src)
        assert result["react_use_client_rate"] > 0

    def test_use_server_detected(self):
        src = "'use server';\n\nexport const action = async () => {}\n"
        result = self._extract(src)
        assert result["react_use_server_rate"] > 0

    def test_arrow_components(self):
        src = "export const Foo = () => <div/>\nexport const Bar = () => <span/>\nexport const Baz = () => <p/>\n"
        result = self._extract(src)
        assert result["react_component_style"] == "arrow"

    def test_function_components(self):
        src = "export function Foo() { return <div/> }\nexport function Bar() { return <span/> }\nexport function Baz() { return <p/> }\n"
        result = self._extract(src)
        assert result["react_component_style"] == "function"

    def test_custom_hooks_detected(self):
        src = "export const useMyHook = () => {}\nexport function useOtherHook() {}\n"
        result = self._extract(src)
        assert "useMyHook" in result["react_hooks_patterns"]
        assert "useOtherHook" in result["react_hooks_patterns"]

    def test_zustand_detected(self):
        src = "import { create } from 'zustand'\nexport const useStore = create(() => ({}))\n"
        result = self._extract(src)
        assert result["react_state_management"] == "zustand"

    def test_redux_detected(self):
        src = "import { useSelector } from 'react-redux'\nconst val = useSelector((s) => s.x)\n"
        result = self._extract(src)
        assert result["react_state_management"] == "redux"

    def test_context_detected(self):
        src = "const ctx = createContext(null)\nconst val = useContext(ctx)\n"
        result = self._extract(src)
        assert result["react_state_management"] == "context"

    def test_framework_detection(self):
        result = extract_react_next([], [], SAMPLE_WEB_REPO)
        assert "Next.js" in result["web_frameworks"]
        assert "React" in result["web_frameworks"]
        assert "Tailwind CSS" in result["web_frameworks"]


# ---------------------------------------------------------------------------
# CSS / Styling extractor unit tests
# ---------------------------------------------------------------------------

class TestCssStylingExtractor:
    def test_tailwind_via_directives(self):
        css_src = "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"
        result = extract_css_styling([css_src], [Path("globals.css")], [], [], Path("."))
        assert result["styling_approach"] == "tailwind"

    def test_css_modules_detected(self):
        js_src = "import styles from './Button.module.css'\n"
        result = extract_css_styling(
            [], [],
            [js_src, js_src, js_src], [Path("a.tsx"), Path("b.tsx"), Path("c.tsx")],
            Path(".")
        )
        assert result["styling_approach"] == "css_modules"

    def test_bem_naming(self):
        css_src = ".card__header { color: red }\n.card__body--active { color: blue }\n.card__footer { color: green }\n.btn__icon--large { color: yellow }\n"
        result = extract_css_styling([css_src], [Path("style.css")], [], [], Path("."))
        assert result["css_class_naming"] == "BEM"

    def test_kebab_naming(self):
        css_src = ".nav-item { color: red }\n.nav-link { color: blue }\n.page-header { color: green }\n.side-bar { color: yellow }\n"
        result = extract_css_styling([css_src], [Path("style.css")], [], [], Path("."))
        assert result["css_class_naming"] == "kebab-case"

    def test_css_variables_detected(self):
        css_src = ":root { --color-primary: #fff; --color-bg: #000; --spacing: 1rem; --radius: 4px }\nbody { color: var(--color-primary) }\n"
        result = extract_css_styling([css_src], [Path("style.css")], [], [], Path("."))
        assert result["css_variables_usage"] is True

    def test_hex_color_format(self):
        css_src = "body { color: #333; background: #ffffff; border: 1px solid #eee; outline: #aaa }\n"
        result = extract_css_styling([css_src], [Path("style.css")], [], [], Path("."))
        assert result["css_color_format"] == "hex"

    def test_hsl_color_format(self):
        css_src = ":root { --a: hsl(220, 90%, 50%); --b: hsl(0, 0%, 10%); --c: hsla(120, 50%, 50%, 0.5); --d: hsl(60, 70%, 40%) }\n"
        result = extract_css_styling([css_src], [Path("style.css")], [], [], Path("."))
        assert result["css_color_format"] == "hsl"


# ---------------------------------------------------------------------------
# HTML extractor unit tests
# ---------------------------------------------------------------------------

class TestHtmlExtractor:
    def test_indent_2_spaces(self):
        src = "<div>\n  <p>Hello</p>\n  <span>World</span>\n</div>\n"
        result = extract_html([src], [Path("test.html")])
        assert result["html_indent_style"] == "spaces_2"

    def test_indent_tabs(self):
        src = "<div>\n\t<p>Hello</p>\n\t<span>World</span>\n</div>\n"
        result = extract_html([src], [Path("test.html")])
        assert result["html_indent_style"] == "tabs"

    def test_double_quotes(self):
        src = '<div class="container">\n<a href="/home" title="Home">Link</a>\n<img src="test.jpg" alt="Test" />\n</div>\n'
        result = extract_html([src], [Path("test.html")])
        assert result["html_attr_quote_style"] == "double"

    def test_single_quotes(self):
        src = "<div class='container'>\n<a href='/home' title='Home'>Link</a>\n<img src='test.jpg' alt='Test' />\n</div>\n"
        result = extract_html([src], [Path("test.html")])
        assert result["html_attr_quote_style"] == "single"

    def test_semantic_usage_high(self):
        src = "<header><nav><a>Link</a></nav></header>\n<main><section><article><p>Hi</p></article></section></main>\n<footer><p>End</p></footer>\n"
        result = extract_html([src], [Path("test.html")])
        assert result["html_semantic_usage"] > 0.5

    def test_semantic_usage_low(self):
        src = "<div><div><div><span>Hi</span></div></div></div>\n<div><span>More</span></div>\n"
        result = extract_html([src], [Path("test.html")])
        assert result["html_semantic_usage"] < 0.1

    def test_empty_html(self):
        result = extract_html([], [])
        assert result["html_indent_style"] == "unknown"
        assert result["html_attr_quote_style"] == "unknown"
        assert result["html_semantic_usage"] == 0.0


# ---------------------------------------------------------------------------
# Profile web rules rendering
# ---------------------------------------------------------------------------

class TestWebPromptRules:
    def test_web_only_project_renders_rules(self):
        """A project with only web files should still generate good rules."""
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        rules = profile.as_prompt_rules()
        assert len(rules) > 100  # Substantial output
        assert "Web Conventions" in rules

    def test_profile_save_load_roundtrip(self, tmp_path):
        profile = analyze_codebase(str(SAMPLE_WEB_REPO))
        path = tmp_path / "profile.json"
        profile.save(path)
        from style_dna.profile import StyleProfile
        loaded = StyleProfile.load(path)
        assert loaded.web_files_analyzed == profile.web_files_analyzed
        assert loaded.web_frameworks == profile.web_frameworks
        assert loaded.nextjs_router == profile.nextjs_router
        assert loaded.react_component_style == profile.react_component_style
        assert loaded.styling_approach == profile.styling_approach
