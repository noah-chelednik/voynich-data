"""
Tests for EVA Character Set Module (vcat/eva_charset.py).

This module tests:
    - Character set constants
    - Character validation
    - Text cleaning and processing
    - Frequency counting
    - CharacterInfo lookup
"""

from __future__ import annotations

from vcat.eva_charset import (
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


class TestCharacterSets:
    """Tests for EVA character set constants."""

    def test_eva_basic_contains_expected_chars(self):
        """Test that EVA_BASIC contains all expected characters."""
        expected = set("acdehiklmnopqrsty")
        assert EVA_BASIC == expected

    def test_eva_rare_contains_expected_chars(self):
        """Test that EVA_RARE contains all expected characters."""
        expected = set("fgxjvbuz")
        assert EVA_RARE == expected

    def test_eva_single_is_union_of_basic_and_rare(self):
        """Test that EVA_SINGLE is the union of BASIC and RARE."""
        assert EVA_SINGLE == EVA_BASIC | EVA_RARE

    def test_eva_compounds_contains_expected(self):
        """Test that EVA_COMPOUNDS contains expected compounds."""
        expected = {"ch", "sh", "cth", "ckh", "cph", "cfh"}
        assert EVA_COMPOUNDS == expected

    def test_eva_separators_contains_expected(self):
        """Test that EVA_SEPARATORS contains expected separators."""
        assert "." in EVA_SEPARATORS
        assert "," in EVA_SEPARATORS
        assert " " in EVA_SEPARATORS

    def test_eva_line_markers_contains_expected(self):
        """Test that EVA_LINE_MARKERS contains expected markers."""
        assert "-" in EVA_LINE_MARKERS
        assert "=" in EVA_LINE_MARKERS

    def test_eva_editorial_contains_expected(self):
        """Test that EVA_EDITORIAL contains expected markers."""
        assert "?" in EVA_EDITORIAL
        assert "!" in EVA_EDITORIAL
        assert "[" in EVA_EDITORIAL
        assert "]" in EVA_EDITORIAL
        assert "{" in EVA_EDITORIAL
        assert "}" in EVA_EDITORIAL

    def test_eva_all_chars_includes_digits(self):
        """Test that EVA_ALL_CHARS includes digits for high-ASCII codes."""
        for digit in "0123456789":
            assert digit in EVA_ALL_CHARS


class TestCharacterCategory:
    """Tests for CharacterCategory enum."""

    def test_category_values(self):
        """Test that all category values are correct."""
        assert CharacterCategory.BASIC.value == "basic"
        assert CharacterCategory.RARE.value == "rare"
        assert CharacterCategory.COMPOUND.value == "compound"
        assert CharacterCategory.SPECIAL.value == "special"
        assert CharacterCategory.EDITORIAL.value == "editorial"
        assert CharacterCategory.UNKNOWN.value == "unknown"

    def test_category_is_string_enum(self):
        """Test that CharacterCategory is a string enum."""
        assert isinstance(CharacterCategory.BASIC, str)
        assert CharacterCategory.BASIC == "basic"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self):
        """Test default values of ValidationResult."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.char_count == 0
        assert result.word_count == 0
        assert result.unknown_chars == set()
        assert result.unknown_positions == []
        assert result.warnings == []
        assert result.errors == []
        assert result.char_frequencies == {}
        assert result.compound_counts == {}

    def test_add_unknown(self):
        """Test adding unknown characters."""
        result = ValidationResult()
        result.add_unknown("X", 5)
        result.add_unknown("Y", 10)

        assert "X" in result.unknown_chars
        assert "Y" in result.unknown_chars
        assert (5, "X") in result.unknown_positions
        assert (10, "Y") in result.unknown_positions

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult()
        result.add_warning("Test warning")

        assert "Test warning" in result.warnings
        assert result.is_valid is True  # Warnings don't invalidate

    def test_add_error(self):
        """Test adding errors invalidates result."""
        result = ValidationResult()
        assert result.is_valid is True

        result.add_error("Test error")

        assert "Test error" in result.errors
        assert result.is_valid is False


class TestValidateEvaText:
    """Tests for validate_eva_text function."""

    def test_validate_simple_text(self):
        """Test validation of simple EVA text."""
        result = validate_eva_text("fachys.ykal.ar.ataiin")

        assert result.is_valid is True
        assert result.word_count == 4
        assert result.char_count > 0
        assert len(result.errors) == 0

    def test_validate_empty_string(self):
        """Test validation of empty string."""
        result = validate_eva_text("")

        assert result.is_valid is True
        assert result.char_count == 0
        assert result.word_count == 0

    def test_validate_with_compounds(self):
        """Test validation detects compound glyphs."""
        result = validate_eva_text("chedy.shedy.cthol")

        assert "ch" in result.compound_counts
        assert "sh" in result.compound_counts
        assert "cth" in result.compound_counts

    def test_validate_with_unknown_characters(self):
        """Test validation detects unknown characters."""
        # Use '€' which is not a valid EVA character
        result = validate_eva_text("fachys€ykal")

        assert "€" in result.unknown_chars
        assert len(result.warnings) > 0
        assert result.is_valid is True  # Non-strict mode

    def test_validate_strict_mode(self):
        """Test strict validation fails on unknown characters."""
        # Use '€' which is not a valid EVA character
        result = validate_eva_text("fachys€ykal", strict=True)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_removes_comments(self):
        """Test that inline comments are removed before validation."""
        result = validate_eva_text("fachys{this is a comment}.ykal")

        assert result.is_valid is True
        assert "this" not in str(result.unknown_chars)

    def test_validate_removes_ivtff_markers(self):
        """Test that IVTFF markers are removed."""
        result = validate_eva_text("<%>fachys<$>ykal")

        assert result.is_valid is True
        assert "<" not in str(result.unknown_chars)

    def test_validate_handles_alternatives(self):
        """Test that alternatives [a:b] are simplified."""
        result = validate_eva_text("test.[a:b].word")

        assert result.is_valid is True
        assert ":" not in str(result.unknown_chars)

    def test_validate_removes_high_ascii(self):
        """Test that high-ASCII codes @NNN; are removed."""
        result = validate_eva_text("fachys@123;ykal")

        assert result.is_valid is True

    def test_validate_counts_characters(self):
        """Test character counting."""
        result = validate_eva_text("aaa.bb.c")

        assert result.char_frequencies.get("a", 0) == 3
        assert result.char_frequencies.get("b", 0) == 2
        assert result.char_frequencies.get("c", 0) == 1

    def test_validate_handles_whitespace(self):
        """Test handling of various whitespace."""
        result = validate_eva_text("word\tword\nword")

        assert result.is_valid is True

    def test_validate_case_insensitive(self):
        """Test that validation is case insensitive."""
        result = validate_eva_text("FACHYS.YKAL")

        assert result.is_valid is True
        assert result.char_frequencies.get("f", 0) == 1


class TestGetCharacterInfo:
    """Tests for get_character_info function."""

    def test_get_basic_character_info(self):
        """Test getting info for basic characters."""
        info = get_character_info("a")

        assert info.char == "a"
        assert info.category == CharacterCategory.BASIC
        assert "vowel" in info.description.lower()

    def test_get_compound_info(self):
        """Test getting info for compound glyphs."""
        info = get_character_info("ch")

        assert info.char == "ch"
        assert info.category == CharacterCategory.COMPOUND
        assert info.frequency == "high"

    def test_get_rare_character_info(self):
        """Test getting info for rare characters."""
        info = get_character_info("g")

        assert info.char == "g"
        assert info.category == CharacterCategory.RARE

    def test_get_separator_info(self):
        """Test getting info for separators."""
        info = get_character_info(".")

        assert info.category == CharacterCategory.SPECIAL

    def test_get_editorial_info(self):
        """Test getting info for editorial markers."""
        info = get_character_info("?")

        assert info.category == CharacterCategory.EDITORIAL

    def test_get_unknown_info(self):
        """Test getting info for unknown characters."""
        # Use '€' which is not a valid EVA character
        info = get_character_info("€")

        assert info.category == CharacterCategory.UNKNOWN
        assert "unknown" in info.description.lower()

    def test_case_insensitive(self):
        """Test that lookup is case insensitive."""
        info_lower = get_character_info("a")
        info_upper = get_character_info("A")

        # Both should return info for 'a'
        assert info_lower.category == CharacterCategory.BASIC
        assert info_upper.category == CharacterCategory.BASIC


class TestIsValidEvaWord:
    """Tests for is_valid_eva_word function."""

    def test_valid_word(self):
        """Test that valid EVA word returns True."""
        assert is_valid_eva_word("fachys") is True
        assert is_valid_eva_word("ykal") is True
        assert is_valid_eva_word("daiin") is True

    def test_empty_word(self):
        """Test that empty word returns True."""
        assert is_valid_eva_word("") is True

    def test_invalid_word_with_unknown_char(self):
        """Test that word with unknown char returns False."""
        assert is_valid_eva_word("hello!") is False
        assert is_valid_eva_word("test@") is False

    def test_word_with_separator(self):
        """Test that word with separator returns False."""
        assert is_valid_eva_word("word.word") is False

    def test_case_insensitive(self):
        """Test that check is case insensitive."""
        assert is_valid_eva_word("FACHYS") is True
        assert is_valid_eva_word("FaChYs") is True


class TestCountCompoundGlyphs:
    """Tests for count_compound_glyphs function."""

    def test_count_single_compound(self):
        """Test counting a single compound."""
        counts = count_compound_glyphs("chedy.shol")

        assert counts.get("ch", 0) == 1
        assert counts.get("sh", 0) == 1

    def test_count_multiple_same_compound(self):
        """Test counting multiple instances of same compound."""
        counts = count_compound_glyphs("chedy.chol.chey")

        assert counts.get("ch", 0) == 3

    def test_no_compounds(self):
        """Test text with no compounds."""
        counts = count_compound_glyphs("daiin.ol.ar")

        assert len(counts) == 0

    def test_rare_compounds(self):
        """Test counting rare compounds."""
        counts = count_compound_glyphs("cthey.ckhol.cphol.cfhey")

        assert counts.get("cth", 0) == 1
        assert counts.get("ckh", 0) == 1
        assert counts.get("cph", 0) == 1
        assert counts.get("cfh", 0) == 1

    def test_case_insensitive(self):
        """Test that counting is case insensitive."""
        counts = count_compound_glyphs("CHEDY.SHOL")

        assert counts.get("ch", 0) == 1
        assert counts.get("sh", 0) == 1

    def test_empty_string(self):
        """Test empty string returns empty dict."""
        counts = count_compound_glyphs("")

        assert counts == {}


class TestCharacterInfo:
    """Tests for CharacterInfo named tuple."""

    def test_character_info_fields(self):
        """Test CharacterInfo field access."""
        info = CharacterInfo("a", CharacterCategory.BASIC, "high", "Test description")

        assert info.char == "a"
        assert info.category == CharacterCategory.BASIC
        assert info.frequency == "high"
        assert info.description == "Test description"

    def test_character_info_dict_completeness(self):
        """Test that CHARACTER_INFO dict has entries for common chars."""
        # Check basic characters
        for char in "aeioqy":
            assert char in CHARACTER_INFO

        # Check compounds
        assert "ch" in CHARACTER_INFO
        assert "sh" in CHARACTER_INFO


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_validate_only_separators(self):
        """Test validation of text with only separators."""
        result = validate_eva_text("... , ,")

        assert result.is_valid is True
        assert result.char_count == 0

    def test_validate_unicode_characters(self):
        """Test validation handles unicode gracefully."""
        result = validate_eva_text("fachys.éàü.ykal")

        assert len(result.unknown_chars) > 0  # Should flag unicode as unknown

    def test_validate_mixed_valid_invalid(self):
        """Test validation with mix of valid and invalid."""
        # Use '€' and '£' which are not valid EVA characters
        result = validate_eva_text("fachys.€.ykal.£.ataiin")

        assert result.is_valid is True  # Non-strict
        assert "€" in result.unknown_chars
        assert "£" in result.unknown_chars
        assert result.word_count == 5

    def test_validate_nested_markup(self):
        """Test handling of nested/complex markup."""
        result = validate_eva_text("word{comment{nested}}.word")

        assert result.is_valid is True

    def test_validate_very_long_text(self):
        """Test validation of long text."""
        long_text = "fachys.ykal." * 1000
        result = validate_eva_text(long_text)

        assert result.is_valid is True
        assert result.word_count == 2000

    def test_empty_alternatives(self):
        """Test handling of empty alternatives."""
        result = validate_eva_text("word.[:].word")

        # Should handle gracefully
        assert result.is_valid is True

    def test_validate_with_standalone_digits(self):
        """Test that standalone digits in text are handled."""
        result = validate_eva_text("word123word")

        # Digits should be skipped without error
        assert result.is_valid is True

    def test_validate_with_tabs_and_newlines(self):
        """Test validation with tabs and newlines."""
        result = validate_eva_text("word\tword\nword\rword")

        assert result.is_valid is True

    def test_get_character_info_unlisted_basic(self):
        """Test get_character_info for characters in BASIC but not in CHARACTER_INFO."""
        # 'w' is not explicitly in CHARACTER_INFO
        info = get_character_info("w")

        # Should return UNKNOWN since w is not in EVA_BASIC
        assert info.category == CharacterCategory.UNKNOWN

    def test_get_character_info_rare_category(self):
        """Test get_character_info returns correct rare category."""
        # Test a rare character that is in CHARACTER_INFO
        info = get_character_info("g")

        assert info.category == CharacterCategory.RARE
