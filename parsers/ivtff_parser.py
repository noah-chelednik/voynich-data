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
import sys
import warnings as python_warnings
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from .ivtff_markup import (
    PARAGRAPH_END,
    PARAGRAPH_START,
    Markup,
    locus_code,
    parse_markup,
    word_space_problems,
)

#: One source line and its terminator (``\r\n``, ``\n``, ``\r``, or none on the last line).
_LINE = re.compile(r"([^\r\n]*)(\r\n|\n|\r|$)")


class LocusType(StrEnum):
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


class LocusPosition(StrEnum):
    """The locator of a locus: its position relative to the previous item (IVTFF 2.0, Table 8).

    The first four member names predate item 1.1 and are kept for existing readers; the values and
    the meanings below are the specification's.

    Attributes:
        NEW_UNIT: ``@`` unrelated to the previous item (always used for the first item on a page)
        CONTINUE: ``+`` generally below the previous item (the most common case)
        END_PARA: ``=`` on the same line as the previous item, separated by white space
        NEW_PARA: ``*`` at the start of the line below, at the left margin, while the previous was not
        CIRCULAR: ``&`` like ``=`` but along a circular line
        MISALIGNED: ``~`` like ``=`` but not well aligned vertically
        ABOVE_RIGHT: ``/`` to the right of, and above, the previous locus
        NOT_IN_MS: ``!`` text that in reality does not exist in the manuscript
    """

    NEW_UNIT = "@"
    CONTINUE = "+"
    END_PARA = "="
    NEW_PARA = "*"
    CIRCULAR = "&"
    MISALIGNED = "~"
    ABOVE_RIGHT = "/"
    NOT_IN_MS = "!"


#: Valid subtypes of each generic locus type (IVTFF 2.0, Table 9).
LOCUS_SUBTYPES: dict[str, str] = {
    "P": "01bcrt",
    "L": "0acfnpstxz",
    "C": "ac",
    "R": "io",
}

#: Page names (IVTFF 2.0, section 4.2): ``f`` + folio + ``r``/``v`` + optional panel, or ``fRos``.
PAGE_NAME = re.compile(r"^(?:f\d+[rv]\d*|fRos)$")


def page_order_key(page_id: str) -> tuple[int, int, int]:
    """Sort key of a page: (folio number, side, panel), the dataset's record ordering contract.

    ``fRos`` (one page over f85 verso and f86 recto, IVTFF 2.0 section 4.2) sorts as f85 verso, which
    is where Annex 1 places it: after ``f85r2`` and before the ``f86v`` panels. A name that is not a
    page name sorts after every page.
    """
    if page_id == "fRos":
        return (85, 1, 0)
    match = re.match(r"^f(\d+)([rv])(\d*)$", page_id)
    if not match:
        return (999999, 0, 0)
    return (int(match.group(1)), 0 if match.group(2) == "r" else 1, int(match.group(3) or 0))


@dataclass(frozen=True)
class ParseWarning:
    """A line the non-strict parser could not accept, recorded instead of skipped (principle 3), or a
    line it accepted that breaks a rule of IVTFF 2.0 which does not stop it being read.

    Attributes:
        line_number: 1-based line number in the input.
        reason: Why the line was not accepted, or which rule it breaks.
        line: The line as read (without its line end).
        locus_id: ``page:number`` when the line is a source locus that was NOT emitted.
        page_id: The page name when the line is a page header that was NOT accepted.
        emitted_id: The locus or page id when the line WAS emitted all the same: its text breaks a
            rule on page variables (section 6.3), word spaces (6.7) or paragraphs (6.9) but is
            read in full, so it is kept and the break recorded; strict mode raises instead
            (DECISIONS Q33). ``locus_id`` and ``page_id`` are then None.
    """

    line_number: int
    reason: str
    line: str
    locus_id: str | None = None
    page_id: str | None = None
    emitted_id: str | None = None

    def __str__(self) -> str:
        what = self.locus_id or self.page_id or self.emitted_id or "line"
        return f"line {self.line_number} ({what}): {self.reason}"


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
        cluster: Currier's hand ($C: 1 to 5, X or Z), the value as written (the name predates the
            specification's meaning and is kept for existing readers)
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
    cluster: str | None = None
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
            if value == "@":
                # set by text tags on the page, so unset before the first tag (IVTFF 2.0 section 6.8, conventions 2
                # and 3; B-051, reach 8e09e8e7 gap 2): no variable takes the literal '@'
                continue
            if var == "Q":
                pv.quire = value
            elif var == "P":
                pv.page_in_quire = value
            elif var == "F":
                pv.folio = value
            elif var == "B":
                # ASCII digits only: '²' is a digit to str.isdigit but not to int (reach 61cfe3b0 gap 1)
                pv.bifolio = int(value) if value.isascii() and value.isdigit() else None
            elif var == "I":
                pv.illustration = value
            elif var == "L":
                pv.language = value
            elif var == "H":
                pv.hand = value
            elif var == "C":
                pv.cluster = value
            elif var == "X":
                pv.extraneous = value

        return pv


#: One page variable setting in a page header: an upper-case letter set to one character (IVTFF 2.0
#: section 6.3).
_PAGE_VARIABLE = re.compile(r"\$([A-Z])=([^\s<>$])")
#: Table 6 values of the variables the dataset constrains: $B, the bifolio within the quire, which
#: the parser turns into an integer, and $L, the Currier language, which the row schema allows
#: only as A or B (reach 61cfe3b0 gap 2).
_TABLE_6_VALUES = {"B": "123456", "L": "AB"}
#: The value of a page variable that text tags set on the page (IVTFF 2.0 section 6.8, convention 2): valid for every
#: variable, and unset before the first tag (convention 3; B-051)
TEXT_TAG_VALUE = "@"


def page_header_problem(header_raw: str) -> str | None:
    """Why the text after a page name is not a valid page header (IVTFF 2.0 section 6.3), or None.

    The text (after the whitespace that follows ``<page-name>``) is empty, or the dedicated comment
    ``<! page-vars >`` with nothing but whitespace after it. Inside the comment, whitespace separates
    settings ``$X=y``: ``X`` one upper-case letter, ``y`` one character, each variable set at most
    once. Values are kept as written, except ``$B`` (an integer, 1 to 6) and ``$L`` (``A`` or ``B``),
    which must be Table 6 values because the dataset constrains them (AP3 F4, B-040; DECISIONS Q33).

    Args:
        header_raw: The page header after ``<page-name>`` and the whitespace that follows it.
    """
    if not header_raw.strip():
        return None
    match = re.fullmatch(r"<!([^<>]*)>[ \t]*", header_raw)
    if not match:
        return f"page header text {header_raw!r} is not one '<! page-vars >' comment"
    seen: set[str] = set()
    for setting in match.group(1).split():
        variable = _PAGE_VARIABLE.fullmatch(setting)
        if not variable:
            return f"page variable {setting!r} is not '$X=y' (one upper-case letter, one character)"
        name, value = variable.groups()
        if name in seen:
            return f"page variable ${name} is set twice"
        seen.add(name)
        if value == TEXT_TAG_VALUE:
            continue  # set by text tags on the page (IVTFF 2.0 section 6.8, conventions 2 and 3; B-051)
        if name == "B" and value not in _TABLE_6_VALUES["B"]:
            return f"page variable $B={value} is not a bifolio number 1 to 6 (IVTFF 2.0 Table 6)"
        if name == "L" and value not in _TABLE_6_VALUES["L"]:
            return f"page variable $L={value} is not a Currier language A or B (IVTFF 2.0 Table 6)"
    return None


def page_variables(header_raw: str) -> PageVariables:
    """The page variables of a page header, from its well-formed settings only.

    For a valid header these are ``PageVariables.from_header``'s values. When the header breaks
    section 6.3, the header text is kept as written (it rebuilds the line) and the parser records the
    break; a setting that is not ``$X=y``, a variable set again, or a ``$B`` or ``$L`` outside Table
    6 gives no value, so nothing invalid reaches the rows (reach 61cfe3b0 gaps 1 and 2).
    """
    match = re.match(r"<!([^<>]*)>", header_raw)
    kept: list[str] = []
    seen: set[str] = set()
    for setting in match.group(1).split() if match else []:
        variable = _PAGE_VARIABLE.fullmatch(setting)
        if not variable or variable.group(1) in seen:
            if variable:
                kept = [k for k in kept if not k.startswith(f"${variable.group(1)}=")]
            continue
        name, value = variable.groups()
        seen.add(name)
        if value == TEXT_TAG_VALUE and name in _TABLE_6_VALUES:
            continue  # unset until a text tag sets it (section 6.8, convention 3; B-051)
        if name in _TABLE_6_VALUES and value not in _TABLE_6_VALUES[name]:
            continue
        kept.append(setting)
    return PageVariables.from_header(" ".join(kept))


@dataclass
class Locus:
    """A single text locus (line/unit) in the manuscript.

    Represents one line or text unit from the manuscript with its
    locator information and transcription text.

    Attributes:
        page_id: Page identifier, e.g., "f1r", "f86v3"
        locus_number: Line/locus number within page, starting from 1
        position: Locator (IVTFF 2.0 Table 8), one of the eight LocusPosition values
        locus_type: Generic locus type (P, L, C, R)
        subtype: The subtype character as written (``"0"``, ``"z"``, ``"b"`` ...; Table 9)
        text: The actual transcription text
        transcriber: Transcriber code for interlinear files (H, C, F, etc.)
        raw_locator: Original locator string from the file
        comments: List of inline comments associated with this locus
        text_raw: The transliterated text exactly as written: everything after the identifier and
            the whitespace that follows it, to the end of the line (terminator excluded); a wrapped
            locus continues with its exact line terminators and continuation lines (DECISIONS Q24)
        separator: The whitespace between the identifier and ``text_raw``
        source_line: 1-based line number of the identifier in the input
        markup: ``text_raw`` cut into tokens (``parsers.ivtff_markup``)
        number_text: The locus number as written in the identifier (``"7"``, or ``"07"``)

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
    subtype: str | None = None
    text: str = ""
    transcriber: str | None = None
    raw_locator: str = ""
    comments: list[str] = field(default_factory=list)
    text_raw: str = ""
    separator: str = ""
    source_line: int = 0
    markup: Markup = field(default_factory=Markup)
    number_text: str = ""

    @property
    def identifier(self) -> str:
        """The locus identifier rebuilt from the parsed fields: ``<f1r.7,*P0>``, ``<f1r.1,@P0;H>``.

        For a locus the parser read, this is the identifier as written (``raw_locator``).
        """
        number = self.number_text or str(self.locus_number)
        transcriber = f";{self.transcriber}" if self.transcriber else ""
        return f"<{self.page_id}.{number},{self.locus_code}{transcriber}>"

    @property
    def locus_code(self) -> str:
        """The locus code as written, without the transcriber: ``@P0``, ``&Lz`` (D7)."""
        return locus_code(
            self.position.value if self.position else "",
            self.locus_type.value if self.locus_type else "",
            self.subtype or "",
        )

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
        source_line: 1-based line number of the page header in the input
        header_separator: The whitespace between ``<page-name>`` and ``header_raw``
        header_raw: The page header after ``<page-name>`` and that whitespace, as written (the
            ``<! page-vars >`` comment the variables are read from)

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
    source_line: int = 0
    header_separator: str = ""
    header_raw: str = ""

    @property
    def header(self) -> str:
        """The page header line rebuilt from the parsed fields: ``<f1r>      <! $Q=A ...>``."""
        return f"<{self.page_id}>{self.header_separator}{self.header_raw}"

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


@dataclass(kw_only=True)
class SourceRecord:
    """One or more consecutive input lines, as the parser read them (roadmap item 1.4).

    After a parse, ``IVTFFParser.document`` lists one record per item of the input, in input order:
    every line belongs to exactly one record, and ``parsers.ivtff_roundtrip.rebuild_source`` rebuilds
    the input from the records' parsed fields, byte for byte.

    Attributes:
        line_number: 1-based line number of the record's first line.
        ending: The line terminator of the record's last line (``"\n"``, ``"\r\n"``, ``"\r"``, or
            ``""`` for a last line without one).
    """

    line_number: int
    ending: str = ""
    # The encoding the record's text was decoded with, so the rebuild encodes it back the same way (S13: LSI is
    # Latin-1); a record kept as bytes is rebuilt as read.
    encoding: str = "utf-8"

    def render(self) -> str | bytes:
        """The record's lines rebuilt from its fields, without the last line's terminator."""
        raise NotImplementedError


@dataclass(kw_only=True)
class FileHeaderRecord(SourceRecord):
    """The file header (IVTFF 2.0 section 6.1), ``#=IVTFF Eva- 2.0 M 5``.

    Attributes:
        alphabet: The transliteration alphabet code.
        format_version: The format version, or None when the header has only an alphabet.
        format_options: The rest of the header as written (``M 5``; whitespace kept).
        separators: The whitespace before the alphabet, before the version, and before the rest.
    """

    alphabet: str
    format_version: str | None
    format_options: str
    separators: tuple[str, str, str]

    def render(self) -> str:
        before_alphabet, before_version, before_rest = self.separators
        version = before_version + self.format_version if self.format_version is not None else ""
        return f"#=IVTFF{before_alphabet}{self.alphabet}{version}{before_rest}{self.format_options}"


@dataclass(kw_only=True)
class CommentRecord(SourceRecord):
    """A comment line (IVTFF 2.0 section 6.2); ``text`` is everything after the ``#``."""

    text: str

    def render(self) -> str:
        return "#" + self.text


@dataclass(kw_only=True)
class BlankRecord(SourceRecord):
    """A line holding only whitespace (no meaning, IVTFF 2.0 section 5.6), kept as written."""

    text: str

    def render(self) -> str:
        return self.text


@dataclass(kw_only=True)
class PageHeaderRecord(SourceRecord):
    """An accepted page header; the page is the one the parser yields."""

    page: Page

    def render(self) -> str:
        return self.page.header


@dataclass(kw_only=True)
class LocusRecord(SourceRecord):
    """A locus line with its continuation lines, rebuilt from the locus's identifier fields,
    separator and markup tokens.

    Attributes:
        locus: The locus as parsed.
        emitted: Whether the parser emitted it; False when it was reported instead (undefined
            markup, a broken wrap, a paragraph rule), its text kept here all the same.
    """

    locus: Locus
    emitted: bool = True

    def render(self) -> str:
        return self.locus.identifier + self.locus.separator + self.locus.markup.raw


@dataclass(kw_only=True)
class RejectedRecord(SourceRecord):
    """A line the parser did not accept and could not read into fields, kept as read (``bytes``
    when it is not UTF-8); its warning is in ``IVTFFParser.warnings``."""

    text: str | bytes

    def render(self) -> str | bytes:
        return self.text


def recovered_id(match: re.Match[str]) -> str:
    """The id a malformed locus line is reported under (``IVTFFParser.RECOVER_LOCUS``): its page, its number and anything
    written after the number (LSI's ``44a``), so the report names the line as the file does (S13).
    """
    page_id, number, suffix = match.groups()
    return f"{page_id}:{int(number)}{suffix}"


class IVTFFParser:
    """Parser for IVTFF-format transcription files.

    Parses Intermediate Voynich Transliteration File Format (IVTFF) files
    and yields Page objects containing the parsed data.

    Attributes:
        strict: If True, raise ValueError on a line that cannot be accepted; if False, record it
            in ``warnings`` and do not emit it (never a silent skip)
        alphabet: Transliteration alphabet code from the file header (``Eva-``, ``EvaT`` ...)
        format_version: IVTFF format version from the file header (``2.0``, ``1.7`` ...)
        format_options: The rest of the file header after the version (``M 5``), or None
        warnings: ParseWarning per line not accepted in the last parse (non-strict mode)
        document: SourceRecord per item of the input of the last parse, in input order (complete
            once the parse has run to its end); every input line is in exactly one record

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

    # Regex patterns for parsing. The locus and page patterns recognize the SHAPE of a locus line or
    # page header (the same shapes vcat.loss_accounting counts); whether the parts are valid is then
    # checked against IVTFF 2.0, so an invalid line is reported with its id instead of vanishing.
    # The groups join to the whole line: whitespace, alphabet, whitespace and version (optional),
    # whitespace, the rest.
    HEADER_PATTERN = re.compile(r"^#=IVTFF(\s+)(\S+)(?:(\s+)(\S+))?(\s*)(.*)$")
    PAGE_PATTERN = re.compile(r"^<([^<>.,\s]+)>\s*(.*)$")
    LOCUS_PATTERN = re.compile(r"^<([^<>.,\s]+)\.(\d+),([^<>]*)>(.*)$")
    CODE_PATTERN = re.compile(r"^([@+*=&~/!])([A-Z])([a-z0-9])(?:;([^\s<>;]))?$")
    COMMENT_PATTERN = re.compile(r"^#(.*)$")
    # The recognizable start of a malformed locus identifier or page header.
    RECOVER_LOCUS = re.compile(r"^<([^<>.,;\s]+)\.(\d+)([^<>.,;\s]*)")
    RECOVER_PAGE = re.compile(r"^<(f\d+[rv]\d*|fRos)(?:\s|$)")

    def __init__(self, strict: bool = False) -> None:
        """Initialize parser.

        Args:
            strict: If True, raise ValueError on the first line that cannot be accepted. If False
                (default), do not emit that line and record it in ``warnings``: never skip silently.
        """
        self.strict = strict
        self.alphabet: str | None = None
        self.format_version: str | None = None
        self.format_options: str | None = None
        self.warnings: list[ParseWarning] = []
        self.document: list[SourceRecord] = []
        # The record of each locus read, by identity, to mark the ones reported instead of emitted.
        self._records: dict[int, LocusRecord] = {}
        # The locus whose paragraph start '<%>' has no end '<$>' yet on the current page (IVTFF 2.0
        # section 6.9), per transcriber: an interlinear file's parallel readings each have their own paragraphs
        # (B-049).
        self._paragraph_open: dict[str | None, Locus] = {}
        # Whether a paragraph end must follow a start: from format 1.6, which introduced the start mark <%> (the
        # spec's version history); a 1.5 file such as LSI marks only ends (S13).
        self._paragraph_pairs = True
        # Whether the word-space rules of IVTFF 2.0 section 6.7 apply: format 2.0 and later.
        self._word_space_rules = False

    def parse_file(self, filepath: Path | str, encoding: str | None = None) -> Iterator[Page]:
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
        if encoding is None:
            # A cached source is read in the encoding its record states (S13); any other file as UTF-8
            from vcat.sources import source_encoding

            encoding = source_encoding(filepath)
        data = filepath.read_bytes()
        # Each line is decoded on its own, strictly: a line that is not in the file's encoding is an
        # error or a recorded warning, never silently replaced (AP2 F5); every other line keeps its bytes.
        lines: list[str | bytes] = []
        for match in re.finditer(rb"([^\r\n]*)(\r\n|\n|\r|$)", data):
            if not match.group(0):
                continue
            try:
                lines.append(match.group(0).decode(encoding))
            except UnicodeDecodeError:
                lines.append(match.group(0))
        yield from self._parse_stream(lines)
        for record in self.document:
            record.encoding = encoding

    def parse_string(self, content: str) -> Iterator[Page]:
        """Parse IVTFF content from a string.

        Useful for parsing content already loaded into memory or
        for testing purposes.

        Args:
            content: IVTFF file content as string.

        Yields:
            Page objects parsed from the content.

        Example:
            >>> content = "<f1r> $L=A\\n<f1r.1,@P0;H> fachys.ykal"
            >>> parser = IVTFFParser()
            >>> pages = list(parser.parse_string(content))
        """
        yield from self._parse_stream(
            [match.group(0) for match in _LINE.finditer(content) if match.group(0)]
        )

    def _reject(
        self,
        line_number: int,
        line: str,
        reason: str,
        locus_id: str | None = None,
        page_id: str | None = None,
        emitted_id: str | None = None,
    ) -> None:
        """Raise in strict mode; otherwise record the line as a warning."""
        if self.strict:
            raise ValueError(f"Line {line_number}: {reason}: {line[:60]}")
        self.warnings.append(ParseWarning(line_number, reason, line, locus_id, page_id, emitted_id))

    def _unemit(self, page: Page | None, locus: Locus) -> None:
        """Take a locus out of its page: it is reported instead of emitted, and its record says so."""
        if page is not None:
            page.loci[:] = [kept for kept in page.loci if kept is not locus]
        self._records[id(locus)].emitted = False

    def _drop_wrapped(self, page: Page | None, record: LocusRecord, reason: str) -> None:
        """Report the wrapped locus of ``record`` as incomplete and remove it from its page."""
        locus = record.locus
        locus.markup = parse_markup(locus.text_raw)
        self._unemit(page, locus)
        self._reject(locus.source_line, _first_line(locus), reason, locus_id=locus.locus_id)

    def _check_markup(self, page: Page, locus: Locus) -> None:
        """Read the markup of a locus, now complete.

        A locus whose text holds markup IVTFF 2.0 does not define is reported under its id and not
        emitted (DECISIONS Q25). A locus whose word spaces break section 6.7 (format 2.0 and later)
        or whose paragraph marks break section 6.9 is read in full: it is emitted, and the break is
        an error in strict mode and otherwise a warning naming it (DECISIONS Q33).
        """
        locus.markup = parse_markup(locus.text_raw)
        if locus.markup.problems:
            self._unemit(page, locus)
            self._reject(
                locus.source_line,
                _first_line(locus),
                "undefined markup: " + "; ".join(locus.markup.problems),
                locus_id=locus.locus_id,
            )
            return
        rules = word_space_problems(locus.markup) if self._word_space_rules else []
        rules += self._paragraph_step(locus)
        if rules:
            self._reject(
                locus.source_line,
                _first_line(locus),
                "; ".join(rules),
                emitted_id=locus.locus_id,
            )

    def _paragraph_step(self, locus: Locus) -> list[str]:
        """Follow the paragraph marks of an emitted locus (IVTFF 2.0 section 6.9): only loci of
        generic type P carry them, and starts and ends alternate on a page. The paragraph state
        follows every mark, so each break is named once.

        Returns:
            The breaks of the rule, in text order; none when the marks follow it.
        """
        breaks: list[str] = []
        for token in locus.markup.tokens:
            if token.kind not in (PARAGRAPH_START, PARAGRAPH_END):
                continue
            if locus.locus_type != LocusType.PARAGRAPH:
                breaks.append(
                    f"paragraph mark {token.raw} on a locus of type {locus.locus_code!r} "
                    "(IVTFF 2.0 section 6.9: paragraphs are of generic type P only)"
                )
            opener = self._paragraph_open.get(locus.transcriber)
            if token.kind == PARAGRAPH_START:
                if opener is not None:
                    breaks.append(
                        f"<%> while the paragraph begun at {opener.locus_id} has not ended "
                        "(IVTFF 2.0 section 6.9)"
                    )
                self._paragraph_open[locus.transcriber] = locus
            else:
                if opener is None and self._paragraph_pairs:
                    breaks.append("<$> with no paragraph begun (IVTFF 2.0 section 6.9)")
                self._paragraph_open.pop(locus.transcriber, None)
        return breaks

    def _finish_page(self, page: Page) -> Page:
        """End a page: a paragraph begun on it and not ended on it breaks IVTFF 2.0 section 6.9
        (AP3 F6, B-042); the locus that began it stays emitted and the break is recorded."""
        openers, self._paragraph_open = self._paragraph_open, {}
        for opener in openers.values():
            self._reject(
                opener.source_line,
                _first_line(opener),
                f"the paragraph begun here does not end on page {page.page_id} "
                "(IVTFF 2.0 section 6.9)",
                emitted_id=opener.locus_id,
            )
        return page

    def _reject_line(self, line_number: int, line: str, reason: str) -> None:
        """Reject a whole line, recording the locus or page it names when that is recognizable."""
        if match := self.LOCUS_PATTERN.match(line):
            self._reject(
                line_number, line, reason, locus_id=f"{match.group(1)}:{int(match.group(2))}"
            )
        elif match := self.RECOVER_LOCUS.match(line):
            self._reject(line_number, line, reason, locus_id=recovered_id(match))
        elif (match := self.PAGE_PATTERN.match(line)) or (match := self.RECOVER_PAGE.match(line)):
            self._reject(line_number, line, reason, page_id=match.group(1))
        else:
            self._reject(line_number, line, reason)

    def _locus_code_problem(self, page: str, number: str, code: str) -> str | None:
        """Why a locus identifier is invalid (IVTFF 2.0 section 6.4), or None when it is valid."""
        if not PAGE_NAME.match(page):
            return f"invalid page name {page!r}"
        if len(number) > 3 or int(number) < 1:
            return f"locus number {number!r} is not 1 to 999"
        match = self.CODE_PATTERN.match(code)
        if not match:
            return f"invalid locus code {code!r} (a locator, a locus type, an optional ';' transcriber)"
        generic, subtype = match.group(2), match.group(3)
        if generic not in LOCUS_SUBTYPES:
            return f"unknown generic locus type {generic!r}"
        if subtype not in LOCUS_SUBTYPES[generic]:
            return f"locus type {generic + subtype!r} is not in IVTFF Table 9"
        return None

    def _parse_stream(self, lines: Iterable[str | bytes]) -> Iterator[Page]:
        """Parse a stream of lines.

        Internal method that handles the actual parsing logic. Every line becomes part of exactly
        one record of ``self.document`` (roadmap item 1.4).

        Args:
            lines: The input lines, each with its line terminator; a line given as bytes could
                not be decoded as UTF-8 and is reported.

        Yields:
            Page objects as they are completed.
        """
        # Everything the parser records belongs to the current input (review 8dc8e2d0 finding 2).
        self.warnings = []
        self.document = []
        self._records = {}
        self._paragraph_open = {}
        self._paragraph_pairs = True
        self._word_space_rules = False
        self.alphabet = self.format_version = self.format_options = None
        document = self.document
        current_page: Page | None = None
        pending_comments: list[str] = []
        # The record of a locus whose line ends with '/' and whose wrap is still open (IVTFF 2.0
        # Table 10), and the number of the line that began it; None and 0 when no wrap is open.
        wrapped: LocusRecord | None = None
        wrapped_line = 0
        # The terminator of the previous line, which joins a continuation to its locus text_raw.
        previous_ending = ""

        for line_num, item in enumerate(lines, 1):
            undecodable = isinstance(item, bytes)
            whole = item.decode("latin-1") if isinstance(item, bytes) else item
            ending_match = re.search(r"(\r\n|\n|\r)$", whole)
            ending = ending_match.group(1) if ending_match else ""
            line = whole[: len(whole) - len(ending)]
            joiner, previous_ending = previous_ending, ending

            # A line kept as read, when it is not accepted and has no fields to rebuild it from.
            rejected = RejectedRecord(line_number=line_num, ending=ending, text=line)

            if undecodable:
                assert isinstance(item, bytes)
                if wrapped is not None:
                    self._drop_wrapped(
                        current_page,
                        wrapped,
                        f"its wrap is not continued: line {line_num} is not UTF-8",
                    )
                    wrapped, wrapped_line = None, 0
                self._reject_line(line_num, line, "the line is not valid UTF-8")
                rejected.text = item[: len(item) - len(ending)]
                document.append(rejected)
                # An undecodable page header still starts a new page: the previous page ends here,
                # so a later locus naming it is not accepted under stale context (review f6b92c86
                # finding 1). Its own loci are then reported, as under any rejected page header.
                if not self.LOCUS_PATTERN.match(line) and (
                    self.PAGE_PATTERN.match(line) or self.RECOVER_PAGE.match(line)
                ):
                    if current_page is not None:
                        yield self._finish_page(current_page)
                    current_page = None
                continue

            if wrapped is not None:
                if line.startswith("/"):
                    more = line[1:].strip()
                    if more.endswith("/"):
                        more = more[:-1].rstrip()
                    elif more:
                        wrapped_line = 0
                    # A continuation with no text ("/" alone) completes nothing: the wrap stays
                    # open (review 8dc8e2d0 finding 1).
                    wrapped.locus.text += more
                    wrapped.locus.text_raw += joiner + line
                    wrapped.ending = ending
                    if not wrapped_line:
                        if current_page is not None:
                            self._check_markup(current_page, wrapped.locus)
                        wrapped = None
                    continue
                # The wrapped locus is incomplete: it is reported, not emitted (review 49c77167
                # finding 2); this line is then read on its own. A comment line cannot interrupt a
                # wrap (IVTFF 2.0 Table 10), so it ends the wrap too: keeping the wrap open would
                # emit a text_raw that skips a source line (review 09e1ca3c finding 1).
                what = "is a comment" if line.startswith("#") else "does not start with '/'"
                self._drop_wrapped(
                    current_page,
                    wrapped,
                    f"its wrap is not continued: line {line_num} {what}",
                )
                wrapped, wrapped_line = None, 0

            # Whitespace has no meaning (IVTFF 2.0 section 5.6).
            if not line.strip():
                document.append(BlankRecord(line_number=line_num, ending=ending, text=line))
                continue

            # The file header is the first line (IVTFF 2.0 section 6.1); a later line of that shape is a comment (B-050)
            header_match = self.HEADER_PATTERN.match(line) if line_num == 1 else None
            if header_match:
                gap1, alphabet, gap2, version, gap3, rest = header_match.groups()
                self.alphabet = alphabet
                self.format_version = version
                self.format_options = rest.strip() or None
                self._word_space_rules = _format_at_least(version, (2, 0))
                # off only for a stated format older than 1.6 (a header without a version keeps the rule)
                self._paragraph_pairs = not _format_older(version, (1, 6))
                document.append(
                    FileHeaderRecord(
                        line_number=line_num,
                        ending=ending,
                        alphabet=alphabet,
                        format_version=version,
                        format_options=rest,
                        separators=(gap1, gap2 or "", gap3),
                    )
                )
                continue

            # a file header on a later line of a file with none on line 1 is kept as the comment it is (B-050), but never
            # silently: without it the alphabet and version are unknown and the section 6.7 rules are off (audit
            # 20261021-parsers F3); an error when strict
            if line_num > 1 and self.alphabet is None and self.HEADER_PATTERN.match(line):
                self._reject(
                    line_num,
                    line,
                    "a file header not on line 1 (IVTFF 2.0 section 6.1): read as a comment, the file has no header",
                )

            comment_match = self.COMMENT_PATTERN.match(line)
            if comment_match:
                pending_comments.append(comment_match.group(1).strip())
                document.append(
                    CommentRecord(line_number=line_num, ending=ending, text=comment_match.group(1))
                )
                continue

            locus_match = self.LOCUS_PATTERN.match(line)
            if locus_match:
                page_id, number, code, rest = locus_match.groups()
                locus_id = f"{page_id}:{int(number)}"
                problem = self._locus_code_problem(page_id, number, code)
                if problem is None and current_page is None:
                    problem = "Locus without page context"
                if problem is None and current_page is not None and page_id != current_page.page_id:
                    problem = (
                        f"locus page {page_id!r} differs from the page header "
                        f"{current_page.page_id!r}"
                    )
                if problem is not None or current_page is None:
                    self._reject(line_num, line, problem or "", locus_id=locus_id)
                    document.append(rejected)
                    continue

                code_match = self.CODE_PATTERN.match(code)
                assert code_match is not None  # checked by _locus_code_problem
                text_raw = rest.lstrip(" \t")
                text_content = rest.strip()
                if text_content.endswith("/"):
                    text_content = text_content[:-1].rstrip()
                    wrapped_line = line_num

                locus = Locus(
                    page_id=page_id,
                    locus_number=int(number),
                    position=LocusPosition(code_match.group(1)),
                    locus_type=LocusType(code_match.group(2)),
                    subtype=code_match.group(3),
                    text=text_content,
                    transcriber=code_match.group(4),
                    raw_locator=line.split(">")[0] + ">",
                    comments=pending_comments.copy(),
                    text_raw=text_raw,
                    separator=rest[: len(rest) - len(text_raw)],
                    source_line=line_num,
                    number_text=number,
                )
                current_page.loci.append(locus)
                record = LocusRecord(line_number=line_num, ending=ending, locus=locus)
                self._records[id(locus)] = record
                document.append(record)
                pending_comments.clear()
                if wrapped_line:
                    wrapped = record
                else:
                    self._check_markup(current_page, locus)
                continue

            page_match = self.PAGE_PATTERN.match(line)
            if page_match:
                if current_page is not None:
                    yield self._finish_page(current_page)
                    current_page = None
                page_id = page_match.group(1)
                if not PAGE_NAME.match(page_id):
                    self._reject(line_num, line, f"invalid page name {page_id!r}", page_id=page_id)
                    document.append(rejected)
                    continue
                after_name = line[len(page_id) + 2 :]
                header_raw = after_name.lstrip(" \t")
                # Page variables that break section 6.3 are an error in strict mode; otherwise the
                # page is kept with its header text as written, and the break recorded (AP3 F4,
                # B-040, DECISIONS Q33).
                header_problem = page_header_problem(header_raw)
                if header_problem:
                    self._reject(line_num, line, header_problem, emitted_id=page_id)
                current_page = Page(
                    page_id=page_id,
                    variables=page_variables(header_raw),
                    comments=pending_comments.copy(),
                    source_line=line_num,
                    header_separator=after_name[: len(after_name) - len(header_raw)],
                    header_raw=header_raw,
                )
                document.append(
                    PageHeaderRecord(line_number=line_num, ending=ending, page=current_page)
                )
                pending_comments.clear()
                continue

            document.append(rejected)
            if line.startswith("/"):
                self._reject(
                    line_num, line, "continuation line with no line ending in '/' before it"
                )
                continue

            # A line starting with '<' that matches neither shape still names a locus or a page when
            # its start is recognizable (reach 06fb787e gaps 1 and 2); record that id.
            if recovered := self.RECOVER_LOCUS.match(line):
                self._reject(
                    line_num,
                    line,
                    "Unrecognized format: malformed locus identifier",
                    locus_id=recovered_id(recovered),
                )
            elif recovered := self.RECOVER_PAGE.match(line):
                self._reject(
                    line_num,
                    line,
                    "Unrecognized format: malformed page header",
                    page_id=recovered.group(1),
                )
                # A malformed page header still starts a new page, as a rejected or undecodable one
                # does: the previous page ends here (AP3 F3, B-039).
                if current_page is not None:
                    yield self._finish_page(current_page)
                current_page = None
            else:
                self._reject(line_num, line, "Unrecognized format")

        if wrapped is not None:
            self._drop_wrapped(current_page, wrapped, "the file ends inside its wrap")
            wrapped = None

        # Yield final page
        if current_page is not None:
            yield self._finish_page(current_page)

    def extract_text(self, text: str, clean: bool = True) -> str:
        """Extract readable text from raw IVTFF transcription text.

        Removes IVTFF markup that is not glyph data. Ligatures and high-ASCII codes are glyph data
        and are kept; a drawing interruption is a word boundary (IVTFF 2.0 Table 11, D1, D2,
        DECISIONS Q26).

        Removes:
            - In-line comments ``<!...>`` (first, so their contents never leak), text tags and
              paragraph marks ``<%>``, ``<$>``
            - Alternative readings ``[a:b]`` -> the first reading (when ``clean``)
            - Ligature braces ``{ct}`` -> ``ct`` (when ``clean``)

        Replaces:
            - ``<->`` and ``<~>`` (text interrupted by a drawing) -> a space

        Preserves:
            - High-ASCII codes ``@NNN;`` (transcription data, not markup)

        Args:
            text: Raw transcription text with IVTFF markup.
            clean: If True (default), keep the first reading of each alternate and drop ligature
                braces. If False, keep the alternate and ligature notation as written.

        Returns:
            The text with markup removed and whitespace normalized.

        Example:
            >>> parser = IVTFFParser()
            >>> parser.extract_text("dlo{ct}o")
            'dlocto'
            >>> parser.extract_text("a[b:c]d")
            'abd'
            >>> parser.extract_text("cthyd<->otar")
            'cthyd otar'
            >>> parser.extract_text("@140;")
            '@140;'
        """
        result = re.sub(r"<![^>]*>", "", text)
        result = re.sub(r"<[-~]>", " ", result)
        result = re.sub(r"<[^>]*>", "", result)
        if clean:
            result = re.sub(r"\[([^:\]]*)(?::[^\]]*)+\]", r"\1", result)
            result = re.sub(r"\{([^}]*)\}", r"\1", result)
        return re.sub(r"\s+", " ", result).strip()

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


def _first_line(locus: Locus) -> str:
    """The first source line of a locus, as written, without its terminator."""
    return locus.raw_locator + locus.separator + re.split(r"\r\n|\n|\r", locus.text_raw)[0]


def _format_older(version: str | None, than: tuple[int, int]) -> bool:
    """Whether a file header states a format version ``A.B`` older than ``than``; False when it states none."""
    match = re.fullmatch(r"(\d+)\.(\d+)", version or "")
    return match is not None and (int(match.group(1)), int(match.group(2))) < than


def _format_at_least(version: str | None, minimum: tuple[int, int]) -> bool:
    """Whether a file header's format version (``A.B``) is at least ``minimum``. Before format 2.0
    the version may be any text (IVTFF 2.0 Table 4), so anything that is not ``A.B`` is older."""
    match = re.fullmatch(r"(\d+)\.(\d+)", version or "")
    if match is None:
        return False
    return (int(match.group(1)), int(match.group(2))) >= minimum


class IVTFFWarning(UserWarning):
    """A line the non-strict parser did not accept, issued by ``parse_ivtff`` (DECISIONS Q27)."""


def parse_ivtff(filepath: Path | str) -> list[Page]:
    """Convenience function to parse an IVTFF file.

    Creates a parser instance and parses the entire file,
    returning all pages as a list. Every line the parser did not accept is issued as an
    ``IVTFFWarning`` naming its line and its locus or page id (AP2 F1): the helper never returns
    a partial transcription silently.

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
    pages = list(parser.parse_file(filepath))
    for warning in parser.warnings:
        python_warnings.warn(str(warning), IVTFFWarning, stacklevel=2)
    return pages


# Module test
if __name__ == "__main__":  # pragma: no cover
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
    # Lines the parser did not accept are shown and fail the command (AP2 F1, DECISIONS Q27).
    for warning in parser.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if parser.warnings:
        print(f"{len(parser.warnings)} line(s) not accepted", file=sys.stderr)
        sys.exit(1)
