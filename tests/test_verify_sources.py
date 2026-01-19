"""
Tests for Source Verification Module (data_sources/verify_sources.py).

This module tests:
    - VerificationResult dataclass
    - Network request utilities (mocked)
    - IVTFF structure checking
    - EVA character detection
    - Source verification functions
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from data_sources.verify_sources import (
    VerificationResult,
    check_eva_characters,
    check_ivtff_structure,
    compute_sha256,
    fetch_content,
    print_result,
    run_all_verifications,
    save_results,
    verify_lsi_file,
    verify_stolfi,
    verify_voynich_nu,
)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_default_values(self):
        """Test default values of VerificationResult."""
        result = VerificationResult(source_name="Test", url="http://example.com")

        assert result.source_name == "Test"
        assert result.url == "http://example.com"
        assert result.accessible is False
        assert result.status_code is None
        assert result.errors == []
        assert result.warnings == []

    def test_is_success_false_by_default(self):
        """Test is_success returns False by default."""
        result = VerificationResult(source_name="Test", url="http://example.com")

        assert result.is_success() is False

    def test_is_success_true_when_accessible_no_errors(self):
        """Test is_success returns True when accessible with no errors."""
        result = VerificationResult(
            source_name="Test",
            url="http://example.com",
            accessible=True,
        )

        assert result.is_success() is True

    def test_is_success_false_with_errors(self):
        """Test is_success returns False when there are errors."""
        result = VerificationResult(
            source_name="Test",
            url="http://example.com",
            accessible=True,
            errors=["Some error"],
        )

        assert result.is_success() is False

    def test_to_dict(self):
        """Test to_dict method."""
        result = VerificationResult(
            source_name="Test Source",
            url="http://example.com",
            accessible=True,
            status_code=200,
            sample_hash="abc123",
            page_count=10,
        )

        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["source_name"] == "Test Source"
        assert d["accessible"] is True
        assert d["status_code"] == 200
        assert d["is_success"] is True

    def test_to_dict_includes_is_success(self):
        """Test that to_dict includes computed is_success."""
        result = VerificationResult(
            source_name="Test",
            url="http://example.com",
            accessible=False,
        )

        d = result.to_dict()

        assert "is_success" in d
        assert d["is_success"] is False


class TestComputeSha256:
    """Tests for compute_sha256 function."""

    def test_compute_sha256_basic(self):
        """Test basic SHA256 computation."""
        content = b"Hello, World!"
        result = compute_sha256(content)

        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex is 64 chars

    def test_compute_sha256_consistent(self):
        """Test SHA256 is consistent."""
        content = b"Test content"

        result1 = compute_sha256(content)
        result2 = compute_sha256(content)

        assert result1 == result2

    def test_compute_sha256_different_content(self):
        """Test different content produces different hashes."""
        content1 = b"Content 1"
        content2 = b"Content 2"

        assert compute_sha256(content1) != compute_sha256(content2)

    def test_compute_sha256_empty(self):
        """Test SHA256 of empty content."""
        result = compute_sha256(b"")

        # Known SHA256 of empty string
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestFetchContent:
    """Tests for fetch_content function (mocked)."""

    @patch("data_sources.verify_sources.requests.get")
    def test_fetch_content_success(self, mock_get: MagicMock):
        """Test successful content fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"Test content"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_get.return_value = mock_response

        content, status, content_type = fetch_content("http://example.com/file.txt")

        assert content == b"Test content"
        assert status == 200
        assert content_type == "text/plain"

    @patch("data_sources.verify_sources.requests.get")
    def test_fetch_content_not_found(self, mock_get: MagicMock):
        """Test 404 response handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b"Not Found"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_get.return_value = mock_response

        content, status, content_type = fetch_content("http://example.com/missing.txt")

        assert status == 404

    @patch("data_sources.verify_sources.requests.get")
    def test_fetch_content_network_error(self, mock_get: MagicMock):
        """Test network error handling."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(requests.exceptions.RequestException):
            fetch_content("http://example.com")

    @patch("data_sources.verify_sources.requests.get")
    def test_fetch_content_sends_user_agent(self, mock_get: MagicMock):
        """Test that user agent is sent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.headers = {}
        mock_get.return_value = mock_response

        fetch_content("http://example.com")

        # Check that headers were passed
        call_args = mock_get.call_args
        assert "headers" in call_args.kwargs
        assert "User-Agent" in call_args.kwargs["headers"]


class TestCheckIvtffStructure:
    """Tests for check_ivtff_structure function."""

    def test_check_valid_ivtff(self):
        """Test checking valid IVTFF content."""
        content = """#=IVTFF Eva- 2.0
<f1r>      <! $Q=A>
<f1r.P.1;H>       test.text
<f1v>      <! $Q=A>
<f1v.P.1;H>       more.text
"""

        can_pages, can_lines, page_count, line_count = check_ivtff_structure(content)

        assert can_pages is True
        assert can_lines is True
        assert page_count == 2  # f1r and f1v
        assert line_count == 2

    def test_check_no_pages(self):
        """Test content with no page markers."""
        content = "Just some random text without IVTFF structure."

        can_pages, can_lines, page_count, line_count = check_ivtff_structure(content)

        assert can_pages is False
        assert can_lines is False
        assert page_count == 0
        assert line_count == 0

    def test_check_pages_but_no_lines(self):
        """Test content with page markers but no line markers."""
        content = """#=IVTFF
<f1r>      header only
<f1v>      another header
"""

        can_pages, can_lines, page_count, line_count = check_ivtff_structure(content)

        assert can_pages is True
        assert can_lines is False

    def test_check_foldout_pages(self):
        """Test content with foldout page markers."""
        content = """<f85v3>      <! $Q=A>
<f85v3.P.1;H>       foldout.text
"""

        can_pages, can_lines, page_count, line_count = check_ivtff_structure(content)

        assert can_pages is True
        assert can_lines is True


class TestCheckEvaCharacters:
    """Tests for check_eva_characters function."""

    def test_check_all_eva_characters(self):
        """Test with all valid EVA characters."""
        content = """<f1r.P.1;H>       fachys.ykal.ar
<f1r.P.2;H>       shol.chedy.daiin
"""

        known, unknown = check_eva_characters(content)

        assert len(known) > 0
        assert len(unknown) == 0

    def test_check_with_unknown_characters(self):
        """Test with unknown characters."""
        content = """<f1r.P.1;H>       fachys.UNKNOWN.ykal
"""

        known, unknown = check_eva_characters(content)

        # 'U', 'N', 'K', 'W' are not EVA characters
        assert len(unknown) > 0

    def test_check_empty_content(self):
        """Test with empty content."""
        known, unknown = check_eva_characters("")

        assert known == set()


class TestVerifyLsiFile:
    """Tests for verify_lsi_file function (mocked)."""

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_lsi_success(self, mock_fetch: MagicMock):
        """Test successful LSI file verification."""
        mock_content = b"""#=IVTFF Eva- 2.0
<f1r>      <! $Q=A>
<f1r.P.1;H>       fachys.ykal
"""
        mock_fetch.return_value = (mock_content, 200, "text/plain")

        result = verify_lsi_file("http://example.com/test.txt")

        assert result.accessible is True
        assert result.status_code == 200
        assert result.is_success() is True

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_lsi_not_found(self, mock_fetch: MagicMock):
        """Test LSI file not found."""
        mock_fetch.return_value = (b"Not Found", 404, "text/html")

        result = verify_lsi_file("http://example.com/missing.txt")

        assert result.accessible is False
        assert result.is_success() is False
        assert len(result.errors) > 0

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_lsi_network_error(self, mock_fetch: MagicMock):
        """Test LSI verification with network error."""
        mock_fetch.side_effect = requests.exceptions.RequestException("Network error")

        result = verify_lsi_file("http://example.com/test.txt")

        assert result.is_success() is False
        assert len(result.errors) > 0
        assert "Network error" in result.errors[0]

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_lsi_detects_transcriber_codes(self, mock_fetch: MagicMock):
        """Test that transcriber codes are detected."""
        mock_content = b"""#=IVTFF Eva- 2.0
<f1r.P.1;H>       test
<f1r.P.2;T>       test
"""
        mock_fetch.return_value = (mock_content, 200, "text/plain")

        result = verify_lsi_file("http://example.com/test.txt")

        # Should note transcriber codes in notes
        assert any("Transcriber" in note or "H" in note for note in result.notes)


class TestVerifyVoynichNu:
    """Tests for verify_voynich_nu function (mocked)."""

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_voynich_nu_success(self, mock_fetch: MagicMock):
        """Test successful voynich.nu verification."""
        mock_content = b"<html><body>Voynich Manuscript transcription</body></html>"
        mock_fetch.return_value = (mock_content, 200, "text/html")

        result = verify_voynich_nu("https://www.voynich.nu/transcr.html")

        assert result.accessible is True
        assert result.is_success() is True

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_voynich_nu_detects_content(self, mock_fetch: MagicMock):
        """Test that Voynich-related content is detected."""
        mock_content = b"Voynich manuscript transliteration resources"
        mock_fetch.return_value = (mock_content, 200, "text/html")

        result = verify_voynich_nu("https://www.voynich.nu/")

        assert any("Voynich" in note for note in result.notes)


class TestVerifyStolfi:
    """Tests for verify_stolfi function (mocked)."""

    @patch("data_sources.verify_sources.fetch_content")
    def test_verify_stolfi_success(self, mock_fetch: MagicMock):
        """Test successful Stolfi page verification."""
        mock_content = b"Voynich interlinear concordance Takahashi"
        mock_fetch.return_value = (mock_content, 200, "text/html")

        result = verify_stolfi("https://www.ic.unicamp.br/~stolfi/voynich/")

        assert result.accessible is True
        assert result.is_success() is True


class TestPrintResult:
    """Tests for print_result function."""

    def test_print_success_result(self, capsys):
        """Test printing successful result."""
        result = VerificationResult(
            source_name="Test Source",
            url="http://example.com",
            accessible=True,
            status_code=200,
            sample_size=1000,
            sample_hash="abc123" + "0" * 58,
            page_count=10,
        )

        print_result(result)

        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Test Source" in captured.out
        assert "200" in captured.out

    def test_print_failed_result(self, capsys):
        """Test printing failed result."""
        result = VerificationResult(
            source_name="Test Source",
            url="http://example.com",
            accessible=False,
            errors=["Connection failed"],
        )

        print_result(result)

        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "Connection failed" in captured.out

    def test_print_result_with_warnings(self, capsys):
        """Test printing result with warnings."""
        result = VerificationResult(
            source_name="Test",
            url="http://example.com",
            accessible=True,
            warnings=["Unknown characters found"],
        )

        print_result(result)

        captured = capsys.readouterr()
        assert "⚠" in captured.out or "Warning" in captured.out


class TestSaveResults:
    """Tests for save_results function."""

    def test_save_results_creates_file(self, tmp_path: Path):
        """Test that save_results creates JSON file."""
        results = {"test": {"is_success": True}}
        output_path = tmp_path / "results.json"

        save_results(results, output_path)

        assert output_path.exists()

    def test_save_results_valid_json(self, tmp_path: Path):
        """Test that saved file is valid JSON."""
        import json

        results = {
            "source1": {"accessible": True, "status_code": 200},
            "_metadata": {"all_pass": True},
        }
        output_path = tmp_path / "results.json"

        save_results(results, output_path)

        loaded = json.loads(output_path.read_text())
        assert loaded["source1"]["accessible"] is True


class TestRunAllVerifications:
    """Tests for run_all_verifications function (mocked)."""

    @patch("data_sources.verify_sources.verify_lsi_file")
    @patch("data_sources.verify_sources.verify_voynich_nu")
    @patch("data_sources.verify_sources.verify_stolfi")
    def test_run_all_returns_dict(
        self, mock_stolfi: MagicMock, mock_vnu: MagicMock, mock_lsi: MagicMock
    ):
        """Test that run_all_verifications returns a dictionary."""
        # Setup mocks
        mock_result = VerificationResult(source_name="Test", url="http://test", accessible=True)
        mock_lsi.return_value = mock_result
        mock_vnu.return_value = mock_result
        mock_stolfi.return_value = mock_result

        results = run_all_verifications()

        assert isinstance(results, dict)
        assert "_metadata" in results

    @patch("data_sources.verify_sources.verify_lsi_file")
    @patch("data_sources.verify_sources.verify_voynich_nu")
    @patch("data_sources.verify_sources.verify_stolfi")
    def test_run_all_includes_all_pass_flag(
        self, mock_stolfi: MagicMock, mock_vnu: MagicMock, mock_lsi: MagicMock
    ):
        """Test that all_pass flag is included in results."""
        mock_result = VerificationResult(source_name="Test", url="http://test", accessible=True)
        mock_lsi.return_value = mock_result
        mock_vnu.return_value = mock_result
        mock_stolfi.return_value = mock_result

        results = run_all_verifications()

        assert "all_pass" in results["_metadata"]


class TestComputeFileHash:
    """Additional tests for file hash computation."""

    def test_hash_file_content(self, tmp_path: Path):
        """Test hashing actual file content."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Test file content")

        expected = compute_sha256(b"Test file content")
        actual = compute_sha256(test_file.read_bytes())

        assert actual == expected
