"""
Release Acceptance Tests for the committed output

The committed rows are checked against their own build report and release manifest. No expected
value is written by hand (roadmap item 1.5): whether the rows account for every source locus is the
validators' job (`validators/`), and the parser's loss is tested in tests/test_loss_accounting.py.
"""

import json
from pathlib import Path

import pytest

OUTPUT_DIR = Path(__file__).parent.parent / "output"
JSONL_PATH = OUTPUT_DIR / "eva_lines.jsonl"
REPORT_PATH = OUTPUT_DIR / "eva_lines_build_report.json"
MANIFEST_PATH = OUTPUT_DIR / "release_manifest.json"


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

    def test_total_records(self, records, build_report):
        """The row count is the one the build report and the manifest record."""
        manifest = json.loads(MANIFEST_PATH.read_text())
        assert records
        assert len(records) == build_report["total_lines"]
        assert len(records) == manifest["statistics"]["total_records"]

    def test_unique_pages(self, records, build_report):
        """The pages the rows carry are the report's pages with lines."""
        pages = {r["page_id"] for r in records}
        assert len(pages) == build_report["pages_with_lines"]

    def test_report_pages_with_lines(self, records, build_report):
        """No page the report lists without lines carries a row."""
        pages = {r["page_id"] for r in records}
        assert pages.isdisjoint(build_report["page_ids_without_lines"])

    def test_report_pages_in_source(self, build_report):
        """Pages with and without lines add up to the pages the build parsed."""
        assert (
            build_report["pages_with_lines"] + build_report["pages_without_lines"]
            == build_report["total_pages_in_source"]
        )

    def test_report_pages_without_lines(self, build_report):
        """The count of pages without lines is the length of their list."""
        assert build_report["pages_without_lines"] == len(build_report["page_ids_without_lines"])

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
        """Manifest version matches the package version (single source of truth)."""
        from vcat import __version__

        manifest_path = OUTPUT_DIR / "release_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["dataset"]["version"] == __version__


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
