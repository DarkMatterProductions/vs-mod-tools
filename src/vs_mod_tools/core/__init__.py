"""Core logic: loading, variant generation, and pattern validation."""

from vs_mod_tools.core.loader import load_vs_json
from vs_mod_tools.core.validation import (
    expand_vs_template,
    extract_patterns,
    find_invalid_patterns,
)
from vs_mod_tools.core.variants import generate_variants, raw_cartesian

__all__ = [
    "load_vs_json",
    "generate_variants",
    "raw_cartesian",
    "expand_vs_template",
    "extract_patterns",
    "find_invalid_patterns",
]
