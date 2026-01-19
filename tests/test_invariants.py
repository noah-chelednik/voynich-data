"""
Contract Invariant Tests

These tests verify structural guarantees that hold for ANY valid VCAT EVA dataset.
They test principles, not specific values. They FAIL (not skip) if output is missing.

Uses the SAME authoritative modules as the builder and verifier.
"""

import json

# Import authoritative modules
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from vcat.charset import contains_forbidden_markup, contains_uncertainty_markers
from vcat.text_processing import strip_ivtff_markup

OUTPUT_DIR = Path(__file__).parent.parent / "output"
JSONL_PATH = OUTPUT_DIR / "eva_lines.jsonl"


def require_output():
    """Assert output exists. FAIL if missing."""
    if not JSONL_PATH.exists():
        pytest.fail(f"Output not found: {JSONL_PATH}. Build first. Tests FAIL, not skip.")


@pytest.fixture(scope="module")
def records():
    require_output()
    return [json.loads(line) for line in JSONL_PATH.open()]


class TestTextCleanInvariants:
    """text_clean structural guarantees."""

    def test_no_markup_chars(self, records):
        """No IVTFF markup characters in text_clean."""
        for r in records:
            assert not contains_forbidden_markup(r["text_clean"]), f"Markup in {r['line_id']}"

    def test_no_uncertainty_markers(self, records):
        """Uncertainty markers stripped from text_clean."""
        for r in records:
            assert not contains_uncertainty_markers(r["text_clean"]), f"Markers in {r['line_id']}"


class TestFlagInvariants:
    """Flag computation guarantees - uses authoritative stripping."""

    def test_has_illegible_principle(self, records):
        """has_illegible reflects tag-stripped text."""
        for r in records:
            # Use the SAME stripping function as builder
            flag_basis = strip_ivtff_markup(r["text"])
            expected = "!" in flag_basis or "*" in flag_basis
            assert r["has_illegible"] == expected, f"{r['line_id']}: expected {expected}"

    def test_has_uncertain_principle(self, records):
        """has_uncertain reflects tag-stripped text."""
        for r in records:
            flag_basis = strip_ivtff_markup(r["text"])
            expected = "?" in flag_basis
            assert r["has_uncertain"] == expected, f"{r['line_id']}: expected {expected}"


class TestStructuralInvariants:
    """Data structure guarantees."""

    def test_line_id_format(self, records):
        """line_id matches {page_id}:{line_number}."""
        for r in records:
            expected = f"{r['page_id']}:{r['line_number']}"
            assert r["line_id"] == expected

    def test_line_id_uniqueness(self, records):
        """All line_ids are unique."""
        ids = [r["line_id"] for r in records]
        assert len(ids) == len(set(ids))

    def test_line_index_sequential(self, records):
        """line_index is sequential (1..N) within each page."""
        from collections import defaultdict

        pages = defaultdict(list)
        for r in records:
            pages[r["page_id"]].append(r["line_index"])

        for page_id, indices in pages.items():
            expected = list(range(1, len(indices) + 1))
            assert sorted(indices) == expected, f"Page {page_id}"

    def test_deterministic_ordering(self, records):
        """Records ordered by (folio_number, side, panel, line_index)."""
        import re

        def sort_key(r):
            match = re.match(r"f(\d+)([rv])(\d*)", r["page_id"])
            if match:
                return (
                    int(match.group(1)),
                    0 if match.group(2) == "r" else 1,
                    int(match.group(3)) if match.group(3) else 0,
                    r["line_index"],
                )
            return (999999, 0, 0, 0)

        prev = None
        for r in records:
            curr = sort_key(r)
            if prev:
                assert curr >= prev, f"{r['line_id']} out of order"
            prev = curr
