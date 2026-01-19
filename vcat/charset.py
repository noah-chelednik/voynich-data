"""
Authoritative character set definitions for VCAT.

This module is the SINGLE SOURCE OF TRUTH for what characters are allowed
in text_clean and other normalized fields. All validators, builders, and
tests import from here. Nothing duplicates these definitions.

CHARSET COVENANT (v0.2.1):
=========================
Once the charset is decided for a version, it is LOCKED for that version.
Changing the allowed characters requires:
1. A version bump (at least minor version)
2. Documentation of the rationale in docs/charset_decisions.md
3. CHANGELOG entry explaining the change

This covenant prevents silent policy drift that could break downstream analysis.
"""

# =============================================================================
# CORE CHARACTER SETS
# =============================================================================

# EVA Core Alphabet
# The basic letters of the European Voynich Alphabet transcription system.
# Standard EVA uses lowercase Latin letters. Note: 'j' appears rarely (14 occurrences)
# but is a valid EVA character.
EVA_CORE: frozenset[str] = frozenset("abcdefghijklmnopqrstuvxyz")

# Structural Separators
# Characters that separate words/tokens in text_clean.
# - Dot (.) is the primary word separator in EVA transcription
# - Comma (,) is an occasional alternative separator
# - Space ( ) for readability after normalization
SEPARATORS: frozenset[str] = frozenset("., ")

# High-ASCII Token Characters
# The @NNN; format represents special/rare glyphs in IVTFF transcription.
# These characters appear as part of those tokens.
HIGH_ASCII_CHARS: frozenset[str] = frozenset("@;0123456789")

# Variant Characters (EMPIRICALLY DETERMINED)
# Characters that appear in legitimate EVA content beyond the core set.
# This was determined by running scripts/analyze_charset.py on the actual
# ZL3b-n.txt transcription (2026-01-18).
#
# EMPIRICAL ANALYSIS RESULTS:
#   - Apostrophe ('): 27 occurrences - used as variant marker (e.g., c'y)
#   - Added to charset for v0.2.1
#
# Current setting (LOCKED for v0.2.x):
VARIANT_CHARS: frozenset[str] = frozenset("'")

# =============================================================================
# COMPOSITE DEFINITIONS
# =============================================================================

# The Complete Allowed Set for text_clean
# This is what text_clean may contain and NOTHING ELSE.
ALLOWED_TEXT_CLEAN_CHARSET: frozenset[str] = (
    EVA_CORE | SEPARATORS | HIGH_ASCII_CHARS | VARIANT_CHARS
)

# Forbidden in text_clean (for explicit sanity checks)
FORBIDDEN_MARKUP_CHARS: frozenset[str] = frozenset("<>{}")

# Uncertainty markers - stripped from text_clean after flags computed
UNCERTAINTY_MARKERS: frozenset[str] = frozenset("?!*")

# Combined forbidden set (should not appear in text_clean)
FORBIDDEN_IN_TEXT_CLEAN: frozenset[str] = FORBIDDEN_MARKUP_CHARS | UNCERTAINTY_MARKERS


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_text_clean(text: str) -> tuple[bool, set[str]]:
    """
    Validate that text contains only allowed characters.

    Args:
        text: The text_clean string to validate

    Returns:
        Tuple of (is_valid, invalid_chars):
        - is_valid: True if all characters are allowed
        - invalid_chars: Set of characters that are not allowed (empty if valid)
    """
    chars = set(text)
    invalid = chars - ALLOWED_TEXT_CLEAN_CHARSET
    return (len(invalid) == 0, invalid)


def contains_forbidden_markup(text: str) -> bool:
    """Check if text contains any forbidden markup characters."""
    return bool(set(text) & FORBIDDEN_MARKUP_CHARS)


def contains_uncertainty_markers(text: str) -> bool:
    """Check if text contains uncertainty markers that should have been stripped."""
    return bool(set(text) & UNCERTAINTY_MARKERS)
