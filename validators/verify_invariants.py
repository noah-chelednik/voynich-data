"""
VCAT Invariant Verification System

Tests principles that must hold for ANY valid VCAT EVA dataset.
Uses the SAME authoritative stripping logic as the builder.

Usage:
    python -m validators.verify_invariants --output-dir ./output

Exit codes:
    0 - All invariants passed
    1 - One or more invariants failed
"""

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import authoritative modules - SAME as builder uses
from vcat.charset import (
    contains_forbidden_markup,
    contains_uncertainty_markers,
    validate_text_clean,
)
from vcat.text_processing import strip_ivtff_markup, validate_stripped_text


@dataclass
class InvariantReport:
    """Report of invariant check results."""

    total_records: int = 0
    checks_run: int = 0
    failures: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0

    def add_failure(self, invariant: str, message: str, record_id: str | None = None) -> None:
        self.failures.append({"invariant": invariant, "message": message, "record_id": record_id})

    def summary(self) -> str:
        if self.passed:
            return f"✓ All invariants passed ({self.checks_run} checks on {self.total_records} records)"
        else:
            return f"✗ {len(self.failures)} failures"


def stream_records(jsonl_path: Path) -> Iterator[dict]:
    """Stream records from JSONL."""
    with jsonl_path.open() as f:
        for line in f:
            yield json.loads(line)


def check_text_clean_contract(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: text_clean contains only allowed characters."""
    for r in records:
        text_clean = r.get("text_clean", "")
        line_id = r.get("line_id", "unknown")

        if contains_forbidden_markup(text_clean):
            report.add_failure("TEXT_CLEAN_NO_MARKUP", "Forbidden markup", line_id)

        if contains_uncertainty_markers(text_clean):
            report.add_failure("TEXT_CLEAN_NO_MARKERS", "Uncertainty markers present", line_id)

        is_valid, invalid_chars = validate_text_clean(text_clean)
        if not is_valid:
            report.add_failure("TEXT_CLEAN_CHARSET", f"Invalid: {invalid_chars}", line_id)

    report.checks_run += 3


def check_flags_contract(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: Flags computed from tag-stripped text."""
    for r in records:
        raw_text = r.get("text", "")
        line_id = r.get("line_id", "unknown")

        # Use the SAME stripping function as the builder
        flag_basis = strip_ivtff_markup(raw_text)

        # Sanity check: stripping should have removed all markup
        if not validate_stripped_text(flag_basis):
            report.add_failure("FLAG_BASIS_CLEAN", "Stripping failed", line_id)

        expected_illegible = "!" in flag_basis or "*" in flag_basis
        if r.get("has_illegible", False) != expected_illegible:
            report.add_failure("HAS_ILLEGIBLE_CONTRACT", f"Expected {expected_illegible}", line_id)

        expected_uncertain = "?" in flag_basis
        if r.get("has_uncertain", False) != expected_uncertain:
            report.add_failure("HAS_UNCERTAIN_CONTRACT", f"Expected {expected_uncertain}", line_id)

    report.checks_run += 3


def check_ids_contract(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: line_id format and uniqueness."""
    seen_ids = set()

    for r in records:
        line_id = r.get("line_id", "")
        expected_id = f"{r.get('page_id', '')}:{r.get('line_number', 0)}"

        if line_id != expected_id:
            report.add_failure("LINE_ID_FORMAT", f"Expected {expected_id}", line_id)

        if line_id in seen_ids:
            report.add_failure("LINE_ID_UNIQUE", "Duplicate", line_id)
        seen_ids.add(line_id)

    report.checks_run += 2


def check_line_index_sequencing(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: line_index is sequential (1..N) within each page."""
    pages: dict[str, list[int]] = {}
    for r in records:
        page_id = r.get("page_id", "")
        if page_id not in pages:
            pages[page_id] = []
        pages[page_id].append(r.get("line_index", 0))

    for page_id, indices in pages.items():
        expected = list(range(1, len(indices) + 1))
        if sorted(indices) != expected:
            report.add_failure(
                "LINE_INDEX_SEQUENTIAL", f"Expected {expected}, got {sorted(indices)}", page_id
            )

    report.checks_run += 1


def check_ordering_contract(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: Records ordered by (folio_number, side, panel, line_index)."""

    def parse_key(r: dict) -> tuple[int, int, int, int]:
        page_id = r.get("page_id", "")
        match = re.match(r"f(\d+)([rv])(\d*)", page_id)
        if match:
            return (
                int(match.group(1)),
                0 if match.group(2) == "r" else 1,
                int(match.group(3)) if match.group(3) else 0,
                r.get("line_index", 0),
            )
        return (999999, 0, 0, 0)

    prev_key = None
    for r in records:
        current_key = parse_key(r)
        if prev_key and current_key < prev_key:
            report.add_failure("ORDERING", "Out of order", r.get("line_id"))
            break
        prev_key = current_key

    report.checks_run += 1


def check_record_count(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: Expected record count for v0.2.1."""
    expected_count = 4072
    actual_count = len(records)

    if actual_count != expected_count:
        report.add_failure("RECORD_COUNT", f"Expected {expected_count}, got {actual_count}")

    report.checks_run += 1


def check_page_count(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: Expected unique page count for v0.2.1."""
    expected_pages = 206
    unique_pages = len({r.get("page_id", "") for r in records})

    if unique_pages != expected_pages:
        report.add_failure(
            "PAGE_COUNT", f"Expected {expected_pages} unique pages, got {unique_pages}"
        )

    report.checks_run += 1


def verify_all_invariants(output_dir: Path) -> InvariantReport:
    """Run all invariant checks."""
    report = InvariantReport()

    jsonl_path = output_dir / "eva_lines.jsonl"
    if not jsonl_path.exists():
        report.add_failure("OUTPUT_EXISTS", f"Not found: {jsonl_path}")
        return report

    records = list(stream_records(jsonl_path))
    report.total_records = len(records)

    check_record_count(records, report)
    check_page_count(records, report)
    check_text_clean_contract(records, report)
    check_flags_contract(records, report)
    check_ids_contract(records, report)
    check_line_index_sequencing(records, report)
    check_ordering_contract(records, report)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify VCAT dataset invariants")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # Ensure path is relative to repo root
    repo_root = Path(__file__).parent.parent
    output_dir = (
        repo_root / args.output_dir if not args.output_dir.is_absolute() else args.output_dir
    )

    print("=" * 60)
    print("VCAT Invariant Verification System")
    print("=" * 60)
    print(f"\nVerifying: {output_dir}")
    print()

    report = verify_all_invariants(output_dir)

    if args.json:
        # sort_keys for consistent output
        print(
            json.dumps(
                {"passed": report.passed, "failures": report.failures}, indent=2, sort_keys=True
            )
        )
    else:
        print(report.summary())
        if not report.passed:
            print("\nFailures:")
            for f in report.failures[:20]:
                print(f"  - {f['invariant']}: {f['message']} [{f.get('record_id', '')}]")
            if len(report.failures) > 20:
                print(f"  ... and {len(report.failures) - 20} more")

    print()
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
