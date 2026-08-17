<div align="center">

# Style DNA Ghostwriter

**Learn a codebase's unwritten conventions. Ghostwrite code that belongs.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

</div>

---

## The problem

Style guides and linters only enforce rules a team bothered to *write down*.
The rest of a codebase's real personality — how errors get handled, how
private helpers get named, how verbose the docstrings actually are in
practice — lives nowhere except the code itself. AI-generated code ignores
all of that and defaults to generic, textbook style, which is exactly what
makes it stand out as not-quite-belonging.

**Style DNA Ghostwriter** fixes this by learning conventions the way a new
senior engineer would: by reading the code, not the wiki page nobody updated.

```
$ style-dna analyze ./my_repo

Analyzed 87 files from './my_repo'.
Style profile saved to: style_profile.json

- Name functions and variables in snake_case (observed in 87 files from ./my_repo).
- Prefix internal/private names with a leading underscore (observed in ~25% of internal names).
- Write google-style docstrings on public functions/classes (coverage ~80% in this codebase).
- Use type hints (observed in ~100% of function signatures).
- Error handling convention: custom exceptions.
- Use double quotes for strings, matching the rest of the codebase.
```

---

## Works with any coding agent

One command wires the extracted style into every agent your team uses —
no plugin, no per-tool config:

```bash
style-dna init
```

This writes the rules directly into the convention files agents already
read at session start:

| File | Read automatically by |
|---|---|
| `CLAUDE.md` | Claude Code |
| `AGENTS.md` | Codex, OpenCode, and other tools converging on this convention |
| `.cursorrules` | Cursor |
| `.github/copilot-instructions.md` | GitHub Copilot |

For agents that speak the **Model Context Protocol** (Claude Code and
others), `style-dna init` also prints a ready-to-paste MCP config so the
agent can pull rules live instead of from a static file:

```json
{
  "mcpServers": {
    "style-dna": {
      "command": "style-dna",
      "args": ["mcp"]
    }
  }
}
```

Exposed MCP tools: `analyze_repo`, `get_style_rules`, `refresh_style_profile`.

---

## How it works

1. **`analyze`** walks a codebase and parses every `.py` file with Python's
   `ast` module. A set of extractors runs over the parse trees — naming
   convention, docstring style, error-handling pattern, type-hint coverage,
   quote style, import ordering, average function length, common decorators
   — and the result is compiled into a `StyleProfile`: a structured,
   versionable fingerprint of the codebase, saved as `style_profile.json`.
2. **`init`** runs `analyze`, then writes that profile into every convention
   file coding agents read, so the whole team's tooling picks it up
   automatically.
3. **`generate`** (optional) turns the profile into a system prompt and
   calls the Claude API directly, for teams that want ghostwritten code
   without going through an agent at all.

```
style-dna-ghostwriter/
├── style_dna/
│   ├── analyzer.py         # walks a codebase, builds a StyleProfile
│   ├── profile.py          # StyleProfile data model + save/load + prompt rendering
│   ├── generator.py        # profile -> system prompt -> Claude API call
│   ├── mcp_server.py       # exposes analyze/get_rules/refresh as MCP tools
│   ├── conventions.py      # writes rules into CLAUDE.md/AGENTS.md/.cursorrules/etc.
│   ├── cli.py               # `style-dna` entrypoint (init/analyze/show/generate/mcp)
│   └── extractors/           # naming, docstrings, error_handling, structure
├── examples/sample_repo/     # fixture codebase used by the test suite
└── tests/test_analyzer.py    # verifies extraction against the fixture
```

---

## Install

```bash
pip install -e ".[mcp]"        # core + MCP server support
pip install -e ".[generate]"   # + anthropic, for direct code generation
```

## Usage

```bash
# One-shot setup for a project (recommended)
style-dna init

# Or step by step:
style-dna analyze ./my_repo --out style_profile.json   # learn the style
style-dna show style_profile.json                        # inspect the rules

# Direct generation (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-...
style-dna generate style_profile.json \
  "Write a function that cancels a pending order and refunds the customer" \
  --out cancel_order.py
```

As a library:

```python
from style_dna import analyze_codebase
from style_dna.generator import generate_code

profile = analyze_codebase("./my_repo")
code = generate_code(profile, "Add a function to archive completed orders")
```

---

## What it extracts

| Category | Signals |
|---|---|
| Naming | function/variable case style, private-prefix rate, getter/setter convention |
| Docstrings | style (google / numpy / rest / plain / none), coverage |
| Typing | type-hint coverage across signatures |
| Error handling | broad vs. specific `except`, custom exception classes, logging-on-catch rate |
| Formatting | quote style, average/max line length |
| Imports | grouped vs. ungrouped, relative vs. absolute preference |
| Structure | average function length, common decorators |

## Limitations & roadmap

- **Python only** for now. The extractor layer is isolated
  (`style_dna/extractors/`) specifically so a JS/TS front end (e.g. via
  tree-sitter) can be added without rearchitecting.
- Extraction uses `ast`-based heuristics, not a full type-checker — fast and
  dependency-free, though not exhaustive.
- Planned: per-directory profiles for monorepos, a `diff` command that flags
  newly written code violating the learned profile, and a pre-commit hook.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/
```

## License

Released under the [MIT License](LICENSE).

---

<div align="center">

Created by **Kaifazad** — [kaifazad.in](https://kaifazad.in)

</div>
