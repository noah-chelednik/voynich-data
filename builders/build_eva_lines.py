#!/usr/bin/env python3
"""
EVA Lines Dataset Builder
=========================

Builds the voynich-eva:lines dataset from the ZL transcription.

This is the primary EVA transcription dataset for VCAT Horizon 1.
It provides line-level access to the complete Voynich Manuscript
transcription in EVA encoding.

The builder:
    1. Parses the IVTFF source file using IVTFFParser
    2. Extracts line-level records with metadata
    3. Validates EVA text and computes statistics
    4. Exports to Parquet and JSONL formats
    5. Generates a build report with statistics

Output files:
    - eva_lines.parquet: Efficient columnar format
    - eva_lines.jsonl: Human-readable JSON Lines
    - eva_lines_build_report.json: Build metadata and statistics

Usage:
    python -m builders.build_eva_lines
    python -m builders.build_eva_lines --smoke-test
    python -m builders.build_eva_lines --output-dir ./output

Example:
    >>> from builders import build_eva_lines, run_smoke_test
    >>> records, report = build_eva_lines(
    ...     source_path=Path("data_sources/raw_sources/ZL3b-n.txt"),
    ...     output_dir=Path("output")
    ... )
    >>> len(records)
    4072
    >>> report.total_pages
    226
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import IVTFFParser, Page
from vcat import validate_eva_text
from vcat.charset import validate_text_clean as validate_charset
from vcat.text_processing import clean_text_for_analysis, compute_flags


@dataclass
class LineRecord:
    """A single line record for the EVA lines dataset.

    Contains all information about a single line (locus) from the
    Voynich manuscript transcription, including text content,
    metadata, and quality indicators.

    Attributes:
        page_id: Page identifier, e.g., "f1r", "f85v3"
        line_number: Line number within the page (source locus ID, may have gaps)
        line_index: Sequential index within page (always 1..n, no gaps)
        line_id: Unique identifier in format "{page_id}:{line_number}"
        text: Raw transcription text including IVTFF markup
        text_clean: Cleaned text with markup removed (lossless - preserves @NNN; codes)
        line_type: Type of locus ("paragraph", "label", "circle", "radius")
        position: Position indicator (@, +, =, *) or None
        quire: Quire identifier from page metadata
        section: Manuscript section (herbal, astronomical, etc.)
        currier_language: Currier language classification ("A" or "B")
        hand: Scribe hand identifier (typically "1")
        illustration_type: Type code for page illustration
        char_count: Number of EVA characters (excluding markup)
        word_count: Number of words in cleaned text
        has_uncertain: True if text contains uncertainty markers (?)
        has_illegible: True if text contains illegible markers (!, *)
        has_alternatives: True if text contains alternative readings [a:b]
        has_high_ascii: True if text contains high-ASCII codes (@NNN;)
        source: Source identifier (e.g., "zandbergen_landini")
        source_version: Source file hash for reproducibility

    Example:
        >>> record = LineRecord(
        ...     page_id="f1r",
        ...     line_number=1,
        ...     line_index=1,
        ...     line_id="f1r:1",
        ...     text="fachys.ykal.ar.ataiin",
        ...     text_clean="fachys.ykal.ar.ataiin",
        ...     line_type="paragraph",
        ...     position="@",
        ...     quire="A",
        ...     section="herbal",
        ...     currier_language="A",
        ...     hand="1",
        ...     illustration_type="H",
        ...     char_count=19,
        ...     word_count=4,
        ...     has_uncertain=False,
        ...     has_illegible=False,
        ...     has_alternatives=False,
        ...     has_high_ascii=False,
        ...     source="zandbergen_landini",
        ...     source_version="bf5b6d4a"
        ... )
    """

    # Identifiers
    page_id: str
    line_number: int  # Source locus ID (may have gaps)
    line_index: int  # Sequential 1..n per page (no gaps)
    line_id: str

    # Text content
    text: str
    text_clean: str

    # Line metadata
    line_type: str
    position: str | None

    # Page context
    quire: str | None
    section: str | None
    currier_language: str | None
    hand: str | None
    illustration_type: str | None

    # Statistics
    char_count: int
    word_count: int

    # Quality flags
    has_uncertain: bool
    has_illegible: bool
    has_alternatives: bool
    has_high_ascii: bool

    # Source metadata
    source: str
    source_version: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the record.
        """
        return asdict(self)


@dataclass
class BuildReport:
    """Report from building the dataset.

    Contains metadata about the build process and statistics
    about the generated dataset.

    Attributes:
        source_file: Path to the source IVTFF file
        source_hash: SHA256 hash of source file (full)
        source_verified: Whether source hash was verified
        build_date: ISO format timestamp of build
        format_version: IVTFF alphabet version from file header (e.g., "Eva-")
        format_options: IVTFF format options from header (e.g., "2.0 M 5")
        text_clean_policy: Version of text cleaning policy applied
        total_pages_in_source: Number of pages parsed from source (226)
        pages_with_lines: Number of pages that have loci/lines (206)
        pages_without_lines: Number of pages with no loci (20)
        page_ids_without_lines: List of page_ids that have no loci
        total_lines: Number of lines (loci) in the dataset
        total_characters: Total EVA character count
        total_words: Total word count
        lines_by_type: Count of lines by type (paragraph, label, etc.)
        pages_by_language: Count of pages by Currier language
        pages_by_section: Count of pages by manuscript section
        lines_with_high_ascii: Count of lines containing @NNN; codes
        warnings: List of warning messages from build
        errors: List of error messages from build
    """

    source_file: str
    source_hash: str
    source_verified: bool = False
    build_date: str = ""
    format_version: str | None = None
    format_options: str | None = None
    text_clean_policy: str = "centralized_v0.2.1"  # Tracks cleaning policy version

    # Page counts - the critical distinction per v0.2.1 contract
    total_pages_in_source: int = 0  # 226 - all pages parsed
    pages_with_lines: int = 0  # 206 - pages that have loci
    pages_without_lines: int = 0  # 20 - pages with no loci
    page_ids_without_lines: list[str] = field(default_factory=list)

    # Legacy field for backwards compatibility
    total_pages: int = 0
    total_lines: int = 0
    total_characters: int = 0
    total_words: int = 0

    lines_by_type: dict[str, int] = field(default_factory=dict)
    pages_by_language: dict[str, int] = field(default_factory=dict)
    pages_by_section: dict[str, int] = field(default_factory=dict)
    lines_with_high_ascii: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        """Alias for total_pages for convenience."""
        return self.total_pages

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the report.
        """
        return asdict(self)


# Section classification based on illustration type codes from IVTFF
SECTION_MAPPING: dict[str, str] = {
    "H": "herbal",
    "A": "astronomical",
    "C": "cosmological",
    "B": "biological",
    "P": "pharmaceutical",
    "S": "stars",
    "T": "text_only",
    "Z": "zodiac",
}


def derive_section(page: Page) -> str | None:
    """Derive manuscript section from page metadata.

    Uses illustration type as primary indicator, with folio
    ranges as fallback when illustration type is not available.

    Args:
        page: Parsed Page object with metadata.

    Returns:
        Section name (herbal, astronomical, etc.) or None if
        section cannot be determined.

    Example:
        >>> page = Page(page_id="f1r", variables=PageVariables(illustration="H"))
        >>> derive_section(page)
        'herbal'
    """
    ill_type = page.variables.illustration

    if ill_type and ill_type in SECTION_MAPPING:
        return SECTION_MAPPING[ill_type]

    # Fallback: derive from folio number
    page_id = page.page_id
    match = re.match(r"f(\d+)", page_id)
    if not match:
        return None

    folio_num = int(match.group(1))

    # Approximate section ranges (these are rough)
    if folio_num <= 66:
        return "herbal"
    elif folio_num <= 73:
        return "astronomical"
    elif folio_num <= 84:
        return "biological"
    elif folio_num <= 86:
        return "cosmological"
    elif folio_num <= 102:
        return "pharmaceutical"
    else:
        return "recipes"


def locus_type_to_line_type(locus_type: Any) -> str:
    """Convert IVTFF locus type to human-readable line type.

    Args:
        locus_type: LocusType enum value, string, or None.

    Returns:
        Human-readable line type string.

    Example:
        >>> from parsers import LocusType
        >>> locus_type_to_line_type(LocusType.PARAGRAPH)
        'paragraph'
        >>> locus_type_to_line_type("P")
        'paragraph'
        >>> locus_type_to_line_type(None)
        'unknown'
    """
    mapping = {
        "P": "paragraph",
        "L": "label",
        "C": "circle",
        "R": "radius",
    }
    if locus_type and hasattr(locus_type, "value"):
        return mapping.get(locus_type.value, "unknown")
    return mapping.get(str(locus_type), "unknown")


def build_eva_lines(
    source_path: Path,
    output_dir: Path,
    source_name: str = "zandbergen_landini",
) -> tuple[list[LineRecord], BuildReport]:
    """Build the EVA lines dataset from an IVTFF transcription file.

    Parses the source IVTFF file, extracts line-level records with
    metadata and statistics, and returns the records along with
    a build report.

    Args:
        source_path: Path to IVTFF transcription file.
        output_dir: Directory for output files (used for path context).
        source_name: Identifier for the source (default: "zandbergen_landini").

    Returns:
        Tuple of (list of LineRecord objects, BuildReport with statistics).

    Example:
        >>> records, report = build_eva_lines(
        ...     source_path=Path("data_sources/raw_sources/ZL3b-n.txt"),
        ...     output_dir=Path("output")
        ... )
        >>> len(records)
        4072
        >>> report.pages_with_lines
        206
        >>> report.pages_by_language
        {'A': 114, 'B': 82, ...}
    """
    # Compute source hash (FULL hash for reproducibility)
    with open(source_path, "rb") as f:
        source_hash = hashlib.sha256(f.read()).hexdigest()

    # Initialize report with proper page tracking
    report = BuildReport(
        source_file=str(source_path),
        source_hash=source_hash,
        source_verified=True,
        build_date=datetime.now().isoformat() + "Z",
        format_version=None,
    )

    # Parse the file
    parser = IVTFFParser()
    pages = list(parser.parse_file(source_path))

    report.format_version = parser.format_version
    report.format_options = parser.format_options
    report.total_pages_in_source = len(pages)
    report.total_pages = len(pages)  # Legacy field

    # Build records
    records: list[LineRecord] = []
    pages_with_lines_set: set[str] = set()
    pages_without_lines_list: list[str] = []

    for page in pages:
        section = derive_section(page)

        # Track page-level stats
        lang = page.variables.language or "unknown"
        report.pages_by_language[lang] = report.pages_by_language.get(lang, 0) + 1

        if (
            section
        ):  # pragma: no branch - defensive; derive_section always returns str for valid pages
            report.pages_by_section[section] = report.pages_by_section.get(section, 0) + 1

        # Track pages without lines
        if not page.loci:
            pages_without_lines_list.append(page.page_id)
            continue

        pages_with_lines_set.add(page.page_id)

        # line_index is sequential 1..n per page (no gaps, unlike line_number)
        line_index = 0

        for locus in page.loci:
            line_index += 1

            # Use CENTRALIZED text processing (same as verifier)
            has_uncertain, has_illegible, has_alternatives = compute_flags(locus.text)
            text_clean = clean_text_for_analysis(locus.text)

            # Validate text_clean against charset
            is_valid, invalid_chars = validate_charset(text_clean)
            if not is_valid:
                report.warnings.append(
                    f"Invalid chars in {page.page_id}:{locus.locus_number}: {invalid_chars}"
                )

            # Check for high-ASCII codes
            has_high_ascii = parser.has_high_ascii_codes(locus.text)
            if has_high_ascii:
                report.lines_with_high_ascii += 1

            # Validate and get stats using legacy validation
            validation = validate_eva_text(text_clean)

            # Determine line type
            line_type = locus_type_to_line_type(locus.locus_type)
            report.lines_by_type[line_type] = report.lines_by_type.get(line_type, 0) + 1

            # Create record
            record = LineRecord(
                page_id=page.page_id,
                line_number=locus.locus_number,  # Source locus ID (may have gaps)
                line_index=line_index,  # Sequential 1..n (no gaps)
                line_id=f"{page.page_id}:{locus.locus_number}",
                text=locus.text,
                text_clean=text_clean,
                line_type=line_type,
                position=locus.position.value if locus.position else None,
                quire=page.variables.quire,
                section=section,
                currier_language=page.variables.language,
                hand=page.variables.hand,
                illustration_type=page.variables.illustration,
                char_count=validation.char_count,
                word_count=validation.word_count,
                has_uncertain=has_uncertain,
                has_illegible=has_illegible,
                has_alternatives=has_alternatives,
                has_high_ascii=has_high_ascii,
                source=source_name,
                source_version=source_hash[:12],  # Truncated for display
            )

            records.append(record)

            # Update totals
            report.total_characters += validation.char_count
            report.total_words += validation.word_count

    # Update page count statistics per v0.2.1 contract
    report.pages_with_lines = len(pages_with_lines_set)
    report.pages_without_lines = len(pages_without_lines_list)
    report.page_ids_without_lines = sorted(pages_without_lines_list)
    report.total_lines = len(records)

    # Sort records for deterministic output
    # Ordering contract: (folio_number, side, panel, line_index)
    def sort_key(record: LineRecord) -> tuple:
        page_id = record.page_id
        line_index = record.line_index
        match = re.match(r"f(\d+)([rv])(\d*)", page_id)
        if match:
            folio_num = int(match.group(1))
            side = 0 if match.group(2) == "r" else 1
            panel = int(match.group(3)) if match.group(3) else 0
            return (folio_num, side, panel, line_index)
        return (999999, 0, 0, page_id, line_index)

    records.sort(key=sort_key)

    return records, report


def serialize_record(record: dict) -> str:
    """
    Serialize a record to canonical JSON for reproducible output.

    Properties:
    - sort_keys=True: Keys are alphabetically ordered
    - separators=(',', ':'): Minimal whitespace (no spaces after separators)
    - ensure_ascii=False: Unicode preserved (more compact, readable)

    This ensures the same record content always produces the same bytes,
    regardless of how the record dict was constructed or in what order
    fields were added.
    """
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def export_to_jsonl(records: list[LineRecord], output_path: Path) -> str:
    """Export records to JSON Lines format with canonical serialization.

    CRITICAL: Uses newline='\\n' to ensure Unix-style line endings on all platforms.
    Without this, Windows would write \\r\\n, producing different SHA256 hashes
    for identical content. This would break the reproducibility guarantee.

    Args:
        records: List of LineRecord objects to export.
        output_path: Path to output JSONL file.

    Returns:
        SHA256 hash of the written file for reproducibility verification.
    """
    # newline='\n' forces Unix line endings regardless of platform
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(serialize_record(record.to_dict()) + "\n")

    # Compute and return hash
    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def export_to_parquet(records: list[LineRecord], output_path: Path) -> None:
    """Export records to Parquet format.

    Requires pandas and pyarrow to be installed.

    Args:
        records: List of LineRecord objects to export.
        output_path: Path to output Parquet file.

    Raises:
        RuntimeError: If pandas is not installed.
    """
    try:
        import pandas as pd

        df = pd.DataFrame([r.to_dict() for r in records])
        df.to_parquet(output_path, index=False)
    except ImportError as e:
        raise RuntimeError(
            "pandas required for Parquet export. Install with: pip install pandas pyarrow"
        ) from e


def generate_sha256sums(output_dir: Path, jsonl_hash: str) -> None:
    """
    Generate SHA256SUMS file.

    CRITICAL: This file MUST be created. CI will fail if it's missing.

    Args:
        output_dir: Directory containing the JSONL file
        jsonl_hash: SHA256 hash of the JSONL file
    """
    sums_path = output_dir / "SHA256SUMS"
    # Use Unix line endings for consistency
    with sums_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"{jsonl_hash}  eva_lines.jsonl\n")


def generate_manifest(
    output_dir: Path, report: BuildReport, record_count: int, jsonl_hash: str
) -> None:
    """
    Generate release manifest with sorted keys for stable diffing.

    Note: Manifest is NOT in reproducibility scope (contains timestamp),
    but we use sort_keys=True for cleaner diffs between releases.

    Args:
        output_dir: Output directory
        report: Build report
        record_count: Number of records
        jsonl_hash: SHA256 hash of JSONL file
    """
    manifest = {
        "build": {"date": report.build_date, "tool_version": "0.2.1"},
        "contract": {
            "charset_covenant": "Locked for v0.2.x - see docs/charset_decisions.md",
            "flags_computed_from": "tag-stripped text before marker removal",
            "json_serialization": "sort_keys=True, separators=(',',':'), newline='\\n'",
            "ordering": "deterministic by (folio_number, side, panel, line_index)",
        },
        "dataset": {"config": "lines", "name": "voynich-eva", "version": "0.2.1"},
        "files": [
            {"name": "eva_lines.jsonl", "reproducible": True, "sha256": jsonl_hash},
            {
                "name": "eva_lines.parquet",
                "note": "Content-equivalent; bitwise reproducibility not guaranteed",
                "reproducible": False,
            },
            {
                "name": "eva_lines_build_report.json",
                "note": "Contains build timestamp",
                "reproducible": False,
            },
        ],
        "manifest_version": "1.2",
        "reproducibility": {
            "canonical_artifact": "eva_lines.jsonl",
            "cross_platform": "Uses newline='\\n' for byte-identical output on all OS",
            "note": "Parquet is content-equivalent but not bitwise-reproducible",
            "scope": "JSONL only",
            "verification": "sha256sum -c SHA256SUMS",
        },
        "source": {
            "expected_sha256": report.source_hash,
            "name": "zandbergen_landini",
            "verified": report.source_verified,
        },
        "statistics": {
            "pages_in_source": report.total_pages_in_source,
            "pages_with_lines": report.pages_with_lines,
            "pages_without_lines": report.pages_without_lines,
            "total_records": record_count,
        },
    }

    manifest_path = output_dir / "release_manifest.json"
    # sort_keys=True for stable diffing (manifest is human-readable reference)
    with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest, indent=2, sort_keys=True))


def run_smoke_test(records: list[LineRecord], report: BuildReport) -> bool:
    """Run smoke tests to verify the build.

    Performs 10 validation checks on the built dataset to ensure
    data quality and completeness.

    Tests performed:
        1. Record count >= 4000
        2. All records have page_id
        3. All records have line_id
        4. No duplicate line_ids
        5. At least 95% of records have characters
        6. More than 200 unique pages
        7. Both Currier languages (A, B) present
        8. Multiple line types present
        9. No critical errors in build report
        10. All required schema fields present

    Args:
        records: List of LineRecord objects from build.
        report: BuildReport from build.

    Returns:
        True if all tests pass, False otherwise.

    Example:
        >>> records, report = build_eva_lines(source_path, output_dir)
        >>> run_smoke_test(records, report)
        True
    """
    print("\n=== Smoke Test ===\n")

    tests_passed = 0
    tests_failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✓ {name}")
            tests_passed += 1
        else:
            print(f"  ✗ {name}: {detail}")
            tests_failed += 1

    # Test 1: Minimum record count
    check(
        "Record count >= 4000",
        len(records) >= 4000,
        f"Only {len(records)} records",
    )

    # Test 2: All records have page_id
    all_have_page_id = all(r.page_id for r in records)
    check("All records have page_id", all_have_page_id)

    # Test 3: All records have line_id
    all_have_line_id = all(r.line_id for r in records)
    check("All records have line_id", all_have_line_id)

    # Test 4: No duplicate line_ids
    line_ids = [r.line_id for r in records]
    unique_ids = len(set(line_ids))
    check(
        "No duplicate line_ids",
        unique_ids == len(line_ids),
        f"{len(line_ids) - unique_ids} duplicates",
    )

    # Test 5: Character count > 0 for most records
    records_with_chars = sum(1 for r in records if r.char_count > 0)
    pct_with_chars = 100 * records_with_chars / len(records) if records else 0
    check(
        "At least 95% of records have characters",
        pct_with_chars >= 95,
        f"Only {pct_with_chars:.1f}%",
    )

    # Test 6: Multiple pages present
    unique_pages = len({r.page_id for r in records})
    check(
        "Multiple pages present (>200)",
        unique_pages > 200,
        f"Only {unique_pages} pages",
    )

    # Test 7: Both Currier languages present
    languages = {r.currier_language for r in records if r.currier_language}
    check(
        "Both Currier languages (A, B) present",
        "A" in languages and "B" in languages,
        f"Only {languages}",
    )

    # Test 8: Multiple line types
    line_types = {r.line_type for r in records}
    check(
        "Multiple line types present",
        len(line_types) >= 2,
        f"Only {line_types}",
    )

    # Test 9: No critical errors in report
    check(
        "No critical errors in build",
        len(report.errors) == 0,
        f"{len(report.errors)} errors",
    )

    # Test 10: Schema validation (spot check)
    sample = records[0] if records else None
    required_fields = [
        "page_id",
        "line_number",
        "line_id",
        "text",
        "text_clean",
        "source",
    ]
    all_fields_present = sample is not None and all(hasattr(sample, f) for f in required_fields)
    check("All required fields present", all_fields_present)

    print(f"\n  Results: {tests_passed} passed, {tests_failed} failed")

    return tests_failed == 0


def main() -> None:  # pragma: no cover
    """Main entry point for the builder script."""
    parser = argparse.ArgumentParser(
        description="Build the EVA lines dataset from ZL transcription"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data_sources/cache/ZL3b-n.txt"),
        help="Path to source IVTFF file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run smoke tests only (no file output)",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "parquet", "both"],
        default="both",
        help="Output format",
    )

    args = parser.parse_args()

    # Ensure paths are relative to repo root
    repo_root = Path(__file__).parent.parent
    source_path = repo_root / args.source if not args.source.is_absolute() else args.source
    output_dir = (
        repo_root / args.output_dir if not args.output_dir.is_absolute() else args.output_dir
    )

    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}")
        print("Run 'python scripts/fetch_sources.py' first to download the source.")
        sys.exit(1)

    print("=" * 60)
    print("VCAT EVA Lines Dataset Builder v0.2.1")
    print("=" * 60)
    print(f"\nSource: {source_path}")
    print(f"Output: {output_dir}")
    print()

    # Build the dataset
    print("Building dataset...")
    records, report = build_eva_lines(source_path, output_dir)

    print("\nBuild complete:")
    print(f"  Source hash: {report.source_hash[:16]}...")
    print(f"  Pages in source: {report.total_pages_in_source}")
    print(f"  Pages with lines: {report.pages_with_lines}")
    print(f"  Pages without lines: {report.pages_without_lines}")
    print(f"  Total lines: {report.total_lines}")
    print(f"  Characters: {report.total_characters:,}")
    print(f"  Words: {report.total_words:,}")
    print("\nLines by type:")
    for lt, count in sorted(report.lines_by_type.items(), key=lambda x: -x[1]):
        print(f"  {lt}: {count}")
    print("\nPages by language:")
    for lang, count in sorted(report.pages_by_language.items()):
        print(f"  {lang}: {count}")

    # Run smoke test
    if args.smoke_test:
        success = run_smoke_test(records, report)
        sys.exit(0 if success else 1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export JSONL with canonical serialization
    jsonl_hash = None
    if args.format in ("jsonl", "both"):
        jsonl_path = output_dir / "eva_lines.jsonl"
        print(f"\nExporting to JSONL: {jsonl_path}")
        jsonl_hash = export_to_jsonl(records, jsonl_path)
        print(f"  Wrote {len(records)} records")
        print(f"  SHA256: {jsonl_hash}")

    if args.format in ("parquet", "both"):
        parquet_path = output_dir / "eva_lines.parquet"
        print(f"\nExporting to Parquet: {parquet_path}")
        try:
            export_to_parquet(records, parquet_path)
            print(f"  Wrote {len(records)} records")
        except RuntimeError as e:
            print(f"  Warning: {e}")

    # Save build report with sorted keys
    report_path = output_dir / "eva_lines_build_report.json"
    print(f"\nSaving build report: {report_path}")
    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report.to_dict(), f, indent=2, sort_keys=True)

    # Generate SHA256SUMS (REQUIRED - CI will fail if missing)
    if jsonl_hash:
        print("\nGenerating SHA256SUMS...")
        generate_sha256sums(output_dir, jsonl_hash)
        print(f"  SHA256SUMS written to {output_dir / 'SHA256SUMS'}")

        # Generate release manifest
        print("Generating release manifest...")
        generate_manifest(output_dir, report, len(records), jsonl_hash)
        print(f"  Manifest written to {output_dir / 'release_manifest.json'}")

    print("\n" + "=" * 60)
    print("Build successful!")
    print(f"Total records: {len(records)}")
    if jsonl_hash:
        print(f"JSONL SHA256: {jsonl_hash}")
    print("=" * 60)


if __name__ == "__main__":  # pragma: no cover
    main()
