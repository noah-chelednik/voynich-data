"""
Tests for Validators Module (validators/schema.py).

This module tests:
    - Schema loading
    - Record validation against schemas
    - Batch validation
    - Error handling
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

from validators.schema import (
    SCHEMA_DIR,
    load_schema,
    validate_against_schema,
    validate_mismatch_index,
    validate_transcription_lines,
)


class TestLoadSchema:
    """Tests for load_schema function."""

    def test_load_schema_exists(self):
        """Test loading an existing schema."""
        schema = load_schema("transcription_lines.schema.json")

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "type" in schema

    def test_load_schema_without_extension(self):
        """Test loading schema without .json extension."""
        schema = load_schema("transcription_lines.schema")

        assert isinstance(schema, dict)
        assert "properties" in schema

    def test_load_schema_not_found(self):
        """Test that loading non-existent schema raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_schema("non_existent_schema.json")

    def test_load_mismatch_index_schema(self):
        """Test loading mismatch index schema."""
        schema = load_schema("mismatch_index.schema.json")

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "status" in schema["properties"]

    def test_schema_dir_exists(self):
        """Test that SCHEMA_DIR points to valid directory."""
        assert SCHEMA_DIR.exists()
        assert SCHEMA_DIR.is_dir()


class TestValidateAgainstSchema:
    """Tests for validate_against_schema function."""

    def test_validate_valid_record(self, valid_transcription_record: dict[str, Any]):
        """Test validating a valid record."""
        is_valid, errors = validate_against_schema(
            valid_transcription_record, "transcription_lines.schema.json"
        )

        assert is_valid is True
        assert errors == []

    def test_validate_invalid_page_id_format(self):
        """Test validation fails for invalid page_id format."""
        record = {
            "page_id": "invalid!",  # Invalid format
            "line_number": 1,
            "line_id": "invalid!:1",
            "text": "test",
            "text_clean": "test",
            "line_type": "paragraph",
            "source": "test",
            "source_version": "abc",
        }

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        assert is_valid is False
        assert len(errors) > 0
        assert any("page_id" in e for e in errors)

    def test_validate_missing_required_field(self):
        """Test validation fails when required field is missing."""
        record = {
            "page_id": "f1r",
            # Missing line_number - required
            "line_id": "f1r:1",
            "text": "test",
        }

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_invalid_line_number(self, valid_transcription_record):
        """A record valid in every field but `line_number` 0 fails, for its line number (B-098, AT7 F2: the old record
        lacked required fields, so it failed whatever the line number's rule)."""
        assert validate_against_schema(
            valid_transcription_record, "transcription_lines.schema.json"
        )[0]
        record = dict(valid_transcription_record, line_number=0)  # must be >= 1

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        assert is_valid is False
        assert errors and all(
            "line_number" in error or "0 is less than" in error for error in errors
        ), errors

    def test_validate_invalid_enum_value(self):
        """Test validation fails for invalid enum value."""
        record = {
            "page_id": "f1r",
            "line_number": 1,
            "line_id": "f1r:1",
            "text": "test",
            "text_clean": "test",
            "line_type": "invalid_type",  # Not in enum
            "source": "test",
            "source_version": "abc",
        }

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        assert is_valid is False
        assert any("line_type" in e for e in errors)

    def test_validate_batch_records(self, valid_transcription_record: dict[str, Any]):
        """Test validating multiple records at once."""
        records = [valid_transcription_record, valid_transcription_record.copy()]

        is_valid, errors = validate_against_schema(records, "transcription_lines.schema.json")

        assert is_valid is True
        assert errors == []

    def test_validate_batch_with_one_invalid(self, valid_transcription_record: dict[str, Any]):
        """Test batch validation catches invalid records."""
        invalid_record = {"page_id": "invalid!", "line_number": 1}
        records = [valid_transcription_record, invalid_record]

        is_valid, errors = validate_against_schema(records, "transcription_lines.schema.json")

        assert is_valid is False
        assert any("Record 1" in e for e in errors)

    def test_validate_raise_on_error(self):
        """Test raise_on_error flag raises ValidationError."""
        record = {"page_id": "invalid!"}

        with pytest.raises(ValidationError):
            validate_against_schema(record, "transcription_lines.schema.json", raise_on_error=True)

    def test_validate_empty_list(self):
        """Test validating empty list passes."""
        is_valid, errors = validate_against_schema([], "transcription_lines.schema.json")

        assert is_valid is True
        assert errors == []

    def test_validate_schema_not_found(self):
        """Test validation with non-existent schema raises error."""
        with pytest.raises(FileNotFoundError):
            validate_against_schema({"test": "data"}, "non_existent.json")


class TestValidateTranscriptionLines:
    """Tests for validate_transcription_lines convenience function."""

    def test_validate_valid_data(self, valid_transcription_record: dict[str, Any]):
        """Test validating valid transcription lines data."""
        is_valid, errors = validate_transcription_lines([valid_transcription_record])

        assert is_valid is True
        assert errors == []

    def test_validate_invalid_data(self):
        """Test validating invalid transcription lines data."""
        is_valid, errors = validate_transcription_lines([{"page_id": "invalid!"}])

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_empty_list(self):
        """Test validating empty list."""
        is_valid, errors = validate_transcription_lines([])

        assert is_valid is True


class TestValidateMismatchIndex:
    """Tests for validate_mismatch_index convenience function."""

    @staticmethod
    def committed_rows() -> list[dict[str, Any]]:
        path = Path(__file__).resolve().parent.parent / "output" / "mismatch_index.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_validate_valid_mismatch_record(self):
        """The committed index rows (built by builders.build_mismatch_index) are valid."""
        is_valid, errors = validate_mismatch_index(self.committed_rows())

        assert is_valid is True
        assert errors == []

    def test_validate_invalid_status(self):
        """Test validation fails for invalid status value."""
        record = {**self.committed_rows()[0], "status": "invalid_status"}

        is_valid, errors = validate_mismatch_index([record])

        assert is_valid is False
        assert any("status" in e for e in errors)

    def test_validate_all_status_values(self):
        """Every status the builder writes is valid, and the 0.2.3 statuses are not (item 1.8)."""
        from builders.build_mismatch_index import STATUSES

        # the whole clause (reach 1c53841b gap 4): every committed row is valid, an invalid status is not
        rows = self.committed_rows()
        assert validate_mismatch_index(rows) == (True, [])
        assert not validate_mismatch_index([{**rows[0], "status": "invalid_status"}])[0]
        template = rows[0]
        for status in STATUSES:
            is_valid, errors = validate_mismatch_index([{**template, "status": status}])
            assert is_valid is True, f"Status '{status}' should be valid"
        for status in ("ok", "content_mismatch", "high_similarity"):
            assert not validate_mismatch_index([{**template, "status": status}])[0], status


class TestSchemaFiles:
    """Tests for the actual schema files."""

    def test_transcription_lines_schema_valid_json(self):
        """Test that transcription_lines schema is valid JSON."""
        schema_path = SCHEMA_DIR / "transcription_lines.schema.json"
        content = schema_path.read_text()

        # Should not raise
        schema = json.loads(content)
        assert "$schema" in schema

    def test_mismatch_index_schema_valid_json(self):
        """Test that mismatch_index schema is valid JSON."""
        schema_path = SCHEMA_DIR / "mismatch_index.schema.json"
        content = schema_path.read_text()

        # Should not raise
        schema = json.loads(content)
        assert "$schema" in schema

    def test_transcription_lines_schema_has_required_fields(self):
        """Test that schema defines expected required fields."""
        schema = load_schema("transcription_lines.schema.json")

        required = schema.get("required", [])
        assert "page_id" in required
        assert "line_number" in required
        assert "line_id" in required

    def test_mismatch_index_schema_has_required_fields(self):
        """Test that mismatch index schema defines expected required fields."""
        schema = load_schema("mismatch_index.schema.json")

        required = schema.get("required", [])
        assert "page_id" in required
        assert "status" in required


class TestEdgeCases:
    """Tests for edge cases in validation."""

    def test_validate_with_null_values(self, structured_layer):
        """Test validation handles null values correctly for nullable fields."""
        record = {
            "page_id": "f1r",
            "line_number": 1,
            "line_index": 1,
            "line_id": "f1r:1",
            "text": "test",
            "text_clean": "test",
            "line_type": "paragraph",
            "quire": None,  # Nullable field
            "section": None,  # Nullable field
            "currier_language": None,  # Nullable field
            "source": "test",
            "source_version": "abc",
            **structured_layer("test"),
        }

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        assert is_valid is True

    def test_validate_with_extra_fields(self, valid_transcription_record: dict[str, Any]):
        """Test validation allows extra fields (additionalProperties not restricted)."""
        record = valid_transcription_record.copy()
        record["extra_field"] = "extra_value"

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        # Schema doesn't restrict additional properties
        assert is_valid is True

    def test_validate_foldout_page_id(self, structured_layer):
        """Test validation accepts foldout page IDs."""
        record = {
            "page_id": "f85v3",  # Foldout panel
            "line_number": 1,
            "line_index": 1,
            "line_id": "f85v3:1",
            "text": "test",
            "text_clean": "test",
            "line_type": "paragraph",
            "source": "test",
            "source_version": "abc",
            **structured_layer("test"),
        }

        is_valid, errors = validate_against_schema(record, "transcription_lines.schema.json")

        assert is_valid is True
