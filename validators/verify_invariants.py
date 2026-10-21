"""
VCAT Invariant Verification System

Tests principles that must hold for ANY valid VCAT EVA dataset.
Uses the SAME authoritative stripping logic as the builder.

Population checks are derived from the source file the build report names
(counted by vcat.loss_accounting without the parser), never from fixed numbers:
a dataset that lost source loci fails them.

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
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# Import authoritative modules - SAME as builder uses
from parsers import page_order_key
from parsers.ivtff_markup import GLYPHS, LIGATURE, _walk, parse_markup
from vcat import sources as _sources
from vcat.charset import (
    contains_forbidden_markup,
    contains_uncertainty_markers,
    validate_text_clean,
)
from vcat.loss_accounting import account, census_source, resolve_source
from vcat.text_processing import (
    clean_text_for_analysis,
    strip_ivtff_markup,
    validate_stripped_text,
)

#: The source a dataset is checked against when no build report names one.
# The source the registry records for ZL, not a spelled-out path (AV7 F5)
DEFAULT_SOURCE = _sources.ROOT / _sources.source_file("ZL")


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

        # A character outside the basic EVA set is accepted only when it is a glyph the source
        # itself writes in this locus (ZL f57v.3 has 'I'): text_clean keeps glyphs as written
        # (DECISIONS Q39), and markup never becomes a glyph, so a leak still fails.
        is_valid, invalid_chars = validate_text_clean(text_clean)
        source_glyphs = {
            char
            for token in _walk(parse_markup(str(r.get("text_raw", ""))).tokens)
            if token.kind in (GLYPHS, LIGATURE)
            # glyphs at any depth: top level, inside ligatures and inside alternate readings
            # (reach a17b6e30 gap 3); a ligature's high-ASCII codes are not glyphs
            for char in (token.raw if token.kind == GLYPHS else re.sub(r"@\d{3};", "", token.value))
        }
        if not is_valid and not invalid_chars <= source_glyphs:
            report.add_failure(
                "TEXT_CLEAN_CHARSET", f"Invalid: {invalid_chars - source_glyphs}", line_id
            )

    report.checks_run += 3


def check_text_clean_correspondence(records: list[dict], report: InvariantReport) -> None:
    """INVARIANT: text_clean is the current cleaning function applied to text.

    The check point of roadmap item 1.5 (B-021); item 1.6 replaces the function with a named
    normalization profile.
    """
    for r in records:
        if r.get("text_clean") != clean_text_for_analysis(r.get("text", "")):
            report.add_failure(
                "TEXT_CLEAN_CORRESPONDS",
                "text_clean is not clean_text_for_analysis(text)",
                r.get("line_id", "unknown"),
            )

    report.checks_run += 1


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
        return (*page_order_key(r.get("page_id", "")), r.get("line_index", 0))

    prev_key = None
    for r in records:
        current_key = parse_key(r)
        if prev_key and current_key < prev_key:
            report.add_failure("ORDERING", "Out of order", r.get("line_id"))
            break
        prev_key = current_key

    report.checks_run += 1


def check_record_count(
    records: list[dict],
    report: InvariantReport,
    source: Path | None = None,
    reported: int = 0,
) -> None:
    """INVARIANT: one record per source locus, less the loci the build reported.

    The expectation is counted from the source file (default: the cached ZL source).
    """
    census = census_source(source or DEFAULT_SOURCE)
    expected = len(census.loci) - reported
    actual = len(records)

    if actual != expected:
        report.add_failure(
            "RECORD_COUNT",
            f"Expected {expected} (source loci {len(census.loci)}, reported {reported}), "
            f"got {actual}",
        )

    report.checks_run += 1


def check_page_count(
    records: list[dict],
    report: InvariantReport,
    source: Path | None = None,
    reported: list[str] | None = None,
) -> None:
    """INVARIANT: the records cover every source page that has a locus not reported.

    The expectation is counted from the source file (default: the cached ZL source); a page whose
    loci are all explicitly reported carries no record.
    """
    census = census_source(source or DEFAULT_SOURCE)
    # By occurrence (review 49c77167 finding 3): a reported reading removes one source line, so a
    # page keeps its record when another reading of the same id was emitted.
    unreported = Counter(census.loci)
    unreported.subtract(Counter(reported or []))
    expected = {locus_id.rsplit(":", 1)[0] for locus_id, n in unreported.items() if n > 0}
    actual = {r.get("page_id", "") for r in records}

    if actual != expected:
        report.add_failure(
            "PAGE_COUNT",
            f"Expected the {len(expected)} source pages with loci, got {len(actual)}; "
            f"missing {sorted(expected - actual)[:5]}, unexpected {sorted(actual - expected)[:5]}",
        )

    report.checks_run += 1


def check_loci_accounted(
    records: list[dict],
    report: InvariantReport,
    source: Path | None = None,
    reported: list[str] | None = None,
) -> None:
    """INVARIANT: each record is a distinct source locus, and every source locus is a record or
    reported (by id, not only by count); a reported id must itself be a source locus."""
    result = account(
        census_source(source or DEFAULT_SOURCE),
        emitted_loci=[r.get("line_id", "") for r in records],
        emitted_pages=[],
        reported_loci=reported or [],
    )
    for problem in [p for p in result.problems() if "pages" not in p]:
        report.add_failure("LOCI_ACCOUNTED", problem)

    report.checks_run += 1


def _source_of(output_dir: Path, report: InvariantReport) -> tuple[Path | None, list[str]]:
    """The source the build report names, resolved, and the loci it reported; else the default."""
    report_path = output_dir / "eva_lines_build_report.json"
    if not report_path.exists():
        return DEFAULT_SOURCE, []
    build = json.loads(report_path.read_text())
    source = resolve_source(build.get("source_file", ""))
    if source is None:
        report.add_failure("SOURCE_EXISTS", f"Source not found: {build.get('source_file')!r}")
    reported = build.get("reported_loci", [])
    if not isinstance(reported, list):
        report.add_failure("REPORTED_LOCI", f"reported_loci is not a list: {reported!r}")
        reported = []
    return source, [str(x) for x in reported]


def check_schema_and_build_report(
    records: list[dict], output_dir: Path, report: InvariantReport
) -> None:
    """INVARIANT: rows conform to the schema, and the build report is complete, reports success,
    names a source whose bytes match its hash, agrees with the rows, and accounts for every
    source locus and page (recounted from the source). The same checks as
    validators.validate_phase1_outputs, so both validators enforce one contract."""
    from validators.validate_phase1_outputs import (
        check_against_source,
        check_build_report,
        check_loss_accounting,
        check_manifest_files,
        check_mismatch_index,
        check_rows_against_report,
        check_schema,
        check_structured_layer,
        load_build_report,
    )

    for message in check_schema(records):
        report.add_failure("SCHEMA", message)
    report_path = output_dir / "eva_lines_build_report.json"
    if not report_path.exists():
        report.add_failure("BUILD_REPORT_EXISTS", f"Not found: {report_path}")
    else:
        for message in check_build_report(report_path):
            report.add_failure("BUILD_REPORT", message)
        build = load_build_report(report_path)
        for message in check_rows_against_report(records, build):
            report.add_failure("ROWS_AGAINST_REPORT", message)
        for message in check_loss_accounting(records, build):
            report.add_failure("LOSS_ACCOUNTING", message)
        for message in check_structured_layer(records, build):
            report.add_failure("STRUCTURED_LAYER", message)
        for message in check_against_source(records, build):
            report.add_failure("AGAINST_SOURCE", message)
    for message in check_manifest_files(output_dir, records):
        report.add_failure("MANIFEST_FILES", message)
    for message in check_mismatch_index(output_dir):
        report.add_failure("MISMATCH_SCHEMA", message)

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

    source, reported = _source_of(output_dir, report)
    if source is not None:
        check_record_count(records, report, source, len(reported))
        check_page_count(records, report, source, reported)
        check_loci_accounted(records, report, source, reported)
    check_schema_and_build_report(records, output_dir, report)
    check_text_clean_contract(records, report)
    check_text_clean_correspondence(records, report)
    check_flags_contract(records, report)
    check_ids_contract(records, report)
    check_line_index_sequencing(records, report)
    check_ordering_contract(records, report)
    # the metadata tables beside the rows, by the same independent check (B-095)
    from validators.validate_phase1_outputs import check_metadata

    for problem in check_metadata(output_dir):
        report.add_failure("METADATA", problem)
    # and the word level (roadmap item 2.6)
    from validators.validate_phase1_outputs import check_words

    for problem in check_words(output_dir):
        report.add_failure("WORDS", problem)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify VCAT dataset invariants")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # a relative path is relative to the working directory, as for the other validator, so both check the same files
    # (audit 20261021-validators F3: an empty ./output passed here while this repository's output was checked instead)
    output_dir = args.output_dir.resolve()

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
            shown = 20  # a display limit
            for f in report.failures[:shown]:
                print(f"  - {f['invariant']}: {f['message']} [{f.get('record_id', '')}]")
            if report.failures[shown:]:
                print(f"  ... and {len(report.failures[shown:])} more")

    print()
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
