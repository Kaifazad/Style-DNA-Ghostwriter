# Security Policy

## Reporting a Vulnerability

We take the security of **Style DNA Ghostwriter** seriously. If you discover a vulnerability or security issue, please do **not** disclose it publicly via GitHub issues.

Instead, please send a responsible disclosure report to:
* **Email:** [hello@kaifazad.in](mailto:hello@kaifazad.in)
* **Security Contact:** Kaifazad (@Kaifazad)

Please include:
1. A description of the issue and potential impact.
2. Steps to reproduce or proof-of-concept code.
3. Any proposed remediations.

We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure timeline.

---

## MCP Server Security Architecture

Style DNA Ghostwriter is designed from the ground up for high-trust environments and compliance with the **Model Context Protocol (MCP)** security standards:

### 1. 100% Local Execution (Zero Network / Zero Telemetry)
* The MCP server (`style-dna mcp`) executes **entirely locally** on your machine via `stdio`.
* It performs **zero external network requests**, sends no analytics or telemetry, and never uploads code to any cloud service or third party.

### 2. Zero Credentials Required for MCP
* The MCP server **reads no environment variables, API keys, or credentials**.
* *Note on `ANTHROPIC_API_KEY`:* The `ANTHROPIC_API_KEY` environment variable is **only** used by the optional terminal CLI subcommand (`style-dna generate`), which allows terminal users to generate code directly via the Claude SDK. The MCP server itself never reads or transmits this key.

### 3. Workspace Boundary Guard
* All file analysis is strictly sandboxed to the target project directory.
* Path traversal attempts (`../`) are automatically resolved and validated against the workspace root.
* Analysis strictly honors `.gitignore` rules (via `pathspec`), preventing sensitive files, secrets, or credential caches (`.env`, `.git`, `credentials.json`, `venv`, etc.) from ever being read or analyzed.

### 4. Read-Only Safety Hints
* The server declares explicit MCP tool annotations (`readOnlyHint`, `destructiveHint: False`, `idempotentHint: True`, `openWorldHint: False`) so agents and orchestrators can safely audit tool permissions prior to execution.
