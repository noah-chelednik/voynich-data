"""
EVA Character Set Specification and Validation
===============================================

This module defines the EVA (Extensible Voynich Alphabet) character set
and provides validation functions for EVA transcription text.

EVA was developed by René Zandbergen, Gabriel Landini, and John Grove in 1998
to provide a standard ASCII representation of Voynich manuscript characters.
It is the most widely used transcription alphabet for the Voynich manuscript.

The module provides:
    - Character set constants (EVA_BASIC, EVA_RARE, EVA_COMPOUNDS, etc.)
    - Character information and categorization
    - Text validation functions
    - Character frequency analysis utilities

Reference: http://www.voynich.nu/extra/eva.html

Example:
    >>> from vcat.eva_charset import validate_eva_text, EVA_BASIC
    >>> result = validate_eva_text("fachys.ykal.ar.ataiin")
    >>> result.is_valid
    True
    >>> result.word_count
    4
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple


class CharacterCategory(str, Enum):
    """Categories of EVA characters.

    EVA characters are classified into categories based on their frequency
    and function in the transcription system.

    Attributes:
        BASIC: Core EVA alphabet characters (a-y excluding rare)
        RARE: Rare but valid single characters (f, g, x, j, v, b, u, z)
        COMPOUND: Multi-glyph combinations (ch, sh, cth, etc.)
        SPECIAL: Separators and markers
        EDITORIAL: Editorial annotations and uncertainty markers
        UNKNOWN: Characters not recognized in EVA
    """

    BASIC = "basic"
    RARE = "rare"
    COMPOUND = "compound"
    SPECIAL = "special"
    EDITORIAL = "editorial"
    UNKNOWN = "unknown"


# Basic EVA characters (lowercase letters)
# These are the core characters that appear frequently
EVA_BASIC: set[str] = set("acdehiklmnopqrsty")

# Rare but valid EVA characters
# These appear infrequently but are part of the alphabet
EVA_RARE: set[str] = set("fgxjvbuz")

# All valid single EVA characters
EVA_SINGLE: set[str] = EVA_BASIC | EVA_RARE

# Compound glyphs (multi-character combinations representing single glyphs)
EVA_COMPOUNDS: set[str] = {
    "ch",  # Very common, often word-initial
    "sh",  # Common
    "cth",  # Rare - gallows with pedestal
    "ckh",  # Rare - gallows with pedestal
    "cph",  # Rare - gallows with pedestal
    "cfh",  # Rare - gallows with pedestal
}

# Valid word/text separators
EVA_SEPARATORS: set[str] = {
    ".",  # Word separator (standard)
    ",",  # Possible/uncertain word separator
    " ",  # Space
}

# Line and paragraph markers
EVA_LINE_MARKERS: set[str] = {
    "-",  # Line break
    "=",  # Paragraph break
}

# Editorial/uncertainty markers
EVA_EDITORIAL: set[str] = {
    "?",  # Uncertain reading
    "!",  # Illegible
    "*",  # Editorial insertion
    "[",  # Start alternative/lacuna
    "]",  # End alternative/lacuna
    ":",  # Alternative separator
    "{",  # Start comment/ligature
    "}",  # End comment/ligature
    "'",  # Ligature connector
    "<",  # Start marker
    ">",  # End marker
    "@",  # High-ASCII code prefix
    ";",  # High-ASCII code terminator
    "%",  # Paragraph start marker (IVTFF)
    "$",  # End marker (IVTFF)
    "~",  # Column separator (IVTFF)
}

# Combined set of all valid characters in EVA transcription text
EVA_ALL_CHARS: set[str] = (
    EVA_SINGLE
    | EVA_SEPARATORS
    | EVA_LINE_MARKERS
    | EVA_EDITORIAL
    | set("0123456789")  # For high-ASCII codes
)


class CharacterInfo(NamedTuple):
    """Information about a character or character sequence.

    Attributes:
        char: The character or compound glyph.
        category: The CharacterCategory classification.
        frequency: Frequency descriptor ("high", "medium", "low", "rare").
        description: Human-readable description of the character.
    """

    char: str
    category: CharacterCategory
    frequency: str
    description: str


# Character descriptions for documentation
CHARACTER_INFO: dict[str, CharacterInfo] = {
    # Basic high-frequency
    "a": CharacterInfo(
        "a", CharacterCategory.BASIC, "high", "Common vowel-like, often word-initial"
    ),
    "c": CharacterInfo(
        "c", CharacterCategory.BASIC, "high", "Often in combinations (ch, cth, etc.)"
    ),
    "d": CharacterInfo("d", CharacterCategory.BASIC, "high", "Common character"),
    "e": CharacterInfo("e", CharacterCategory.BASIC, "high", "Often word-final"),
    "h": CharacterInfo("h", CharacterCategory.BASIC, "high", "Often in combinations"),
    "i": CharacterInfo("i", CharacterCategory.BASIC, "high", "Often in sequences (ii, iii)"),
    "k": CharacterInfo("k", CharacterCategory.BASIC, "high", "Gallows character"),
    "l": CharacterInfo("l", CharacterCategory.BASIC, "medium", "Common character"),
    "o": CharacterInfo("o", CharacterCategory.BASIC, "high", "Often word-initial"),
    "q": CharacterInfo(
        "q", CharacterCategory.BASIC, "high", "Often word-initial, usually followed by o"
    ),
    "r": CharacterInfo("r", CharacterCategory.BASIC, "medium", "Common character"),
    "s": CharacterInfo("s", CharacterCategory.BASIC, "high", "Common character"),
    "t": CharacterInfo("t", CharacterCategory.BASIC, "medium", "Gallows character"),
    "y": CharacterInfo("y", CharacterCategory.BASIC, "high", "Often word-final"),
    # Basic medium-frequency
    "m": CharacterInfo("m", CharacterCategory.BASIC, "medium", "Less common"),
    "n": CharacterInfo("n", CharacterCategory.BASIC, "medium", "Common character"),
    # Basic low-frequency
    "p": CharacterInfo("p", CharacterCategory.BASIC, "low", "Gallows character"),
    "f": CharacterInfo("f", CharacterCategory.RARE, "low", "Gallows character"),
    # Rare characters
    "g": CharacterInfo("g", CharacterCategory.RARE, "rare", "Rare character"),
    "x": CharacterInfo("x", CharacterCategory.RARE, "rare", "Rare character"),
    "j": CharacterInfo("j", CharacterCategory.RARE, "rare", "Rare character"),
    "v": CharacterInfo("v", CharacterCategory.RARE, "rare", "Rare character"),
    "b": CharacterInfo("b", CharacterCategory.RARE, "rare", "Rare character (added in Eva)"),
    "u": CharacterInfo("u", CharacterCategory.RARE, "rare", "Rare character (added in Eva)"),
    "z": CharacterInfo("z", CharacterCategory.RARE, "rare", "Rare character (added in Eva)"),
    # Compound glyphs
    "ch": CharacterInfo(
        "ch", CharacterCategory.COMPOUND, "high", "Very common, often word-initial"
    ),
    "sh": CharacterInfo("sh", CharacterCategory.COMPOUND, "high", "Common benched character"),
    "cth": CharacterInfo("cth", CharacterCategory.COMPOUND, "low", "Gallows with pedestal"),
    "ckh": CharacterInfo("ckh", CharacterCategory.COMPOUND, "low", "Gallows with pedestal"),
    "cph": CharacterInfo("cph", CharacterCategory.COMPOUND, "rare", "Gallows with pedestal"),
    "cfh": CharacterInfo("cfh", CharacterCategory.COMPOUND, "rare", "Gallows with pedestal"),
}


@dataclass
class ValidationResult:
    """Result of validating EVA text.

    This dataclass holds the results of EVA text validation, including
    character counts, word counts, any unknown characters found, and
    warnings or errors encountered during validation.

    Attributes:
        is_valid: Whether the text passed validation.
        char_count: Total number of EVA characters (excluding markup).
        word_count: Number of words (separated by . , or space).
        unknown_chars: Set of characters not in EVA character set.
        unknown_positions: List of (position, char) tuples for unknowns.
        warnings: List of warning messages.
        errors: List of error messages.
        char_frequencies: Dictionary mapping characters to their counts.
        compound_counts: Dictionary mapping compounds to their counts.

    Example:
        >>> result = validate_eva_text("fachys.ykal")
        >>> result.is_valid
        True
        >>> result.word_count
        2
    """

    is_valid: bool = True
    char_count: int = 0
    word_count: int = 0
    unknown_chars: set[str] = field(default_factory=set)
    unknown_positions: list[tuple[int, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    char_frequencies: dict[str, int] = field(default_factory=dict)
    compound_counts: dict[str, int] = field(default_factory=dict)

    def add_unknown(self, char: str, position: int) -> None:
        """Record an unknown character.

        Args:
            char: The unknown character.
            position: Position in the text where it was found.
        """
        self.unknown_chars.add(char)
        self.unknown_positions.append((position, char))
        if len(self.unknown_chars) == 1:  # First unknown
            self.warnings.append("Unknown characters found")

    def add_warning(self, message: str) -> None:
        """Add a warning message.

        Args:
            message: The warning message to add.
        """
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message and mark validation as failed.

        Args:
            message: The error message to add.
        """
        self.errors.append(message)
        self.is_valid = False


def validate_eva_text(text: str, strict: bool = False) -> ValidationResult:
    """Validate EVA transcription text.

    Validates text against the EVA character set, counting characters,
    words, and identifying any unknown characters. IVTFF markup is
    automatically stripped before validation.

    Args:
        text: Raw EVA transcription text, may include IVTFF markup.
        strict: If True, unknown characters cause validation failure.
            If False (default), unknowns generate warnings only.

    Returns:
        ValidationResult with validation details including character
        frequencies, word count, and any warnings or errors.

    Example:
        >>> result = validate_eva_text("fachys.ykal.ar.ataiin")
        >>> result.is_valid
        True
        >>> result.word_count
        4
        >>> result.char_frequencies.get('a', 0)
        4

    Note:
        IVTFF markup such as inline comments {}, locators <>, and
        high-ASCII codes @NNN; are removed before validation.
        Alternatives like [a:b] are simplified to keep only the
        first option.
    """
    result = ValidationResult()

    # Remove IVTFF markup for validation
    clean_text = text

    # Remove inline comments {like this}
    clean_text = re.sub(r"\{[^}]*\}", "", clean_text)

    # Remove IVTFF markers
    clean_text = re.sub(r"<[^>]*>", "", clean_text)

    # Remove high-ASCII codes @NNN;
    clean_text = re.sub(r"@\d+;", "", clean_text)

    # Remove alternatives, keep first [a:b] -> a
    clean_text = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", clean_text)

    # Count words (separated by . , or space)
    words = re.split(r"[.,\s]+", clean_text)
    words = [w for w in words if w.strip()]
    result.word_count = len(words)

    # Check compound glyphs
    for compound in EVA_COMPOUNDS:
        count = clean_text.count(compound)
        if count > 0:
            result.compound_counts[compound] = count

    # Validate characters
    i = 0
    while i < len(clean_text):
        char = clean_text[i]

        # Skip whitespace and separators
        if char in EVA_SEPARATORS or char in EVA_LINE_MARKERS or char in EVA_EDITORIAL:
            i += 1
            continue

        # Check if it's a known character
        if char.lower() in EVA_SINGLE:
            key = char.lower()
            result.char_frequencies[key] = result.char_frequencies.get(key, 0) + 1
            result.char_count += 1
        elif char.isdigit():
            # Numbers in context of @NNN; are ok, standalone might be uncertain
            i += 1
            continue
        elif char in "\t\n\r":
            # Whitespace variants
            i += 1
            continue
        else:
            # Unknown character
            result.add_unknown(char, i)
            if strict:
                result.add_error(f"Unknown character '{char}' at position {i}")

        i += 1

    # Add summary warnings
    if result.unknown_chars:
        result.add_warning(
            f"Found {len(result.unknown_chars)} unknown character types: " f"{result.unknown_chars}"
        )

    return result


def get_character_info(char: str) -> CharacterInfo:
    """Get information about an EVA character.

    Looks up detailed information about a character including its
    category, typical frequency, and description.

    Args:
        char: Single character or compound glyph (e.g., 'a', 'ch', 'cth').

    Returns:
        CharacterInfo with details about the character. For unknown
        characters, returns info with category UNKNOWN.

    Example:
        >>> info = get_character_info('ch')
        >>> info.category
        <CharacterCategory.COMPOUND: 'compound'>
        >>> info.frequency
        'high'

        >>> info = get_character_info('a')
        >>> info.description
        'Common vowel-like, often word-initial'

        >>> info = get_character_info('.')
        >>> info.category
        <CharacterCategory.SPECIAL: 'special'>
    """
    char_lower = char.lower()

    if char_lower in CHARACTER_INFO:
        return CHARACTER_INFO[char_lower]

    # Check category - these fallbacks are for defensive programming
    # All EVA_BASIC and EVA_RARE chars are in CHARACTER_INFO
    if char_lower in EVA_BASIC:  # pragma: no cover
        return CharacterInfo(char, CharacterCategory.BASIC, "unknown", "Basic EVA character")
    elif char_lower in EVA_RARE:  # pragma: no cover
        return CharacterInfo(char, CharacterCategory.RARE, "rare", "Rare EVA character")
    elif char in EVA_SEPARATORS:
        return CharacterInfo(char, CharacterCategory.SPECIAL, "high", "Word/text separator")
    elif char in EVA_EDITORIAL:
        return CharacterInfo(char, CharacterCategory.EDITORIAL, "n/a", "Editorial marker")
    else:
        return CharacterInfo(char, CharacterCategory.UNKNOWN, "unknown", "Unknown character")


def is_valid_eva_word(word: str) -> bool:
    """Check if a word contains only valid EVA characters.

    Args:
        word: A single word (no separators). Case insensitive.

    Returns:
        True if all characters are valid single EVA characters,
        False otherwise.

    Example:
        >>> is_valid_eva_word("fachys")
        True
        >>> is_valid_eva_word("hello!")
        False
        >>> is_valid_eva_word("")
        True
    """
    for char in word.lower():
        if char not in EVA_SINGLE:
            return False
    return True


def count_compound_glyphs(text: str) -> dict[str, int]:
    """Count occurrences of compound glyphs in text.

    Compound glyphs are multi-character sequences that represent
    single glyphs in EVA (ch, sh, cth, ckh, cph, cfh).

    Args:
        text: EVA transcription text.

    Returns:
        Dictionary mapping compound glyphs to their counts.
        Only compounds that appear at least once are included.

    Example:
        >>> counts = count_compound_glyphs("chedy.qokedy.chol.shedy")
        >>> counts.get('ch', 0)
        2
        >>> counts.get('sh', 0)
        1
        >>> 'cth' in counts
        False
    """
    counts: dict[str, int] = {}
    text_lower = text.lower()
    for compound in EVA_COMPOUNDS:
        count = text_lower.count(compound)
        if count > 0:
            counts[compound] = count
    return counts


# Module test
if __name__ == "__main__":  # pragma: no cover
    # Test validation
    test_text = "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy"

    print("Testing EVA validation")
    print(f"Text: {test_text}")
    print()

    result = validate_eva_text(test_text)

    print(f"Valid: {result.is_valid}")
    print(f"Characters: {result.char_count}")
    print(f"Words: {result.word_count}")
    print(f"Compounds: {result.compound_counts}")
    print(f"Warnings: {result.warnings}")
    print()

    print("Character frequencies:")
    for char, count in sorted(result.char_frequencies.items(), key=lambda x: -x[1])[:10]:
        info = get_character_info(char)
        print(f"  {char}: {count} ({info.description})")
