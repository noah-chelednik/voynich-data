"""
Rules of IVTFF 2.0 the parser enforces since item 1.4: page headers end the previous page even
when malformed (B-039), page variables (section 6.3, B-040), word spaces (section 6.7, B-041) and
paragraphs (section 6.9, B-042); and the validators' check of `position` and `line_type` against
the source (B-044).

A break of 6.3, 6.7 or 6.9 leaves the text readable: strict mode raises, and otherwise the page or
locus is emitted and the break is a warning naming it (`ParseWarning.emitted_id`, DECISIONS Q33).
Real-source expectations are derived from the cached files at test time by checks written here
independently of the parser; no count is hand-written (principle 2).
"""

from __future__ import annotations

import contextlib
import io
import json
import re
from pathlib import Path

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from parsers import IVTFFParser, parse_ivtff
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from vcat.sources import cached_sources, source_encoding

ROOT = Path(__file__).resolve().parent.parent
# every cached file the registry records, wherever under the cache it is (S13: LSI under latin-1/)
SOURCES = sorted(source.path for source in cached_sources())
V2 = "#=IVTFF Eva- 2.0 M 5\n"
V17 = "#=IVTFF EvaT 1.7\n"


def parse(content: str, strict: bool = False) -> tuple[IVTFFParser, list]:
    parser = IVTFFParser(strict=strict)
    return parser, list(parser.parse_string(content))


def loci_of(pages: list) -> list[str]:
    return [locus.locus_id for page in pages for locus in page.loci]


def build(base: Path, content: str) -> tuple[Path, dict]:
    """Build a synthetic source the way the builder's command line does, into base/out."""
    base.mkdir(parents=True, exist_ok=True)
    source = base / "source.txt"
    source.write_text(content, encoding="utf-8", newline="")
    out = base / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(json.dumps(report.to_dict()))
    return out, report.to_dict()


def validator_errors(out: Path) -> tuple[list[str], list]:
    with contextlib.redirect_stdout(io.StringIO()):
        _, phase_errors = phase.validate_outputs(out)
        invariants = inv.verify_all_invariants(out)
    return phase_errors, invariants.failures


def kept_with_warning(content: str, emitted_id: str) -> IVTFFParser:
    """The break raises in strict mode; otherwise everything is emitted and one warning names the
    kept page or locus, with no id of a line not emitted."""
    with pytest.raises(ValueError):
        parse(content, strict=True)
    parser, pages = parse(content)
    census = re.findall(r"(?m)^<([^<>.,\s]+)\.(\d+),", content)
    assert loci_of(pages) == [f"{page}:{int(n)}" for page, n in census]
    assert [w.emitted_id for w in parser.warnings] == [emitted_id]
    assert all(w.locus_id is None and w.page_id is None for w in parser.warnings)
    return parser


# --- B-039: a malformed page header ends the previous page ---------------------------------


def test_malformed_page_header_ends_the_page():
    content = V2 + "<f1r>\n<f1r.1,@P0> daiin\n<f2r\n<f1r.2,+P0> ol\n<f2r>\n<f2r.1,@P0> o\n"
    parser, pages = parse(content)
    assert [p.page_id for p in pages] == ["f1r", "f2r"]
    assert loci_of(pages) == ["f1r:1", "f2r:1"]
    assert [(w.page_id, w.locus_id) for w in parser.warnings] == [("f2r", None), (None, "f1r:2")]
    with pytest.raises(ValueError, match="malformed page header"):
        parse(content, strict=True)


def test_malformed_page_header_is_accounted_by_the_build(tmp_path: Path):
    content = V2 + "<f1r>\n<f1r.1,@P0> daiin\n<f2r\n<f1r.2,+P0> ol\n"
    out, report = build(tmp_path, content)
    assert report["reported_loci"] == ["f1r:2"] and report["reported_pages"] == ["f2r"]
    assert not report["unaccounted_loci"] and not report["unaccounted_pages"]
    assert validator_errors(out) == ([], [])


# --- B-040: page variables (section 6.3) ----------------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "",
        "<!>",
        "<! >",
        "<! $Q=A $P=B $F=a $B=1 $I=T $L=A $H=1 $C=X $X=V>",
        "<!$L=A>",
        "<! $H=@ $L=B>   ",
        "<! $Z=q $C=Y>",
    ],
)
def test_valid_page_headers(header: str):
    for strict in (False, True):
        parser, pages = parse(f"{V2}<f1r>      {header}\n<f1r.1,@P0> daiin\n", strict)
        assert parser.warnings == [] and pages[0].header_raw == header
        assert loci_of(pages) == ["f1r:1"]


INVALID_HEADERS = [
    ("<! $L=AB>", "is not '$X=y'"),
    ("<! $L=C>", "Currier language"),
    ("<! $B=\u00b2>", "bifolio"),
    ("<! $B=x>", "bifolio"),
    ("<! $B=7>", "bifolio"),
    ("<! $B=0>", "bifolio"),
    ("<! $q=A>", "is not '$X=y'"),
    ("<! $L=A$B=1>", "is not '$X=y'"),
    ("<! L=A>", "is not '$X=y'"),
    ("<! $L=A $L=B>", "set twice"),
    ("<! $L=A> daiin", "is not one"),
    ("<! $L=A", "is not one"),
    ("daiin", "is not one"),
    ("<! $L=A><! $H=1>", "is not one"),
]


@pytest.mark.parametrize("header, why", INVALID_HEADERS)
def test_invalid_page_variables_are_errors_or_kept_with_a_warning(header: str, why: str):
    content = f"{V2}<f1r> {header}\n<f1r.1,@P0> daiin\n<f2r>\n<f2r.1,@P0> ol\n"
    parser = kept_with_warning(content, "f1r")
    assert why in parser.warnings[0].reason
    pages = list(IVTFFParser().parse_string(content))
    assert pages[0].header_raw == header


@pytest.mark.parametrize("header", [header for header, _ in INVALID_HEADERS])
def test_page_variable_warning_reaches_the_build(tmp_path: Path, header: str):
    """For every kind of invalid header the build emits the page and its loci, records the
    warning, reports nothing, and both validators accept it (reach 61cfe3b0 gap 2)."""
    out, report = build(tmp_path, f"{V2}<f1r> {header}\n<f1r.1,@P0> daiin\n")
    assert [json.loads(line)["line_id"] for line in (out / "eva_lines.jsonl").open()] == ["f1r:1"]
    assert any("page" in w for w in report["warnings"])
    assert report["reported_loci"] == [] and report["reported_pages"] == []
    assert validator_errors(out) == ([], [])


@pytest.mark.parametrize(
    "header, language, bifolio",
    [
        ("<! $L=AB $B=2>", None, 2),
        ("<! $L=C $B=\u00b2>", None, None),
        ("<! $L=A $L=B $B=1>", None, 1),
        ("<! $L=B $B=7 $q=A>", "B", None),
        ("<! $L=A> daiin", "A", None),
        ("daiin $L=A", None, None),
    ],
)
def test_invalid_settings_give_no_value(header: str, language: str | None, bifolio: int | None):
    """A header that breaks 6.3 keeps its text as written, and only its well-formed settings give
    values: nothing invalid reaches the rows."""
    _, pages = parse(f"{V2}<f1r> {header}\n<f1r.1,@P0> daiin\n")
    assert pages[0].header_raw == header
    assert (pages[0].variables.language, pages[0].variables.bifolio) == (language, bifolio)


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_every_source_page_header_follows_section_6_3(source: Path):
    """No cached page header breaks section 6.3, by the parser and by a check written here."""
    parser = IVTFFParser()
    pages = list(parser.parse_file(source))
    headers = [
        m.group(1)
        for line in source.read_text(encoding=source_encoding(source)).splitlines()
        if (m := re.match(r"^<f[^<>.,\s]*>\s*(.*)$", line))
    ]
    assert len(headers) == len(pages)
    for header in headers:
        assert re.fullmatch(r"(?:<!(?:\s*\$[A-Z]=[^\s<>$])*\s*>\s*)?", header), header
    assert not [w for w in parser.warnings if "page variable" in w.reason]


# --- B-041: word spaces (section 6.7) -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "<->daiin",
        ".daiin",
        "daiin,",
        "daiin<~>",
        "da<-><~>iin",
        "da.,iin",
        "da.<!c>.iin",
        "<%><!c>.daiin<$>",
        "da. /\n/ .iin",
        ".",
    ],
)
def test_word_space_breaks_in_format_2_0(text: str):
    content = f"{V2}<f1r>\n<f1r.1,@P0> {text}\n"
    parser = kept_with_warning(content, "f1r:1")
    assert "6.7" in parser.warnings[0].reason or "next to a word space" in parser.warnings[0].reason


@pytest.mark.parametrize(
    "text",
    [
        "da<->iin",
        "da.iin,ol<~>y",
        "<%><!c>daiin<$>",
        "<!c>da.iin<!d>",
        "da<!c>.iin",
        "[a:.]daiin",
        "?.???",
        "{ct}.@192;",
        "da. /\n/ iin",
        "da /\n/ <->iin",
        "",
    ],
)
def test_word_spaces_that_follow_section_6_7(text: str):
    for strict in (False, True):
        parser, pages = parse(f"{V2}<f1r>\n<f1r.1,@P0> {text}\n", strict)
        assert parser.warnings == [] and loci_of(pages) == ["f1r:1"]


@pytest.mark.parametrize("header", [V17, "#=IVTFF Eva-\n", "#=IVTFF Eva- x.y M\n", ""])
def test_word_space_rules_do_not_apply_before_format_2_0(header: str):
    """Section 6.7: files of format 1.7 or earlier did not follow the rules (and a version that is
    not A.B is from before 2.0, Table 4)."""
    for strict in (False, True):
        parser, pages = parse(f"{header}<f1r>\n<f1r.1,@P0> <->da<-><~>iin.\n", strict)
        assert parser.warnings == [] and loci_of(pages) == ["f1r:1"]


def breaks_section_6_7(text_raw: str) -> bool:
    """Section 6.7 by a check independent of the parser: word spaces between text only."""
    text = re.sub(r"<![^>]*>|<[%$]>|<@[A-Z]=[^>]>", "", text_raw)
    text = re.sub(r"[ \t]*/(?:\r\n|\n|\r)/[ \t]*", "", text)  # wraps
    text = re.sub(r"\[[^\]]*\]|\{[^}]*\}|@\d{3};", "x", text)  # alternates, ligatures, codes
    # A drawing break becomes NUL, which no alphabet uses ('|' is a v101 glyph).
    text = re.sub(r"<[-~]>", "\0", text).replace(" ", "").replace("\t", "")
    return bool(re.search(r"^[.,\0]|[.,\0]$|[.,\0]{2}", text))


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_the_sources_word_space_breaks_are_the_ones_found_independently(source: Path):
    """The loci the parser names for section 6.7 are exactly those the independent check finds in
    a file of format 2.0 or later, and none in an older file; each stays emitted."""
    first = source.read_text(encoding=source_encoding(source)).splitlines()[0]
    version = re.match(r"#=IVTFF\s+\S+\s+(\d+)\.\d+(?:\s|$)", first)
    modern = version is not None and int(version.group(1)) >= 2
    found = set()
    for line in source.read_text(encoding=source_encoding(source)).splitlines():
        if m := re.match(r"^<([^<>.,\s]+)\.(\d+),[^<>]*>[ \t]*(.*)$", line):
            if breaks_section_6_7(m.group(3)):
                found.add(f"{m.group(1)}:{int(m.group(2))}")
    parser = IVTFFParser()
    emitted = set(loci_of(list(parser.parse_file(source))))
    named = {w.emitted_id for w in parser.warnings if "6.7" in w.reason}
    assert named == (found if modern else set())
    assert named <= emitted
    if source.name.startswith("IT_"):
        assert found, "the 1.7 source holds text that format 2.0 would not allow"


# --- B-042: paragraphs (section 6.9) --------------------------------------------------------


@pytest.mark.parametrize(
    "body, kept",
    [
        ("<f1r>\n<f1r.1,@L0> <%>daiin<$>\n", "f1r:1"),
        ("<f1r>\n<f1r.1,@Cc> daiin<$>\n", "f1r:1"),
        ("<f1r>\n<f1r.1,@P0> <%>daiin\n<f2r>\n<f2r.1,@P0> ol\n", "f1r:1"),
        ("<f1r>\n<f1r.1,@P0> <%>daiin\n", "f1r:1"),
        ("<f1r>\n<f1r.1,@P0> daiin<$>\n", "f1r:1"),
        ("<f1r>\n<f1r.1,@P0> <%>daiin\n<f1r.2,+P0> <%>ol<$>\n", "f1r:2"),
        ("<f1r>\n<f1r.1,@P0> <%>daiin<$>\n<f1r.2,+P0> ol<$>\n", "f1r:2"),
    ],
)
def test_paragraph_breaks(body: str, kept: str):
    kept_with_warning(V17 + body, kept)


def test_paragraph_across_pages_names_both_ends():
    content = V2 + "<f1r>\n<f1r.1,@P0> <%>daiin\n<f2r>\n<f2r.1,@P0> ol<$>\n"
    with pytest.raises(ValueError, match="6.9"):
        parse(content, strict=True)
    parser, pages = parse(content)
    assert loci_of(pages) == ["f1r:1", "f2r:1"]
    assert [w.emitted_id for w in parser.warnings] == ["f1r:1", "f2r:1"]


@pytest.mark.parametrize(
    "body",
    [
        "<f1r>\n<f1r.1,@P0> <%>daiin\n<f1r.2,+P0> ol\n<f1r.3,+Pt> o<$>\n",
        "<f1r>\n<f1r.1,@P0> <%>daiin<$>\n<f1r.2,*P1> <%>o /\n/ l<$>\n<f2r>\n<f2r.1,@L0> d\n",
        "<f1r>\n<f1r.1,@L0> d\n<f1r.2,@Pb> <%><!c>o<$>\n",
    ],
)
def test_paragraphs_that_follow_section_6_9(body: str):
    for strict in (False, True):
        parser, pages = parse(V2 + body, strict)
        assert parser.warnings == [] and loci_of(pages)


def test_paragraph_warnings_reach_parse_ivtff_and_the_build(tmp_path: Path):
    content = V2 + "<f1r>\n<f1r.1,@L0> <%>daiin<$>\n"
    source = tmp_path / "source.txt"
    source.write_text(content, encoding="utf-8")
    with pytest.warns(UserWarning, match="6.9"):
        pages = parse_ivtff(source)
    assert loci_of(pages) == ["f1r:1"]
    out, report = build(tmp_path / "b", content)
    assert any("6.9" in w for w in report["warnings"]) and report["reported_loci"] == []
    assert validator_errors(out) == ([], [])


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_the_sources_paragraphs_follow_section_6_9(source: Path):
    """Paragraph marks in every cached source pair up on their page in P loci only, by a check
    written here, and the parser names no break. Each transcriber of an interlinear file has its own
    paragraphs (B-049), and a file older than format 1.6, which introduced the start mark `<%>`, has
    only end marks, so an end there needs no start (S13)."""
    lines = source.read_text(encoding=source_encoding(source)).splitlines()
    version = re.match(r"^#=IVTFF\s+\S+\s+(\d+)\.(\d+)", lines[0])
    pairs = not (version and (int(version.group(1)), int(version.group(2))) < (1, 6))
    breaks = []
    page, openers = None, {}
    for line in lines:
        if m := re.match(r"^<([^<>.,\s]+)>", line):
            breaks.extend(openers.values())
            page, openers = m.group(1), {}
        elif m := re.match(r"^<([^<>.,\s]+)\.(\d+),.(.)[^<>;]*(?:;([^<>]+))?>(.*)$", line):
            transcriber = m.group(4)
            locus = f"{m.group(1)}:{int(m.group(2))}"
            for mark in re.findall(r"<[%$]>", re.sub(r"<![^>]*>", "", m.group(5))):
                opener = openers.get(transcriber)
                if (
                    m.group(3) != "P"
                    or (mark == "<%>" and opener)
                    or (mark == "<$>" and not opener and pairs)
                ):
                    breaks.append(locus)
                if mark == "<%>":
                    openers[transcriber] = locus
                else:
                    openers.pop(transcriber, None)
    assert page and not openers
    parser = IVTFFParser()
    list(parser.parse_file(source))
    assert breaks == [w.emitted_id for w in parser.warnings if "6.9" in w.reason] == []


# --- B-044: position and line_type against the source ---------------------------------------

TYPES = V2 + (
    "<f1r>\n<f1r.1,@P0> daiin\n<f1r.2,&Lz> ol\n<f1r.3,~Cc> o\n<f1r.4,/Ri> d\n<f1r.5,!Ro> y\n"
)


def test_validators_accept_every_locus_type(tmp_path: Path):
    out, _ = build(tmp_path, TYPES)
    rows = [json.loads(line) for line in (out / "eva_lines.jsonl").open()]
    assert [r["position"] for r in rows] == ["@", "&", "~", "/", "!"]
    assert validator_errors(out) == ([], [])


@pytest.mark.parametrize("field", ["position", "line_type"])
def test_validators_reject_structure_that_contradicts_the_source(tmp_path: Path, field: str):
    """Each row in turn gets another row's value, the report's lines_by_type following the rows as
    the builder computes it; both validators reject every such build."""
    out, _ = build(tmp_path, TYPES)
    path = out / "eva_lines.jsonl"
    rows = [json.loads(line) for line in path.open()]
    report_path = out / "eva_lines_build_report.json"
    report = json.loads(report_path.read_text())
    for index, row in enumerate(rows):
        other = next(r[field] for r in rows if r[field] != row[field])
        changed = [dict(r) for r in rows]
        changed[index][field] = other
        path.write_text("".join(json.dumps(r) + "\n" for r in changed))
        by_type: dict[str, int] = {}
        for r in changed:
            by_type[r["line_type"]] = by_type.get(r["line_type"], 0) + 1
        report_path.write_text(json.dumps({**report, "lines_by_type": by_type}))
        phase_errors, invariant_failures = validator_errors(out)
        assert any(field in e for e in phase_errors), (index, phase_errors)
        assert invariant_failures, index


# --- S13: every source, LSI included (item 2.3 part 2) ---------------------------------------

V15 = "#=IVTFF Eva- 1.5\n"


def paragraph_breaks(content: str) -> list[str | None]:
    parser, _ = parse(content)
    return [w.emitted_id for w in parser.warnings if "6.9" in w.reason]


def test_each_transcriber_has_its_own_paragraphs():
    """Parallel readings of an interlinear file open and close their own paragraphs (B-049)."""
    content = V2 + (
        "<f1r>\n<f1r.1,@P0;H> <%>daiin\n<f1r.1,@P0;C> <%>daiin\n"
        "<f1r.2,+P0;H> ol<$>\n<f1r.2,+P0;C> ol<$>\n"
    )
    assert paragraph_breaks(content) == []
    # one transcriber's pairs still have to alternate
    assert paragraph_breaks(V2 + "<f1r>\n<f1r.1,@P0;H> <%>daiin\n<f1r.2,+P0;H> <%>ol<$>\n") == [
        "f1r:2"
    ]


@pytest.mark.parametrize(
    ("header", "breaks"),
    [
        (V15, []),
        ("#=IVTFF Eva- 1.6\n", ["f1r:1"]),
        (V2, ["f1r:1"]),
        ("#=IVTFF Eva-\n", ["f1r:1"]),
        ("", ["f1r:1"]),
    ],
)
def test_a_paragraph_end_needs_a_start_from_format_1_6(header: str, breaks: list[str]):
    """The start mark <%> came with format 1.6 (the spec's version history), so before it an end mark stands alone; a
    header that states no version, or no header, keeps the rule (S13)."""
    assert paragraph_breaks(header + "<f1r>\n<f1r.1,@P0> daiin<$>\n") == breaks


def test_the_file_header_is_the_first_line_only():
    """A later line of the header's shape is a comment and changes nothing (IVTFF 2.0 section 6.1; B-050)."""
    parser, pages = parse(V2 + "#=IVTFF Cuva 1.5\n<f1r>\n<f1r.1,@P0> daiin\n")
    assert (parser.alphabet, parser.format_version) == ("Eva-", "2.0")
    assert parser.warnings == [] and [p.page_id for p in pages] == ["f1r"]


@pytest.mark.parametrize("variable", ["L", "B"])
def test_a_variable_set_by_text_tags_is_accepted_and_unset(variable: str):
    """`$X=@` says text tags set X on the page (section 6.8, conventions 2 and 3): accepted, the value unset (B-051)."""
    parser, pages = parse(V2 + f"<f1r> <! $Q=A ${variable}=@>\n<f1r.1,@P0> daiin\n")
    assert parser.warnings == []
    value = pages[0].variables.language if variable == "L" else pages[0].variables.bifolio
    assert value is None


def test_a_registered_file_is_read_in_its_recorded_encoding(tmp_path: Path, monkeypatch):
    """A cached file is decoded in the encoding its record states (S13: LSI is Latin-1) and rebuilt in it, byte for
    byte; read as UTF-8 the same line is reported, never replaced."""
    from parsers.ivtff_roundtrip import rebuild_source
    from vcat import sources

    data = (V2 + "<f1r>\n<f1r.1,@P0> <!label \xa4->daiin\n").encode("latin-1")
    path = tmp_path / "latin.txt"
    path.write_bytes(data)
    monkeypatch.setattr(sources, "source_encoding", lambda p: "latin-1")
    parser = IVTFFParser()
    pages = list(parser.parse_file(path))
    assert parser.warnings == [] and [loc.locus_id for p in pages for loc in p.loci] == ["f1r:1"]
    assert rebuild_source(parser.document) == data
    utf8 = IVTFFParser()
    assert [loc.locus_id for p in utf8.parse_file(path, encoding="utf-8") for loc in p.loci] == []
    assert [w.locus_id for w in utf8.warnings] == ["f1r:1"]
    assert rebuild_source(utf8.document) == data
