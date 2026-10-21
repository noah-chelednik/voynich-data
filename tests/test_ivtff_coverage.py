"""
The parser accepts every IVTFF locus and page header (roadmap item 1.1).

Real-source expectations come from the cached files at test time, through the independent census in
``vcat.loss_accounting``; the synthetic inputs exercise each rule of IVTFF 2.0 (sections 5.5, 6.1, 6.3,
6.4 and 6.6; Tables 4, 7, 8, 9 and 10) that no cached source happens to use.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from builders.build_eva_lines import build_eva_lines
from parsers import IVTFFParser, LocusPosition, LocusType, page_order_key
from vcat.loss_accounting import census_source
from vcat.sources import cached_sources, nonconforming_lines, source_encoding

# every cached file the registry records, wherever under the cache it is (S13: LSI under latin-1/)
SOURCES = sorted(source.path for source in cached_sources())

# IVTFF 2.0 Table 8 (locators) and Table 9 (complete locus types), transcribed from the spec.
LOCATORS = "@+*=&~/!"
LOCUS_TYPES = {
    "P": "01bcrt",
    "L": "0acfnpstxz",
    "C": "ac",
    "R": "io",
}


def parse(content: str, strict: bool = False) -> tuple[IVTFFParser, list]:
    parser = IVTFFParser(strict=strict)
    return parser, list(parser.parse_string(content))


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: p.name)
def test_every_source_page_header_is_parsed(source: Path):
    census = census_source(source)
    parser = IVTFFParser()
    pages = list(parser.parse_file(source))
    assert [p.page_id for p in pages] == list(census.pages)
    assert all(locus.page_id == page.page_id for page in pages for locus in page.loci)
    emitted = [f"{p.page_id}:{locus.locus_number}" for p in pages for locus in p.loci]
    # Nothing is rejected but the lines the source's record lists as breaking IVTFF itself (S13: LSI's four `44a`
    # loci), each reported under its id; a warning may otherwise only name a line kept all the same (a break of IVTFF
    # 2.0 sections 6.3, 6.7 or 6.9, DECISIONS Q33; tests/test_round_trip.py checks which).
    known = nonconforming_lines(source)
    rejected = {w.line_number: w.locus_id for w in parser.warnings if w.emitted_id is None}
    assert rejected == known
    assert emitted == [locus for locus in census.loci if locus not in set(known.values())]


def test_every_spec_locator_and_locus_type_parses():
    codes = [
        f"{locator}{generic}{subtype}"
        for locator in LOCATORS
        for generic, subtypes in LOCUS_TYPES.items()
        for subtype in subtypes
    ]
    content = "<f1r>\n" + "".join(
        f"<f1r.{n},{code}>       text\n" for n, code in enumerate(codes, 1)
    )
    for strict in (False, True):
        parser, pages = parse(content, strict=strict)
        loci = pages[0].loci
        assert [locus.raw_locator[-4:-1] for locus in loci] == codes
        assert [locus.position.value for locus in loci] == [c[0] for c in codes]
        assert [locus.locus_type.value for locus in loci] == [c[1] for c in codes]
        assert [locus.subtype for locus in loci] == [c[2] for c in codes]
        assert parser.warnings == []
    assert {p.value for p in LocusPosition} == set(LOCATORS)
    assert {t.value for t in LocusType} == set(LOCUS_TYPES)


MALFORMED_LOCI = [
    "<f1r.2,P0>       no locator",
    "<f1r.2,@X0>      unknown generic type",
    "<f1r.2,@Pz>      subtype Table 9 does not list for P",
    "<f1r.2,@PO>      capital subtype",
    "<f1r.2,#P0>      unknown locator",
    "<f1r.2,@P0;HH>   two-character transcriber",
    "<f1r.0,@P0>      number zero",
    "<f1r.2 @P0>      no comma",
    "<f1r.2,@P0       no closing caret",
]


@pytest.mark.parametrize("bad", MALFORMED_LOCI)
def test_malformed_locus_is_an_error_or_a_warning(bad: str):
    content = f"<f1r>\n<f1r.1,@P0>       good\n{bad}\n<f1r.3,+P0>       good\n"
    with pytest.raises(ValueError, match="Line 3"):
        parse(content, strict=True)
    parser, pages = parse(content)
    assert [locus.locus_number for locus in pages[0].loci] == [1, 3]
    assert len(parser.warnings) == 1
    warning = parser.warnings[0]
    assert warning.line_number == 3
    assert warning.line == bad
    number = re.match(r"<f1r\.(\d+)", bad)
    assert number is not None
    assert warning.locus_id == f"f1r:{int(number.group(1))}"
    assert warning.reason


@pytest.mark.parametrize(
    ("bad", "page_id"),
    [
        ("<fXr>      <! $Q=A>", "fXr"),
        ("<f1x>", "f1x"),
        ("this is not a valid line", None),
        ("<f2r", "f2r"),
    ],
)
def test_unrecognized_lines_are_errors_or_warnings(bad: str, page_id: str | None):
    content = f"<f1r>\n<f1r.1,@P0>       good\n{bad}\n"
    with pytest.raises(ValueError, match="Line 3"):
        parse(content, strict=True)
    parser, pages = parse(content)
    assert [p.page_id for p in pages] == ["f1r"]
    assert [w.line_number for w in parser.warnings] == [3]
    assert parser.warnings[0].page_id == page_id
    assert parser.warnings[0].locus_id is None


def test_locus_outside_its_page_is_a_warning():
    content = "<f1r.1,@P0>       before any page\n<f1r>\n<f1r.2,@P0>       good\n<f2r.1,@P0>       wrong page\n"
    with pytest.raises(ValueError, match="Locus without page context"):
        parse(content, strict=True)
    with pytest.raises(ValueError, match="Line 3"):
        parse(content.split("\n", 1)[1], strict=True)
    parser, pages = parse(content)
    assert [(p.page_id, [x.locus_number for x in p.loci]) for p in pages] == [("f1r", [2])]
    assert [(w.line_number, w.locus_id) for w in parser.warnings] == [(1, "f1r:1"), (4, "f2r:1")]


def test_continuation_lines():
    wrapped = (
        "<f1r>\n<f1r.1,@P0>       qokeedy.dal /\n/ chedy.shol /\n/ daiin\n<f1r.2,+P0>       otal\n"
    )
    for strict in (False, True):
        parser, pages = parse(wrapped, strict=strict)
        assert [x.text for x in pages[0].loci] == ["qokeedy.dalchedy.sholdaiin", "otal"]
        assert parser.warnings == []

    # name: (content, line the strict error and the first warning name, the first warning's locus
    # id, locus texts emitted in non-strict mode). An incomplete wrap is reported under its locus id
    # and not emitted. A comment inside a wrap ends the wrap: the locus is reported and the next
    # continuation line is an orphan (review 09e1ca3c finding 1, DECISIONS Q30; until then the
    # wrap continued around the comment, which emitted a text_raw that skipped a source line).
    broken = {
        "orphan": ("<f1r>\n<f1r.1,@P0>       otal\n/ daiin\n", 3, None, ["otal"]),
        "comment inside": (
            "<f1r>\n<f1r.1,@P0>       otal /\n# note\n/ daiin\n",
            2,
            "f1r:1",
            [],
        ),
        "locus inside": (
            "<f1r>\n<f1r.1,@P0>       otal /\n<f1r.2,+P0>       daiin\n",
            2,
            "f1r:1",
            ["daiin"],
        ),
        "open at end": ("<f1r>\n<f1r.1,@P0>       otal /\n", 2, "f1r:1", []),
    }
    # The warning lines in non-strict mode, where they differ from the strict error's line alone.
    warning_lines = {"comment inside": [2, 4]}
    for name, (content, line, locus_id, texts) in broken.items():
        with pytest.raises(ValueError, match=f"Line {line}"):
            parse(content, strict=True)
        parser, pages = parse(content)
        assert [w.line_number for w in parser.warnings] == warning_lines.get(name, [line]), name
        assert [x.text for x in pages[0].loci] == texts, name
        assert parser.warnings[0].locus_id == locus_id, name


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: p.name)
def test_file_header_fields(source: Path, tmp_path: Path):
    header = (
        source.read_text(encoding=source_encoding(source), errors="surrogateescape")
        .splitlines()[0]
        .split()
    )
    parser = IVTFFParser()
    list(parser.parse_file(source))
    assert parser.alphabet == header[1]
    assert parser.format_version == header[2]
    assert parser.format_options == (" ".join(header[3:]) or None)

    _, report = build_eva_lines(source, tmp_path)
    assert (report.alphabet, report.format_version, report.format_options) == (
        parser.alphabet,
        parser.format_version,
        parser.format_options,
    )


def test_warnings_reset_per_parse():
    parser = IVTFFParser()
    list(parser.parse_string("<f1r>\ngarbage\n"))
    assert len(parser.warnings) == 1
    list(parser.parse_string("<f1r>\n<f1r.1,@P0>       good\n"))
    assert parser.warnings == []


def test_page_order_key():
    names = ["f85r1", "f85r2", "fRos", "f86v4", "f86v6", "f86v5", "f86v3", "f87r"]
    assert sorted(names, key=page_order_key) == [
        "f85r1",
        "f85r2",
        "fRos",
        "f86v3",
        "f86v4",
        "f86v5",
        "f86v6",
        "f87r",
    ]
    assert page_order_key("f1r") < page_order_key("f1v") < page_order_key("f2r")
