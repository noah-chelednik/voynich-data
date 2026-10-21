"""
Tests for VCAT parsers.
"""

from pathlib import Path

import pytest

from parsers import IVTFFParser, PageVariables, parse_ivtff
from vcat.loss_accounting import census_source


class TestIVTFFParser:
    """Tests for the IVTFF parser."""

    def test_parse_page_header(self):
        """Test parsing page headers with variables."""
        content = """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       test.text.here
"""
        parser = IVTFFParser()
        pages = list(parser.parse_string(content))

        assert len(pages) == 1
        assert pages[0].page_id == "f1r"
        assert pages[0].variables.quire == "A"
        assert pages[0].variables.language == "A"
        assert pages[0].variables.hand == "1"

    def test_parse_locus(self):
        """Test parsing individual loci."""
        content = """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A>
<f1r.1,@P0>       fachys.ykal.ar.ataiin
<f1r.2,+P0>       sory.ckhar.or
"""
        parser = IVTFFParser()
        pages = list(parser.parse_string(content))

        assert len(pages) == 1
        assert len(pages[0].loci) == 2
        assert pages[0].loci[0].locus_number == 1
        assert pages[0].loci[1].locus_number == 2
        assert "fachys" in pages[0].loci[0].text

    def test_extract_text_removes_comments(self):
        """Test that text extraction removes in-line comments and keeps ligature glyphs.

        Braces mark a ligature in IVTFF 2.0 (D1): the old version of this test asserted that
        ``{...}`` was deleted as a comment, which is the defect itself.
        """
        parser = IVTFFParser()

        raw = "fachys.ykal<!comment here>.ar.dlo{ct}o"
        clean = parser.extract_text(raw)

        assert "comment" not in clean
        assert clean == "fachys.ykal.ar.dlocto"
        assert "fachys" in clean

    def test_extract_text_handles_alternatives(self):
        """Test that alternatives are handled correctly."""
        parser = IVTFFParser()

        raw = "test.[a:b].word"
        clean = parser.extract_text(raw)

        assert "[" not in clean
        assert ":" not in clean
        assert "a" in clean  # First alternative kept

    def test_extract_text_removes_markers(self):
        """Test that IVTFF markers are removed."""
        parser = IVTFFParser()

        raw = "<%>start.text<->continue<$>"
        clean = parser.extract_text(raw)

        assert "<" not in clean
        assert ">" not in clean
        assert "start" in clean

    def test_multiple_pages(self):
        """Test parsing multiple pages."""
        content = """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A>
<f1r.1,@P0>       page.one
<f1v>      <! $Q=A>
<f1v.1,@P0>       page.two
<f2r>      <! $Q=A>
<f2r.1,@P0>       page.three
"""
        parser = IVTFFParser()
        pages = list(parser.parse_string(content))

        assert len(pages) == 3
        assert pages[0].page_id == "f1r"
        assert pages[1].page_id == "f1v"
        assert pages[2].page_id == "f2r"

    def test_format_version_extracted(self):
        """The file header's alphabet, version and remainder are separate (IVTFF 2.0 Table 4)."""
        content = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $Q=A>
<f1r.1,@P0>       test
"""
        parser = IVTFFParser()
        list(parser.parse_string(content))

        assert parser.alphabet == "Eva-"
        assert parser.format_version == "2.0"
        assert parser.format_options == "M 5"


class TestPageVariables:
    """Tests for PageVariables parsing."""

    def test_parse_all_variables(self):
        """Test parsing all possible page variables."""
        header = "$Q=A $P=B $F=a $B=1 $I=H $L=A $H=1 $C=2 $X=V"
        pv = PageVariables.from_header(header)

        assert pv.quire == "A"
        assert pv.page_in_quire == "B"
        assert pv.folio == "a"
        assert pv.bifolio == 1
        assert pv.illustration == "H"
        assert pv.language == "A"
        assert pv.hand == "1"
        assert pv.cluster == "2"  # Currier's hand, as written (B-013, DECISIONS Q27)
        assert pv.extraneous == "V"

    def test_parse_partial_variables(self):
        """Test parsing with only some variables present."""
        header = "$Q=A $L=B"
        pv = PageVariables.from_header(header)

        assert pv.quire == "A"
        assert pv.language == "B"
        assert pv.hand is None
        assert pv.illustration is None


class TestIntegration:
    """Integration tests with real data."""

    @pytest.fixture
    def zl_file(self):
        """Path to the cached ZL transcription. A missing source FAILS, never skips."""
        path = Path(__file__).parent.parent / "data_sources/cache/ZL3b-n.txt"
        if not path.is_file():
            pytest.fail(f"ZL transcription not found: {path}")
        return path

    def test_parse_real_file(self, zl_file):
        """Test parsing the actual ZL file."""
        pages = parse_ivtff(zl_file)
        census = census_source(zl_file)

        assert pages
        assert all(p.page_id for p in pages)
        page_ids = [p.page_id for p in pages]
        assert len(page_ids) == len(set(page_ids))
        assert set(page_ids) <= set(census.pages)

    def test_pages_with_loci_come_from_source(self, zl_file):
        """Every parsed locus is a source locus of its own page (loss: test_loss_accounting)."""
        pages = parse_ivtff(zl_file)
        census = census_source(zl_file)

        emitted = {f"{p.page_id}:{locus.locus_number}" for p in pages for locus in p.loci}
        assert emitted
        assert emitted <= set(census.loci)
        assert all(locus.page_id == p.page_id for p in pages for locus in p.loci)

    def test_locus_ids_unique(self, zl_file):
        """Test that all locus IDs are unique."""
        pages = parse_ivtff(zl_file)

        all_ids = []
        for page in pages:
            for locus in page.loci:
                all_ids.append(locus.locus_id)

        assert len(all_ids) == len(set(all_ids))


class TestHighASCIICodes:
    """Tests for high-ASCII code handling (@NNN;)."""

    def test_extract_text_preserves_high_ascii_codes(self):
        """Test that @NNN; codes are preserved in text_clean (lossless)."""
        parser = IVTFFParser()

        raw = "@140;"
        clean = parser.extract_text(raw)

        # The @NNN; code should be preserved, not stripped
        assert clean == "@140;"

    def test_extract_text_preserves_mixed_content_with_high_ascii(self):
        """Test that text with @NNN; codes preserves the codes."""
        parser = IVTFFParser()

        raw = "fachys.@140;.ykal"
        clean = parser.extract_text(raw)

        assert "@140;" in clean
        assert "fachys" in clean
        assert "ykal" in clean

    def test_has_high_ascii_codes_detects_codes(self):
        """Test that has_high_ascii_codes correctly identifies @NNN; patterns."""
        parser = IVTFFParser()

        assert parser.has_high_ascii_codes("@140;") is True
        assert parser.has_high_ascii_codes("text.@192;.more") is True
        assert parser.has_high_ascii_codes("@1;") is True

    def test_has_high_ascii_codes_returns_false_when_absent(self):
        """Test that has_high_ascii_codes returns False when no codes present."""
        parser = IVTFFParser()

        assert parser.has_high_ascii_codes("fachys.ykal") is False
        assert parser.has_high_ascii_codes("@position") is False  # Not a code format
        assert parser.has_high_ascii_codes("test@text") is False

    def test_previously_empty_lines_now_have_content(self):
        """Test that lines that were only @NNN; are now non-empty after cleaning."""
        parser = IVTFFParser()

        # These patterns caused empty text_clean in the old implementation
        test_cases = ["@140;", "@192;", "@164;"]

        for raw in test_cases:
            clean = parser.extract_text(raw)
            assert clean.strip() != "", f"'{raw}' should produce non-empty text_clean"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
