"""
Release Acceptance Tests for v0.2.1

Version-specific expected values. Update for each release.
"""

import json
from pathlib import Path

import pytest

OUTPUT_DIR = Path(__file__).parent.parent / "output"
JSONL_PATH = OUTPUT_DIR / "eva_lines.jsonl"
REPORT_PATH = OUTPUT_DIR / "eva_lines_build_report.json"

# v0.2.1 expected values
EXPECTED_V0_2_1 = {
    "total_records": 4072,
    "unique_pages": 206,
    "pages_in_source": 226,
    "pages_without_lines": 20,
}


def require_output():
    if not JSONL_PATH.exists():
        pytest.fail(f"Output not found: {JSONL_PATH}")


@pytest.fixture(scope="module")
def records():
    require_output()
    return [json.loads(line) for line in JSONL_PATH.open()]


@pytest.fixture(scope="module")
def build_report():
    require_output()
    return json.loads(REPORT_PATH.read_text())


class TestReleaseV0_2_1:
    """Acceptance tests for v0.2.1 release."""

    def test_total_records(self, records):
        """Total record count matches expected value."""
        assert len(records) == EXPECTED_V0_2_1["total_records"]

    def test_unique_pages(self, records):
        """Unique page count matches expected value."""
        pages = {r["page_id"] for r in records}
        assert len(pages) == EXPECTED_V0_2_1["unique_pages"]

    def test_report_pages_with_lines(self, build_report):
        """Build report shows correct pages_with_lines count."""
        assert build_report["pages_with_lines"] == EXPECTED_V0_2_1["unique_pages"]

    def test_report_pages_in_source(self, build_report):
        """Build report shows correct total_pages_in_source count."""
        assert build_report["total_pages_in_source"] == EXPECTED_V0_2_1["pages_in_source"]

    def test_report_pages_without_lines(self, build_report):
        """Build report shows correct pages_without_lines count."""
        assert build_report["pages_without_lines"] == EXPECTED_V0_2_1["pages_without_lines"]

    def test_sha256sums_exists(self):
        """SHA256SUMS file must exist (CI requirement)."""
        sums_path = OUTPUT_DIR / "SHA256SUMS"
        assert sums_path.exists(), "SHA256SUMS not found - reproducibility contract violation"

    def test_sha256sums_not_empty(self):
        """SHA256SUMS file must not be empty (CI requirement)."""
        sums_path = OUTPUT_DIR / "SHA256SUMS"
        assert (
            sums_path.stat().st_size > 0
        ), "SHA256SUMS is empty - reproducibility contract violation"

    def test_manifest_exists(self):
        """Release manifest must exist."""
        manifest_path = OUTPUT_DIR / "release_manifest.json"
        assert manifest_path.exists(), "release_manifest.json not found"

    def test_manifest_version(self):
        """Manifest contains correct version."""
        manifest_path = OUTPUT_DIR / "release_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["dataset"]["version"] == "0.2.2"


class TestReproducibility:
    """Reproducibility contract tests."""

    def test_jsonl_hash_matches_sha256sums(self):
        """JSONL hash matches the recorded hash in SHA256SUMS."""
        import hashlib

        # Compute actual hash
        actual_hash = hashlib.sha256(JSONL_PATH.read_bytes()).hexdigest()

        # Read expected hash from SHA256SUMS
        sums_path = OUTPUT_DIR / "SHA256SUMS"
        sums_content = sums_path.read_text().strip()
        expected_hash = sums_content.split()[0]

        assert actual_hash == expected_hash, "JSONL hash mismatch"

    def test_unix_line_endings(self):
        """JSONL uses Unix line endings for cross-platform byte identity."""
        content = JSONL_PATH.read_bytes()
        crlf_count = content.count(b"\r\n")

        assert crlf_count == 0, f"Found {crlf_count} Windows line endings (CRLF)"
