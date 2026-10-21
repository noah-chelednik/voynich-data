"""
IVTFF round trip
================

The definition of correct (principle 2, roadmap item 1.4): the parsed data rebuilds the source IVTFF
file byte for byte.

After a parse, ``IVTFFParser.document`` holds one record per item of the input, in input order: the
file header, comment lines, whitespace-only lines, page headers, loci with their continuation lines,
and the lines the parser did not accept. ``rebuild_source`` joins the records rebuilt from their
parsed fields (a locus from its identifier fields, separator and markup tokens; a page header from
its page name, separator and header text; the file header from its alphabet, version and rest), each
followed by its line terminator. Nothing is read back from the input.

Command line::

    python -m parsers.ivtff_roundtrip data_sources/cache/*.txt

prints one line per file and exits 1 when any file does not rebuild byte for byte.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .ivtff_parser import IVTFFParser, SourceRecord


def rebuild_source(records: Iterable[SourceRecord]) -> bytes:
    """The input of a parse rebuilt from its records (``IVTFFParser.document``).

    Args:
        records: The records of one parse, in input order.

    Returns:
        The bytes of the input: each record rendered from its fields (in the encoding it was decoded
        with; a line that could not be decoded, as read), then its line terminator.
    """
    out = bytearray()
    for record in records:
        body = record.render()
        out += body if isinstance(body, bytes) else body.encode(record.encoding)
        out += record.ending.encode("ascii")
    return bytes(out)


@dataclass(frozen=True)
class RoundTrip:
    """The round trip of one file.

    Attributes:
        path: The file.
        identical: Whether the rebuild is the file, byte for byte.
        size: The file's size in bytes.
        sha256: The SHA-256 of the file.
        records: How many records the parse produced.
        warnings: How many lines the (non-strict) parser did not accept; they are rebuilt too.
        first_difference: The 1-based line number of the first line that differs, or None.
    """

    path: Path
    identical: bool
    size: int
    sha256: str
    records: int
    warnings: int
    first_difference: int | None


def round_trip(path: Path | str) -> RoundTrip:
    """Parse a file (non-strict, so every line is read) and compare its rebuild with it."""
    path = Path(path)
    original = path.read_bytes()
    parser = IVTFFParser()
    for _ in parser.parse_file(path):
        pass
    rebuilt = rebuild_source(parser.document)
    first_difference = None
    if rebuilt != original:
        mine = rebuilt.splitlines(keepends=True)
        theirs = original.splitlines(keepends=True)
        first_difference = next(
            (n for n, (a, b) in enumerate(zip(mine, theirs, strict=False), 1) if a != b),
            min(len(mine), len(theirs)) + 1,
        )
    return RoundTrip(
        path=path,
        identical=rebuilt == original,
        size=len(original),
        sha256=hashlib.sha256(original).hexdigest(),
        records=len(parser.document),
        warnings=len(parser.warnings),
        first_difference=first_difference,
    )


def main(argv: list[str] | None = None) -> int:
    """Round-trip each named file; exit 1 when any does not rebuild byte for byte."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("files", nargs="+", type=Path, help="IVTFF files")
    args = parser.parse_args(argv)
    failed = False
    for path in args.files:
        result = round_trip(path)
        if result.identical:
            verdict = "identical"
        else:
            verdict = f"DIFFERS from line {result.first_difference}"
            failed = True
        print(
            f"{path.name}: {verdict} ({result.size} bytes, sha256 {result.sha256[:16]}..., "
            f"{result.records} records, {result.warnings} parser warnings)"
        )
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
