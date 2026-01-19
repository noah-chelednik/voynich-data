"""
Tests for Metadata Parser and Builder
=====================================

Tests for the metadata extraction and dataset building functionality.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from builders import (
    MetadataBuildReport,
    MetadataBuildResult,
    build_metadata_datasets,
)
from parsers import (
    FOLDOUT_PAGES,
    MISSING_FOLIOS,
    SECTION_MAPPING,
    IllustrationType,
    IVTFFParser,
    Locus,
    LocusPosition,
    LocusType,
    ManuscriptSection,
    MetadataExtractionResult,
    MetadataParser,
    Page,
    PageVariables,
    UncertainValue,
    extract_all_metadata,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_page() -> Page:
    """Create a sample Page object for testing."""
    variables = PageVariables(
        quire="A",
        page_in_quire="1",
        language="A",
        hand="1",
        illustration="H",
    )
    loci = [
        Locus(
            page_id="f1r",
            locus_number=1,
            position=LocusPosition.NEW_UNIT,
            locus_type=LocusType.PARAGRAPH,
            text="fachys.ykal.ar.ataiin",
        ),
        Locus(
            page_id="f1r",
            locus_number=2,
            position=LocusPosition.CONTINUE,
            locus_type=LocusType.PARAGRAPH,
            text="shory.cthy.y",
        ),
        Locus(
            page_id="f1r",
            locus_number=3,
            position=LocusPosition.NEW_UNIT,
            locus_type=LocusType.LABEL,
            text="oteey",
        ),
    ]
    return Page(page_id="f1r", variables=variables, loci=loci)


@pytest.fixture
def sample_pages() -> list[Page]:
    """Create a list of sample pages for testing."""
    pages = []

    # f1r - Herbal A, Language A
    pages.append(
        Page(
            page_id="f1r",
            variables=PageVariables(
                quire="A", page_in_quire="1", language="A", hand="1", illustration="H"
            ),
            loci=[
                Locus(
                    page_id="f1r",
                    locus_number=1,
                    position=LocusPosition.NEW_UNIT,
                    locus_type=LocusType.PARAGRAPH,
                    text="fachys.ykal",
                ),
                Locus(
                    page_id="f1r",
                    locus_number=2,
                    position=LocusPosition.CONTINUE,
                    locus_type=LocusType.PARAGRAPH,
                    text="shory.cthy",
                ),
            ],
        )
    )

    # f1v - Herbal A, Language A
    pages.append(
        Page(
            page_id="f1v",
            variables=PageVariables(
                quire="A", page_in_quire="2", language="A", hand="1", illustration="H"
            ),
            loci=[
                Locus(
                    page_id="f1v",
                    locus_number=1,
                    position=LocusPosition.NEW_UNIT,
                    locus_type=LocusType.PARAGRAPH,
                    text="kshor.shory",
                ),
            ],
        )
    )

    # f2r - Herbal A, Language A (different quire)
    pages.append(
        Page(
            page_id="f2r",
            variables=PageVariables(
                quire="A", page_in_quire="3", language="A", hand="1", illustration="H"
            ),
            loci=[
                Locus(
                    page_id="f2r",
                    locus_number=1,
                    position=LocusPosition.NEW_UNIT,
                    locus_type=LocusType.PARAGRAPH,
                    text="pchedy.qokedy",
                ),
            ],
        )
    )

    # f75r - Biological, Language B
    pages.append(
        Page(
            page_id="f75r",
            variables=PageVariables(
                quire="M", page_in_quire="1", language="B", hand="2", illustration="B"
            ),
            loci=[
                Locus(
                    page_id="f75r",
                    locus_number=1,
                    position=LocusPosition.NEW_UNIT,
                    locus_type=LocusType.PARAGRAPH,
                    text="chedy.qokeedy",
                ),
            ],
        )
    )

    return pages


@pytest.fixture
def metadata_parser() -> MetadataParser:
    """Create a MetadataParser instance."""
    return MetadataParser()


@pytest.fixture
def zl_source_path() -> Path:
    """Get path to ZL transcription file if available."""
    path = Path("data_sources/cache/ZL3b-n.txt")
    if not path.exists():
        pytest.skip("ZL3b-n.txt not found in cache")
    return path


# =============================================================================
# Test UncertainValue
# =============================================================================


class TestUncertainValue:
    """Tests for UncertainValue dataclass."""

    def test_create_uncertain_value(self):
        """Test creating an UncertainValue instance."""
        uv = UncertainValue(
            value="herbal_a",
            attribution="zandbergen",
            confidence="high",
            disputed=False,
        )
        assert uv.value == "herbal_a"
        assert uv.attribution == "zandbergen"
        assert uv.confidence == "high"
        assert not uv.disputed

    def test_to_dict(self):
        """Test converting UncertainValue to dict."""
        uv = UncertainValue(value="herbal_a", attribution="test")
        d = uv.to_dict()
        assert d["value"] == "herbal_a"
        assert d["attribution"] == "test"
        assert "confidence" in d
        assert "disputed" in d
        assert "alternatives" in d


# =============================================================================
# Test MetadataParser Page ID Parsing
# =============================================================================


class TestMetadataParserPageId:
    """Tests for MetadataParser page ID parsing."""

    def test_parse_simple_page_id(self, metadata_parser):
        """Test parsing a simple page_id."""
        folio, side, panel = metadata_parser.parse_page_id("f1r")
        assert folio == 1
        assert side == "r"
        assert panel is None

    def test_parse_verso_page_id(self, metadata_parser):
        """Test parsing a verso page_id."""
        folio, side, panel = metadata_parser.parse_page_id("f85v")
        assert folio == 85
        assert side == "v"
        assert panel is None

    def test_parse_foldout_panel(self, metadata_parser):
        """Test parsing a foldout panel page_id."""
        folio, side, panel = metadata_parser.parse_page_id("f85v3")
        assert folio == 85
        assert side == "v"
        assert panel == 3

    def test_parse_high_folio_number(self, metadata_parser):
        """Test parsing a high folio number."""
        folio, side, panel = metadata_parser.parse_page_id("f116v")
        assert folio == 116
        assert side == "v"
        assert panel is None

    def test_parse_uppercase(self, metadata_parser):
        """Test parsing uppercase page_id."""
        folio, side, panel = metadata_parser.parse_page_id("F1R")
        assert folio == 1
        assert side == "r"

    def test_invalid_page_id(self, metadata_parser):
        """Test parsing an invalid page_id raises ValueError."""
        with pytest.raises(ValueError):
            metadata_parser.parse_page_id("invalid")

    def test_invalid_page_id_no_side(self, metadata_parser):
        """Test parsing page_id without side raises ValueError."""
        with pytest.raises(ValueError):
            metadata_parser.parse_page_id("f1")


# =============================================================================
# Test Section Mapping
# =============================================================================


class TestSectionMapping:
    """Tests for section mapping functionality."""

    def test_herbal_a_section(self, metadata_parser):
        """Test Herbal A section assignment."""
        section = metadata_parser.get_section(1)
        assert section == ManuscriptSection.HERBAL_A

        section = metadata_parser.get_section(25)
        assert section == ManuscriptSection.HERBAL_A

    def test_herbal_b_section(self, metadata_parser):
        """Test Herbal B section assignment."""
        section = metadata_parser.get_section(26)
        assert section == ManuscriptSection.HERBAL_B

        section = metadata_parser.get_section(50)
        assert section == ManuscriptSection.HERBAL_B

    def test_biological_section(self, metadata_parser):
        """Test Biological section assignment."""
        section = metadata_parser.get_section(75)
        assert section == ManuscriptSection.BIOLOGICAL

    def test_cosmological_section(self, metadata_parser):
        """Test Cosmological section assignment."""
        section = metadata_parser.get_section(85)
        assert section == ManuscriptSection.COSMOLOGICAL

    def test_pharmaceutical_section(self, metadata_parser):
        """Test Pharmaceutical section assignment."""
        section = metadata_parser.get_section(87)
        assert section == ManuscriptSection.PHARMACEUTICAL

    def test_recipes_section(self, metadata_parser):
        """Test Recipes section assignment."""
        section = metadata_parser.get_section(103)
        assert section == ManuscriptSection.RECIPES

    def test_uncertain_section(self, metadata_parser):
        """Test UncertainValue for section."""
        uv = metadata_parser.get_section_uncertain(25)  # Boundary
        assert uv.value == "herbal_a"
        assert uv.confidence == "medium"
        assert uv.disputed is True


# =============================================================================
# Test Foldout Detection
# =============================================================================


class TestFoldoutDetection:
    """Tests for foldout page detection."""

    def test_is_foldout_panel(self, metadata_parser):
        """Test detecting foldout panels."""
        assert metadata_parser.is_foldout("f85v1") is True
        assert metadata_parser.is_foldout("f85v3") is True
        assert metadata_parser.is_foldout("f86v2") is True

    def test_not_foldout(self, metadata_parser):
        """Test non-foldout pages."""
        assert metadata_parser.is_foldout("f1r") is False
        assert metadata_parser.is_foldout("f50v") is False

    def test_foldout_base_page(self, metadata_parser):
        """Test detecting foldout base pages."""
        # f85v is a known foldout base
        assert metadata_parser.is_foldout("f85v") is True


# =============================================================================
# Test Page Record Extraction
# =============================================================================


class TestPageRecordExtraction:
    """Tests for extracting PageRecords from IVTFF pages."""

    def test_extract_page_record(self, metadata_parser, sample_page):
        """Test extracting a PageRecord from a Page."""
        record = metadata_parser.extract_page_record(sample_page)

        assert record.page_id == "f1r"
        assert record.folio_id == "f1"
        assert record.side == "recto"
        assert record.folio_number == 1
        assert record.quire_id == "qA"
        assert record.currier_language == "A"
        assert record.hand == "1"
        assert record.illustration_type == "H"
        assert record.line_count == 2  # Two PARAGRAPH loci
        assert record.label_count == 1  # One LABEL locus
        assert record.has_text is True
        assert record.is_foldout_panel is False

    def test_extract_pages(self, metadata_parser, sample_pages):
        """Test extracting multiple PageRecords."""
        records = metadata_parser.extract_pages(sample_pages)

        assert len(records) == 4
        assert records[0].page_id == "f1r"
        assert records[1].page_id == "f1v"
        assert records[3].page_id == "f75r"

    def test_page_record_to_dict(self, metadata_parser, sample_page):
        """Test converting PageRecord to dict."""
        record = metadata_parser.extract_page_record(sample_page)
        d = record.to_dict()

        assert d["page_id"] == "f1r"
        assert d["folio_id"] == "f1"
        assert "section" in d
        assert isinstance(d["section"], dict)


# =============================================================================
# Test Folio Record Extraction
# =============================================================================


class TestFolioRecordExtraction:
    """Tests for extracting FolioRecords from IVTFF pages."""

    def test_extract_folios(self, metadata_parser, sample_pages):
        """Test extracting FolioRecords."""
        records = metadata_parser.extract_folios(sample_pages)

        # Should have 3 unique folios: f1, f2, f75
        assert len(records) == 3

        # Check f1 folio
        f1 = next(r for r in records if r.folio_id == "f1")
        assert f1.folio_number == 1
        assert f1.recto_page_id == "f1r"
        assert "f1v" in f1.verso_page_ids
        assert f1.is_foldout is False

    def test_folio_aggregates_lines(self, metadata_parser, sample_pages):
        """Test that FolioRecord aggregates line counts."""
        records = metadata_parser.extract_folios(sample_pages)

        f1 = next(r for r in records if r.folio_id == "f1")
        # f1r has 2 lines, f1v has 1 line
        assert f1.total_lines == 3

    def test_folio_record_to_dict(self, metadata_parser, sample_pages):
        """Test converting FolioRecord to dict."""
        records = metadata_parser.extract_folios(sample_pages)
        d = records[0].to_dict()

        assert "folio_id" in d
        assert "verso_page_ids" in d
        assert "section" in d


# =============================================================================
# Test Quire Record Extraction
# =============================================================================


class TestQuireRecordExtraction:
    """Tests for extracting QuireRecords from IVTFF pages."""

    def test_extract_quires(self, metadata_parser, sample_pages):
        """Test extracting QuireRecords."""
        records = metadata_parser.extract_quires(sample_pages)

        # Should have 2 quires: A and M
        assert len(records) == 2

        # Check quire A
        qa = next(r for r in records if r.quire_id == "qA")
        assert qa.quire_letter == "A"
        assert "f1" in qa.folio_ids
        assert "f2" in qa.folio_ids

    def test_quire_aggregates_folios(self, metadata_parser, sample_pages):
        """Test that QuireRecord aggregates folios."""
        records = metadata_parser.extract_quires(sample_pages)

        qa = next(r for r in records if r.quire_id == "qA")
        assert qa.folio_count == 2  # f1 and f2

    def test_quire_sections(self, metadata_parser, sample_pages):
        """Test that QuireRecord lists sections."""
        records = metadata_parser.extract_quires(sample_pages)

        qa = next(r for r in records if r.quire_id == "qA")
        assert "herbal_a" in qa.sections


# =============================================================================
# Test extract_all_metadata
# =============================================================================


class TestExtractAllMetadata:
    """Tests for extract_all_metadata convenience function."""

    def test_extract_all(self, sample_pages):
        """Test extracting all metadata."""
        result = extract_all_metadata(sample_pages, "test.txt", "abc123")

        assert isinstance(result, MetadataExtractionResult)
        assert len(result.pages) == 4
        assert len(result.folios) == 3
        assert len(result.quires) == 2
        assert result.source_file == "test.txt"
        assert result.source_hash == "abc123"

    def test_extract_all_stats(self, sample_pages):
        """Test that extract_all_metadata computes stats."""
        result = extract_all_metadata(sample_pages)

        assert result.total_pages == 4
        assert result.total_folios == 3
        assert result.total_quires == 2
        assert result.total_lines > 0
        assert "A" in result.languages
        assert "B" in result.languages


# =============================================================================
# Test Metadata Builder
# =============================================================================


class TestMetadataBuilder:
    """Tests for the metadata dataset builder."""

    def test_build_metadata_datasets(self, zl_source_path):
        """Test building metadata datasets from ZL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_metadata_datasets(zl_source_path, tmpdir)

            assert isinstance(result, MetadataBuildResult)
            assert len(result.pages) > 200
            assert len(result.folios) > 100
            assert len(result.quires) > 10

    def test_build_report(self, zl_source_path):
        """Test that build produces a valid report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_metadata_datasets(zl_source_path, tmpdir)

            assert isinstance(result.report, MetadataBuildReport)
            assert result.report.total_pages == len(result.pages)
            assert result.report.total_folios == len(result.folios)
            assert result.report.total_quires == len(result.quires)
            assert result.report.source_hash != ""

    def test_export_metadata(self, zl_source_path):
        """Test exporting metadata to JSONL files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_metadata_datasets(zl_source_path, tmpdir)

            # Check files exist
            assert Path(tmpdir, "pages.jsonl").exists()
            assert Path(tmpdir, "folios.jsonl").exists()
            assert Path(tmpdir, "quires.jsonl").exists()
            assert Path(tmpdir, "metadata_report.json").exists()

    def test_export_valid_json(self, zl_source_path):
        """Test that exported JSONL is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_metadata_datasets(zl_source_path, tmpdir)

            # Read and parse pages.jsonl
            pages_path = Path(tmpdir, "pages.jsonl")
            with open(pages_path) as f:
                for line in f:
                    data = json.loads(line)
                    assert "page_id" in data
                    assert "folio_id" in data


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_section_mapping_coverage(self):
        """Test that section mapping covers full folio range."""
        covered = set()
        for _name, (start, end, _section) in SECTION_MAPPING.items():
            covered.update(range(start, end + 1))

        # Should cover folios 1-116 with some gaps
        assert 1 in covered
        assert 116 in covered

    def test_foldout_pages(self):
        """Test foldout pages constant."""
        assert "f85v" in FOLDOUT_PAGES
        assert "f86v" in FOLDOUT_PAGES
        assert len(FOLDOUT_PAGES["f85v"]) == 6
        assert len(FOLDOUT_PAGES["f86v"]) == 4

    def test_missing_folios(self):
        """Test missing folios constant."""
        assert 12 in MISSING_FOLIOS
        assert 74 in MISSING_FOLIOS
        # Folios 59-64 are missing
        for i in range(59, 65):
            assert i in MISSING_FOLIOS


# =============================================================================
# Integration Tests with Real Data
# =============================================================================


class TestIntegrationWithRealData:
    """Integration tests with actual transcription file."""

    def test_parse_zl_file(self, zl_source_path):
        """Test parsing ZL transcription file."""
        parser = IVTFFParser()
        pages = list(parser.parse_file(zl_source_path))

        assert len(pages) >= 220

    def test_extract_metadata_from_zl(self, zl_source_path):
        """Test extracting metadata from ZL file."""
        parser = IVTFFParser()
        pages = list(parser.parse_file(zl_source_path))

        result = extract_all_metadata(pages)

        # Verify reasonable counts
        assert result.total_pages >= 220
        assert result.total_folios >= 100
        assert result.total_quires >= 10

        # Verify language distribution
        assert "A" in result.languages
        assert "B" in result.languages

        # Verify section distribution
        assert "herbal_a" in result.sections or "herbal_b" in result.sections

    def test_page_variables_extracted(self, zl_source_path):
        """Test that page variables are correctly extracted."""
        parser = IVTFFParser()
        pages = list(parser.parse_file(zl_source_path))

        mp = MetadataParser()
        records = mp.extract_pages(pages)

        # Check first page has expected metadata
        f1r = next(r for r in records if r.page_id == "f1r")
        assert f1r.quire_id is not None
        assert f1r.currier_language in ("A", "B", None)
        assert f1r.section is not None


# =============================================================================
# Test Enums
# =============================================================================


class TestEnums:
    """Tests for enum classes."""

    def test_manuscript_section_values(self):
        """Test ManuscriptSection enum values."""
        assert ManuscriptSection.HERBAL_A.value == "herbal_a"
        assert ManuscriptSection.BIOLOGICAL.value == "biological"
        assert ManuscriptSection.RECIPES.value == "recipes"

    def test_illustration_type_values(self):
        """Test IllustrationType enum values."""
        assert IllustrationType.HERBAL.value == "H"
        assert IllustrationType.BIOLOGICAL.value == "B"
        assert IllustrationType.TEXT.value == "T"
