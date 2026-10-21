"""
Centralized text processing for VCAT.

This module is the SINGLE SOURCE OF TRUTH for text cleaning and stripping.
Both the builder (builders/build_eva_lines.py) and the verifier
(validators/verify_invariants.py) MUST import from here.

CRITICAL: Do not duplicate this logic elsewhere. If you need to strip
markup or clean text, import these functions. This ensures the builder
and verifier always apply identical rules, preventing subtle bugs where
they diverge over time.
"""

import re


def strip_ivtff_markup(text: str) -> str:
    """
    Strip IVTFF markup from text, preserving uncertainty markers.

    This produces the "flag basis" - the text used to compute
    has_uncertain and has_illegible flags.

    Removes (DECISIONS Q26, items 1.3 for D1 and D2):
    - In-line comments: <!...> (first, so their contents never leak)
    - Alternative brackets: [a:b] -> a (keeps first option)
    - Ligature braces: {ct} -> ct (the glyphs are kept; braces mark a ligature, IVTFF 2.0 Table 10)
    - Every other angle-bracket tag: <%>, <$>, <@X=y>

    Replaces:
    - Drawing interruptions <-> and <~> -> "." (a word space, IVTFF 2.0 Table 11)

    Preserves:
    - Uncertainty markers: ?, !, *
    - High-ASCII tokens: @NNN;
    - EVA characters

    Args:
        text: Raw IVTFF transcription text

    Returns:
        Text with markup stripped but uncertainty markers intact
    """
    # Remove in-line comments first: they are free text and may hold any character
    result = re.sub(r"<![^>]*>", "", text)

    # A drawing interruption is a word boundary (D2)
    result = re.sub(r"<[-~]>", ".", result)

    # Remove every other angle-bracket tag (<%>, <$>, <@X=y>)
    result = re.sub(r"<[^>]*>", "", result)

    # Handle alternatives [a:b] - keep first option
    # Uses * not + to handle empty alternatives like [:ch] or [a:]
    result = re.sub(r"\[([^:\]]*):([^\]]*)\]", lambda m: m.group(1), result)

    # A ligature keeps its glyphs (D1)
    result = re.sub(r"\{([^}]*)\}", r"\1", result)

    # Normalize whitespace
    result = re.sub(r"\s+", " ", result).strip()

    return result


def clean_text_for_analysis(text: str) -> str:
    """
    Produce analysis-ready text (text_clean): the normalization profile ``analysis-v1``.

    ``text_clean`` is an alias for that profile (roadmap item 1.6, DECISIONS Q39): a ligature's
    glyphs without braces, the first reading of each alternate, ``<->`` and ``<~>`` as ``.``, ``?``
    and the legacy EVA markers ``!`` and ``*`` dropped, ``,`` kept, comments, paragraph marks, text
    tags, whitespace and wraps removed. Every other glyph is kept as written: the earlier
    lower-casing of ``I`` corrected the transliteration and is gone (ZL f57v.3; D6).

    Args:
        text: Raw IVTFF transcription text

    Returns:
        The analysis-v1 reading of the text
    """
    from vcat.profiles import TEXT_CLEAN_PROFILE, apply_profile

    return apply_profile(TEXT_CLEAN_PROFILE, text)


def compute_flags(text: str) -> tuple[bool, bool, bool]:
    """
    Compute quality flags from raw text.

    Flags are computed from the "flag basis" (markup stripped, markers present)
    BEFORE uncertainty markers are removed.

    Args:
        text: Raw IVTFF transcription text

    Returns:
        Tuple of (has_uncertain, has_illegible, has_alternatives)
    """
    # Get flag basis (markup stripped, uncertainty markers present)
    flag_basis = strip_ivtff_markup(text)

    has_uncertain = "?" in flag_basis
    has_illegible = "!" in flag_basis or "*" in flag_basis
    # An alternate outside the comments (the row's `alternates` field is not empty; Q25)
    has_alternatives = bool(re.search(r"\[[^\]]*:[^\]]*\]", re.sub(r"<![^>]*>", "", text)))

    return (has_uncertain, has_illegible, has_alternatives)


def validate_stripped_text(text: str) -> bool:
    """
    Sanity check that stripped text contains no markup.

    Use this as a defensive check after stripping.

    Args:
        text: Text that should have been stripped

    Returns:
        True if text contains no markup characters
    """
    forbidden = set("<>{}")
    return not bool(set(text) & forbidden)
