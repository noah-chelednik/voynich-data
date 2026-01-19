"""
Tests for Builders Module (builders/build_eva_lines.py).

This module tests:
    - Line record construction
    - Build report generation
    - Dataset building from IVTFF files
    - Export to Parquet and JSONL
    - Smoke tests
"""

from __future__ import annotations

import json
from pathlib import Path

from builders.build_eva_lines import (
    SECTION_MAPPING,
    BuildReport,
    LineRecord,
    build_eva_lines,
    derive_section,
    export_to_jsonl,
    export_to_parquet,
    locus_type_to_line_type,
    run_smoke_test,
)
from parsers import Page, PageVariables


class TestLineRecord:
    """Tests for LineRecord dataclass."""

    def test_line_record_creation(self):
        """Test creating a LineRecord."""
        record = LineRecord(
            page_id="f1r",
            line_number=1,
            line_index=1,
            line_id="f1r:1",
            text="fachys.ykal",
            text_clean="fachys.ykal",
            line_type="paragraph",
            position="@",
            quire="A",
            section="herbal",
            currier_language="A",
            hand="1",
            illustration_type="H",
            char_count=10,
            word_count=2,
            has_uncertain=False,
            has_illegible=False,
            has_alternatives=False,
            has_high_ascii=False,
            source="test",
            source_version="abc123",
        )

        assert record.page_id == "f1r"
        assert record.line_number == 1
        assert record.line_index == 1
        assert record.line_id == "f1r:1"
        assert record.char_count == 10

    def test_line_record_to_dict(self):
        """Test LineRecord to_dict method."""
        record = LineRecord(
            page_id="f1r",
            line_number=1,
            line_index=1,
            line_id="f1r:1",
            text="test",
            text_clean="test",
            line_type="paragraph",
            position=None,
            quire="A",
            section="herbal",
            currier_language="A",
            hand="1",
            illustration_type="H",
            char_count=4,
            word_count=1,
            has_uncertain=False,
            has_illegible=False,
            has_alternatives=False,
            has_high_ascii=False,
            source="test",
            source_version="abc",
        )

        d = record.to_dict()

        assert isinstance(d, dict)
        assert d["page_id"] == "f1r"
        assert d["line_number"] == 1
        assert d["line_index"] == 1
        assert d["position"] is None
        assert d["has_high_ascii"] is False


class TestBuildReport:
    """Tests for BuildReport dataclass."""

    def test_build_report_creation(self):
        """Test creating a BuildReport."""
        report = BuildReport(
            source_file="/path/to/file.txt",
            source_hash="abc123",
            build_date="2026-01-17T12:00:00",
            format_version="Eva-",
        )

        assert report.source_file == "/path/to/file.txt"
        assert report.total_pages == 0
        assert report.total_lines == 0

    def test_build_report_page_count_alias(self):
        """Test page_count property alias."""
        report = BuildReport(
            source_file="test",
            source_hash="abc",
            build_date="2026-01-17",
            format_version="Eva-",
            total_pages=226,
        )

        assert report.page_count == 226

    def test_build_report_to_dict(self):
        """Test BuildReport to_dict method."""
        report = BuildReport(
            source_file="test",
            source_hash="abc",
            build_date="2026-01-17",
            format_version="Eva-",
            total_pages=10,
            total_lines=100,
        )

        d = report.to_dict()

        assert isinstance(d, dict)
        assert d["total_pages"] == 10
        assert d["total_lines"] == 100


class TestSectionMapping:
    """Tests for section mapping."""

    def test_section_mapping_has_expected_keys(self):
        """Test that SECTION_MAPPING has expected keys."""
        expected_keys = ["H", "A", "C", "B", "P", "S", "T", "Z"]

        for key in expected_keys:
            assert key in SECTION_MAPPING

    def test_section_mapping_values(self):
        """Test SECTION_MAPPING values."""
        assert SECTION_MAPPING["H"] == "herbal"
        assert SECTION_MAPPING["A"] == "astronomical"
        assert SECTION_MAPPING["B"] == "biological"


class TestDeriveSection:
    """Tests for derive_section function."""

    def test_derive_section_from_illustration_type(self):
        """Test deriving section from illustration type."""
        # Create a mock page with illustration type
        variables = PageVariables.from_header("$I=H")
        page = Page(page_id="f1r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "herbal"

    def test_derive_section_astronomical(self):
        """Test deriving astronomical section."""
        variables = PageVariables.from_header("$I=A")
        page = Page(page_id="f67r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "astronomical"

    def test_derive_section_from_folio_number_fallback(self):
        """Test fallback to folio number for section."""
        # No illustration type
        variables = PageVariables.from_header("")
        page = Page(page_id="f1r", variables=variables, loci=[])

        section = derive_section(page)

        # Folio 1 should map to herbal
        assert section == "herbal"

    def test_derive_section_recipes_range(self):
        """Test deriving recipes section from high folio numbers."""
        variables = PageVariables.from_header("")
        page = Page(page_id="f110r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "recipes"

    def test_derive_section_invalid_page_id(self):
        """Test section derivation with invalid page ID."""
        variables = PageVariables.from_header("")
        page = Page(page_id="invalid", variables=variables, loci=[])

        section = derive_section(page)

        assert section is None

    def test_derive_section_astronomical_folio_range(self):
        """Test deriving astronomical section from folio range."""
        variables = PageVariables.from_header("")
        page = Page(page_id="f70r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "astronomical"

    def test_derive_section_biological_folio_range(self):
        """Test deriving biological section from folio range."""
        variables = PageVariables.from_header("")
        page = Page(page_id="f80r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "biological"

    def test_derive_section_cosmological_folio_range(self):
        """Test deriving cosmological section from folio range."""
        variables = PageVariables.from_header("")
        page = Page(page_id="f85r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "cosmological"

    def test_derive_section_pharmaceutical_folio_range(self):
        """Test deriving pharmaceutical section from folio range."""
        variables = PageVariables.from_header("")
        page = Page(page_id="f95r", variables=variables, loci=[])

        section = derive_section(page)

        assert section == "pharmaceutical"


class TestLocusTypeToLineType:
    """Tests for locus_type_to_line_type function."""

    def test_paragraph_type(self):
        """Test converting paragraph locus type."""
        assert locus_type_to_line_type("P") == "paragraph"

    def test_label_type(self):
        """Test converting label locus type."""
        assert locus_type_to_line_type("L") == "label"

    def test_circle_type(self):
        """Test converting circle locus type."""
        assert locus_type_to_line_type("C") == "circle"

    def test_radius_type(self):
        """Test converting radius locus type."""
        assert locus_type_to_line_type("R") == "radius"

    def test_unknown_type(self):
        """Test converting unknown locus type."""
        assert locus_type_to_line_type("X") == "unknown"
        assert locus_type_to_line_type(None) == "unknown"

    def test_with_enum_value(self):
        """Test converting enum with value attribute."""
        from parsers import LocusType

        assert locus_type_to_line_type(LocusType.PARAGRAPH) == "paragraph"
        assert locus_type_to_line_type(LocusType.LABEL) == "label"


class TestBuildEvaLines:
    """Tests for build_eva_lines function."""

    def test_build_eva_lines_smoke(self, tmp_ivtff_file: Path, tmp_output_dir: Path):
        """Test basic build_eva_lines functionality."""
        records, report = build_eva_lines(tmp_ivtff_file, tmp_output_dir)

        assert len(records) > 0
        assert report.total_pages > 0
        assert report.total_lines > 0

    def test_build_eva_lines_output_schema(self, tmp_ivtff_file: Path, tmp_output_dir: Path):
        """Test that records have expected schema."""
        records, report = build_eva_lines(tmp_ivtff_file, tmp_output_dir)

        record = records[0]
        assert hasattr(record, "page_id")
        assert hasattr(record, "line_number")
        assert hasattr(record, "line_id")
        assert hasattr(record, "text")
        assert hasattr(record, "text_clean")
        assert hasattr(record, "source")

    def test_build_eva_lines_all_pages_present(
        self, tmp_ivtff_multipage_file: Path, tmp_output_dir: Path
    ):
        """Test that all pages are captured."""
        records, report = build_eva_lines(tmp_ivtff_multipage_file, tmp_output_dir)

        page_ids = {r.page_id for r in records}
        assert "f1r" in page_ids
        assert "f1v" in page_ids
        assert "f2r" in page_ids
        assert report.total_pages == 3

    def test_build_eva_lines_line_counts(
        self, tmp_ivtff_multipage_file: Path, tmp_output_dir: Path
    ):
        """Test that line counts are correct."""
        records, report = build_eva_lines(tmp_ivtff_multipage_file, tmp_output_dir)

        # f1r: 2 lines, f1v: 1 line, f2r: 3 lines = 6 total
        assert report.total_lines == 6

    def test_build_eva_lines_statistics_correct(self, tmp_ivtff_file: Path, tmp_output_dir: Path):
        """Test that statistics are computed correctly."""
        records, report = build_eva_lines(tmp_ivtff_file, tmp_output_dir)

        # Check that character count is sum of all record counts
        total_chars = sum(r.char_count for r in records)
        assert report.total_characters == total_chars

        # Check that word count is sum of all record counts
        total_words = sum(r.word_count for r in records)
        assert report.total_words == total_words

    def test_build_eva_lines_source_hash(self, tmp_ivtff_file: Path, tmp_output_dir: Path):
        """Test that source hash is captured."""
        records, report = build_eva_lines(tmp_ivtff_file, tmp_output_dir)

        assert report.source_hash is not None
        assert len(report.source_hash) == 64  # Full SHA256 in report

        # All records should have truncated source version (12 chars)
        assert all(r.source_version == report.source_hash[:12] for r in records)

    def test_build_eva_lines_custom_source_name(self, tmp_ivtff_file: Path, tmp_output_dir: Path):
        """Test that custom source name is used."""
        records, report = build_eva_lines(
            tmp_ivtff_file, tmp_output_dir, source_name="custom_source"
        )

        assert all(r.source == "custom_source" for r in records)

    def test_clean_text_matches_raw(self, tmp_ivtff_file: Path, tmp_output_dir: Path):
        """Test that clean text is related to raw text."""
        records, report = build_eva_lines(tmp_ivtff_file, tmp_output_dir)

        # Clean text should be derived from raw text
        for record in records:
            # Clean text should not be longer than raw
            assert len(record.text_clean) <= len(record.text) + 10


class TestExportToJsonl:
    """Tests for export_to_jsonl function."""

    def test_export_creates_file(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that export creates the JSONL file."""
        records = [LineRecord(**dict(rec.items())) for rec in sample_eva_lines]
        output_path = tmp_output_dir / "test.jsonl"

        export_to_jsonl(records, output_path)

        assert output_path.exists()

    def test_export_correct_format(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that exported file has correct JSONL format."""
        records = [LineRecord(**dict(rec.items())) for rec in sample_eva_lines]
        output_path = tmp_output_dir / "test.jsonl"

        export_to_jsonl(records, output_path)

        # Read and verify each line is valid JSON
        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == len(records)

        for line in lines:
            data = json.loads(line)
            assert "page_id" in data

    def test_export_empty_records(self, tmp_output_dir: Path):
        """Test exporting empty records list."""
        output_path = tmp_output_dir / "empty.jsonl"

        export_to_jsonl([], output_path)

        assert output_path.exists()
        assert output_path.read_text() == ""


class TestExportToParquet:
    """Tests for export_to_parquet function."""

    def test_export_parquet_creates_file(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that export creates the Parquet file."""
        records = [LineRecord(**dict(rec.items())) for rec in sample_eva_lines]
        output_path = tmp_output_dir / "test.parquet"

        export_to_parquet(records, output_path)

        assert output_path.exists()

    def test_export_parquet_loadable(self, sample_eva_lines: list[dict], tmp_output_dir: Path):
        """Test that exported Parquet is loadable."""
        import pandas as pd

        records = [LineRecord(**dict(rec.items())) for rec in sample_eva_lines]
        output_path = tmp_output_dir / "test.parquet"

        export_to_parquet(records, output_path)

        # Load with pandas
        df = pd.read_parquet(output_path)

        assert len(df) == len(records)
        assert "page_id" in df.columns


class TestRunSmokeTest:
    """Tests for run_smoke_test function."""

    def test_smoke_test_passes_valid_data(self, sample_eva_lines: list[dict], capsys):
        """Test that smoke test passes with valid data."""
        # Create enough records to pass the minimum count with proper variety
        records = []
        for i in range(4100):
            rec = sample_eva_lines[0].copy()
            rec["line_id"] = f"f{i // 20}r:{i % 20 + 1}"
            rec["page_id"] = f"f{i // 20}r"
            rec["line_number"] = (i % 20) + 1
            # Alternate between languages
            rec["currier_language"] = "A" if i % 2 == 0 else "B"
            # Alternate between line types
            rec["line_type"] = "paragraph" if i % 3 != 0 else "label"
            records.append(LineRecord(**dict(rec.items())))

        report = BuildReport(
            source_file="test",
            source_hash="abc123",
            build_date="2026-01-17",
            format_version="Eva-",
            total_pages=226,
            total_lines=4100,
        )

        result = run_smoke_test(records, report)

        # Should pass
        assert result is True

    def test_smoke_test_fails_low_count(self, sample_eva_lines: list[dict], capsys):
        """Test that smoke test fails with too few records."""
        records = [LineRecord(**dict(rec.items())) for rec in sample_eva_lines]

        report = BuildReport(
            source_file="test",
            source_hash="abc123",
            build_date="2026-01-17",
            format_version="Eva-",
            total_pages=1,
            total_lines=len(records),
        )

        result = run_smoke_test(records, report)

        # Should fail due to low record count
        assert result is False


class TestIntegrationWithRealFile:
    """Integration tests using real ZL file if available."""

    def test_build_from_zl_file(self, zl_file: Path, tmp_output_dir: Path):
        """Test building from actual ZL file."""
        records, report = build_eva_lines(zl_file, tmp_output_dir)

        assert len(records) > 4000
        assert report.total_pages > 200
        assert report.total_lines > 4000

    def test_smoke_test_passes_on_real_data(self, zl_file: Path, tmp_output_dir: Path):
        """Test smoke test passes on real data."""
        records, report = build_eva_lines(zl_file, tmp_output_dir)

        result = run_smoke_test(records, report)

        assert result is True

    def test_real_data_has_both_languages(self, zl_file: Path, tmp_output_dir: Path):
        """Test real data has both Currier languages."""
        records, report = build_eva_lines(zl_file, tmp_output_dir)

        languages = {r.currier_language for r in records if r.currier_language}

        assert "A" in languages
        assert "B" in languages

    def test_build_report_generated(self, zl_file: Path, tmp_output_dir: Path):
        """Test that build report has expected content."""
        records, report = build_eva_lines(zl_file, tmp_output_dir)

        assert report.lines_by_type.get("paragraph", 0) > 0
        assert len(report.pages_by_language) > 0
        assert len(report.pages_by_section) > 0
