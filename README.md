<div align="center">

# Style DNA Ghostwriter

**Learn a codebase's unwritten conventions. Ghostwrite code that belongs.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![M8ven Score](https://m8ven.ai/badge/mcp/kaifazad-style-dna-ghostwriter-ihehal)](https://m8ven.ai/mcp/kaifazad-style-dna-ghostwriter-ihehal)

</div>

---

## The problem

Style guides and linters only enforce rules a team bothered to *write down*.
The rest of a codebase's real personality — how errors get handled, how
components get structured, whether arrow functions or declarations are preferred,
how Tailwind utilities or CSS modules are used, how verbose docstrings actually are —
lives nowhere except the code itself. AI-generated code ignores all of that and
defaults to generic, textbook style, which is exactly what makes it stand out as
not-quite-belonging.

**Style DNA Ghostwriter** fixes this by learning conventions the way a new
senior engineer would: by reading the code, not the wiki page nobody updated.

```
$ style-dna analyze ./my_web_app

Analyzed 42 files from './my_web_app' (0 Python, 42 Web).
Style profile saved to: style_profile.json

## Web Conventions
- Detected frameworks/tools: Next.js, React, Tailwind CSS, TypeScript.

### JavaScript / TypeScript
- Use single quotes for JS/TS strings.
- Omit semicolons at end of statements.
- Prefer arrow functions (`const fn = () => {}`).
- Prefer named exports.
- Use path aliases (`@/...`) for imports instead of deep relative paths.
- Prefer `interface` over `type` for object shapes in TypeScript.

### React / Next.js
- Next.js routing: App Router (`app/`).
- Define React components as arrow functions (`const Button = () => ...`).
- Component file naming: PascalCase.
- ~40% of components use 'use client' directive.
- State management: zustand.

### CSS / Styling
- Styling approach: Tailwind CSS utility classes.
- Uses CSS custom properties (`var(--token-name)`) for design tokens.
- Preferred color format: HSL.
```

---

## Works with any coding agent

### Zero-Friction Setup via `uvx` (No local clone or venv needed)
Run directly in any project:

```bash
uvx style-dna-ghostwriter init
```

This analyzes the repository, writes conventions into your agent instruction files, and sets up `.style-dna/style_profile.json`.

One command wires the extracted style into every agent your team uses —
no plugin, no per-tool config:

| File | Read automatically by |
|---|---|
| `GEMINI.md` | Google Antigravity & Gemini Code Assist |
| `CLAUDE.md` | Claude Code |
| `AGENTS.md` | Google Antigravity, Codex, OpenCode, and tools following the AGENTS standard |
| `.cursorrules` | Cursor |
| `.windsurfrules` | Windsurf |
| `.github/copilot-instructions.md` | GitHub Copilot |

---

## MCP Server (Model Context Protocol)

Add Style DNA to your Claude Code, Cursor, or Zed configuration (`claude_desktop_config.json` or `mcp.json`):

```json
{
  "mcpServers": {
    "style-dna": {
      "command": "uvx",
      "args": ["style-dna-ghostwriter", "mcp"]
    }
  }
}
```

### Exposed MCP Primitives

* **Tools**:
  * `analyze_repo(path, save, force)`: Extracts conventions from source code.
  * `get_style_rules(path, scope)`: Returns human-readable rules (scopes: `all`, `python`, `web`, `compact`).
  * `refresh_style_profile(path)`: Re-analyzes after code changes.
  * `check_code_style(code, path, language)`: Verifies a generated snippet against repo conventions and returns line-specific violations.
* **Passive Resources** (auto-attached to agent context):
  * `style-dna://profile`: Full JSON profile of extracted conventions.
  * `style-dna://rules`: Full plain-English rules.
  * `style-dna://rules/python`: Python rules only (saves context tokens).
  * `style-dna://rules/web`: Web & TypeScript rules only (saves context tokens).
  * `style-dna://rules/compact`: High-density 1-line bullet points (saves ~65% tokens).
* **Prompt**:
  * `/ghostwrite(task, path, scope)`: System prompt template conditioning any model to ghostwrite conforming code.

---

## Verification & Linting (`style-dna check`)

Ensure generated or modified code strictly adheres to your codebase's style DNA before committing:

```bash
# Verify a Python, TypeScript, or React file:
style-dna check ./src/components/ProductCard.tsx

# Output:
# FAIL: ProductCard.tsx - 2 violation(s) found:
#   [WARN]  line 12 [style.semicolons] Remove trailing semicolon - this repo omits them.
#   [INFO]  line 24 [style.imports]    Use path aliases (`@/...`) instead of relative paths - repo convention.
```

---

## Git Pre-Commit Hook (`style-dna hook install`)

Stop convention violations before they get committed:

```bash
# Automatically install pre-commit hook in .git/hooks/
style-dna hook install

# Uninstallation:
style-dna hook uninstall
```

Whenever you run `git commit`, Style DNA automatically lints staged Python, TypeScript, and React files.

---

## Compact Mode (Save ~65% Context Window Tokens)

Instead of feeding 50 lines of instructions into your LLM, generate an ultra-dense, token-saving summary:

```bash
style-dna show style_profile.json --scope compact

# Output:
# ## Style DNA (Compact)
# - Web: Next.js App Router, state: zustand, styling: tailwind.
# - JS/TS: single quotes, prefer interface, path aliases (@/...).
```

---

## Monorepo Support (`style-dna monorepo`)

Analyzes npm/pnpm/Yarn workspaces, Lerna, Nx, and Python sub-packages with distinct conventions per package:

```bash
style-dna monorepo . --out .style-dna/packages/
```

---

## GitHub Action

Automatically extract and verify conventions in CI or sync agent instructions on push:

```yaml
- name: Extract & Verify Style DNA
  uses: kaifazad/style-dna-ghostwriter@v0.2.0
  with:
    path: "."
    write-convention-files: "true"
```

---

## What it extracts

| Stack / Category | Extracted Signals |
|---|---|
| **Python** | Function/variable case style, private prefix rate (`_name`), docstring style (Google/NumPy/reST/plain) and coverage, type-hint rate, error handling (broad vs specific vs custom exceptions), quote style, import ordering, average function length, common patterns (`@dataclass`, `Protocol`, `async`, etc.) |
| **JavaScript / TypeScript** | Semicolons (`always` vs `never`), quote style (`single` / `double`), arrow functions vs function declarations, named vs default exports, import path aliases (`@/...`), TypeScript `interface` vs `type` preference, typing coverage, comment style (JSDoc/inline/block) |
| **React / Next.js** | **App Router** (`app/`) vs **Pages Router** (`pages/`), Server vs Client Components (`'use client'` rate), Server Actions (`'use server'`), component style, custom hook patterns (`use*`), state management (Zustand, Redux, Context, TanStack Query, SWR, Jotai, Recoil), framework detection |
| **CSS & Styling** | **Tailwind CSS** vs **CSS Modules** (`*.module.css`) vs **CSS-in-JS** vs **Vanilla CSS**, class naming conventions (BEM / kebab-case / camelCase), CSS custom property design tokens (`var(--token)`), color formats (HEX, HSL, RGB) |
| **HTML** | Indentation style (2 spaces / 4 spaces / tabs), attribute quote style (`"` vs `'`), semantic markup usage rate (`<header>`, `<main>`, `<section>`, etc.) |

---

## How it works

1. **`analyze`** walks a codebase and analyzes every source file without external binary or compiler dependencies. A pluggable suite of specialized extractors runs over the parse trees and source tokens to build a `StyleProfile` — a structured, versionable fingerprint saved as `style_profile.json`.
2. **`init`** runs `analyze`, then injects that profile into standard agent convention files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, etc.) surrounded by clean update markers (`<!-- style-dna:start -->` ... `<!-- style-dna:end -->`).
3. **`generate`** (optional) turns the profile into a system prompt and calls the Claude API directly, for teams that want ghostwritten code from the terminal.

```
style-dna-ghostwriter/
├── style_dna/
│   ├── analyzer.py         # multi-language codebase scanner
│   ├── profile.py          # StyleProfile data model + save/load + multi-stack rules
│   ├── generator.py        # profile -> system prompt -> Claude API call
│   ├── mcp_server.py       # MCP server exposing tools for agents
│   ├── conventions.py      # upserts rules into CLAUDE.md/AGENTS.md/.cursorrules/etc.
│   ├── cli.py              # `style-dna` CLI (init, analyze, show, generate, mcp)
│   └── extractors/         # Python, JS/TS, React/Next.js, CSS/Tailwind, HTML
├── examples/
│   ├── sample_repo/        # Python test fixture
│   └── sample_web_repo/    # Next.js 14 + React TSX + Tailwind test fixture
└── tests/                  # Complete test suite
```

---

## Install

```bash
# Core only (zero external dependencies):
pip install -e .

# With MCP server support:
pip install -e ".[mcp]"

# With direct Claude code generation support:
pip install -e ".[generate]"

# All features:
pip install -e ".[all]"
```

## Usage

```bash
# One-shot setup for any repo (Python, React, Next.js, etc.):
style-dna init

# Inspect codebase style rules:
style-dna analyze ./my_repo --out style_profile.json
style-dna show style_profile.json
style-dna show style_profile.json --format json

# Direct generation (requires ANTHROPIC_API_KEY):
export ANTHROPIC_API_KEY=sk-...
style-dna generate style_profile.json \
  "Write a React component that displays a product card with add to cart button" \
  --out ProductCard.tsx
```

As a Python library:

```python
from style_dna import analyze_codebase
from style_dna.generator import generate_code

profile = analyze_codebase("./my_repo")
code = generate_code(profile, "Add a custom hook to manage user favorites")
```

---

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## License

Released under the [MIT License](LICENSE).

---

<div align="center">

Created by **Kaifazad** — [kaifazad.in](https://kaifazad.in)

</div>
