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

from data_sources.verify_sources import (
    VerificationResult,
    print_result,
    run_all_verifications,
    save_results,
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
    """The online check is the upstream check: each fetched source's served bytes against its pin, voynich.nu only
    (B-087). The fetcher is replaced: no network."""

    @staticmethod
    def served(changed: str | None = None, down: str | None = None):
        from vcat.sources import cached_sources

        by_url = {s.url: s for s in cached_sources()}

        def fetch(url: str) -> bytes:
            source = by_url[url]
            if source.id == down:
                raise OSError("connection refused")
            data = source.path.read_bytes()
            return data + b" " if source.id == changed else data

        return fetch

    def test_every_fetched_source_passes_when_served_as_pinned(self):
        from vcat.sources import load_sources

        fetched = {e["id"] for e in load_sources()["cached"] if e.get("url_fetched")}
        results = run_all_verifications(self.served())
        assert set(results) - {"_metadata"} == fetched
        assert results["_metadata"]["all_pass"] is True
        assert all(
            v["url"].startswith("https://www.voynich.nu/")
            for k, v in results.items()
            if k != "_metadata"
        )

    def test_a_changed_or_unreachable_source_fails(self):
        results = run_all_verifications(self.served(changed="ZL", down="IT"))
        assert (
            results["ZL"]["is_success"] is False and "not the pinned" in results["ZL"]["errors"][0]
        )
        assert results["IT"]["is_success"] is False and "unreachable" in results["IT"]["errors"][0]
        assert results["_metadata"]["all_pass"] is False

    def test_no_other_host_is_named(self):
        """The module names no host the roadmap does not fetch from (B-087: Stolfi's site was checked)."""
        text = (
            Path(__file__).resolve().parent.parent / "data_sources" / "verify_sources.py"
        ).read_text()
        assert "unicamp" not in text.lower() and "~stolfi" not in text
