"""
VCAT - Voynich Computational Analysis Toolkit
=============================================

Core library for VCAT data processing, providing EVA (Extensible Voynich
Alphabet) character set validation and text processing utilities.

This module exports:

Character Sets:
    EVA_BASIC: Set of 17 basic EVA characters (a, c, d, e, h, i, k, l, m, n, o, p, q, r, s, t, y)
    EVA_RARE: Set of 8 rare EVA characters (f, g, x, j, v, b, u, z)
    EVA_SINGLE: Union of EVA_BASIC and EVA_RARE
    EVA_COMPOUNDS: Set of compound glyphs (ch, sh, cth, ckh, cph, cfh)
    EVA_SEPARATORS: Set of word/text separators (., ,, space)
    EVA_EDITORIAL: Set of editorial/uncertainty markers
    EVA_ALL_CHARS: All valid characters in EVA transcription text

Classes:
    CharacterCategory: Enum for character categories (BASIC, RARE, COMPOUND, etc.)
    CharacterInfo: NamedTuple with character metadata
    ValidationResult: Dataclass with text validation results

Functions:
    validate_eva_text: Validate EVA transcription text
    get_character_info: Get information about an EVA character
    is_valid_eva_word: Check if a word contains only valid EVA characters
    count_compound_glyphs: Count compound glyph occurrences in text

Exceptions:
    VCATError: Base exception for all VCAT errors
    ParseError: Parser-related errors
    ValidationError: Validation-related errors
    BuildError: Build process errors

Logging:
    get_logger: Get a configured logger instance
    configure_logging: Configure logging for the package

Example:
    >>> from vcat import validate_eva_text, EVA_BASIC
    >>> result = validate_eva_text("fachys.ykal.ar.ataiin")
    >>> result.is_valid
    True
    >>> result.word_count
    4
    >>> 'a' in EVA_BASIC
    True

Author: Noah Chelednik
License: MIT
"""

from __future__ import annotations

from .eva_charset import (
    CHARACTER_INFO,
    EVA_ALL_CHARS,
    EVA_BASIC,
    EVA_COMPOUNDS,
    EVA_EDITORIAL,
    EVA_LINE_MARKERS,
    EVA_RARE,
    EVA_SEPARATORS,
    EVA_SINGLE,
    CharacterCategory,
    CharacterInfo,
    ValidationResult,
    count_compound_glyphs,
    get_character_info,
    is_valid_eva_word,
    validate_eva_text,
)
from .exceptions import (
    BuildError,
    CharacterValidationError,
    ConfigurationError,
    DataIntegrityError,
    ExportError,
    InvalidFormatError,
    MalformedLocusError,
    MissingPageContextError,
    ParseError,
    SchemaValidationError,
    SmokeTestError,
    SourceNotFoundError,
    ValidationError,
    VCATError,
)
from .logging import configure_logging, get_logger

__version__ = "0.2.3"
__author__ = "Noah Chelednik"

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Character sets
    "EVA_BASIC",
    "EVA_RARE",
    "EVA_SINGLE",
    "EVA_COMPOUNDS",
    "EVA_SEPARATORS",
    "EVA_LINE_MARKERS",
    "EVA_EDITORIAL",
    "EVA_ALL_CHARS",
    # Character info
    "CHARACTER_INFO",
    # Classes
    "CharacterCategory",
    "CharacterInfo",
    "ValidationResult",
    # Functions
    "validate_eva_text",
    "get_character_info",
    "is_valid_eva_word",
    "count_compound_glyphs",
    # Exceptions
    "VCATError",
    "ParseError",
    "InvalidFormatError",
    "MalformedLocusError",
    "MissingPageContextError",
    "ValidationError",
    "SchemaValidationError",
    "CharacterValidationError",
    "DataIntegrityError",
    "BuildError",
    "SourceNotFoundError",
    "ExportError",
    "SmokeTestError",
    "ConfigurationError",
    # Logging
    "get_logger",
    "configure_logging",
]
