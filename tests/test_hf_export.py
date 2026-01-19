"""
Tests for HuggingFace Export Module (hf/export.py).

This module tests:
    - Exporting to HuggingFace dataset format
    - Creating DatasetDict structures
    - Generating dataset cards from templates
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hf.export import (
    create_dataset_card,
    create_dataset_dict,
    export_to_hf,
)


class TestExportToHf:
    """Tests for export_to_hf function."""

    def test_export_creates_parquet(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that export creates a Parquet file."""
        export_to_hf(sample_eva_lines, tmp_output_dir)

        # Check parquet file was created
        parquet_path = tmp_output_dir / "train.parquet"
        assert parquet_path.exists()

    def test_export_returns_dataset(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that export returns a HuggingFace Dataset."""
        ds = export_to_hf(sample_eva_lines, tmp_output_dir)

        # Should be a Dataset object
        assert hasattr(ds, "num_rows")
        assert ds.num_rows == len(sample_eva_lines)

    def test_export_correct_schema(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that exported dataset has correct columns."""
        ds = export_to_hf(sample_eva_lines, tmp_output_dir)

        assert "page_id" in ds.column_names
        assert "line_number" in ds.column_names
        assert "text" in ds.column_names

    def test_export_data_accessible(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that data is accessible in exported dataset."""
        ds = export_to_hf(sample_eva_lines, tmp_output_dir)

        first_record = ds[0]
        assert first_record["page_id"] == sample_eva_lines[0]["page_id"]
        assert first_record["line_number"] == sample_eva_lines[0]["line_number"]

    def test_export_creates_directory(self, sample_eva_lines: list[dict], tmp_path: Path):
        """Test that export creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_dir" / "nested"
        assert not output_dir.exists()

        export_to_hf(sample_eva_lines, output_dir)

        assert output_dir.exists()

    def test_export_empty_data(self, tmp_output_dir: Path):
        """Test exporting empty data list."""
        ds = export_to_hf([], tmp_output_dir)

        assert ds.num_rows == 0

    def test_export_custom_split(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test export with custom split name."""
        export_to_hf(sample_eva_lines, tmp_output_dir, split="validation")

        # Check parquet file with custom name
        parquet_path = tmp_output_dir / "validation.parquet"
        assert parquet_path.exists()

    def test_export_preserves_types(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that data types are preserved."""
        ds = export_to_hf(sample_eva_lines, tmp_output_dir)

        first = ds[0]
        # Integers should be int
        assert isinstance(first["line_number"], int)
        assert isinstance(first["char_count"], int)
        # Booleans should be bool
        assert isinstance(first["has_uncertain"], bool)

    def test_export_handles_none_values(self, tmp_output_dir: Path):
        """Test that None values are handled correctly."""
        data = [
            {
                "page_id": "f1r",
                "line_number": 1,
                "optional_field": None,
                "text": "test",
            }
        ]

        ds = export_to_hf(data, tmp_output_dir)

        assert ds[0]["optional_field"] is None


class TestCreateDatasetDict:
    """Tests for create_dataset_dict function."""

    def test_create_dataset_dict_structure(
        self, sample_eva_lines: list[dict], tmp_output_dir: Path
    ):
        """Test that DatasetDict has correct structure."""
        dd = create_dataset_dict(sample_eva_lines, tmp_output_dir)

        assert "train" in dd
        assert dd["train"].num_rows == len(sample_eva_lines)

    def test_create_dataset_dict_saves_to_disk(
        self, sample_eva_lines: list[dict], tmp_output_dir: Path
    ):
        """Test that DatasetDict is saved to disk."""
        create_dataset_dict(sample_eva_lines, tmp_output_dir)

        # Check for dataset files
        assert (tmp_output_dir / "train").exists() or (
            tmp_output_dir / "dataset_dict.json"
        ).exists()

    def test_create_dataset_dict_data_accessible(
        self, sample_eva_lines: list[dict], tmp_output_dir: Path
    ):
        """Test that data in DatasetDict is accessible."""
        dd = create_dataset_dict(sample_eva_lines, tmp_output_dir)

        first = dd["train"][0]
        assert first["page_id"] == sample_eva_lines[0]["page_id"]


class TestCreateDatasetCard:
    """Tests for create_dataset_card function."""

    @pytest.fixture
    def sample_template(self, tmp_path: Path) -> Path:
        """Create a sample template file."""
        template = """# {{DATASET_NAME}}

This dataset contains {{RECORD_COUNT}} records.
Version: {{VERSION}}
Author: {{AUTHOR}}
"""
        template_path = tmp_path / "template.md"
        template_path.write_text(template)
        return template_path

    def test_create_dataset_card_replacements(self, sample_template: Path, tmp_output_dir: Path):
        """Test that replacements are applied correctly."""
        output_path = tmp_output_dir / "README.md"
        replacements = {
            "DATASET_NAME": "voynich-eva",
            "RECORD_COUNT": "4072",
            "VERSION": "0.1.0",
            "AUTHOR": "Test Author",
        }

        create_dataset_card(sample_template, output_path, replacements)

        content = output_path.read_text()
        assert "# voynich-eva" in content
        assert "4072 records" in content
        assert "Version: 0.1.0" in content
        assert "Test Author" in content

    def test_create_dataset_card_creates_file(self, sample_template: Path, tmp_output_dir: Path):
        """Test that output file is created."""
        output_path = tmp_output_dir / "output.md"

        create_dataset_card(sample_template, output_path, {})

        assert output_path.exists()

    def test_create_dataset_card_preserves_unreplaced(
        self, sample_template: Path, tmp_output_dir: Path
    ):
        """Test that unreplaced placeholders are preserved."""
        output_path = tmp_output_dir / "partial.md"
        replacements = {"DATASET_NAME": "test"}

        create_dataset_card(sample_template, output_path, replacements)

        content = output_path.read_text()
        assert "# test" in content
        # Unreplaced placeholders remain as-is
        assert "{{RECORD_COUNT}}" in content

    def test_create_dataset_card_empty_replacements(
        self, sample_template: Path, tmp_output_dir: Path
    ):
        """Test with empty replacements dict."""
        output_path = tmp_output_dir / "empty.md"

        create_dataset_card(sample_template, output_path, {})

        content = output_path.read_text()
        assert "{{DATASET_NAME}}" in content  # Unchanged

    def test_create_dataset_card_special_characters(self, tmp_path: Path, tmp_output_dir: Path):
        """Test that special characters in replacements work."""
        template = "URL: {{URL}}\nMath: {{MATH}}"
        template_path = tmp_path / "special.md"
        template_path.write_text(template)

        output_path = tmp_output_dir / "special_out.md"
        replacements = {
            "URL": "https://example.com/path?q=1&a=2",
            "MATH": "x < y && y > z",
        }

        create_dataset_card(template_path, output_path, replacements)

        content = output_path.read_text()
        assert "https://example.com" in content
        assert "x < y" in content


class TestLoadAfterExport:
    """Tests for loading datasets after export."""

    def test_load_exported_parquet(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test loading exported Parquet with HuggingFace datasets."""
        from datasets import load_dataset

        # Export
        export_to_hf(sample_eva_lines, tmp_output_dir)

        # Load
        ds = load_dataset(
            "parquet", data_files=str(tmp_output_dir / "train.parquet"), split="train"
        )

        assert len(ds) == len(sample_eva_lines)
        assert ds[0]["page_id"] == sample_eva_lines[0]["page_id"]

    def test_roundtrip_preserves_data(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that export and reload preserves data."""
        from datasets import load_dataset

        # Export
        export_to_hf(sample_eva_lines, tmp_output_dir)

        # Reload
        ds = load_dataset(
            "parquet", data_files=str(tmp_output_dir / "train.parquet"), split="train"
        )

        # Compare
        for i, orig in enumerate(sample_eva_lines):
            loaded = ds[i]
            for key in orig:
                assert loaded[key] == orig[key], f"Mismatch in {key}"


class TestEdgeCases:
    """Tests for edge cases in export."""

    def test_export_with_unicode(self, tmp_output_dir: Path):
        """Test export handles unicode correctly."""
        data = [
            {
                "page_id": "f1r",
                "line_number": 1,
                "text": "café résumé naïve",
            }
        ]

        ds = export_to_hf(data, tmp_output_dir)

        assert "café" in ds[0]["text"]

    def test_export_large_dataset(self, tmp_output_dir: Path):
        """Test export handles larger datasets."""
        data = [{"page_id": f"f{i}r", "line_number": 1, "text": f"text_{i}"} for i in range(1000)]

        ds = export_to_hf(data, tmp_output_dir)

        assert ds.num_rows == 1000

    def test_export_with_nested_data(self, tmp_output_dir: Path):
        """Test export handles nested structures."""
        data = [
            {
                "page_id": "f1r",
                "line_number": 1,
                "metadata": {"key": "value"},
                "tags": ["tag1", "tag2"],
            }
        ]

        ds = export_to_hf(data, tmp_output_dir)

        # Nested data should be preserved
        assert ds[0]["metadata"] == {"key": "value"}
        assert ds[0]["tags"] == ["tag1", "tag2"]
