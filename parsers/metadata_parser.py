"""
Metadata Parser
===============

Parser for extracting manuscript metadata from IVTFF transcription files.

This module extracts page-level, folio-level, and quire-level metadata
from IVTFF files and builds structured metadata records suitable for
dataset publication.

Main classes:
    PageRecord: Page-level metadata record
    FolioRecord: Folio-level metadata record (aggregates pages)
    QuireRecord: Quire-level metadata record (aggregates folios)
    MetadataParser: Parser that extracts metadata from IVTFF files

Example:
    >>> from parsers import IVTFFParser, MetadataParser
    >>> parser = IVTFFParser()
    >>> pages = list(parser.parse_file("ZL3b-n.txt"))
    >>> metadata = MetadataParser()
    >>> page_records = metadata.extract_pages(pages)
    >>> folio_records = metadata.extract_folios(pages)
    >>> quire_records = metadata.extract_quires(pages)
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from parsers.ivtff_parser import LocusType, Page


class ManuscriptSection(str, Enum):
    """Manuscript sections based on content and illustration type.

    Section boundaries are approximate and based on scholarly consensus.
    """

    HERBAL_A = "herbal_a"
    HERBAL_B = "herbal_b"
    ASTRONOMICAL = "astronomical"
    BIOLOGICAL = "biological"
    COSMOLOGICAL = "cosmological"
    PHARMACEUTICAL = "pharmaceutical"
    RECIPES = "recipes"
    UNKNOWN = "unknown"


class IllustrationType(str, Enum):
    """Illustration type codes from IVTFF $I variable.

    Attributes:
        HERBAL: Plant illustrations (H)
        ASTRONOMICAL: Astronomical/zodiac diagrams (A)
        BIOLOGICAL: Human figures and biological imagery (B)
        COSMOLOGICAL: Cosmological diagrams (C)
        PHARMACEUTICAL: Pharmaceutical/plant parts (P)
        STARS: Star diagrams (S)
        TEXT: Text only, no illustrations (T)
        ZODIAC: Zodiac signs (Z)
    """

    HERBAL = "H"
    ASTRONOMICAL = "A"
    BIOLOGICAL = "B"
    COSMOLOGICAL = "C"
    PHARMACEUTICAL = "P"
    STARS = "S"
    TEXT = "T"
    ZODIAC = "Z"


# Section mapping based on folio ranges
# Note: These are approximate boundaries from scholarly consensus
SECTION_MAPPING: dict[str, tuple[int, int, ManuscriptSection]] = {
    # (start_folio, end_folio, section)
    "herbal_a": (1, 25, ManuscriptSection.HERBAL_A),
    "herbal_b": (26, 66, ManuscriptSection.HERBAL_B),
    "astronomical": (67, 73, ManuscriptSection.ASTRONOMICAL),
    "biological": (75, 84, ManuscriptSection.BIOLOGICAL),
    "cosmological": (85, 86, ManuscriptSection.COSMOLOGICAL),
    "pharmaceutical": (87, 102, ManuscriptSection.PHARMACEUTICAL),
    "recipes": (103, 116, ManuscriptSection.RECIPES),
}


# Known foldout pages
FOLDOUT_PAGES: dict[str, list[str]] = {
    "f85v": ["f85v1", "f85v2", "f85v3", "f85v4", "f85v5", "f85v6"],
    "f86v": ["f86v1", "f86v2", "f86v3", "f86v4"],
}


# Known missing folios
MISSING_FOLIOS: list[int] = [12, 59, 60, 61, 62, 63, 64, 74, 91, 92, 93, 94, 95, 96, 109, 110]


@dataclass
class UncertainValue:
    """Structured representation of a value with uncertainty metadata.

    Used for fields where scholarly consensus may be lacking.

    Attributes:
        value: The assigned value
        attribution: Source of this assignment
        confidence: Confidence level (high/medium/low)
        disputed: Whether other sources disagree
        alternatives: Other proposed values
    """

    value: str | None
    attribution: str = "ivtff_transcription"
    confidence: str = "high"
    disputed: bool = False
    alternatives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class PageRecord:
    """Page-level metadata record.

    Represents metadata for a single manuscript page (one side of a folio).

    Attributes:
        page_id: Canonical page identifier (e.g., "f1r", "f85v3")
        folio_id: Parent folio identifier (e.g., "f1", "f85")
        side: Page side ("recto" or "verso")
        folio_number: Numeric folio number
        quire_id: Quire identifier (e.g., "qA", "q1")
        quire_letter: Quire letter from IVTFF $Q variable
        page_in_quire: Position within quire from IVTFF $P variable
        section: Manuscript section with uncertainty metadata
        currier_language: Currier language classification ("A" or "B")
        hand: Scribe/hand identifier
        illustration_type: Illustration type code
        line_count: Number of text lines on this page
        label_count: Number of labels on this page
        has_text: Whether page has any transcribed text
        is_foldout_panel: Whether this is a panel of a foldout page
        panel_number: Panel number if foldout (1-indexed)
        total_panels: Total panels if foldout
        is_missing: Whether this page is from a missing folio
        notes: Additional notes
    """

    page_id: str
    folio_id: str
    side: str
    folio_number: int
    quire_id: str | None = None
    quire_letter: str | None = None
    page_in_quire: str | None = None
    section: UncertainValue | None = None
    currier_language: str | None = None
    hand: str | None = None
    illustration_type: str | None = None
    line_count: int = 0
    label_count: int = 0
    has_text: bool = False
    is_foldout_panel: bool = False
    panel_number: int | None = None
    total_panels: int | None = None
    is_missing: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON/Parquet export."""
        d = asdict(self)
        # Convert UncertainValue to dict
        if self.section:
            d["section"] = self.section.to_dict()
        return d


@dataclass
class FolioRecord:
    """Folio-level metadata record.

    Represents metadata for a physical folio (leaf with two sides).

    Attributes:
        folio_id: Folio identifier (e.g., "f1", "f85")
        folio_number: Numeric folio number
        quire_id: Parent quire identifier
        recto_page_id: Recto page identifier
        verso_page_id: Verso page identifier (or list for foldouts)
        is_foldout: Whether this is a foldout folio
        panel_count: Number of panels if foldout
        is_missing: Whether this folio is missing
        total_lines: Total lines across all pages
        currier_language: Predominant Currier language
        section: Predominant section assignment
        notes: Additional notes
    """

    folio_id: str
    folio_number: int
    quire_id: str | None = None
    recto_page_id: str | None = None
    verso_page_ids: list[str] = field(default_factory=list)
    is_foldout: bool = False
    panel_count: int | None = None
    is_missing: bool = False
    total_lines: int = 0
    currier_language: str | None = None
    section: UncertainValue | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON/Parquet export."""
        d = asdict(self)
        if self.section:
            d["section"] = self.section.to_dict()
        return d


@dataclass
class QuireRecord:
    """Quire-level metadata record.

    Represents metadata for a quire (gathering of folios).

    Attributes:
        quire_id: Quire identifier (e.g., "qA", "q1")
        quire_letter: Original quire letter from IVTFF
        folio_ids: List of folio IDs in this quire
        folio_count: Number of folios
        page_count: Number of pages
        is_complete: Whether quire has no missing folios
        total_lines: Total lines in quire
        sections: Sections represented in this quire
        notes: Additional notes
    """

    quire_id: str
    quire_letter: str | None = None
    folio_ids: list[str] = field(default_factory=list)
    folio_count: int = 0
    page_count: int = 0
    is_complete: bool = True
    total_lines: int = 0
    sections: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON/Parquet export."""
        return asdict(self)


class MetadataParser:
    """Parser for extracting manuscript metadata from IVTFF pages.

    This class extracts page-level, folio-level, and quire-level metadata
    from parsed IVTFF Page objects.

    Example:
        >>> parser = MetadataParser()
        >>> page_records = parser.extract_pages(pages)
        >>> folio_records = parser.extract_folios(pages)
        >>> quire_records = parser.extract_quires(pages)
    """

    # Regex to parse page_id components
    PAGE_ID_PATTERN = re.compile(r"^f(\d+)([rv])(\d*)$")

    def __init__(self) -> None:
        """Initialize the metadata parser."""
        pass

    def parse_page_id(self, page_id: str) -> tuple[int, str, int | None]:
        """Parse a page_id into its components.

        Args:
            page_id: Page identifier (e.g., "f1r", "f85v3")

        Returns:
            Tuple of (folio_number, side, panel_number or None)

        Raises:
            ValueError: If page_id format is invalid
        """
        match = self.PAGE_ID_PATTERN.match(page_id.lower())
        if not match:
            raise ValueError(f"Invalid page_id format: {page_id}")

        folio_num = int(match.group(1))
        side = match.group(2)
        panel = int(match.group(3)) if match.group(3) else None

        return folio_num, side, panel

    def get_section(self, folio_number: int) -> ManuscriptSection:
        """Determine manuscript section based on folio number.

        Args:
            folio_number: Numeric folio number

        Returns:
            ManuscriptSection enum value
        """
        for _name, (start, end, section) in SECTION_MAPPING.items():
            if start <= folio_number <= end:
                return section
        return ManuscriptSection.UNKNOWN

    def get_section_uncertain(self, folio_number: int) -> UncertainValue:
        """Get section assignment with uncertainty metadata.

        Args:
            folio_number: Numeric folio number

        Returns:
            UncertainValue with section assignment
        """
        section = self.get_section(folio_number)

        # Mark boundary folios as having lower confidence
        is_boundary = False
        for _name, (start, end, _sec) in SECTION_MAPPING.items():
            if folio_number in (start, end):
                is_boundary = True
                break

        return UncertainValue(
            value=section.value,
            attribution="zandbergen_voynich_nu",
            confidence="medium" if is_boundary else "high",
            disputed=is_boundary,
            alternatives=[],
        )

    def is_foldout(self, page_id: str) -> bool:
        """Check if a page_id corresponds to a foldout panel.

        Args:
            page_id: Page identifier

        Returns:
            True if this is a foldout panel
        """
        # Check if it's a foldout panel (has panel number)
        folio_num, side, panel = self.parse_page_id(page_id)
        if panel is not None:
            return True

        # Check if base page has known foldout panels
        base_id = f"f{folio_num}{side}"
        return base_id in FOLDOUT_PAGES

    def extract_page_record(self, page: Page) -> PageRecord:
        """Extract a PageRecord from a parsed IVTFF Page.

        Args:
            page: Parsed IVTFF Page object

        Returns:
            PageRecord with extracted metadata
        """
        page_id = page.page_id.lower()
        folio_num, side, panel = self.parse_page_id(page_id)

        # Determine folio_id
        folio_id = f"f{folio_num}"

        # Count line types
        line_count = sum(1 for loc in page.loci if loc.locus_type == LocusType.PARAGRAPH)
        label_count = sum(1 for loc in page.loci if loc.locus_type == LocusType.LABEL)

        # Check for text
        has_text = any(loc.text.strip() for loc in page.loci)

        # Get quire info
        quire_letter = page.variables.quire
        quire_id = f"q{quire_letter}" if quire_letter else None

        # Determine if foldout
        is_foldout_panel = panel is not None
        total_panels = None
        if is_foldout_panel:
            base_id = f"f{folio_num}{side}"
            if base_id in FOLDOUT_PAGES:
                total_panels = len(FOLDOUT_PAGES[base_id])

        # Create record
        return PageRecord(
            page_id=page_id,
            folio_id=folio_id,
            side="recto" if side == "r" else "verso",
            folio_number=folio_num,
            quire_id=quire_id,
            quire_letter=quire_letter,
            page_in_quire=page.variables.page_in_quire,
            section=self.get_section_uncertain(folio_num),
            currier_language=page.variables.language,
            hand=page.variables.hand,
            illustration_type=page.variables.illustration,
            line_count=line_count,
            label_count=label_count,
            has_text=has_text,
            is_foldout_panel=is_foldout_panel,
            panel_number=panel,
            total_panels=total_panels,
            is_missing=folio_num in MISSING_FOLIOS,
            notes=[],
        )

    def extract_pages(self, pages: list[Page]) -> list[PageRecord]:
        """Extract PageRecords from a list of IVTFF pages.

        Args:
            pages: List of parsed IVTFF Page objects

        Returns:
            List of PageRecord objects
        """
        return [self.extract_page_record(page) for page in pages]

    def extract_folios(self, pages: list[Page]) -> list[FolioRecord]:
        """Extract FolioRecords from a list of IVTFF pages.

        Aggregates page-level data into folio-level records.

        Args:
            pages: List of parsed IVTFF Page objects

        Returns:
            List of FolioRecord objects
        """
        # Group pages by folio
        folio_pages: dict[str, list[PageRecord]] = defaultdict(list)

        for page in pages:
            record = self.extract_page_record(page)
            folio_pages[record.folio_id].append(record)

        # Build folio records
        folio_records = []
        for folio_id, page_records in sorted(
            folio_pages.items(), key=lambda x: self._folio_sort_key(x[0])
        ):
            folio_num = page_records[0].folio_number

            # Find recto and verso pages
            recto = [p for p in page_records if p.side == "recto"]
            verso = [p for p in page_records if p.side == "verso"]

            recto_page_id = recto[0].page_id if recto else None
            verso_page_ids = [p.page_id for p in sorted(verso, key=lambda x: x.panel_number or 0)]

            # Determine if foldout
            is_foldout = len(verso) > 1 or any(p.is_foldout_panel for p in page_records)
            panel_count = len(verso) if is_foldout else None

            # Aggregate stats
            total_lines = sum(p.line_count for p in page_records)

            # Get predominant language
            languages = [p.currier_language for p in page_records if p.currier_language]
            currier_language = max(set(languages), key=languages.count) if languages else None

            # Get quire from first page
            quire_id = page_records[0].quire_id

            # Get section
            section = self.get_section_uncertain(folio_num)

            folio_records.append(
                FolioRecord(
                    folio_id=folio_id,
                    folio_number=folio_num,
                    quire_id=quire_id,
                    recto_page_id=recto_page_id,
                    verso_page_ids=verso_page_ids,
                    is_foldout=is_foldout,
                    panel_count=panel_count,
                    is_missing=folio_num in MISSING_FOLIOS,
                    total_lines=total_lines,
                    currier_language=currier_language,
                    section=section,
                    notes=[],
                )
            )

        return folio_records

    def extract_quires(self, pages: list[Page]) -> list[QuireRecord]:
        """Extract QuireRecords from a list of IVTFF pages.

        Aggregates folio-level data into quire-level records.

        Args:
            pages: List of parsed IVTFF Page objects

        Returns:
            List of QuireRecord objects
        """
        # Group pages by quire
        quire_pages: dict[str, list[PageRecord]] = defaultdict(list)

        for page in pages:
            record = self.extract_page_record(page)
            if record.quire_id:
                quire_pages[record.quire_id].append(record)

        # Build quire records
        quire_records = []
        for quire_id, page_records in sorted(quire_pages.items()):
            # Get unique folios
            folio_ids = sorted({p.folio_id for p in page_records}, key=self._folio_sort_key)

            # Get quire letter
            quire_letter = page_records[0].quire_letter

            # Aggregate stats
            total_lines = sum(p.line_count for p in page_records)
            page_count = len(page_records)

            # Get sections represented
            sections = sorted(
                {p.section.value for p in page_records if p.section and p.section.value}
            )

            # Check completeness (no missing folios)
            folio_nums = [int(fid[1:]) for fid in folio_ids]
            missing_in_quire = [f for f in folio_nums if f in MISSING_FOLIOS]
            is_complete = len(missing_in_quire) == 0

            quire_records.append(
                QuireRecord(
                    quire_id=quire_id,
                    quire_letter=quire_letter,
                    folio_ids=folio_ids,
                    folio_count=len(folio_ids),
                    page_count=page_count,
                    is_complete=is_complete,
                    total_lines=total_lines,
                    sections=sections,
                    notes=[],
                )
            )

        return quire_records

    def _folio_sort_key(self, folio_id: str) -> int:
        """Get sort key for a folio_id.

        Args:
            folio_id: Folio identifier (e.g., "f1", "f85")

        Returns:
            Numeric sort key
        """
        match = re.match(r"f(\d+)", folio_id)
        return int(match.group(1)) if match else 0


@dataclass
class MetadataExtractionResult:
    """Result of metadata extraction from an IVTFF file.

    Contains all three levels of metadata plus summary statistics.
    """

    pages: list[PageRecord]
    folios: list[FolioRecord]
    quires: list[QuireRecord]
    source_file: str = ""
    source_hash: str = ""
    total_pages: int = 0
    total_folios: int = 0
    total_quires: int = 0
    total_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    sections: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "total_pages": self.total_pages,
            "total_folios": self.total_folios,
            "total_quires": self.total_quires,
            "total_lines": self.total_lines,
            "languages": self.languages,
            "sections": self.sections,
        }


def extract_all_metadata(
    pages: list[Page], source_file: str = "", source_hash: str = ""
) -> MetadataExtractionResult:
    """Extract all metadata from a list of IVTFF pages.

    Convenience function that extracts pages, folios, and quires
    in a single call.

    Args:
        pages: List of parsed IVTFF Page objects
        source_file: Name of source transcription file
        source_hash: SHA256 hash of source file

    Returns:
        MetadataExtractionResult with all extracted metadata
    """
    parser = MetadataParser()

    page_records = parser.extract_pages(pages)
    folio_records = parser.extract_folios(pages)
    quire_records = parser.extract_quires(pages)

    # Calculate summary stats
    total_lines = sum(p.line_count for p in page_records)

    # Count languages
    languages: dict[str, int] = defaultdict(int)
    for p in page_records:
        if p.currier_language:
            languages[p.currier_language] += 1

    # Count sections
    sections: dict[str, int] = defaultdict(int)
    for p in page_records:
        if p.section and p.section.value:
            sections[p.section.value] += 1

    return MetadataExtractionResult(
        pages=page_records,
        folios=folio_records,
        quires=quire_records,
        source_file=source_file,
        source_hash=source_hash,
        total_pages=len(page_records),
        total_folios=len(folio_records),
        total_quires=len(quire_records),
        total_lines=total_lines,
        languages=dict(languages),
        sections=dict(sections),
    )
