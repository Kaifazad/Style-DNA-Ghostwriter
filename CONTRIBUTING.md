# Contributing to Style DNA Ghostwriter

Thank you for your interest in contributing to **Style DNA Ghostwriter**!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Kaifazad/Style-DNA-Ghostwriter.git
   cd Style-DNA-Ghostwriter
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
   ```

3. **Install dependencies with development tools:**
   ```bash
   pip install -e ".[all,dev]"
   ```

## Running Tests

We maintain a strict 100% pass requirement on all unit tests:

```bash
pytest -v
```

Before submitting a PR:
- Ensure all tests pass.
- Add tests for any new extractors, rules, or CLI subcommands.
- Maintain zero external runtime dependencies for the core analyzer.

## Code Style & Conventions

Style DNA Ghostwriter is self-hosting! Run its own analyzer and checker on your code:

```bash
python -m style_dna.cli analyze .
python -m style_dna.cli check <your_changed_file>
```

## Security

For security vulnerabilities, please refer to [SECURITY.md](SECURITY.md) and report via email to [hello@kaifazad.in](mailto:hello@kaifazad.in).
