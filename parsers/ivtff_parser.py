"""
IVTFF Parser
============

Parser for Intermediate Voynich Transliteration File Format (IVTFF) files.

IVTFF is the standard format for Voynich manuscript transcriptions, developed
by René Zandbergen. This parser handles IVTFF format versions 1.7 and 2.0.

The format includes:
    - Page headers with metadata (quire, language, hand, etc.)
    - Locus identifiers specifying page, position, and type
    - Transcription text with optional markup
    - Comments and annotations

Main classes:
    IVTFFParser: Main parser class with file and string parsing methods
    Page: Represents a parsed manuscript page
    Locus: Represents a single text locus (line of text)
    PageVariables: Page-level metadata from IVTFF headers

Example:
    >>> parser = IVTFFParser()
    >>> pages = list(parser.parse_file("ZL3b-n.txt"))
    >>> len(pages)
    226
    >>> pages[0].page_id
    'f1r'

Format specification: http://www.voynich.nu/software/ivtt/IVTFF_format.pdf
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class LocusType(str, Enum):
    """Types of text loci in the manuscript.

    Different types of text positioning in the Voynich manuscript.

    Attributes:
        PARAGRAPH: Running text in paragraphs (most common)
        LABEL: Labels and single words attached to illustrations
        CIRCLE: Writing along circular paths
        RADIUS: Writing along radial lines
    """

    PARAGRAPH = "P"
    LABEL = "L"
    CIRCLE = "C"
    RADIUS = "R"


class LocusPosition(str, Enum):
    """Position indicators for loci.

    Indicates how a locus relates to surrounding text units.

    Attributes:
        NEW_UNIT: Start of a new text unit
        CONTINUE: Continuation of previous unit
        END_PARA: End of paragraph
        NEW_PARA: Start of new paragraph
    """

    NEW_UNIT = "@"
    CONTINUE = "+"
    END_PARA = "="
    NEW_PARA = "*"


@dataclass
class PageVariables:
    """Page-level metadata from IVTFF page headers.

    Contains all page-level variables that can be specified in IVTFF
    format page headers using $VAR=VALUE syntax.

    Attributes:
        quire: Quire identifier ($Q)
        page_in_quire: Position within quire ($P)
        folio: Folio identifier ($F)
        bifolio: Bifolio number ($B)
        illustration: Illustration type code ($I)
        language: Currier language classification, "A" or "B" ($L)
        hand: Hand/scribe identifier, typically "1" ($H)
        cluster: Page cluster number ($C)
        extraneous: Extraneous text indicator ($X)

    Example:
        >>> header = "<f1r> $Q=A $P=1 $L=A $H=1 $I=H"
        >>> pv = PageVariables.from_header(header)
        >>> pv.quire
        'A'
        >>> pv.language
        'A'
    """

    quire: str | None = None
    page_in_quire: str | None = None
    folio: str | None = None
    bifolio: int | None = None
    illustration: str | None = None
    language: str | None = None
    hand: str | None = None
    cluster: int | None = None
    extraneous: str | None = None

    @classmethod
    def from_header(cls, header_text: str) -> PageVariables:
        """Parse page variables from header text.

        Extracts $VAR=VALUE pairs from an IVTFF page header line.

        Args:
            header_text: The page header line, e.g., "<f1r> $Q=A $L=A $H=1"

        Returns:
            PageVariables instance with extracted values.

        Example:
            >>> pv = PageVariables.from_header("<f1r> $Q=A $P=1 $L=A $H=1")
            >>> pv.language
            'A'
        """
        pv = cls()

        # Pattern to match $VAR=VALUE pairs
        var_pattern = r"\$([A-Z])=([^\s$>]+)"

        for match in re.finditer(var_pattern, header_text):
            var, value = match.groups()
            if var == "Q":
                pv.quire = value
            elif var == "P":
                pv.page_in_quire = value
            elif var == "F":
                pv.folio = value
            elif var == "B":
                pv.bifolio = int(value) if value.isdigit() else None
            elif var == "I":
                pv.illustration = value
            elif var == "L":
                pv.language = value
            elif var == "H":
                pv.hand = value
            elif var == "C":
                pv.cluster = int(value) if value.isdigit() else None
            elif var == "X":
                pv.extraneous = value

        return pv


@dataclass
class Locus:
    """A single text locus (line/unit) in the manuscript.

    Represents one line or text unit from the manuscript with its
    locator information and transcription text.

    Attributes:
        page_id: Page identifier, e.g., "f1r", "f85v3"
        locus_number: Line/locus number within page, starting from 1
        position: Position indicator (@, +, =, *) or None
        locus_type: Type code (P, L, C, R) or None
        subtype: Numeric subtype for the locus type
        text: The actual transcription text
        transcriber: Transcriber code for interlinear files (H, C, F, etc.)
        raw_locator: Original locator string from the file
        comments: List of inline comments associated with this locus

    Example:
        >>> locus = Locus(
        ...     page_id="f1r",
        ...     locus_number=1,
        ...     position=LocusPosition.NEW_UNIT,
        ...     locus_type=LocusType.PARAGRAPH,
        ...     text="fachys.ykal.ar.ataiin"
        ... )
        >>> locus.locus_id
        'f1r:1'
    """

    page_id: str
    locus_number: int
    position: LocusPosition | None
    locus_type: LocusType | None
    subtype: int | None = None
    text: str = ""
    transcriber: str | None = None
    raw_locator: str = ""
    comments: list[str] = field(default_factory=list)

    @property
    def locus_id(self) -> str:
        """Generate unique locus identifier.

        Returns:
            String in format "{page_id}:{locus_number}", e.g., "f1r:1"
        """
        return f"{self.page_id}:{self.locus_number}"

    def __repr__(self) -> str:
        """Return string representation of the locus."""
        if len(self.text) > 30:
            return f"Locus({self.locus_id}, '{self.text[:30]}...')"
        return f"Locus({self.locus_id}, '{self.text}')"


@dataclass
class Page:
    """A single page (folio side) in the manuscript.

    Represents one side of a folio (recto or verso) with all its
    text loci and page-level metadata.

    Attributes:
        page_id: Page identifier, e.g., "f1r" (folio 1 recto)
        variables: Page-level metadata from the page header
        loci: List of Locus objects on this page
        comments: List of comments associated with the page

    Properties:
        line_count: Number of paragraph-type loci
        has_text: Whether the page has any transcribed text

    Example:
        >>> page = Page(page_id="f1r", variables=PageVariables())
        >>> page.line_count
        0
        >>> page.has_text
        False
    """

    page_id: str
    variables: PageVariables
    loci: list[Locus] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        """Count of paragraph-type text lines on this page.

        Returns:
            Number of loci with type PARAGRAPH.
        """
        return len([loc for loc in self.loci if loc.locus_type == LocusType.PARAGRAPH])

    @property
    def has_text(self) -> bool:
        """Whether page has any transcribed text.

        Returns:
            True if any locus has non-empty text.
        """
        return any(loc.text.strip() for loc in self.loci)


class IVTFFParser:
    """Parser for IVTFF-format transcription files.

    Parses Intermediate Voynich Transliteration File Format (IVTFF) files
    and yields Page objects containing the parsed data.

    Attributes:
        strict: If True, raise errors on parse failures
        format_version: IVTFF format version from file header
        format_options: Format options string from file header

    Example:
        >>> parser = IVTFFParser()
        >>> pages = list(parser.parse_file("ZL3b-n.txt"))
        >>> len(pages)
        226
        >>> pages[0].page_id
        'f1r'
        >>> pages[0].variables.language
        'A'
    """

    # Regex patterns for parsing
    HEADER_PATTERN = re.compile(r"^#=IVTFF\s+(\S+)\s*(.*)$")
    PAGE_PATTERN = re.compile(r"^<(f\d+[rv]\d*)>\s*(.*)$")
    LOCUS_PATTERN = re.compile(r"^<(f\d+[rv]\d*)\.(\d+),([+@=*]?)([PLCR])(\d*)(?:;([A-Z]))?>(.*)$")
    COMMENT_PATTERN = re.compile(r"^#(.*)$")

    def __init__(self, strict: bool = False) -> None:
        """Initialize parser.

        Args:
            strict: If True, raise errors on parse failures.
                If False (default), skip problematic lines silently.
        """
        self.strict = strict
        self.format_version: str | None = None
        self.format_options: str | None = None

    def parse_file(self, filepath: Path | str) -> Iterator[Page]:
        """Parse an IVTFF file and yield Page objects.

        Opens the file with UTF-8 encoding and parses it line by line,
        yielding complete Page objects as they are parsed.

        Args:
            filepath: Path to IVTFF file.

        Yields:
            Page objects parsed from the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If strict=True and parsing errors occur.

        Example:
            >>> parser = IVTFFParser()
            >>> for page in parser.parse_file("ZL3b-n.txt"):
            ...     print(f"{page.page_id}: {len(page.loci)} loci")
        """
        filepath = Path(filepath)

        with open(filepath, encoding="utf-8", errors="replace") as f:
            yield from self._parse_stream(f)

    def parse_string(self, content: str) -> Iterator[Page]:
        """Parse IVTFF content from a string.

        Useful for parsing content already loaded into memory or
        for testing purposes.

        Args:
            content: IVTFF file content as string.

        Yields:
            Page objects parsed from the content.

        Example:
            >>> content = "<f1r> $L=A\\n<f1r.1,@P;H> fachys.ykal"
            >>> parser = IVTFFParser()
            >>> pages = list(parser.parse_string(content))
        """
        yield from self._parse_stream(content.splitlines())

    def _parse_stream(self, lines: Iterator[str]) -> Iterator[Page]:
        """Parse a stream of lines.

        Internal method that handles the actual parsing logic.

        Args:
            lines: Iterator of text lines to parse.

        Yields:
            Page objects as they are completed.
        """
        current_page: Page | None = None
        pending_comments: list[str] = []

        for line_num, line in enumerate(lines, 1):
            line = line.rstrip("\n\r")

            # Skip empty lines
            if not line.strip():
                continue

            # Check for format header
            header_match = self.HEADER_PATTERN.match(line)
            if header_match:
                self.format_version = header_match.group(1)
                self.format_options = header_match.group(2).strip() or None
                continue

            # Check for comment
            comment_match = self.COMMENT_PATTERN.match(line)
            if comment_match:
                pending_comments.append(comment_match.group(1).strip())
                continue

            # Check for page header
            page_match = self.PAGE_PATTERN.match(line)
            if page_match:
                # Yield previous page if exists
                if current_page is not None:
                    yield current_page

                page_id = page_match.group(1)
                header_rest = page_match.group(2)

                # Parse page variables from header
                variables = PageVariables.from_header(header_rest)

                current_page = Page(
                    page_id=page_id,
                    variables=variables,
                    comments=pending_comments.copy(),
                )
                pending_comments.clear()
                continue

            # Check for locus/data line
            locus_match = self.LOCUS_PATTERN.match(line)
            if locus_match:
                if current_page is None:
                    if self.strict:
                        raise ValueError(f"Line {line_num}: Locus without page context")
                    continue

                page_id = locus_match.group(1)
                locus_num = int(locus_match.group(2))
                position_str = locus_match.group(3)
                locus_type_str = locus_match.group(4)
                subtype_str = locus_match.group(5)
                transcriber = locus_match.group(6)
                text_content = locus_match.group(7).strip()

                # Parse position
                position: LocusPosition | None = None
                if position_str:
                    try:
                        position = LocusPosition(position_str)
                    except ValueError:  # pragma: no cover
                        pass  # pragma: no cover

                # Parse locus type
                locus_type: LocusType | None = None
                try:
                    locus_type = LocusType(locus_type_str)
                except ValueError:  # pragma: no cover
                    pass  # pragma: no cover

                # Parse subtype
                subtype = int(subtype_str) if subtype_str else None

                # Create locus
                locus = Locus(
                    page_id=page_id,
                    locus_number=locus_num,
                    position=position,
                    locus_type=locus_type,
                    subtype=subtype,
                    text=text_content,
                    transcriber=transcriber,
                    raw_locator=line.split(">")[0] + ">" if ">" in line else "",
                    comments=pending_comments.copy(),
                )

                current_page.loci.append(locus)
                pending_comments.clear()
                continue

            # Unrecognized line
            if self.strict:
                raise ValueError(f"Line {line_num}: Unrecognized format: {line[:50]}")

        # Yield final page
        if current_page is not None:
            yield current_page

    def extract_text(self, text: str, clean: bool = True) -> str:
        """Extract clean text from raw IVTFF transcription text.

        Removes various IVTFF markup elements to produce clean text
        suitable for analysis. High-ASCII codes (@NNN;) are PRESERVED
        as they represent actual transcription data.

        Removes:
            - Inline comments {like this}
            - Alternative readings [a:b] -> keeps first option
            - Special markers (<-> line breaks, <%> paragraph starts)

        Preserves:
            - High-ASCII codes @NNN; (these are transcription data, not markup)

        Args:
            text: Raw transcription text with IVTFF markup.
            clean: If True (default), remove markup and keep first alternative.
                If False, preserve alternative notation.

        Returns:
            Cleaned text string with markup removed and
            whitespace normalized.

        Example:
            >>> parser = IVTFFParser()
            >>> parser.extract_text("{comment}fachys.ykal")
            'fachys.ykal'
            >>> parser.extract_text("a[b:c]d")
            'abd'
            >>> parser.extract_text("@140;")
            '@140;'
        """
        result = text

        # Remove inline comments {like this}
        result = re.sub(r"\{[^}]*\}", "", result)

        # Handle alternatives [a:b] - keep first option
        if clean:
            result = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", result)

        # Remove line continuation markers
        result = re.sub(r"<->", " ", result)
        result = re.sub(r"<\$>", "", result)  # End marker
        result = re.sub(r"<%>", "", result)  # Paragraph start
        result = re.sub(r"<~>", "", result)  # Column marker

        # Remove inline comments <!...>
        result = re.sub(r"<![^>]*>", "", result)

        # NOTE: High-ASCII codes @NNN; are intentionally PRESERVED.
        # They represent actual character data in the transcription,
        # not markup. Removing them causes data loss (9 lines become empty).

        # Normalize spaces
        result = re.sub(r"\s+", " ", result).strip()

        return result

    def has_high_ascii_codes(self, text: str) -> bool:
        """Check if text contains high-ASCII codes (@NNN;).

        High-ASCII codes represent characters that cannot be displayed
        in standard ASCII, encoded as @NNN; where NNN is a decimal code.

        Args:
            text: Text to check for high-ASCII codes.

        Returns:
            True if text contains one or more @NNN; patterns.

        Example:
            >>> parser = IVTFFParser()
            >>> parser.has_high_ascii_codes("@140;")
            True
            >>> parser.has_high_ascii_codes("fachys.ykal")
            False
        """
        return bool(re.search(r"@\d+;", text))


def parse_ivtff(filepath: Path | str) -> list[Page]:
    """Convenience function to parse an IVTFF file.

    Creates a parser instance and parses the entire file,
    returning all pages as a list.

    Args:
        filepath: Path to IVTFF file.

    Returns:
        List of Page objects from the file.

    Example:
        >>> pages = parse_ivtff("ZL3b-n.txt")
        >>> len(pages)
        226
        >>> pages[0].page_id
        'f1r'
    """
    parser = IVTFFParser()
    return list(parser.parse_file(filepath))


# Module test
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ivtff_parser.py <filepath>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    parser = IVTFFParser()

    page_count = 0
    locus_count = 0

    for page in parser.parse_file(filepath):
        page_count += 1
        locus_count += len(page.loci)

        if page_count <= 3:  # Print first 3 pages
            print(f"\n=== {page.page_id} ===")
            print(f"Language: {page.variables.language}, Hand: {page.variables.hand}")
            print(f"Loci: {len(page.loci)}")
            for locus in page.loci[:3]:
                clean_text = parser.extract_text(locus.text)
                print(f"  {locus.locus_number}: {clean_text[:60]}...")

    print(f"\n\nTotal: {page_count} pages, {locus_count} loci")
