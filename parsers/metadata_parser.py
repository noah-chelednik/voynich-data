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
from enum import StrEnum
from typing import Any

from parsers.ivtff_parser import LocusType, Page


class ManuscriptSection(StrEnum):
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


class IllustrationType(StrEnum):
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


# Folio numbers with no page in the manuscript: the numbers IVTFF 2.0 Annex 1 (the list of pages)
# skips. tests/test_metadata_structure.py checks this list against the page headers of the source.
MISSING_FOLIOS: list[int] = [12, 59, 60, 61, 62, 63, 64, 74, 91, 92, 97, 98, 109, 110]

# Pages that span two folios (IVTFF 2.0 section 4.2): page name -> ((folio, side) where its record
# lives, (folio, side) it also covers). fRos is one drawing over f85 verso and f86 recto.
SPANNING_PAGES: dict[str, tuple[tuple[str, str], tuple[str, str]]] = {
    "fRos": (("f85", "verso"), ("f86", "recto")),
}


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
        page_id: Canonical page identifier (e.g., "f1r", "f86v3")
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
        recto_page_id: First recto page (kept for existing readers; see recto_page_ids)
        recto_page_ids: Every recto page of the folio, in panel order
        verso_page_ids: Every verso page of the folio, in panel order
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
    recto_page_ids: list[str] = field(default_factory=list)
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
        is_complete: False when a missing folio lies inside the quire's folio range; None when a
            missing folio lies between this quire and the next or previous one (consecutive quire
            letters) and the source cannot say which lost it; True otherwise
        total_lines: Total lines in quire
        sections: Sections represented in this quire
        notes: Additional notes
    """

    quire_id: str
    quire_letter: str | None = None
    folio_ids: list[str] = field(default_factory=list)
    folio_count: int = 0
    page_count: int = 0
    is_complete: bool | None = True
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
            page_id: Page identifier (e.g., "f1r", "f86v3")

        Returns:
            Tuple of (folio_number, side, panel_number or None)

        Raises:
            ValueError: If page_id format is invalid

        A page that spans two folios (``fRos``) parses as the folio and side its record lives in
        (SPANNING_PAGES).
        """
        for name, ((folio, side), _also) in SPANNING_PAGES.items():
            if page_id.lower() == name.lower():
                return int(folio[1:]), side[0], None
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
            attribution="vcat",  # VCAT's judgement, not a source's statement (roadmap item 2.8; data_sources/layers.yaml)
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
        folio_num, side, panel = self.parse_page_id(page.page_id)
        spanning = next((n for n in SPANNING_PAGES if n.lower() == page.page_id.lower()), None)
        page_id = spanning or page.page_id.lower()
        notes = []
        if spanning:
            (_, _), (also_folio, also_side) = SPANNING_PAGES[spanning]
            notes.append(
                f"{spanning} is one page that also covers {also_folio} {also_side} "
                "(IVTFF 2.0 section 4.2)"
            )

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

        # Determine if foldout. A panel's total needs the source's other pages on its side, which one page does not
        # have: `extract_pages` sets it (the highest panel number on the side); a record made from one page leaves it
        # unknown rather than take a table (reach dec3e688 gap 1: the old table gave f86v6 panel 6 of 4)
        is_foldout_panel = panel is not None
        total_panels = None

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
            notes=notes,
        )

    def extract_pages(self, pages: list[Page], whole_source: bool = False) -> list[PageRecord]:
        """Extract PageRecords from a list of IVTFF pages.

        Args:
            pages: List of parsed IVTFF Page objects
            whole_source: True only when `pages` are every page of one source (as `extract_all_metadata` passes
                them); then the panel totals and counts are stated, otherwise they are left unknown

        Returns:
            List of PageRecord objects
        """
        records = [self.extract_page_record(page) for page in pages]
        # a panel page's total is read from the source, not from a table: the highest panel number the source gives on
        # that folio side (audit 20261021-parsers F1). Only the pages of a whole source can say it (`whole_source`, as
        # `extract_all_metadata` passes); from part of a side the total is left unknown (review 1d0b83fe finding 2:
        # f67r1 alone was "1 of 1", the source's f67 recto has 2)
        if not whole_source:
            return records
        highest: dict[tuple[int, str], int] = {}
        for record in records:
            if record.panel_number is not None:
                key = (record.folio_number, record.side)
                highest[key] = max(highest.get(key, 0), record.panel_number)
        for record in records:
            if record.panel_number is not None:
                record.total_panels = highest[(record.folio_number, record.side)]
        return records

    def extract_folios(self, pages: list[Page], whole_source: bool = False) -> list[FolioRecord]:
        """Extract FolioRecords from a list of IVTFF pages.

        Aggregates page-level data into folio-level records.

        Args:
            pages: List of parsed IVTFF Page objects
            whole_source: True only when `pages` are every page of one source (as `extract_all_metadata` passes
                them); then the panel totals and counts are stated, otherwise they are left unknown

        Returns:
            List of FolioRecord objects
        """
        # Group pages by folio
        folio_pages: dict[str, list[PageRecord]] = defaultdict(list)

        # A spanning page is also listed under the second folio it covers (not counted twice).
        also_listed: dict[str, list[tuple[str, PageRecord]]] = defaultdict(list)
        for page in pages:
            record = self.extract_page_record(page)
            folio_pages[record.folio_id].append(record)
            if record.page_id in SPANNING_PAGES:
                _, (also_folio, also_side) = SPANNING_PAGES[record.page_id]
                also_listed[also_folio].append((also_side, record))

        # Build folio records
        folio_records = []
        # A folio whose only page is a spanning page listed under it still gets a record
        # (reach 06fb787e gap 4).
        folio_ids = sorted(set(folio_pages) | set(also_listed), key=self._folio_sort_key)
        for folio_id in folio_ids:
            page_records = folio_pages.get(folio_id, [])
            listed = [r for _side, r in also_listed.get(folio_id, [])]
            folio_num = self._folio_sort_key(folio_id)

            # Find recto and verso pages
            recto = [p for p in page_records if p.side == "recto"]
            verso = [p for p in page_records if p.side == "verso"]

            recto += [r for side, r in also_listed.get(folio_id, []) if side == "recto"]
            verso += [r for side, r in also_listed.get(folio_id, []) if side == "verso"]
            recto_page_ids = [p.page_id for p in sorted(recto, key=lambda x: x.panel_number or 0)]
            verso_page_ids = [p.page_id for p in sorted(verso, key=lambda x: x.panel_number or 0)]
            recto_page_id = recto_page_ids[0] if recto_page_ids else None

            # Determine if foldout
            is_foldout = len(verso) > 1 or any(p.is_foldout_panel for p in page_records)
            # the folio's panels: the highest panel number on either of its sides among its own pages, as its pages'
            # totals say (audit 20261021-parsers F2: the verso alone gave f85, whose two panels are on its recto, one;
            # review 1d0b83fe finding 3: counting both sides doubled f67, whose pages say "of 2")
            # stated only from the pages of a whole source (`whole_source`, as `extract_all_metadata` passes), as the pages'
            # totals are; from part of a folio it is unknown (review b8d5e9c6 finding 1)
            panel_count = (
                max((p.panel_number or 0) for p in page_records) or None
                if is_foldout and whole_source
                else None
            )

            # Aggregate stats
            total_lines = sum(p.line_count for p in page_records)

            # Get predominant language
            languages = [p.currier_language for p in page_records if p.currier_language]
            currier_language, tie_note = predominant(languages)

            # Get quire from first page (or from the spanning page that alone represents the folio)
            quire_id = (page_records or listed)[0].quire_id

            # Get section
            section = self.get_section_uncertain(folio_num)

            folio_records.append(
                FolioRecord(
                    folio_id=folio_id,
                    folio_number=folio_num,
                    quire_id=quire_id,
                    recto_page_id=recto_page_id,
                    recto_page_ids=recto_page_ids,
                    verso_page_ids=verso_page_ids,
                    is_foldout=is_foldout,
                    panel_count=panel_count,
                    is_missing=folio_num in MISSING_FOLIOS,
                    total_lines=total_lines,
                    currier_language=currier_language,
                    section=section,
                    notes=[
                        f"{r.page_id} is listed here and its lines are counted under {r.folio_id}"
                        for r in listed
                    ]
                    + ([tie_note] if tie_note else []),
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

        # Folio ranges and letters of every quire, for completeness (AP F5): a missing folio is
        # absent from the pages, so it is looked for in the quire's folio RANGE, not among the
        # folios present.
        # Every folio a quire's pages cover: a spanning page (fRos) also covers its second folio,
        # which may have no page of its own (AP2 F6), as extract_folios lists it.
        quire_folios: dict[str, set[str]] = {}
        for quire_id, page_records in quire_pages.items():
            quire_folios[quire_id] = {p.folio_id for p in page_records} | {
                SPANNING_PAGES[p.page_id][1][0] for p in page_records if p.page_id in SPANNING_PAGES
            }
        spans: dict[str, tuple[int, int]] = {}
        for quire_id, folios in quire_folios.items():
            numbers = [self._folio_sort_key(folio) for folio in folios]
            spans[quire_id] = (min(numbers), max(numbers))
        letters = {qid: records[0].quire_letter or "" for qid, records in quire_pages.items()}
        inside = {
            qid: [m for m in sorted(MISSING_FOLIOS) if lo < m < hi]
            for qid, (lo, hi) in spans.items()
        }
        between: dict[str, list[tuple[int, str]]] = defaultdict(list)
        ordered = sorted(spans, key=lambda qid: spans[qid][0])
        for left, right in zip(ordered, ordered[1:], strict=False):
            gap = [m for m in sorted(MISSING_FOLIOS) if spans[left][1] < m < spans[right][0]]
            consecutive = (
                len(letters[left]) == 1
                and len(letters[right]) == 1
                and ord(letters[right]) == ord(letters[left]) + 1
            )
            # Between quires with consecutive letters the gap belongs to one of the two; a skipped
            # letter means a whole quire is lost (IVTFF 2.0 Table 6: $Q P and R are not used).
            if gap and consecutive:
                between[left] += [(m, right) for m in gap]
                between[right] += [(m, left) for m in gap]

        # Build quire records
        quire_records = []
        for quire_id, page_records in sorted(quire_pages.items()):
            # Get unique folios
            folio_ids = sorted(quire_folios[quire_id], key=self._folio_sort_key)

            # Get quire letter
            quire_letter = page_records[0].quire_letter

            # Aggregate stats
            total_lines = sum(p.line_count for p in page_records)
            page_count = len(page_records)

            # Get sections represented
            sections = sorted(
                {p.section.value for p in page_records if p.section and p.section.value}
            )

            notes: list[str] = []
            is_complete: bool | None = True
            if inside[quire_id]:
                is_complete = False
                names = ", ".join(f"f{m}" for m in inside[quire_id])
                notes.append(f"missing folios inside this quire's folio range: {names}")
            if between[quire_id]:
                if is_complete:
                    is_complete = None
                for m, other in between[quire_id]:
                    notes.append(
                        f"missing folio f{m} lies between this quire and {other}; "
                        "the source cannot say which of the two lost it"
                    )

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
                    notes=notes,
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


def predominant(languages: list[str]) -> tuple[str | None, str | None]:
    """The language most of a folio's pages have, and a note when two or more tie: then none is chosen, so the result
    never depends on the order a set happens to iterate in (B-091, AP5 F1)."""
    if not languages:
        return None, None
    counts = {lang: languages.count(lang) for lang in languages}
    top = max(counts.values())
    leaders = sorted(lang for lang, n in counts.items() if n == top)
    if len(leaders) > 1:
        return None, f"its pages' Currier languages tie ({', '.join(leaders)}); none is predominant"
    return leaders[0], None


@dataclass
class BifolioRecord:
    """One bifolio (sheet folded once): the leaves the source's page variables put together.

    The leaves of a quire whose pages carry the same `$B` (bifolio within the quire, IVTFF Table 6) are conjugate: one
    sheet. Read from the source's page headers ($Q, $B). A sheet with one leaf in the source says only that: a partial
    transliteration omits leaves the manuscript keeps (review 1c291209 finding 1, B-106); its note names the folios of the
    quire that VCAT records as missing from the manuscript (MISSING_FOLIOS), if any.

    Attributes:
        bifolio_id: `{quire_id}.b{bifolio_number}` (e.g., "qA.b1")
        quire_id: The quire it belongs to
        bifolio_number: `$B`, counted from the outermost sheet of the quire
        folio_ids: Its leaves, in folio order
        page_ids: The pages of its leaves, in foliation order
        is_complete: Whether both leaves are in the source
        notes: Additional notes
    """

    bifolio_id: str
    quire_id: str
    bifolio_number: int
    folio_ids: list[str] = field(default_factory=list)
    page_ids: list[str] = field(default_factory=list)
    is_complete: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON/Parquet export."""
        return asdict(self)


@dataclass
class PageOrderRecord:
    """One page's place in one named page order (roadmap item 2.5).

    Attributes:
        order: The order's name: `foliation` (the default: folio number, recto before verso, panels in number order) or
            `<source>_file` (the order the source built from lists its pages in: `zl_file` for ZL)
        position: 1-based position in that order
        page_id: The page
        attribution: Who defines the order
    """

    order: str
    position: int
    page_id: str
    attribution: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON/Parquet export."""
        return asdict(self)


#: The named page orders (roadmap item 2.5): each with who defines it. `foliation` is the default; the other is the order
#: of the pages in the source the metadata is built from, named after that source (`file_order`).
PAGE_ORDERS = {
    "foliation": "the folio numbers written on the manuscript's leaves, as IVTFF names its pages",
}


def file_order(source_id: str | None, source_name: str | None) -> tuple[str, str]:
    """The name and attribution of the order of the pages in the source built from: `zl_file` for ZL, `gc_file` for GC,
    `source_file` for a file the registry does not list, so no order claims a source it was not read from (review
    020f7450 finding 1)."""
    if not source_id:
        return "source_file", "the order of the pages in the source file the metadata is built from"
    return (
        f"{source_id.lower()}_file",
        f"the order of the pages in the {source_name}, as voynich.nu publishes it",
    )


def extract_bifolia(pages: list[Page], page_records: list[PageRecord]) -> list[BifolioRecord]:
    """The bifolia the source's page headers define: per quire (`$Q`), the folios sharing a `$B`. Each page's folio is
    the one its page record names (`fRos` lies on f85; the page records place a spanning page)."""
    folio_of = {record.page_id: record.folio_id for record in page_records}
    from parsers.ivtff_parser import page_order_key

    groups: dict[tuple[str, int], list[Page]] = defaultdict(list)
    for page in pages:
        variables = page.variables
        if variables.quire and variables.bifolio is not None:
            groups[(variables.quire, variables.bifolio)].append(page)
    records = []
    # each quire's folio numbers in the source, for a one-leaf sheet's note (B-106)
    quire_folios: dict[str, list[int]] = defaultdict(list)
    for (quire, _number), members in groups.items():
        for page in members:
            folio = folio_of.get(page.page_id) or _folio_of(page.page_id)
            if folio[1:].isdigit():
                quire_folios[quire].append(int(folio[1:]))
    for (quire, number), members in sorted(groups.items()):
        page_ids = sorted({p.page_id for p in members}, key=page_order_key)
        folio_ids = sorted(
            {folio_of.get(p.page_id) or _folio_of(p.page_id) for p in members}, key=_folio_sort_key
        )
        records.append(
            BifolioRecord(
                bifolio_id=f"q{quire}.b{number}",
                quire_id=f"q{quire}",
                bifolio_number=number,
                folio_ids=folio_ids,
                page_ids=page_ids,
                is_complete=len(folio_ids) == 2,
                notes=_sheet_notes(folio_ids, quire_folios.get(quire, [])),
            )
        )
    return records


def extract_page_orders(
    pages: list[Page], source_id: str | None = None, source_name: str | None = None
) -> list[PageOrderRecord]:
    """Every page in each named order: `foliation`, and the order of the pages in the source built from (`file_order`)."""
    from parsers.ivtff_parser import page_order_key

    listed = [p.page_id for p in pages]
    name, attribution = file_order(source_id, source_name)
    orders = {
        "foliation": (sorted(listed, key=page_order_key), PAGE_ORDERS["foliation"]),
        name: (listed, attribution),
    }
    return [
        PageOrderRecord(order=order, position=i, page_id=page_id, attribution=who)
        for order, (ids, who) in orders.items()
        for i, page_id in enumerate(ids, 1)
    ]


def _sheet_notes(folio_ids: list[str], quire_folios: list[int]) -> list[str]:
    """What a sheet's leaf count says: nothing for two; for one, only that one is in the source, with the folios of its
    quire's range VCAT records as missing from the manuscript (MISSING_FOLIOS), which no source places on a sheet. A
    partial transliteration omits leaves the manuscript keeps, so one leaf is never itself a loss (review 1c291209
    finding 1, B-106)."""
    if len(folio_ids) == 2:
        return []
    if len(folio_ids) > 2:
        return [f"{len(folio_ids)} leaves share this bifolio number in the source"]
    low, high = (min(quire_folios), max(quire_folios)) if quire_folios else (0, -1)
    missing = [n for n in MISSING_FOLIOS if low <= n <= high]
    note = "one leaf of this sheet is in the source"
    if missing:
        note += "; folios of this quire missing from the manuscript: " + ", ".join(
            f"f{n}" for n in missing
        )
    return [note]


def _folio_sort_key(folio_id: str) -> tuple[int, str]:
    """Folios in number order; one without a number (`fRos`) after them, by name."""
    match = re.match(r"f(\d+)$", folio_id)
    return (int(match.group(1)), "") if match else (10**6, folio_id)


def _folio_of(page_id: str) -> str:
    match = re.match(r"(f\d+)", page_id)
    return match.group(1) if match else page_id


@dataclass
class MetadataExtractionResult:
    """Result of metadata extraction from an IVTFF file.

    Contains all three levels of metadata plus summary statistics.
    """

    pages: list[PageRecord]
    folios: list[FolioRecord]
    quires: list[QuireRecord]
    bifolia: list[BifolioRecord] = field(default_factory=list)
    page_orders: list[PageOrderRecord] = field(default_factory=list)
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
    pages: list[Page],
    source_file: str = "",
    source_hash: str = "",
    source_id: str | None = None,
    source_name: str | None = None,
) -> MetadataExtractionResult:
    """Extract all metadata from the pages of a whole IVTFF source (every page the parser read from one file, as the
    metadata builder passes them): a panel page's total is the highest panel number on its side among these pages.

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

    page_records = parser.extract_pages(pages, whole_source=True)
    folio_records = parser.extract_folios(pages, whole_source=True)
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
        bifolia=extract_bifolia(pages, page_records),
        page_orders=extract_page_orders(pages, source_id, source_name),
        source_file=source_file,
        source_hash=source_hash,
        total_pages=len(page_records),
        total_folios=len(folio_records),
        total_quires=len(quire_records),
        total_lines=total_lines,
        languages=dict(languages),
        sections=dict(sections),
    )
