"""
VCAT Validators Module
======================

JSON Schema validation utilities for VCAT datasets.

This module provides functions to validate VCAT dataset records against
JSON Schema specifications, ensuring data quality and consistency.

Main functions:
    validate_against_schema: Validate data against any JSON schema
    validate_transcription_lines: Validate transcription line records
    validate_mismatch_index: Validate mismatch index records
    load_schema: Load a JSON schema by name

Schemas are stored in the schemas/ directory:
    - transcription_lines.schema.json: Schema for EVA line records
    - mismatch_index.schema.json: Schema for transcription comparison

Example:
    >>> from validators import validate_transcription_lines
    >>> records = [{"page_id": "f1r", "line_number": 1, ...}]
    >>> is_valid, errors = validate_transcription_lines(records)
    >>> is_valid
    True
"""

from __future__ import annotations

from .schema import (
    SCHEMA_DIR,
    load_schema,
    validate_against_schema,
    validate_mismatch_index,
    validate_transcription_lines,
)

__all__ = [
    "SCHEMA_DIR",
    "load_schema",
    "validate_against_schema",
    "validate_mismatch_index",
    "validate_transcription_lines",
]
