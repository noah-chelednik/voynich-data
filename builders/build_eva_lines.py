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
    4. Accounts for every source locus and page (vcat.loss_accounting); the command line
       refuses to write output while any is unaccounted
    5. Exports to Parquet and JSONL formats
    6. Generates a build report with statistics and the accounting

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
    ...     source_path=Path("data_sources/cache/ZL3b-n.txt"),
    ...     output_dir=Path("output")
    ... )
    >>> len(records) == report.loci_emitted
    True
    >>> report.unaccounted_loci  # every source locus is emitted or reported
    []
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from parsers import IVTFFParser, Page, page_order_key
from vcat import validate_eva_text
from vcat.charset import validate_text_clean as validate_charset
from vcat.loss_accounting import account, census_source
from vcat.profiles import TEXT_CLEAN_PROFILE
from vcat.sources import pinned_sha256, repo_relative, require_licensed, source_file
from vcat.text_processing import clean_text_for_analysis, compute_flags


@dataclass
class LineRecord:
    """A single line record for the EVA lines dataset.

    Contains all information about a single line (locus) from the
    Voynich manuscript transcription, including text content,
    metadata, and quality indicators.

    Attributes:
        page_id: Page identifier, e.g., "f1r", "f86v3"
        line_number: Line number within the page (source locus ID, may have gaps)
        line_index: Sequential index within page (always 1..n, no gaps)
        line_id: Unique identifier in format "{page_id}:{line_number}"
        text: Transcription text including IVTFF markup (stripped, continuations joined)
        text_clean: Cleaned text with markup removed (lossless - preserves @NNN; codes)
        text_raw: The transliterated text exactly as in the source (DECISIONS Q24)
        locus_type: The locus code as written, e.g. "@P0", "&Lz" (D7)
        source_line: 1-based line number of the locus identifier in the source file
        alternates: The readings of each alternate [a:b], as written (DECISIONS Q25)
        ligatures: The characters of each ligature {...}
        uncertain_spaces: How many uncertain word spaces (,)
        illegible: Each run of ? as written
        high_ascii: Each high-ASCII code @NNN; as an integer (comments excluded)
        comments: The text of each in-line comment <!...>
        drawing_breaks: Each drawing interruption <-> or <~> as written
        markers: Each paragraph mark <%>, <$> and text tag <@X=y> as written
        line_type: Type of locus ("paragraph", "label", "circle", "radius")
        position: Locator (IVTFF 2.0 Table 8) or None
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
        ...     text_raw="fachys.ykal.ar.ataiin",
        ...     locus_type="@P0",
        ...     source_line=12,
        ...     alternates=[],
        ...     ligatures=[],
        ...     uncertain_spaces=0,
        ...     illegible=[],
        ...     high_ascii=[],
        ...     comments=[],
        ...     drawing_breaks=[],
        ...     markers=[],
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

    # The raw and structured layer (roadmap item 1.2)
    text_raw: str
    locus_type: str
    source_line: int
    alternates: list[list[str]]
    ligatures: list[str]
    uncertain_spaces: int
    illegible: list[str]
    high_ascii: list[int]
    comments: list[str]
    drawing_breaks: list[str]
    markers: list[str]

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
        alphabet: Transliteration alphabet from the file header (e.g., "Eva-")
        format_version: IVTFF format version from the file header (e.g., "2.0")
        format_options: The rest of the file header after the version (e.g., "M 5")
        text_clean_policy: Version of text cleaning policy applied
        total_pages_in_source: Number of pages the parser returned
        pages_with_lines: Number of pages that have loci/lines
        pages_without_lines: Number of parsed pages with no loci
        page_ids_without_lines: List of page_ids that have no loci
        total_lines: Number of lines (loci) in the dataset
        total_characters: Total EVA character count
        total_words: Total word count
        lines_by_type: Count of lines by type (paragraph, label, etc.)
        pages_by_language: Count of pages by Currier language
        pages_by_section: Count of pages by manuscript section
        lines_with_high_ascii: Count of lines containing @NNN; codes
        source_loci: Locus lines in the source, counted without the parser
        source_page_headers: Page headers in the source, counted without the parser
        loci_emitted: Source loci that became records
        loci_reported: Source loci the parser reported instead of emitting
        reported_loci: Their ids: the loci the parser recorded as warnings instead of emitting
        reported_pages: Page headers the parser recorded as warnings instead of accepting
        unaccounted_loci: Source loci neither emitted nor reported (must be empty)
        unexpected_loci: Emitted loci absent from the source (must be empty)
        unaccounted_pages: Source pages neither emitted nor reported (must be empty)
        unrecognized_source_lines: Source lines starting with '<' that are neither (must be empty)
        warnings: List of warning messages from build
        errors: List of error messages from build
    """

    source_file: str
    source_hash: str
    source_verified: bool = False
    build_date: str = ""
    alphabet: str | None = None
    format_version: str | None = None
    format_options: str | None = None
    text_clean_policy: str = TEXT_CLEAN_PROFILE  # the profile text_clean is (item 1.6, Q39)

    # Page counts - the critical distinction per v0.2.1 contract
    total_pages_in_source: int = 0  # all pages parsed
    pages_with_lines: int = 0  # pages that have loci
    pages_without_lines: int = 0  # parsed pages with no loci
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

    # Loss accounting (vcat.loss_accounting): every source locus emitted or reported
    source_loci: int = 0
    source_page_headers: int = 0
    loci_emitted: int = 0
    loci_reported: int = 0
    reported_loci: list[str] = field(default_factory=list)
    reported_pages: list[str] = field(default_factory=list)
    unaccounted_loci: list[str] = field(default_factory=list)
    unexpected_loci: list[str] = field(default_factory=list)
    unaccounted_pages: list[str] = field(default_factory=list)
    unrecognized_source_lines: list[int] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        """Alias for total_pages for convenience."""
        return self.total_pages

    def loss_problems(self) -> list[str]:
        """Why the build does not account for its source; empty when it does."""
        problems = []
        if self.unaccounted_loci:
            problems.append(
                f"{len(self.unaccounted_loci)} of {self.source_loci} source loci neither emitted "
                f"nor reported, first {self.unaccounted_loci[:5]}"
            )
        if self.unexpected_loci:
            problems.append(f"emitted loci not in the source: {self.unexpected_loci[:5]}")
        if self.unaccounted_pages:
            problems.append(f"source pages neither emitted nor reported: {self.unaccounted_pages}")
        accounted = self.loci_emitted + self.loci_reported + len(self.unaccounted_loci)
        if accounted != self.source_loci:
            problems.append(
                f"{self.loci_emitted} emitted + {self.loci_reported} reported + "
                f"{len(self.unaccounted_loci)} unaccounted != {self.source_loci} source loci"
            )
        if self.unrecognized_source_lines:
            problems.append(
                f"source lines neither locus nor page header: {self.unrecognized_source_lines[:5]}"
            )
        return problems

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
        ...     source_path=Path("data_sources/cache/ZL3b-n.txt"),
        ...     output_dir=Path("output")
        ... )
        >>> len(records) + len(report.unaccounted_loci) == report.source_loci
        True
    """
    # Compute source hash (FULL hash for reproducibility)
    require_licensed(source_path)  # before anything is read or written (S12)
    with open(source_path, "rb") as f:
        source_hash = hashlib.sha256(f.read()).hexdigest()

    # Initialize report with proper page tracking. source_verified: the hash is the SHA-256 of the bytes
    # read (the validators recompute it); whether it is the hash data_sources/sources.yaml pins is the
    # release manifest's "pinned" (B-074). The path is recorded relative to the repository, so no report
    # names a local checkout; the timestamp is the instant in UTC (B-070).
    report = BuildReport(
        source_file=repo_relative(source_path),
        source_hash=source_hash,
        source_verified=True,
        build_date=datetime.now(UTC).isoformat(),
        format_version=None,
    )

    # Parse the file
    parser = IVTFFParser()
    pages = list(parser.parse_file(source_path))

    report.alphabet = parser.alphabet
    report.format_version = parser.format_version
    report.format_options = parser.format_options
    # Lines the parser did not accept: each is a warning, and each rejected locus or page is
    # reported (accounted, not emitted), never lost silently (roadmap item 1.1).
    report.warnings.extend(f"parser: {w}" for w in parser.warnings)
    reported_loci = [w.locus_id for w in parser.warnings if w.locus_id]
    reported_pages = [w.page_id for w in parser.warnings if w.page_id]
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
            has_uncertain, has_illegible, _ = compute_flags(locus.text)
            text_clean = clean_text_for_analysis(locus.text)

            # Validate text_clean against charset
            is_valid, invalid_chars = validate_charset(text_clean)
            if not is_valid:
                report.warnings.append(
                    f"Invalid chars in {page.page_id}:{locus.locus_number}: {invalid_chars}"
                )

            # The structured layer: the markup the parser read from text_raw
            markup = locus.markup.fields()

            # The flags are exactly "the field is not empty" (Q25, B-025)
            has_alternatives = bool(markup["alternates"])
            # High-ASCII codes in the transliterated text (not in comments; Q25)
            has_high_ascii = bool(markup["high_ascii"])
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
                text_raw=locus.text_raw,
                locus_type=locus.locus_code,
                source_line=locus.source_line,
                **markup,
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

    # Account for every source locus and page, counted without the parser: each is emitted, or
    # reported by the parser, or unaccounted (which fails the build).
    loss = account(
        census_source(source_path),
        emitted_loci=[r.line_id for r in records],
        emitted_pages=[page.page_id for page in pages],
        reported_loci=reported_loci,
        reported_pages=reported_pages,
    )
    report.source_loci = loss.source_loci
    report.source_page_headers = loss.source_pages
    report.loci_emitted = loss.loci_emitted
    report.loci_reported = loss.loci_reported
    # One entry per rejected locus line, even when another reading of the same id was emitted
    # (reach 06fb787e gap 3); the accounting counts occurrences.
    report.reported_loci = reported_loci
    report.reported_pages = reported_pages
    report.unaccounted_loci = loss.unaccounted_loci
    report.unexpected_loci = loss.unexpected_loci
    report.unaccounted_pages = loss.unaccounted_pages
    report.unrecognized_source_lines = loss.unrecognized_lines

    # Sort records for deterministic output
    # Ordering contract: (folio_number, side, panel, line_index), parsers.page_order_key
    records.sort(key=lambda record: (*page_order_key(record.page_id), record.line_index))

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
    output_dir: Path,
    report: BuildReport,
    record_count: int,
    jsonl_hash: str,
    parquet_written: bool = False,
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
        parquet_written: whether this build wrote eva_lines.parquet; the manifest lists only files
            the build wrote (AB1 F2, B-069)
    """
    from vcat import __version__

    files: list[dict[str, Any]] = [
        {"name": "eva_lines.jsonl", "reproducible": True, "sha256": jsonl_hash}
    ]
    if parquet_written:
        files.append(
            {
                "name": "eva_lines.parquet",
                "note": "Content-equivalent; bitwise reproducibility not guaranteed",
                "reproducible": False,
            }
        )
    files.append(
        {
            "name": "eva_lines_build_report.json",
            "note": "Contains build timestamp",
            "reproducible": False,
        }
    )

    manifest = {
        "build": {"date": report.build_date, "tool_version": __version__},
        "contract": {
            # The current contract (AD1 F7, B-065): docs/charset_decisions.md is the 0.2.x record it supersedes
            "faithfulness_contract": "docs/data_model.md",
            "flags_computed_from": "tag-stripped text before marker removal",
            "json_serialization": "sort_keys=True, separators=(',',':'), newline='\\n'",
            "ordering": "deterministic by (folio_number, side, panel, line_index)",
        },
        "dataset": {"config": "lines", "name": "voynich-eva", "version": __version__},
        "files": files,
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
            # True only when the hash is the one data_sources/sources.yaml pins for the file (B-074)
            "pinned": pinned_sha256(report.source_file) == report.source_hash,
            "pinned_by": "data_sources/sources.yaml",
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

    Performs 10 validation checks on the built dataset. No check compares
    against a hand-written number: counts are checked against the build
    report. Whether the build accounts for every source locus is checked by
    the loss accounting (BuildReport.loss_problems), which the command line
    enforces before writing.

    Tests performed:
        1. Record count equals the report's total_lines
        2. All records have page_id
        3. All records have line_id
        4. No duplicate line_ids
        5. Every record with letters in text_clean has a character count
        6. Unique pages equal the report's pages_with_lines
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

    # Test 1: Record count agrees with the report
    check(
        "Record count matches report total_lines",
        bool(records) and len(records) == report.total_lines,
        f"{len(records)} records, report says {report.total_lines}",
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

    # Test 5: Records with letters have a character count
    uncounted = [
        r.line_id for r in records if r.char_count <= 0 and any(c.isalpha() for c in r.text_clean)
    ]
    check(
        "Every record with letters has a character count",
        not uncounted,
        f"{len(uncounted)} records, first {uncounted[:5]}",
    )

    # Test 6: Pages agree with the report
    unique_pages = len({r.page_id for r in records})
    check(
        "Unique pages match report pages_with_lines",
        unique_pages == report.pages_with_lines,
        f"{unique_pages} pages, report says {report.pages_with_lines}",
    )

    # Test 7: Both Currier languages present
    languages = {r.currier_language for r in records if r.currier_language}
    check(
        "Both Currier languages (A, B) present",
        "A" in languages and "B" in languages,
        f"Only {languages}",
    )

    # Test 8: Every line type names a generic locus type (no threshold; reach 61cfe3b0 gap 3)
    line_types = {r.line_type for r in records}
    check(
        "Every line type names a generic locus type",
        bool(line_types) and line_types <= {"paragraph", "label", "circle", "radius"},
        f"Line types {line_types}",
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
        default=source_file("ZL"),  # from data_sources/sources.yaml (B-081)
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

    from vcat import __version__

    print("=" * 60)
    print(f"VCAT EVA Lines Dataset Builder v{__version__}")
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

    # Loss accounting: an unaccounted source locus or page fails the build, before any output
    print(f"\nSource loci: {report.source_loci}, emitted: {report.loci_emitted}")
    problems = report.loss_problems()
    if problems:
        print("\nBuild FAILED: the output would not account for the source:")
        for problem in problems:
            print(f"  - {problem}")
        print("No output written.")
        sys.exit(1)

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

    parquet_written = False
    if args.format in ("parquet", "both"):
        parquet_path = output_dir / "eva_lines.parquet"
        print(f"\nExporting to Parquet: {parquet_path}")
        try:
            export_to_parquet(records, parquet_path)
        except RuntimeError as e:
            # A requested format that cannot be written fails the build (AB1 F2, B-069)
            print(f"\nBuild FAILED: the requested Parquet export failed: {e}")
            sys.exit(1)
        parquet_written = True
        print(f"  Wrote {len(records)} records")

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
        generate_manifest(output_dir, report, len(records), jsonl_hash, parquet_written)
        print(f"  Manifest written to {output_dir / 'release_manifest.json'}")

    print("\n" + "=" * 60)
    print("Build successful!")
    print(f"Total records: {len(records)}")
    if jsonl_hash:
        print(f"JSONL SHA256: {jsonl_hash}")
    print("=" * 60)


if __name__ == "__main__":  # pragma: no cover
    main()
