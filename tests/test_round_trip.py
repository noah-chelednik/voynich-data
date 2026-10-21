"""
The round trip (roadmap item 1.4): the parsed data rebuilds every source byte for byte.

Real-source expectations are read from the cached files at test time; the synthetic inputs cover
every kind of line the parser reads, accepts or rejects, and every line terminator. No count is
hand-written (principle 2).
"""

from __future__ import annotations

import random
import re
from dataclasses import replace
from pathlib import Path

import pytest

from parsers import IVTFFParser, PageVariables
from parsers import ivtff_parser as ip
from parsers import ivtff_roundtrip as rt
from vcat.loss_accounting import CACHE_DIR
from vcat.sources import cached_sources

ROOT = Path(__file__).resolve().parent.parent
# every cached file the registry records, wherever under the cache it is (S13: LSI under latin-1/)
SOURCES = sorted(source.path for source in cached_sources())
ZL = CACHE_DIR / "ZL3b-n.txt"
HEADER = "#=IVTFF Eva- 2.0 M 5\n"


def parsed(path: Path) -> IVTFFParser:
    """A non-strict parse of a file, run to its end."""
    parser = IVTFFParser()
    for _ in parser.parse_file(path):
        pass
    return parser


def lines_of(data: bytes) -> list[bytes]:
    """The lines of an input, each with its terminator (the parser's own line split)."""
    return [m.group(0) for m in re.finditer(rb"[^\r\n]*(?:\r\n|\n|\r|$)", data) if m.group(0)]


def span(record: ip.SourceRecord) -> int:
    """How many input lines a record covers: a locus with its continuation lines, else one."""
    if isinstance(record, ip.LocusRecord):
        return 1 + len(re.findall(r"\r\n|\n|\r", record.locus.text_raw))
    return 1


# --- every cached source --------------------------------------------------------------------


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_every_cached_source_rebuilds_byte_for_byte(source: Path):
    """The records of a parse of each cached source rebuild it, byte for byte."""
    assert rt.rebuild_source(parsed(source).document) == source.read_bytes()
    result = rt.round_trip(source)
    assert result.identical and result.first_difference is None
    assert result.size == len(source.read_bytes())


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_every_line_is_in_exactly_one_record(source: Path):
    """The records are in input order and cover every input line once: each begins on the line
    after the previous record ends, and the last ends on the last line."""
    document = parsed(source).document
    expected = 1
    for record in document:
        assert record.line_number == expected, record
        expected += span(record)
    assert expected - 1 == len(lines_of(source.read_bytes()))


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_records_are_the_parsed_data(source: Path):
    """The records hold the very loci and pages the parser yields, in order; every reported locus
    or page is a record too; every locus identifier rebuilt from its fields is the one written."""
    parser = IVTFFParser()
    pages = list(parser.parse_file(source))
    document = parser.document
    headers = [r.page for r in document if isinstance(r, ip.PageHeaderRecord)]
    assert len(headers) == len(pages)
    assert all(a is b for a, b in zip(headers, pages, strict=True))
    emitted = [r.locus for r in document if isinstance(r, ip.LocusRecord) and r.emitted]
    yielded = [locus for page in pages for locus in page.loci]
    assert len(emitted) == len(yielded)
    assert all(a is b for a, b in zip(emitted, yielded, strict=True))
    record_at = {r.line_number: r for r in document}
    for warning in parser.warnings:
        if warning.locus_id or warning.page_id:
            record = record_at[warning.line_number]
            assert isinstance(record, ip.RejectedRecord) or (
                isinstance(record, ip.LocusRecord) and not record.emitted
            )
    for locus in yielded:
        assert locus.identifier == locus.raw_locator, locus.locus_id
    for page in pages:
        assert page.variables == PageVariables.from_header(page.header_raw)


@pytest.mark.parametrize("kind", ["file_header", "comment", "page_header", "locus"])
def test_the_rebuild_reads_the_parsed_fields(kind: str):
    """Changing one parsed field changes exactly that line of the rebuild: the rebuild is made from
    the fields, not from a copy of the input."""
    parser = parsed(ZL)
    document = parser.document
    original = lines_of(ZL.read_bytes())
    if kind == "file_header":
        index = next(i for i, r in enumerate(document) if isinstance(r, ip.FileHeaderRecord))
        header = document[index]
        assert isinstance(header, ip.FileHeaderRecord)
        document[index] = replace(header, alphabet="Curr")
    elif kind == "comment":
        index = next(i for i, r in enumerate(document) if isinstance(r, ip.CommentRecord))
        comment = document[index]
        assert isinstance(comment, ip.CommentRecord)
        document[index] = replace(comment, text=comment.text + "x")
    elif kind == "page_header":
        index = next(i for i, r in enumerate(document) if isinstance(r, ip.PageHeaderRecord))
        page_record = document[index]
        assert isinstance(page_record, ip.PageHeaderRecord)
        page_record.page.page_id = "f999r"
    else:
        index = next(i for i, r in enumerate(document) if isinstance(r, ip.LocusRecord))
        locus_record = document[index]
        assert isinstance(locus_record, ip.LocusRecord)
        locus_record.locus.subtype = "z" if locus_record.locus.subtype != "z" else "0"
    rebuilt = lines_of(rt.rebuild_source(document))
    changed = [n for n, (a, b) in enumerate(zip(rebuilt, original, strict=True)) if a != b]
    assert changed == [document[index].line_number - 1]


def test_round_trip_command_line(capsys: pytest.CaptureFixture[str], monkeypatch):
    """The command line prints one line per file and exits 0 when every file rebuilds; it exits 1
    and names the first differing line when one does not."""
    assert rt.main([str(path) for path in SOURCES]) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split(":")[0] for line in out] == [path.name for path in SOURCES]
    assert all(": identical (" in line for line in out)

    real = rt.rebuild_source
    monkeypatch.setattr(rt, "rebuild_source", lambda records: real(records)[:-1] + b"?")
    assert rt.main([str(ZL)]) == 1
    assert "DIFFERS from line" in capsys.readouterr().out


# --- every kind of line ---------------------------------------------------------------------

#: Inputs for every kind of line: accepted, kept with a warning, and rejected. Each is read
#: without strict mode and must rebuild byte for byte.
CASES = {
    "plain": HEADER + "<f1r>      <! $Q=A $L=A>\n<f1r.1,@P0>       daiin.ol\n",
    "no final terminator": HEADER + "<f1r>\n<f1r.1,@P0> daiin",
    "crlf": (HEADER + "<f1r>\n# note\n<f1r.1,@P0> daiin\n").replace("\n", "\r\n"),
    "cr": (HEADER + "<f1r>\n<f1r.1,@P0> daiin\n").replace("\n", "\r"),
    "mixed terminators": HEADER + "<f1r>\r\n<f1r.1,@P0> a\r<f1r.2,+P0> b\n",
    "blank and whitespace lines": HEADER + "\n  \t\n<f1r>\n\n<f1r.1,@P0> daiin\n \n",
    "tab separator and trailing whitespace": HEADER + "<f1r>\t<! $L=B>  \n<f1r.1,@P0>\tdaiin  \n",
    "no header": "<f1r>\n<f1r.1,@P0> daiin\n",
    "header, alphabet only": "#=IVTFF Eva-\n<f1r>\n<f1r.1,@P0> daiin\n",
    "header with trailing whitespace": "#=IVTFF  Eva-   1.7  \n<f1r>\n<f1r.1,@P0> d\n",
    "byte order mark": "﻿" + HEADER + "<f1r>\n<f1r.1,@P0> daiin\n",
    "comments": HEADER + "#\n#  two spaces\n#no space\n<f1r>\n#x\n<f1r.1,@P0> d\n",
    "transcriber and leading zero": HEADER + "<f1r>\n<f1r.07,@P0;H> d\n<f1r.8,&Lz> o\n",
    "empty locus text": HEADER + "<f1r>\n<f1r.1,@P0>\n<f1r.2,+P0>   \n",
    "every markup": HEADER + "<f1r>\n<f1r.1,@P0> <%><!c>d{ct}o.[a:o:]<->@192;,???<~>y<@H=2><$>\n",
    "wrap": HEADER + "<f1r>\n<f1r.1,@P0> da /\n/ iin\n",
    "wrap through '/ /'": HEADER + "<f1r>\n<f1r.1,@P0> da /\n/ /\n/ iin\n",
    "wrap through '/'": HEADER + "<f1r>\n<f1r.1,@P0> da /\n/\n/ iin\n",
    "wrap through '/ ' and '/<tab>'": HEADER + "<f1r>\n<f1r.1,@P0> da /\n/ \n/\t\n/ iin\n",
    "crlf wrap": (HEADER + "<f1r>\n<f1r.1,@P0> da /\n/\n/ iin\n").replace("\n", "\r\n"),
    "wrap broken by a comment": HEADER + "<f1r>\n<f1r.1,@P0> da /\n# c\n<f1r.2,+P0> o\n",
    "wrap broken by a locus": HEADER + "<f1r>\n<f1r.1,@P0> da /\n<f1r.2,+P0> o\n",
    "wrap open at the end": HEADER + "<f1r>\n<f1r.1,@P0> da /\n/\n",
    "orphan continuation": HEADER + "<f1r>\n/ iin\n<f1r.1,@P0> d\n",
    "invalid page name": HEADER + "<fXr>\n<fXr.1,@P0> d\n",
    "malformed page header": HEADER + "<f1r>\n<f1r.1,@P0> d\n<f2r\n<f1r.2,+P0> o\n",
    "invalid page variables": HEADER + "<f1r> <! $L=AB $B=x>\n<f1r.1,@P0> d\n",
    "page header text": HEADER + "<f1r> garbage\n<f1r.1,@P0> d\n",
    "invalid locus code": HEADER + "<f1r>\n<f1r.1,@X9> d\n<f1r.2,@Pq> o\n",
    "locus without page": HEADER + "<f1r.1,@P0> d\n",
    "locus of another page": HEADER + "<f1r>\n<f2r.1,@P0> d\n",
    "malformed locus identifier": HEADER + "<f1r>\n<f1r.1 @P0> d\n",
    "undefined markup": HEADER + "<f1r>\n<f1r.1,@P0> d<?>o.{x\n",
    "word-space breaks": HEADER + "<f1r>\n<f1r.1,@P0> .da<-><~>iin.\n",
    "paragraph breaks": HEADER + "<f1r>\n<f1r.1,@L0> <%>d<$>\n<f1r.2,@P0> <%>o\n<f2r>\n",
    "garbage": HEADER + "garbage\n  <f1r>\n",
}


@pytest.mark.parametrize("name", list(CASES))
def test_every_kind_of_line_rebuilds(name: str):
    content = CASES[name]
    parser = IVTFFParser()
    list(parser.parse_string(content))
    assert rt.rebuild_source(parser.document) == content.encode("utf-8")


def test_undecodable_lines_rebuild(tmp_path: Path):
    """A line that is not UTF-8 is kept as read: alone, as a page header, and inside a wrap."""
    data = (
        HEADER.encode()
        + b"<f1r>\n<f1r.1,@P0> d\xff\n<f1r.2,@P0> da /\n/ i\xfein\n<f\xffr>\n<f2r>\n"
        + b"<f2r.1,@P0> o\r\n"
    )
    path = tmp_path / "source.txt"
    path.write_bytes(data)
    parser = parsed(path)
    assert parser.warnings
    assert rt.rebuild_source(parser.document) == data


def test_random_inputs_rebuild(tmp_path: Path):
    """Inputs assembled at random from the lines of every case above, with random terminators,
    rebuild byte for byte, whatever the parser makes of them."""
    pool = sorted({line for content in CASES.values() for line in re.split(r"\r\n|\n|\r", content)})
    pool.append("\xff")  # stands for a line that is not UTF-8
    terminators = ["\n", "\r\n", "\r", ""]
    rng = random.Random(14)
    for trial in range(len(pool) * len(terminators)):
        picked = [rng.choice(pool) for _ in range(rng.randrange(1, len(terminators) * 4))]
        data = b"".join(
            (b"\xff" if line == "\xff" else line.encode("utf-8"))
            + rng.choice(terminators[:-1]).encode()
            for line in picked
        )
        if rng.random() < 1 / len(terminators):
            data = data.rstrip(b"\r\n")
        path = tmp_path / f"case{trial}.txt"
        path.write_bytes(data)
        assert rt.rebuild_source(parsed(path).document) == data, data
