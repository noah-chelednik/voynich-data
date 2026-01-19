"""Custom exceptions for the VCAT package.

This module defines a hierarchy of exceptions used throughout the VCAT
codebase. Using custom exceptions allows for:

- More precise error handling and recovery
- Clearer error messages with context
- Distinguishing between different failure modes
- Consistent error handling patterns across modules

Exception Hierarchy:
    VCATError (base)
    ├── ParseError
    │   ├── InvalidFormatError
    │   ├── MalformedLocusError
    │   └── MissingPageContextError
    ├── ValidationError
    │   ├── SchemaValidationError
    │   ├── CharacterValidationError
    │   └── DataIntegrityError
    ├── BuildError
    │   ├── SourceNotFoundError
    │   ├── ExportError
    │   └── SmokeTestError
    └── ConfigurationError

Example:
    >>> from vcat.exceptions import ParseError, SourceNotFoundError
    >>> try:
    ...     build_eva_lines(Path("nonexistent.txt"))
    ... except SourceNotFoundError as e:
    ...     print(f"Source missing: {e.path}")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class VCATError(Exception):
    """Base exception for all VCAT errors.

    All custom exceptions in the VCAT package inherit from this class,
    allowing callers to catch all VCAT-related errors with a single
    except clause.

    Attributes:
        message: Human-readable error description.
        details: Optional dictionary with additional context.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize VCATError.

        Args:
            message: Human-readable error description.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Format error message with details if present."""
        if self.details:
            detail_str = ", ".join(f"{k}={v!r}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


# =============================================================================
# Parsing Errors
# =============================================================================


class ParseError(VCATError):
    """Base exception for parsing errors.

    Raised when the parser encounters invalid or unexpected content
    in source files.

    Attributes:
        line_number: Line number where error occurred (if applicable).
        line_content: Content of the problematic line (if applicable).
    """

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        line_content: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ParseError.

        Args:
            message: Human-readable error description.
            line_number: Line number where error occurred.
            line_content: Content of the problematic line.
            details: Optional dictionary with additional context.
        """
        details = details or {}
        if line_number is not None:
            details["line_number"] = line_number
        if line_content is not None:
            details["line_content"] = line_content[:100]  # Truncate for display

        super().__init__(message, details)
        self.line_number = line_number
        self.line_content = line_content


class InvalidFormatError(ParseError):
    """Raised when file format doesn't match expected IVTFF format.

    This typically indicates the file is not an IVTFF file or uses
    an unsupported version of the format.
    """

    pass


class MalformedLocusError(ParseError):
    """Raised when a locus line cannot be parsed.

    Locus lines contain the actual transcription data and must follow
    a specific format: <page_id.locus_num,@position;type>
    """

    pass


class MissingPageContextError(ParseError):
    """Raised when locus data appears without a preceding page header.

    Every locus line must appear after its corresponding page header
    has been parsed.
    """

    pass


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(VCATError):
    """Base exception for validation errors.

    Raised when data fails validation checks.
    """

    pass


class SchemaValidationError(ValidationError):
    """Raised when data doesn't conform to expected JSON schema.

    Attributes:
        schema_name: Name of the schema that failed validation.
        validation_errors: List of specific validation error messages.
    """

    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        validation_errors: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize SchemaValidationError.

        Args:
            message: Human-readable error description.
            schema_name: Name of the schema that failed.
            validation_errors: List of specific validation errors.
            details: Optional dictionary with additional context.
        """
        details = details or {}
        if schema_name:
            details["schema_name"] = schema_name
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(message, details)
        self.schema_name = schema_name
        self.validation_errors = validation_errors or []


class CharacterValidationError(ValidationError):
    """Raised when text contains invalid EVA characters.

    Attributes:
        invalid_characters: Set of characters that failed validation.
        text_sample: Sample of the problematic text.
    """

    def __init__(
        self,
        message: str,
        invalid_characters: set[str] | None = None,
        text_sample: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize CharacterValidationError.

        Args:
            message: Human-readable error description.
            invalid_characters: Set of invalid characters found.
            text_sample: Sample of the problematic text.
            details: Optional dictionary with additional context.
        """
        details = details or {}
        if invalid_characters:
            details["invalid_characters"] = list(invalid_characters)
        if text_sample:
            details["text_sample"] = text_sample[:100]

        super().__init__(message, details)
        self.invalid_characters = invalid_characters or set()
        self.text_sample = text_sample


class DataIntegrityError(ValidationError):
    """Raised when data integrity checks fail.

    This includes issues like duplicate IDs, orphaned records,
    or referential integrity violations.
    """

    pass


# =============================================================================
# Build Errors
# =============================================================================


class BuildError(VCATError):
    """Base exception for build process errors.

    Raised when the dataset build process fails.
    """

    pass


class SourceNotFoundError(BuildError):
    """Raised when a required source file is not found.

    Attributes:
        path: Path to the missing source file.
    """

    def __init__(
        self,
        message: str,
        path: Path | str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize SourceNotFoundError.

        Args:
            message: Human-readable error description.
            path: Path to the missing source file.
            details: Optional dictionary with additional context.
        """
        details = details or {}
        if path:
            details["path"] = str(path)

        super().__init__(message, details)
        self.path = Path(path) if path else None


class ExportError(BuildError):
    """Raised when dataset export fails.

    This can occur due to I/O errors, missing dependencies (e.g., pandas
    for Parquet export), or format conversion issues.

    Attributes:
        format: Export format that failed (jsonl, parquet, etc.).
        output_path: Path where export was attempted.
    """

    def __init__(
        self,
        message: str,
        format: str | None = None,
        output_path: Path | str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ExportError.

        Args:
            message: Human-readable error description.
            format: Export format that failed.
            output_path: Path where export was attempted.
            details: Optional dictionary with additional context.
        """
        details = details or {}
        if format:
            details["format"] = format
        if output_path:
            details["output_path"] = str(output_path)

        super().__init__(message, details)
        self.format = format
        self.output_path = Path(output_path) if output_path else None


class SmokeTestError(BuildError):
    """Raised when smoke tests fail during build.

    Attributes:
        failed_tests: List of test names that failed.
        test_results: Dictionary of test name -> (passed, message).
    """

    def __init__(
        self,
        message: str,
        failed_tests: list[str] | None = None,
        test_results: dict[str, tuple[bool, str]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize SmokeTestError.

        Args:
            message: Human-readable error description.
            failed_tests: List of test names that failed.
            test_results: Full test results dictionary.
            details: Optional dictionary with additional context.
        """
        details = details or {}
        if failed_tests:
            details["failed_tests"] = failed_tests

        super().__init__(message, details)
        self.failed_tests = failed_tests or []
        self.test_results = test_results or {}


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(VCATError):
    """Raised when configuration is invalid or missing.

    This includes issues with sources.yaml, schema files, or
    environment setup.
    """

    pass
