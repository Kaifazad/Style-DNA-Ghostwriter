"""
Style DNA Ghostwriter
======================

Learns a codebase's unwritten conventions (naming, error handling,
docstrings, structure) purely from examples -- no style guide needed --
and uses that "style DNA" to condition AI code generation so new code
looks like it was written by the same team.
"""

from .profile import StyleProfile
from .analyzer import analyze_codebase
from .verifier import check_code_style, StyleViolation
from .monorepo import analyze_monorepo, MonorepoProfile

__version__ = "0.2.0"
__all__ = [
    "StyleProfile",
    "analyze_codebase",
    "check_code_style",
    "StyleViolation",
    "analyze_monorepo",
    "MonorepoProfile",
]
