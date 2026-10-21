"""
Shared test fixtures for VCAT test suite.

This module provides common fixtures used across test files:
    - Sample IVTFF content (valid and malformed)
    - Sample parsed data structures
    - Temporary directories
    - Mock objects for network operations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# =============================================================================
# IVTFF Content Fixtures
# =============================================================================


@pytest.fixture
def sample_ivtff_content() -> str:
    """Minimal valid IVTFF content for testing."""
    return """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A $P=A $L=A $H=1 $I=H>
<f1r.1,@P0;H>       fachys.ykal.ar.ataiin
<f1r.2,+P0;H>       shory.cthy.cphory.daiin
<f1v>      <! $Q=A $P=B $L=A $H=1 $I=H>
<f1v.1,@P0;H>       oteey.otedy.otchy.otey
"""


@pytest.fixture
def sample_ivtff_multipage() -> str:
    """IVTFF content with multiple pages for testing."""
    return """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A $L=A $H=1>
<f1r.1,@P0;H>       word.one.two
<f1r.2,+P0;H>       word.three
<f1v>      <! $Q=A $L=A $H=1>
<f1v.1,@P0;H>       word.four
<f2r>      <! $Q=A $L=B $H=1>
<f2r.1,@P0;H>       word.five.six
<f2r.2,+P0;H>       word.seven
<f2r.3,+P0;H>       word.eight
"""


@pytest.fixture
def sample_ivtff_malformed_no_header() -> str:
    """IVTFF content missing the header."""
    return """<f1r>      <! $Q=A>
<f1r.P.1;H>       test.text
"""


@pytest.fixture
def sample_ivtff_malformed_empty() -> str:
    """Empty IVTFF content."""
    return ""


@pytest.fixture
def sample_ivtff_no_pages() -> str:
    """IVTFF content with header but no pages."""
    return """#=IVTFF Eva- 2.0
# Comment line
# Another comment
"""


@pytest.fixture
def sample_ivtff_with_markup() -> str:
    """IVTFF content with various markup elements."""
    return """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A $L=A>
<f1r.1,@P0;H>       fachys{comment here}.ykal
<f1r.2,+P0;H>       test.[a:b].word
<f1r.3,+P0;H>       <%>start.text<->continue<$>
<f1r.4,+P0;H>       uncertain?reading!illegible
"""


@pytest.fixture
def sample_ivtff_foldout() -> str:
    """IVTFF content with foldout page."""
    return """#=IVTFF Eva- 2.0
<f85v3>      <! $Q=A $L=B $I=C>
<f85v3.1,@P0;H>       foldout.page.text
<f85v3.2,+P0;H>       more.text.here
"""


@pytest.fixture
def sample_ivtff_labels() -> str:
    """IVTFF content with different locus types."""
    return """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A $L=A>
<f1r.1,@P0;H>       paragraph.text
<f1r.2,@L0;H>       label.text
<f1r.3,@Cc;H>       circle.text
<f1r.4,@Ri;H>       radius.text
"""


# =============================================================================
# Parsed Data Fixtures
# =============================================================================


def structured_fields(
    text_raw: str, source_line: int = 1, locus_type: str = "@P0"
) -> dict[str, Any]:
    """The raw and structured layer of a hand-built row (item 1.2): ``text_raw`` and the markup
    fields read from it by the real tokenizer, so hand-built rows stay consistent with it."""
    from parsers.ivtff_markup import parse_markup

    return {
        "text_raw": text_raw,
        "locus_type": locus_type,
        "source_line": source_line,
        **parse_markup(text_raw).fields(),
    }


@pytest.fixture
def structured_layer() -> Any:
    """``structured_fields`` for tests that build rows by hand."""
    return structured_fields


@pytest.fixture
def sample_eva_lines() -> list[dict[str, Any]]:
    """Sample EVA line records for testing."""
    return [
        {
            "page_id": "f1r",
            "line_number": 1,
            "line_index": 1,
            "line_id": "f1r:1",
            "text": "fachys.ykal.ar.ataiin",
            "text_clean": "fachys.ykal.ar.ataiin",
            "line_type": "paragraph",
            "position": "@",
            "quire": "A",
            "section": "herbal",
            "currier_language": "A",
            "hand": "1",
            "illustration_type": "H",
            "char_count": 19,
            "word_count": 4,
            "has_uncertain": False,
            "has_illegible": False,
            "has_alternatives": False,
            "has_high_ascii": False,
            "source": "test",
            "source_version": "abc123",
            **structured_fields("fachys.ykal.ar.ataiin", source_line=1),
        },
        {
            "page_id": "f1r",
            "line_number": 2,
            "line_index": 2,
            "line_id": "f1r:2",
            "text": "shory.cthy.daiin",
            "text_clean": "shory.cthy.daiin",
            "line_type": "paragraph",
            "position": "+",
            "quire": "A",
            "section": "herbal",
            "currier_language": "A",
            "hand": "1",
            "illustration_type": "H",
            "char_count": 14,
            "word_count": 3,
            "has_uncertain": False,
            "has_illegible": False,
            "has_alternatives": False,
            "has_high_ascii": False,
            "source": "test",
            "source_version": "abc123",
            **structured_fields("shory.cthy.daiin", source_line=2),
        },
    ]


@pytest.fixture
def sample_mismatch_records() -> list[dict[str, Any]]:
    """Sample mismatch index records for testing."""
    return [
        {
            "page_id": "f1r",
            "line_number": 1,
            "line_id": "f1r:1",
            "primary_text": "fachys.ykal",
            "secondary_text": "FAXYS.YKAL",
            "primary_source": "zl",
            "secondary_source": "currier",
            "status": "ok",
            "mismatch_type": None,
            "similarity_score": 0.95,
            "notes": [],
        },
        {
            "page_id": "f1r",
            "line_number": 2,
            "line_id": "f1r:2",
            "primary_text": "shory.cthy",
            "secondary_text": None,
            "primary_source": "zl",
            "secondary_source": "currier",
            "status": "missing_in_secondary",
            "mismatch_type": None,
            "similarity_score": None,
            "notes": ["Line not in secondary transcription"],
        },
    ]


@pytest.fixture
def sample_page_metadata() -> dict[str, Any]:
    """Sample page metadata for testing."""
    return {
        "page_id": "f1r",
        "folio_id": "f1",
        "side": "recto",
        "is_foldout_panel": False,
        "panel_number": None,
        "total_panels": None,
        "section": {"value": "herbal", "attribution": "zandbergen", "confidence": "high"},
        "currier_language": {"value": "A", "attribution": "currier", "confidence": "high"},
        "illustration_type": "H",
        "has_text": True,
        "line_count": 30,
        "image_url": "https://example.com/f1r.jpg",
    }


# =============================================================================
# File System Fixtures
# =============================================================================


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def tmp_ivtff_file(tmp_path: Path, sample_ivtff_content: str) -> Path:
    """Temporary IVTFF file for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text(sample_ivtff_content, encoding="utf-8")
    return file_path


@pytest.fixture
def tmp_ivtff_multipage_file(tmp_path: Path, sample_ivtff_multipage: str) -> Path:
    """Temporary IVTFF file with multiple pages."""
    file_path = tmp_path / "multipage.txt"
    file_path.write_text(sample_ivtff_multipage, encoding="utf-8")
    return file_path


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_network_success() -> MagicMock:
    """Mock for successful network requests."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"#=IVTFF Eva- 2.0\n<f1r><! $Q=A>\n<f1r.P.1;H> test"
    mock_response.headers = {"Content-Type": "text/plain"}
    return mock_response


@pytest.fixture
def mock_network_failure() -> MagicMock:
    """Mock for failed network requests (404)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.content = b"Not Found"
    mock_response.headers = {"Content-Type": "text/html"}
    return mock_response


@pytest.fixture
def mock_network_error() -> MagicMock:
    """Mock that raises network error."""
    import requests

    mock = MagicMock()
    mock.side_effect = requests.exceptions.RequestException("Network error")
    return mock


# =============================================================================
# ZL File Fixture (for integration tests)
# =============================================================================


@pytest.fixture
def zl_file() -> Path:
    """Path to the cached ZL transcription. A missing source FAILS the test, never skips it."""
    path = Path(__file__).parent.parent / "data_sources/cache/ZL3b-n.txt"
    if not path.is_file():
        pytest.fail(f"ZL transcription not found: {path}")
    return path


# A small IVTFF source whose every locus the parser accepts, and the same with one more label locus.
# Since roadmap item 1.1 the parser accepts that locus too, so the `synthetic_lossy` fixture also makes
# the parser drop it WITHOUT reporting it, the defect loss accounting exists to catch (synthetic inputs
# for loss accounting).
SYNTHETIC_ACCOUNTED = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal.ar
<f1r.2,+P0>       sory.ckhar
<f1v>      <! $I=H $Q=A $P=B $L=A $H=1>
<f1v.1,@P0>       kchsy.chadaiin
"""
SYNTHETIC_LOSSY = SYNTHETIC_ACCOUNTED + "<f1v.2,&Lz>       otol\n"


@pytest.fixture
def synthetic_accounted() -> str:
    return SYNTHETIC_ACCOUNTED


@pytest.fixture
def synthetic_lossy(monkeypatch: pytest.MonkeyPatch) -> str:
    from parsers import IVTFFParser

    original = IVTFFParser._parse_stream
    dropped = SYNTHETIC_LOSSY.splitlines()[-1].split(">")[0] + ">"

    def silently_dropping(self, lines):  # type: ignore[no-untyped-def]
        for page in original(self, lines):
            page.loci = [locus for locus in page.loci if locus.raw_locator != dropped]
            yield page

    monkeypatch.setattr(IVTFFParser, "_parse_stream", silently_dropping)
    return SYNTHETIC_LOSSY


# =============================================================================
# Schema Fixtures
# =============================================================================


@pytest.fixture
def valid_transcription_record() -> dict[str, Any]:
    """Valid record matching transcription_lines schema."""
    return {
        "page_id": "f1r",
        "line_number": 1,
        "line_index": 1,
        "line_id": "f1r:1",
        "text": "fachys.ykal.ar.ataiin",
        "text_clean": "fachys.ykal.ar.ataiin",
        "line_type": "paragraph",
        "position": "@",
        "quire": "A",
        "section": "herbal",
        "currier_language": "A",
        "hand": "1",
        "illustration_type": "H",
        "char_count": 19,
        "word_count": 4,
        "has_uncertain": False,
        "has_illegible": False,
        "has_alternatives": False,
        "has_high_ascii": False,
        "source": "zandbergen_landini",
        "source_version": "bf5b6d4a",
        **structured_fields("fachys.ykal.ar.ataiin", source_line=1),
    }


@pytest.fixture
def invalid_transcription_record_bad_page_id() -> dict[str, Any]:
    """Invalid record with bad page_id format."""
    return {
        "page_id": "invalid!",  # Invalid format
        "line_number": 1,
        "line_id": "invalid!:1",
        "text": "test",
        "text_clean": "test",
        "line_type": "paragraph",
        "source": "test",
        "source_version": "abc",
    }


@pytest.fixture
def invalid_transcription_record_missing_field() -> dict[str, Any]:
    """Invalid record missing required field."""
    return {
        "page_id": "f1r",
        # Missing line_number
        "line_id": "f1r:1",
        "text": "test",
    }
