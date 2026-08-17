"""Generates new code conditioned on a codebase's extracted StyleProfile."""

from __future__ import annotations

import os

from .profile import StyleProfile

SYSTEM_PROMPT_TEMPLATE = """You are a ghostwriter engineer joining an existing codebase.
Your job is to write new code that is INDISTINGUISHABLE from what the team that
owns this codebase would have written themselves.

Below are the team's real, observed conventions -- extracted directly from their
source code, not from a style guide. Follow them precisely, even where they
differ from generic "best practice":

{rules}

Rules for your output:
- Return ONLY the code, no explanations, no markdown fences.
- Match the conventions above even if you would personally do it differently.
- Do not add extra docstrings/comments/type hints beyond what the profile indicates.
"""


def build_system_prompt(profile: StyleProfile) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(rules=profile.as_prompt_rules())


def generate_code(
    profile: StyleProfile,
    task: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 2000,
) -> str:
    """Generate code for `task`, styled to match `profile`.

    Requires the anthropic Python package and an ANTHROPIC_API_KEY environment
    variable to be set.
    """
    try:
        import anthropic
    except ImportError as e:
        raise ImportError(
            "The 'anthropic' package is required for generation. "
            "Install it with: pip install anthropic"
        ) from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Export it before running generation."
        )

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(profile)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": task}],
    )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks).strip()
