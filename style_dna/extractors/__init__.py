from .naming import extract_naming
from .docstrings import extract_docstrings
from .error_handling import extract_error_handling
from .structure import (
    extract_formatting,
    extract_imports,
    extract_structure,
    extract_type_hints,
    extract_common_patterns,
)
from .js_ts import extract_js_ts
from .react_next import extract_react_next
from .css_styling import extract_css_styling
from .html_extractor import extract_html

__all__ = [
    # Python extractors
    "extract_naming",
    "extract_docstrings",
    "extract_error_handling",
    "extract_formatting",
    "extract_imports",
    "extract_structure",
    "extract_type_hints",
    "extract_common_patterns",
    # Web extractors
    "extract_js_ts",
    "extract_react_next",
    "extract_css_styling",
    "extract_html",
]
