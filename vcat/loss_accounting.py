"""
Loss accounting for IVTFF sources.

Every locus of a source file must be emitted by a build or explicitly reported; anything else is
UNACCOUNTED, and an unaccounted locus fails the build (docs/ROADMAP.md item 1.5, principle 3:
"never silent").

The census here reads the source with its own recognizer, independent of parsers/ivtff_parser.py,
so a locus the parser rejects is still counted. Per IVTFF 2.0 a line starting with ``<`` is either a
page header (``<f1r>``) or a locus (``<f1r.1,@P0>``); anything else starting with ``<`` is recorded
as unrecognized rather than skipped.

Locus ids use the dataset's ``line_id`` form, ``<page_id>:<locus_number>``. An interlinear file (LSI) holds one reading
per transcriber of a locus under one id, and accounting counts occurrences, so each reading is counted.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

LOCUS_LINE = re.compile(r"^<([^<>.,\s]+)\.(\d+),[^<>]*>")
PAGE_HEADER = re.compile(r"^<([^<>.,\s]+)>")
# A line whose identifier is malformed (a missing comma or closing '>') still counts by its
# recognizable start: a locus as ``<page.number``, a page header as ``<`` + a page name followed by
# whitespace or the line end. The parser reports such lines under the same ids.
LOCUS_START = re.compile(r"^<([^<>.,;\s]+)\.(\d+)([^<>.,;\s]*)")
PAGE_START = re.compile(r"^<(f\d+[rv]\d*|fRos)(?:\s|$)")

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "data_sources" / "cache"


@dataclass(frozen=True)
class SourceCensus:
    """What an IVTFF source contains, counted without the parser.

    Attributes:
        loci: locus ids (``page:n``) in source order.
        pages: page ids of the page headers, in source order.
        unrecognized: 1-based numbers of lines starting with ``<`` that are neither.
    """

    loci: tuple[str, ...]
    pages: tuple[str, ...]
    unrecognized: tuple[int, ...] = ()

    @property
    def pages_with_loci(self) -> set[str]:
        return {locus_id.rsplit(":", 1)[0] for locus_id in self.loci}


def census_text(text: str) -> SourceCensus:
    """Count the loci and page headers of IVTFF text."""
    loci: list[str] = []
    pages: list[str] = []
    unrecognized: list[int] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("<"):
            continue
        if match := LOCUS_LINE.match(line):
            loci.append(f"{match.group(1)}:{int(match.group(2))}")
        elif match := PAGE_HEADER.match(line):
            pages.append(match.group(1))
        elif match := LOCUS_START.match(line):
            # a malformed identifier keeps what follows its number (LSI's `44a`), as the parser reports it (S13)
            page, locus_number, suffix = match.groups()
            loci.append(f"{page}:{int(locus_number)}{suffix}")
        elif match := PAGE_START.match(line):
            pages.append(match.group(1))
        else:
            unrecognized.append(number)
    return SourceCensus(tuple(loci), tuple(pages), tuple(unrecognized))


def census_source(path: Path) -> SourceCensus:
    """Count the loci and page headers of an IVTFF file, read in the encoding its record states (S13)."""
    from vcat.sources import source_encoding

    return census_text(
        Path(path).read_text(encoding=source_encoding(path), errors="surrogateescape")
    )


@dataclass
class LossAccount:
    """Each source locus and page, accounted as emitted, reported, or unaccounted."""

    source_loci: int
    loci_emitted: int
    loci_reported: int
    unaccounted_loci: list[str] = field(default_factory=list)
    unexpected_loci: list[str] = field(default_factory=list)
    unknown_reported: list[str] = field(default_factory=list)
    source_pages: int = 0
    unaccounted_pages: list[str] = field(default_factory=list)
    unexpected_pages: list[str] = field(default_factory=list)
    unrecognized_lines: list[int] = field(default_factory=list)
    overcounted: int = 0

    @property
    def complete(self) -> bool:
        return not self.problems()

    def problems(self) -> list[str]:
        """One message per class of loss; empty when everything is accounted for."""
        found = []
        if self.unaccounted_loci:
            found.append(
                f"{len(self.unaccounted_loci)} source loci neither emitted nor reported, "
                f"first {self.unaccounted_loci[:5]}"
            )
        if self.unexpected_loci:
            found.append(
                f"{len(self.unexpected_loci)} emitted loci not in the source, "
                f"first {self.unexpected_loci[:5]}"
            )
        if self.unknown_reported:
            found.append(
                f"{len(self.unknown_reported)} reported loci not in the source, "
                f"first {self.unknown_reported[:5]}"
            )
        if self.unaccounted_pages:
            found.append(
                f"{len(self.unaccounted_pages)} source pages neither emitted nor reported: "
                f"{self.unaccounted_pages[:5]}"
            )
        if self.unexpected_pages:
            found.append(
                f"{len(self.unexpected_pages)} emitted or reported pages not in the source: "
                f"{self.unexpected_pages[:5]}"
            )
        if self.overcounted:
            found.append(
                f"{self.overcounted} locus lines emitted or reported more often than the source "
                "holds them"
            )
        if self.unrecognized_lines:
            found.append(
                f"{len(self.unrecognized_lines)} source lines start with '<' but are neither a "
                f"locus nor a page header, first at lines {self.unrecognized_lines[:5]}"
            )
        return found


def _unaccounted(occurrences: Sequence[str], covering: Sequence[str]) -> list[str]:
    """The occurrences (in source order) left over once each covering entry has accounted for one occurrence of its id:
    a source line, or a page header, repeated is covered only by as many entries (review 49c77167 finding 1 for loci;
    B-113, AC5 F1 for pages: a repeated header the parser omitted was certified)."""
    short = Counter(occurrences)
    short.subtract(Counter(covering))
    left: list[str] = []
    for x in occurrences:
        if short[x] > 0:
            left.append(x)
            short[x] -= 1
    return left


def account(
    census: SourceCensus,
    emitted_loci: Iterable[str],
    emitted_pages: Iterable[str],
    reported_loci: Iterable[str] = (),
    reported_pages: Iterable[str] = (),
) -> LossAccount:
    """Account every locus and page of ``census`` against what a build emitted or reported.

    Loci are counted as occurrences, not as distinct ids: a source may hold several lines with one
    id (readings by different transcribers in an interlinear file), and each line must be emitted or
    reported exactly once, so emitted + reported + unaccounted equals the source's locus lines.
    """
    emitted_list = list(emitted_loci)
    reported_list = list(reported_loci)
    emitted = set(emitted_list)
    reported = set(reported_list)
    source = set(census.loci)
    emitted_page_list = list(emitted_pages)
    reported_page_list = list(reported_pages)
    pages = set(emitted_page_list) | set(reported_page_list)
    # Per id: source lines minus emitted and reported entries. A shortfall is unaccounted (one
    # entry per missing line, review 49c77167 finding 1); an excess is overcounted. Ids are not
    # netted against each other.
    in_source = Counter(census.loci)
    covered = Counter(x for x in emitted_list if x in source)
    covered.update(x for x in reported_list if x in source)
    unaccounted = _unaccounted(
        census.loci, [x for x in emitted_list + reported_list if x in source]
    )
    return LossAccount(
        source_loci=len(census.loci),
        loci_emitted=sum(1 for x in emitted_list if x in source),
        loci_reported=sum(1 for x in reported_list if x in source),
        unaccounted_loci=unaccounted,
        unexpected_loci=sorted(emitted - source),
        unknown_reported=sorted(reported - source),
        overcounted=sum(max(0, covered[x] - n) for x, n in in_source.items()),
        source_pages=len(census.pages),
        unaccounted_pages=_unaccounted(census.pages, emitted_page_list + reported_page_list),
        unexpected_pages=sorted(pages - set(census.pages)),
        unrecognized_lines=list(census.unrecognized),
    )


def resolve_source(recorded: str | Path) -> Path | None:
    """Find the source file a build report names.

    A report records the path the build ran with: relative to the repository (as the builders record
    it), or absolute and possibly from another checkout. A relative path resolves under this repository
    (never the working directory); an absolute one to itself when the file exists there; else either
    resolves to the file of the same name in this repository's ``data_sources/cache/``, else to None.
    """
    path = Path(recorded)
    # A relative path is relative to the repository, as the builders record it
    # (vcat.sources.repo_relative), never to the caller's working directory (review 729a5385 finding 3)
    if not path.is_absolute():
        if str(recorded) and (REPO_ROOT / path).is_file():
            return REPO_ROOT / path
    elif path.is_file():
        return path
    candidate = CACHE_DIR / path.name
    if path.name and candidate.is_file():
        return candidate
    # a registered file anywhere under the cache, by its name (S13: LSI is in latin-1/)
    from vcat.sources import cached_sources

    return next(
        (s.path for s in cached_sources() if s.path.name == path.name and s.path.is_file()), None
    )
