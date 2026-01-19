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
<f1r.3,@C0;H>       circle.text
<f1r.4,@R0;H>       radius.text
"""


# =============================================================================
# Parsed Data Fixtures
# =============================================================================


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
    """Path to ZL transcription file if available."""
    path = Path(__file__).parent.parent / "data_sources/raw_sources/ZL3b-n.txt"
    if not path.exists():
        pytest.skip("ZL transcription file not found")
    return path


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
