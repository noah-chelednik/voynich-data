"""
JSON Schema Validation Utilities
================================

Provides JSON Schema validation for VCAT dataset records.

This module handles loading JSON schemas from the schemas/ directory
and validating data records against them. It uses JSON Schema Draft 7
for validation.

Functions:
    load_schema: Load a JSON schema by name
    validate_against_schema: Validate data against a schema
    validate_transcription_lines: Validate transcription line records
    validate_mismatch_index: Validate mismatch index records

Example:
    >>> from validators.schema import validate_against_schema
    >>> data = [{"page_id": "f1r", "line_number": 1, ...}]
    >>> is_valid, errors = validate_against_schema(data, "transcription_lines")
    >>> is_valid
    True
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError

# Path to schemas directory
SCHEMA_DIR: Path = Path(__file__).parent.parent / "schemas"


def load_schema(schema_name: str) -> dict[str, Any]:
    """Load a JSON schema by name.

    Loads and parses a JSON schema file from the schemas/ directory.

    Args:
        schema_name: Schema filename, with or without .json extension.
            Examples: "transcription_lines", "transcription_lines.schema.json"

    Returns:
        Parsed JSON schema as a dictionary.

    Raises:
        FileNotFoundError: If the schema file does not exist.

    Example:
        >>> schema = load_schema("transcription_lines")
        >>> schema["type"]
        'object'
        >>> schema = load_schema("transcription_lines.schema.json")
        >>> "properties" in schema
        True
    """
    if not schema_name.endswith(".json"):
        schema_name = f"{schema_name}.json"

    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    return dict(json.loads(schema_path.read_text()))


def validate_against_schema(
    data: dict | list[dict],
    schema_name: str,
    raise_on_error: bool = False,
) -> tuple[bool, list[str]]:
    """Validate data against a JSON schema.

    Validates one or more records against a JSON schema, collecting
    all validation errors.

    Args:
        data: Single record (dict) or list of records to validate.
        schema_name: Name of schema file in schemas/ directory.
        raise_on_error: If True, raise ValidationError on first failure.
            If False (default), collect all errors and return them.

    Returns:
        Tuple of (all_valid, error_messages) where:
            - all_valid: True if all records passed validation
            - error_messages: List of error message strings

    Raises:
        ValidationError: If raise_on_error=True and validation fails.
        FileNotFoundError: If the schema file does not exist.

    Example:
        >>> data = {"page_id": "f1r", "line_number": 1, "line_id": "f1r:1", ...}
        >>> is_valid, errors = validate_against_schema(data, "transcription_lines")
        >>> is_valid
        True
        >>> errors
        []

        >>> bad_data = {"page_id": "invalid!"}
        >>> is_valid, errors = validate_against_schema(bad_data, "transcription_lines")
        >>> is_valid
        False
        >>> len(errors) > 0
        True
    """
    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)

    if isinstance(data, dict):
        data = [data]

    errors: list[str] = []
    for i, record in enumerate(data):
        for error in validator.iter_errors(record):
            error_msg = f"Record {i}: {error.message} at {list(error.absolute_path)}"
            errors.append(error_msg)
            if raise_on_error:
                raise ValidationError(error_msg)

    return len(errors) == 0, errors


def validate_transcription_lines(data: list[dict]) -> tuple[bool, list[str]]:
    """Validate transcription lines data against schema.

    Convenience function for validating EVA line records.

    Args:
        data: List of transcription line record dictionaries.

    Returns:
        Tuple of (all_valid, error_messages).

    Example:
        >>> records = [{"page_id": "f1r", "line_number": 1, ...}]
        >>> is_valid, errors = validate_transcription_lines(records)
    """
    return validate_against_schema(data, "transcription_lines.schema.json")


def validate_mismatch_index(data: list[dict]) -> tuple[bool, list[str]]:
    """Validate mismatch index data against schema.

    Convenience function for validating mismatch index records.

    Args:
        data: List of mismatch index record dictionaries.

    Returns:
        Tuple of (all_valid, error_messages).

    Example:
        >>> records = [{"page_id": "f1r", "line_number": 1, "status": "ok", ...}]
        >>> is_valid, errors = validate_mismatch_index(records)
    """
    return validate_against_schema(data, "mismatch_index.schema.json")
