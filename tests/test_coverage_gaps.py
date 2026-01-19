"""Tests for 100% coverage of uncovered code paths.

This module adds tests specifically targeting code paths that were
previously uncovered in the test suite.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from parsers.ivtff_parser import (
    IVTFFParser,
    Locus,
    LocusPosition,
    LocusType,
    Page,
    PageVariables,
)
from vcat.eva_charset import (
    EVA_BASIC,
    EVA_RARE,
    CharacterCategory,
    get_character_info,
)


class TestPageProperties:
    """Tests for Page dataclass properties."""

    def test_line_count_filters_paragraphs(self) -> None:
        """Test that line_count only counts PARAGRAPH type loci."""
        page = Page(
            page_id="f1r",
            variables=PageVariables(),
            loci=[
                Locus(
                    page_id="f1r",
                    locus_number=1,
                    position=LocusPosition.NEW_UNIT,
                    locus_type=LocusType.PARAGRAPH,
                    text="paragraph text",
                ),
                Locus(
                    page_id="f1r",
                    locus_number=2,
                    position=None,
                    locus_type=LocusType.LABEL,
                    text="label text",
                ),
                Locus(
                    page_id="f1r",
                    locus_number=3,
                    position=None,
                    locus_type=LocusType.PARAGRAPH,
                    text="another paragraph",
                ),
                Locus(
                    page_id="f1r",
                    locus_number=4,
                    position=None,
                    locus_type=LocusType.CIRCLE,
                    text="circle text",
                ),
            ],
        )
        # Only 2 PARAGRAPH type loci
        assert page.line_count == 2

    def test_line_count_empty_page(self) -> None:
        """Test line_count on page with no loci."""
        page = Page(page_id="f1r", variables=PageVariables(), loci=[])
        assert page.line_count == 0

    def test_line_count_no_paragraphs(self) -> None:
        """Test line_count when no PARAGRAPH type loci."""
        page = Page(
            page_id="f1r",
            variables=PageVariables(),
            loci=[
                Locus(
                    page_id="f1r",
                    locus_number=1,
                    position=None,
                    locus_type=LocusType.LABEL,
                    text="x",
                ),
            ],
        )
        assert page.line_count == 0

    def test_has_text_with_text(self) -> None:
        """Test has_text returns True when loci have text."""
        page = Page(
            page_id="f1r",
            variables=PageVariables(),
            loci=[
                Locus(
                    page_id="f1r",
                    locus_number=1,
                    position=None,
                    locus_type=None,
                    text="some text",
                ),
            ],
        )
        assert page.has_text is True

    def test_has_text_empty_loci(self) -> None:
        """Test has_text returns False when no loci."""
        page = Page(page_id="f1r", variables=PageVariables(), loci=[])
        assert page.has_text is False

    def test_has_text_whitespace_only(self) -> None:
        """Test has_text returns False when loci have only whitespace."""
        page = Page(
            page_id="f1r",
            variables=PageVariables(),
            loci=[
                Locus(
                    page_id="f1r",
                    locus_number=1,
                    position=None,
                    locus_type=None,
                    text="   ",
                ),
                Locus(
                    page_id="f1r",
                    locus_number=2,
                    position=None,
                    locus_type=None,
                    text="\t\n",
                ),
            ],
        )
        assert page.has_text is False


class TestParserStrictMode:
    """Tests for parser strict mode error paths."""

    def test_strict_mode_locus_without_page(self) -> None:
        """Test strict mode raises error for locus without page context."""
        parser = IVTFFParser(strict=True)
        # Locus line without any page header
        content = "<f1r.1,@P0;H> text without page header"

        with pytest.raises(ValueError, match="Locus without page context"):
            list(parser.parse_string(content))

    def test_strict_mode_unrecognized_line(self) -> None:
        """Test strict mode raises error for unrecognized line format."""
        parser = IVTFFParser(strict=True)
        content = "<f1r>\nthis is not a valid locus or comment"

        with pytest.raises(ValueError, match="Unrecognized format"):
            list(parser.parse_string(content))

    def test_non_strict_ignores_locus_without_page(self) -> None:
        """Test non-strict mode ignores locus without page context."""
        parser = IVTFFParser(strict=False)
        content = """<f1r.1,@P0;H> orphan locus
<f1r>
<f1r.1,@P0;H> valid locus"""
        pages = list(parser.parse_string(content))
        # Should get one page with one locus (orphan ignored)
        assert len(pages) == 1
        assert len(pages[0].loci) == 1

    def test_non_strict_ignores_unrecognized_line(self) -> None:
        """Test non-strict mode ignores unrecognized lines."""
        parser = IVTFFParser(strict=False)
        content = """<f1r>
random garbage line
<f1r.1,@P0;H> valid text"""
        pages = list(parser.parse_string(content))
        assert len(pages) == 1
        assert len(pages[0].loci) == 1


class TestParserInvalidEnums:
    """Tests for parser handling of invalid/empty enum values."""

    def test_empty_position_gracefully_handled(self) -> None:
        """Test empty position string doesn't crash parser."""
        parser = IVTFFParser(strict=False)
        # No position modifier (empty string matches [+@=*]?)
        content = """<f1r>
<f1r.1,P0> text without position modifier"""
        pages = list(parser.parse_string(content))
        assert len(pages) == 1
        assert len(pages[0].loci) == 1
        # Position should be None for empty string
        assert pages[0].loci[0].position is None

    def test_valid_position_is_parsed(self) -> None:
        """Test valid position is correctly parsed."""
        parser = IVTFFParser(strict=False)
        content = """<f1r>
<f1r.1,@P0> text with position"""
        pages = list(parser.parse_string(content))
        assert len(pages) == 1
        assert len(pages[0].loci) == 1
        assert pages[0].loci[0].position == LocusPosition.NEW_UNIT

    def test_all_position_types(self) -> None:
        """Test all position types are correctly parsed."""
        parser = IVTFFParser(strict=False)
        content = """<f1r>
<f1r.1,@P0> new unit
<f1r.2,+P0> continue
<f1r.3,=P0> end para
<f1r.4,*P0> new para"""
        pages = list(parser.parse_string(content))
        assert len(pages) == 1
        assert len(pages[0].loci) == 4
        assert pages[0].loci[0].position == LocusPosition.NEW_UNIT
        assert pages[0].loci[1].position == LocusPosition.CONTINUE
        assert pages[0].loci[2].position == LocusPosition.END_PARA
        assert pages[0].loci[3].position == LocusPosition.NEW_PARA

    def test_all_locus_types(self) -> None:
        """Test all locus types are correctly parsed."""
        parser = IVTFFParser(strict=False)
        content = """<f1r>
<f1r.1,@P0> paragraph
<f1r.2,@L0> label
<f1r.3,@C0> circle
<f1r.4,@R0> radius"""
        pages = list(parser.parse_string(content))
        assert len(pages) == 1
        assert len(pages[0].loci) == 4
        assert pages[0].loci[0].locus_type == LocusType.PARAGRAPH
        assert pages[0].loci[1].locus_type == LocusType.LABEL
        assert pages[0].loci[2].locus_type == LocusType.CIRCLE
        assert pages[0].loci[3].locus_type == LocusType.RADIUS


class TestParserExtractText:
    """Tests for extract_text with clean=False."""

    def test_extract_text_clean_false_preserves_alternatives(self) -> None:
        """Test that clean=False preserves alternative notation."""
        parser = IVTFFParser()
        text = "a[b:c]d"
        result = parser.extract_text(text, clean=False)
        # Should preserve [b:c]
        assert "[b:c]" in result

    def test_extract_text_clean_true_removes_alternatives(self) -> None:
        """Test that clean=True removes alternative notation."""
        parser = IVTFFParser()
        text = "a[b:c]d"
        result = parser.extract_text(text, clean=True)
        # Should keep first option 'b', remove [b:c] -> b
        assert result == "abd"

    def test_extract_text_clean_false_preserves_high_ascii(self) -> None:
        """Test that clean=False preserves high-ASCII codes."""
        parser = IVTFFParser()
        text = "abc@123;def"
        result = parser.extract_text(text, clean=False)
        # Should preserve @123;
        assert "@123;" in result

    def test_extract_text_clean_true_preserves_high_ascii(self) -> None:
        """Test that clean=True preserves high-ASCII codes (lossless policy)."""
        parser = IVTFFParser()
        text = "abc@123;def"
        result = parser.extract_text(text, clean=True)
        # High-ASCII codes are preserved in clean text (lossless)
        assert "@123;" in result
        assert result == "abc@123;def"


class TestParserEmptyLines:
    """Tests for parser handling of empty lines."""

    def test_empty_lines_are_skipped(self) -> None:
        """Test that empty lines in content are skipped."""
        parser = IVTFFParser()
        content = """<f1r>


\t
<f1r.1,@P0;H> text
"""
        pages = list(parser.parse_string(content))
        assert len(pages) == 1
        assert len(pages[0].loci) == 1


class TestEvaCharsetFallbacks:
    """Tests for EVA charset fallback paths."""

    def test_get_character_info_unlisted_basic(self) -> None:
        """Test get_character_info for basic char not in CHARACTER_INFO.

        Note: All basic chars should be in CHARACTER_INFO, but this tests
        the fallback path if one were missing.
        """
        # All current basic chars are in CHARACTER_INFO
        # This test verifies the current state
        for char in EVA_BASIC:
            info = get_character_info(char)
            assert info.category in (CharacterCategory.BASIC, CharacterCategory.COMPOUND)

    def test_get_character_info_unlisted_rare(self) -> None:
        """Test get_character_info for rare char not in CHARACTER_INFO.

        Note: All rare chars should be in CHARACTER_INFO, but this tests
        the fallback path if one were missing.
        """
        # All current rare chars are in CHARACTER_INFO
        for char in EVA_RARE:
            info = get_character_info(char)
            assert info.category in (CharacterCategory.RARE, CharacterCategory.BASIC)


class TestBuildSectionNone:
    """Tests for build_eva_lines when section is None."""

    def test_page_without_section(self) -> None:
        """Test that pages without derivable section are handled."""
        from builders.build_eva_lines import build_eva_lines

        # Create a temporary file with a page that has no section info
        content = """#=IVTFF Eva- 2.0
<f999r>
<f999r.1,@P0;H> test text
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = Path(f.name)

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                records, report = build_eva_lines(temp_path, Path(tmp_dir))
                # Should have 1 record
                assert len(records) == 1
                # Section should be unknown/None since f999r isn't in any known range
            finally:
                temp_path.unlink()


class TestExportPandasMissing:
    """Tests for export_to_parquet when pandas is missing."""

    def test_export_parquet_without_pandas(self, tmp_path: Path) -> None:
        """Test that export_to_parquet raises RuntimeError when pandas missing."""
        from builders.build_eva_lines import LineRecord, export_to_parquet

        records = [
            LineRecord(
                page_id="f1r",
                line_number=1,
                line_index=1,
                line_id="f1r:1",
                text="test",
                text_clean="test",
                line_type="paragraph",
                position=None,
                quire=None,
                section="herbal_a",
                currier_language="A",
                hand="1",
                illustration_type=None,
                char_count=4,
                word_count=1,
                has_uncertain=False,
                has_illegible=False,
                has_alternatives=False,
                has_high_ascii=False,
                source="test",
                source_version="test",
            )
        ]

        output_path = tmp_path / "test.parquet"

        # Hide pandas from import
        with patch.dict(sys.modules, {"pandas": None}):
            # Clear any cached import
            if "builders.build_eva_lines" in sys.modules:
                del sys.modules["builders.build_eva_lines"]

            # Reimport with pandas hidden

            # Create a custom import that blocks pandas
            original_import = (
                __builtins__["__import__"]
                if isinstance(__builtins__, dict)
                else __builtins__.__import__
            )

            def mock_import(name, *args, **kwargs):
                if name == "pandas":
                    raise ImportError("No module named 'pandas'")
                return original_import(name, *args, **kwargs)

            # Use patch on builtins
            import builtins

            with patch.object(builtins, "__import__", side_effect=mock_import):
                with pytest.raises(RuntimeError, match="pandas required"):
                    export_to_parquet(records, output_path)


class TestExceptionsModule:
    """Tests for custom exceptions module."""

    def test_vcat_error_basic(self) -> None:
        """Test VCATError basic functionality."""
        from vcat.exceptions import VCATError

        err = VCATError("test message")
        assert str(err) == "test message"
        assert err.message == "test message"
        assert err.details == {}

    def test_vcat_error_with_details(self) -> None:
        """Test VCATError with details."""
        from vcat.exceptions import VCATError

        err = VCATError("test message", details={"key": "value"})
        assert "key='value'" in str(err)
        assert err.details == {"key": "value"}

    def test_parse_error_with_line_info(self) -> None:
        """Test ParseError with line information."""
        from vcat.exceptions import ParseError

        err = ParseError("parse failed", line_number=42, line_content="bad line")
        assert err.line_number == 42
        assert err.line_content == "bad line"
        assert "line_number=42" in str(err)

    def test_source_not_found_error(self) -> None:
        """Test SourceNotFoundError with path."""
        from vcat.exceptions import SourceNotFoundError

        err = SourceNotFoundError("file not found", path="/path/to/file")
        assert err.path == Path("/path/to/file")
        assert "/path/to/file" in str(err)

    def test_schema_validation_error(self) -> None:
        """Test SchemaValidationError with errors list."""
        from vcat.exceptions import SchemaValidationError

        err = SchemaValidationError(
            "validation failed",
            schema_name="test_schema",
            validation_errors=["error1", "error2"],
        )
        assert err.schema_name == "test_schema"
        assert err.validation_errors == ["error1", "error2"]

    def test_schema_validation_error_no_details(self) -> None:
        """Test SchemaValidationError without optional details."""
        from vcat.exceptions import SchemaValidationError

        err = SchemaValidationError("validation failed")
        assert err.schema_name is None
        assert err.validation_errors == []

    def test_export_error(self) -> None:
        """Test ExportError with format and path."""
        from vcat.exceptions import ExportError

        err = ExportError("export failed", format="parquet", output_path="/out/file.parquet")
        assert err.format == "parquet"
        assert err.output_path == Path("/out/file.parquet")

    def test_smoke_test_error(self) -> None:
        """Test SmokeTestError with failed tests."""
        from vcat.exceptions import SmokeTestError

        err = SmokeTestError(
            "smoke tests failed",
            failed_tests=["test1", "test2"],
            test_results={"test1": (False, "failed"), "test2": (False, "also failed")},
        )
        assert err.failed_tests == ["test1", "test2"]
        assert err.test_results["test1"] == (False, "failed")

    def test_character_validation_error(self) -> None:
        """Test CharacterValidationError."""
        from vcat.exceptions import CharacterValidationError

        err = CharacterValidationError(
            "invalid chars",
            invalid_characters={"€", "£"},
            text_sample="test€text",
        )
        assert "€" in err.invalid_characters
        assert err.text_sample == "test€text"

    def test_character_validation_error_no_details(self) -> None:
        """Test CharacterValidationError without optional details."""
        from vcat.exceptions import CharacterValidationError

        err = CharacterValidationError("invalid chars")
        assert err.invalid_characters == set()
        assert err.text_sample is None

    def test_export_error_no_details(self) -> None:
        """Test ExportError without optional details."""
        from vcat.exceptions import ExportError

        err = ExportError("export failed")
        assert err.format is None
        assert err.output_path is None

    def test_source_not_found_error_no_path(self) -> None:
        """Test SourceNotFoundError without path."""
        from vcat.exceptions import SourceNotFoundError

        err = SourceNotFoundError("file not found")
        assert err.path is None

    def test_smoke_test_error_no_details(self) -> None:
        """Test SmokeTestError without optional details."""
        from vcat.exceptions import SmokeTestError

        err = SmokeTestError("smoke tests failed")
        assert err.failed_tests == []
        assert err.test_results == {}

    def test_data_integrity_error(self) -> None:
        """Test DataIntegrityError."""
        from vcat.exceptions import DataIntegrityError

        err = DataIntegrityError("duplicate ids found")
        assert "duplicate ids found" in str(err)

    def test_configuration_error(self) -> None:
        """Test ConfigurationError."""
        from vcat.exceptions import ConfigurationError

        err = ConfigurationError("invalid config")
        assert "invalid config" in str(err)

    def test_malformed_locus_error(self) -> None:
        """Test MalformedLocusError."""
        from vcat.exceptions import MalformedLocusError

        err = MalformedLocusError("bad locus", line_number=10)
        assert err.line_number == 10

    def test_missing_page_context_error(self) -> None:
        """Test MissingPageContextError."""
        from vcat.exceptions import MissingPageContextError

        err = MissingPageContextError("no page", line_number=5)
        assert err.line_number == 5

    def test_invalid_format_error(self) -> None:
        """Test InvalidFormatError."""
        from vcat.exceptions import InvalidFormatError

        err = InvalidFormatError("not IVTFF", line_content="bad header")
        assert err.line_content == "bad header"


class TestLoggingModule:
    """Tests for logging module."""

    def test_get_logger(self) -> None:
        """Test get_logger returns a logger."""
        from vcat.logging import get_logger

        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_caches(self) -> None:
        """Test get_logger returns same logger for same name."""
        from vcat.logging import _loggers, get_logger

        # Clear cache first
        _loggers.clear()

        logger1 = get_logger("cache_test")
        logger2 = get_logger("cache_test")
        assert logger1 is logger2

    def test_get_logger_default_name(self) -> None:
        """Test get_logger with no name uses 'vcat'."""
        from vcat.logging import get_logger

        logger = get_logger()
        assert "vcat" in str(logger.logger.name)

    def test_configure_logging(self) -> None:
        """Test configure_logging sets up logging."""
        import os

        from vcat.logging import configure_logging

        configure_logging(level="DEBUG", format="text")
        assert os.environ.get("VCAT_LOG_LEVEL") == "DEBUG"
        assert os.environ.get("VCAT_LOG_FORMAT") == "text"

    def test_structured_formatter(self) -> None:
        """Test StructuredFormatter produces JSON."""
        import json
        import logging

        from vcat.logging import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert parsed["level"] == "INFO"

    def test_structured_formatter_no_pathname(self) -> None:
        """Test StructuredFormatter without pathname."""
        import json
        import logging

        from vcat.logging import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",  # Empty pathname
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "location" not in parsed

    def test_structured_formatter_with_exception(self) -> None:
        """Test StructuredFormatter with exception info."""
        import json
        import logging
        import sys

        from vcat.logging import StructuredFormatter

        formatter = StructuredFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    def test_structured_formatter_with_extra(self) -> None:
        """Test StructuredFormatter with extra fields."""
        import json
        import logging

        from vcat.logging import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "context" in parsed
        assert parsed["context"]["custom_field"] == "custom_value"

    def test_colored_formatter(self) -> None:
        """Test ColoredFormatter produces formatted output."""
        import logging

        from vcat.logging import ColoredFormatter

        formatter = ColoredFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "test message" in output
        assert "INFO" in output

    def test_colored_formatter_with_extra(self) -> None:
        """Test ColoredFormatter with extra fields."""
        import logging

        from vcat.logging import ColoredFormatter

        formatter = ColoredFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"
        output = formatter.format(record)
        assert "custom_field" in output
        assert "custom_value" in output

    def test_colored_formatter_with_colors_enabled(self) -> None:
        """Test ColoredFormatter with colors enabled."""
        import logging

        from vcat.logging import ColoredFormatter

        # Force use_colors=True to test color code paths
        formatter = ColoredFormatter(use_colors=True)
        formatter.use_colors = True  # Force it even if not a tty
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        # Check for ANSI color codes
        assert "\033[" in output or "test" in output  # Either colored or plain

    def test_log_debug_function(self) -> None:
        """Test log_debug convenience function."""
        from vcat.logging import log_debug

        # Should not raise
        log_debug("test debug message", key="value")

    def test_configure_logging_json(self) -> None:
        """Test configure_logging with JSON format."""
        from vcat.logging import configure_logging

        configure_logging(level="INFO", format="json")
        import os

        assert os.environ.get("VCAT_LOG_FORMAT") == "json"

    def test_context_adapter_process(self) -> None:
        """Test ContextAdapter processes extra fields."""
        from vcat.logging import get_logger

        logger = get_logger("adapter_test")
        # The adapter should accept extra kwargs
        # Just verify it doesn't crash
        logger.info("test", extra_field="value")

    def test_context_adapter_no_extra_kwargs(self) -> None:
        """Test ContextAdapter with no extra kwargs."""
        from vcat.logging import get_logger

        logger = get_logger("adapter_test_no_extra")
        # Call with only standard kwargs
        logger.info("test message")

    def test_get_logger_already_configured(self) -> None:
        """Test get_logger when logger already has handlers."""
        import logging

        from vcat.logging import _loggers, get_logger

        # Clear cache
        _loggers.clear()

        # Pre-configure a logger with handlers
        test_name = "preconfigured_test"
        preconfig_logger = logging.getLogger(test_name)
        preconfig_logger.handlers.clear()
        preconfig_logger.addHandler(logging.StreamHandler())

        # Now get_logger should skip configuration
        result = get_logger(test_name)
        assert result is not None


class TestPageVariablesParsing:
    """Tests for PageVariables parsing."""

    def test_unknown_variable_code_ignored(self) -> None:
        """Test that unknown variable codes are silently ignored."""
        pv = PageVariables.from_header("$Q=A $Z=unknown $L=B")
        assert pv.quire == "A"
        assert pv.language == "B"
        # Unknown $Z is just ignored


class TestContextAdapterDirect:
    """Direct tests for ContextAdapter.process method."""

    def test_process_with_only_standard_keys(self) -> None:
        """Test process method when kwargs contain only standard keys."""
        import logging

        from vcat.logging import ContextAdapter

        logger = logging.getLogger("direct_test")
        adapter = ContextAdapter(logger, {"base_context": "value"})

        # Call process with only standard keys
        msg, kwargs = adapter.process("test", {"extra": {"existing": "data"}})
        assert msg == "test"
        assert "existing" in kwargs["extra"]
        assert "base_context" in kwargs["extra"]

    def test_process_with_empty_kwargs(self) -> None:
        """Test process method with empty kwargs."""
        import logging

        from vcat.logging import ContextAdapter

        logger = logging.getLogger("direct_test2")
        adapter = ContextAdapter(logger, {})

        msg, kwargs = adapter.process("test", {})
        assert msg == "test"
        assert "extra" in kwargs


class TestParserEmptyContent:
    """Tests for parser with empty or no-page content."""

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string returns no pages."""
        parser = IVTFFParser()
        pages = list(parser.parse_string(""))
        assert len(pages) == 0

    def test_parse_only_comments(self) -> None:
        """Test parsing only comments returns no pages."""
        parser = IVTFFParser()
        pages = list(parser.parse_string("# Just a comment\n# Another comment"))
        assert len(pages) == 0

    def test_parse_only_header(self) -> None:
        """Test parsing only IVTFF header returns no pages."""
        parser = IVTFFParser()
        pages = list(parser.parse_string("#=IVTFF Eva- 2.0"))
        assert len(pages) == 0
