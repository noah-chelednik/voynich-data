"""
The raw and structured layer (roadmap items 1.2 and 1.3).

Every expectation here is read from the cached sources at test time or written as a small
synthetic IVTFF input; no count is hand-written (principle 2). The reference lines are the three of
the faithfulness contract (`f1r.7`, `f1r.19`, `f10r.11`).
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from builders.build_metadata import build_metadata_datasets
from parsers import IVTFFParser, IVTFFWarning, parse_ivtff, parse_markup
from parsers import ivtff_markup as mk
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from vcat.loss_accounting import CACHE_DIR
from vcat.sources import cached_sources, nonconforming_lines, source_encoding
from vcat.text_processing import clean_text_for_analysis

ROOT = Path(__file__).resolve().parent.parent
CACHE = CACHE_DIR
# every cached file the registry records, wherever under the cache it is (S13: LSI under latin-1/)
SOURCES = sorted(source.path for source in cached_sources())
ZL = CACHE / "ZL3b-n.txt"
OUTPUT = ROOT / "output"


def source_lines(path: Path) -> list[bytes]:
    """The source's lines as bytes, terminators excluded."""
    return re.findall(rb"([^\r\n]*)(?:\r\n|\n|\r|$)", path.read_bytes())


def write_build(base: Path, text: str | bytes) -> Path:
    """Build a synthetic source the way the builder's command line does, into base/out."""
    base.mkdir(parents=True, exist_ok=True)
    source = base / "source.txt"
    if isinstance(text, bytes):
        source.write_bytes(text)
    else:
        source.write_text(text, encoding="utf-8", newline="")
    out = base / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(json.dumps(report.to_dict()))
    return out


def both_validators(out: Path) -> tuple[list[str], list[dict]]:
    with contextlib.redirect_stdout(io.StringIO()):
        _, phase_errors = phase.validate_outputs(out)
        invariants = inv.verify_all_invariants(out)
    return phase_errors, invariants.failures


def rows_of(out: Path) -> list[dict]:
    return [json.loads(line) for line in (out / "eva_lines.jsonl").read_text().splitlines()]


@pytest.fixture(scope="module")
def zl_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_build(tmp_path_factory.mktemp("zl"), ZL.read_bytes())


# --- text_raw is the source, byte for byte -------------------------------------------------


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_every_locus_rebuilds_its_source_line(source: Path):
    """For every locus of every cached source, identifier + separator + text_raw is the source line
    at source_line, byte for byte, and the parser rejects nothing (a warning may only name a locus
    kept all the same, DECISIONS Q33)."""
    lines = source_lines(source)
    parser = IVTFFParser()
    loci = [locus for page in parser.parse_file(source) for locus in page.loci]
    # nothing rejected but the lines the source's record lists as breaking IVTFF (S13: LSI's `44a` loci)
    rejected = {w.line_number for w in parser.warnings if w.emitted_id is None}
    assert loci and rejected == set(nonconforming_lines(source))
    census = sum(1 for line in lines if re.match(rb"^<[^<>.,\s]+\.\d+,", line))
    assert len(loci) == census
    encoding = source_encoding(source)  # once: the lookup reads the registry
    for locus in loci:
        rebuilt = (locus.raw_locator + locus.separator + locus.text_raw).encode(encoding)
        assert rebuilt == lines[locus.source_line - 1], locus.locus_id
        assert locus.text == locus.markup.text


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_tokens_cover_every_character(source: Path):
    """The tokens of every locus join to its text_raw, and no source holds undefined markup.

    Not in strict mode: strict mode also enforces IVTFF 2.0 sections 6.3, 6.7 and 6.9, which one
    cached locus breaks (DECISIONS Q33; tests/test_round_trip.py)."""
    parser = IVTFFParser()
    loci = [locus for page in parser.parse_file(source) for locus in page.loci]
    rejected = {w.line_number for w in parser.warnings if w.emitted_id is None}
    assert loci and rejected == set(nonconforming_lines(source))  # S13: only the listed lines
    for locus in loci:
        assert locus.markup.raw == locus.text_raw, locus.locus_id
        assert not locus.markup.problems, locus.locus_id
        assert mk.UNKNOWN not in {token.kind for token in locus.markup.tokens}


def test_reference_lines(zl_build: Path):
    """The three reference lines: f1r.7 keeps {c'y}, f1r.19 keeps {ct}, f10r.11 splits at <->."""
    lines = {
        f"{m.group(1)}:{m.group(2)}": m.group(4)
        for line in ZL.read_text(encoding="utf-8").splitlines()
        if (m := re.match(r"^<([^.]+)\.(\d+),([^>]+)>\s*(.*)$", line))
    }
    rows = {row["line_id"]: row for row in rows_of(zl_build)}

    first = rows["f1r:7"]
    assert first["text_raw"] == lines["f1r:7"]
    assert first["locus_type"] == "*P0"
    assert first["ligatures"] == ["c'y"]
    assert first["comments"] == ["@252;"]
    assert first["markers"] == ["<%>"]
    assert first["high_ascii"] == [] and first["has_high_ascii"] is False
    assert "odar.c'y.shol" in first["text_clean"]

    second = rows["f1r:19"]
    assert second["text_raw"] == lines["f1r:19"]
    assert second["ligatures"] == ["ct"]
    assert second["high_ascii"] == codes_outside_comments(lines["f1r:19"])
    assert second["high_ascii"] and second["has_high_ascii"] is True
    assert second["text_clean"].endswith("dlocto")

    third = rows["f10r:11"]
    assert third["text_raw"] == lines["f10r:11"]
    assert third["drawing_breaks"] == ["<->"]
    assert "cthyd.otar" in third["text_clean"]
    assert "cthydotar" not in third["text_clean"]


# --- 1.3: D1 and D2 on every row --------------------------------------------------------------


def codes_outside_comments(text: str) -> list[int]:
    """The high-ASCII codes of a text, comments excluded, read with a regular expression."""
    return [int(code) for code in re.findall(r"@(\d{3});", re.sub(r"<![^>]*>", "", text))]


def _first_reading(tokens: list[mk.Token]) -> list[mk.Token]:
    """The tokens with each alternate replaced by the tokens of its first reading."""
    out: list[mk.Token] = []
    for token in tokens:
        if token.kind == mk.ALTERNATES:
            out.extend(_first_reading(parse_markup(token.value[0]).tokens))
        else:
            out.append(token)
    return out


def _glyph_letters(text: str) -> str:
    """The glyph characters of a reading, as written (upper case included; reach a17b6e30 gap 4):
    everything but high-ASCII codes and the separators '.' and ','."""
    return re.sub(r"@\d{3};|[.,]", "", text)


def test_text_clean_keeps_every_glyph_and_word_boundary(zl_build: Path):
    """No ZL row loses a ligature's glyphs (D1) or fuses words at a drawing break (D2): the letters
    of text_clean are those of the glyphs, ligatures and first readings of text_raw, and every word
    space, uncertain space and drawing break of text_raw is a separator in text_clean."""
    rows = rows_of(zl_build)
    with_ligature = with_break = 0
    for row in rows:
        tokens = _first_reading(parse_markup(row["text_raw"]).tokens)
        # glyphs are kept as written: ZL f57v.3 keeps its uppercase 'I' (analysis-v1, DECISIONS Q39)
        letters = "".join(
            _glyph_letters(t.value if t.kind == mk.LIGATURE else t.raw)
            for t in tokens
            if t.kind in (mk.GLYPHS, mk.LIGATURE)
        )
        assert _glyph_letters(row["text_clean"]) == letters, row["line_id"]
        separators = sum(t.kind in (mk.SPACE, mk.UNCERTAIN_SPACE, mk.DRAWING_BREAK) for t in tokens)
        assert len(re.findall(r"[.,]", row["text_clean"])) == separators, row["line_id"]
        with_ligature += bool(row["ligatures"])
        with_break += bool(row["drawing_breaks"])
    assert with_ligature and with_break  # the property was exercised on real ligatures and breaks


def test_clean_text_examples():
    assert clean_text_for_analysis("dlo{ct}o") == "dlocto"
    assert clean_text_for_analysis("odar.{c'y}.shol") == "odar.c'y.shol"
    assert clean_text_for_analysis("cthyd<->otar") == "cthyd.otar"
    assert clean_text_for_analysis("chckhy<~>oltchedy") == "chckhy.oltchedy"
    # a comment ends at its first '>' (IVTFF 5.7.2); nothing inside it reaches text_clean
    assert clean_text_for_analysis("ok<!a {b} [c:d] <x>al") == "okal"


# --- the tokenizer ---------------------------------------------------------------------------


def test_every_token_kind():
    text = "<%><@H=2>qo.k,a?[a:o:e]{c@132;h}<!a @130; ?>@192;???<->x<~>y  z<$>"
    markup = parse_markup(text)
    assert not markup.problems
    assert markup.raw == text
    kinds = [token.kind for token in markup.tokens]
    for kind in (
        mk.PARAGRAPH_START,
        mk.TEXT_TAG,
        mk.GLYPHS,
        mk.SPACE,
        mk.UNCERTAIN_SPACE,
        mk.ILLEGIBLE,
        mk.ALTERNATES,
        mk.LIGATURE,
        mk.COMMENT,
        mk.HIGH_ASCII,
        mk.DRAWING_BREAK,
        mk.WHITESPACE,
        mk.PARAGRAPH_END,
    ):
        assert kind in kinds, kind
    fields = markup.fields()
    assert fields["alternates"] == [["a", "o", "e"]]
    assert fields["ligatures"] == ["c@132;h"]
    # every occurrence at any depth, comments excluded: the code in the ligature and the one after
    assert fields["high_ascii"] == codes_outside_comments(text)
    assert fields["illegible"] == ["?", "???"]
    assert fields["comments"] == ["a @130; ?"]
    assert fields["drawing_breaks"] == ["<->", "<~>"]
    assert fields["markers"] == ["<%>", "<@H=2>", "<$>"]
    assert fields["uncertain_spaces"] == 1


def test_alternates_hold_what_the_sources_hold():
    """Readings may be empty or hold ligatures, codes and '?' (all occur in ZL)."""
    for text, readings in [
        ("dch[s:]ed", ["s", ""]),
        ("[:y]", ["", "y"]),
        ("[{cto}:@194;]", ["{cto}", "@194;"]),
        ("[aiird:???]", ["aiird", "???"]),
        ("[ee:a:ei]", ["ee", "a", "ei"]),
    ]:
        markup = parse_markup(text)
        assert not markup.problems, text
        assert markup.fields()["alternates"] == [readings]
    nested = parse_markup("[{cto}:@194;].[aiird:???]").fields()
    assert nested["ligatures"] == ["cto"]
    assert nested["high_ascii"] == codes_outside_comments("[{cto}:@194;]")
    assert nested["illegible"] == ["???"]


def test_alphabet_characters_are_glyphs():
    """Characters outside IVTFF Table 3 are glyphs of the file's alphabet (GC uses *, !, $, %)."""
    markup = parse_markup("8AM*!$%#(&+\\^|")
    assert not markup.problems
    assert [token.kind for token in markup.tokens] == [mk.GLYPHS]


UNDEFINED = {
    "unclosed comment": "ab<!cd",
    "unknown tag": "ab<x>cd",
    "stray >": "ab>cd",
    "stray }": "ab}cd",
    "stray ]": "ab]cd",
    "stray :": "ab:cd",
    "stray ;": "ab;cd",
    "short code": "ab@12;cd",
    "code above 255": "ab@300;cd",
    "code below 128": "ab@127;cd",
    "one reading": "ab[c]d",
    "four readings": "ab[c:d:e:f]g",
    "unclosed alternate": "ab[c:d",
    "unclosed ligature": "ab{cd",
    "empty ligature": "ab{}cd",
    "ligature with a space": "a{b.c}d",
    "comment in an alternate": "a[b:<!c>]d",
    "nested alternate": "a[b:[c:d]]e",
    "slash inside the text": "ab/cd",
}


@pytest.mark.parametrize("case", sorted(UNDEFINED))
def test_undefined_markup_is_a_problem(case: str):
    markup = parse_markup(UNDEFINED[case])
    assert markup.problems, case
    assert markup.raw == UNDEFINED[case]
    assert mk.UNKNOWN in {token.kind for token in markup.tokens}


HEADER = "#=IVTFF Eva- 2.0 M 5\n<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>\n"


@pytest.mark.parametrize("case", sorted(UNDEFINED))
def test_undefined_markup_is_an_error_or_a_reported_warning(
    tmp_path: Path, synthetic_accounted: str, case: str
):
    """Strict mode raises; non-strict records a warning with the locus id and does not emit the
    locus; the build reports it, accounts for it, and both validators accept the build (Q25)."""
    bad = f"<f1r.2,+P0>       {UNDEFINED[case]}\n"
    with pytest.raises(ValueError, match="undefined markup"):
        list(IVTFFParser(strict=True).parse_string(HEADER + bad))
    parser = IVTFFParser()
    pages = list(parser.parse_string(HEADER + bad))
    assert [w.locus_id for w in parser.warnings] == ["f1r:2"]
    assert not any(locus.locus_id == "f1r:2" for page in pages for locus in page.loci)

    out = write_build(tmp_path, synthetic_accounted + bad.replace("f1r.2", "f1v.9"))
    report = json.loads((out / "eva_lines_build_report.json").read_text())
    assert report["reported_loci"] == ["f1v:9"]
    assert not report["unaccounted_loci"]
    phase_errors, invariant_failures = both_validators(out)
    assert not phase_errors and not invariant_failures, (phase_errors, invariant_failures)


# --- wraps, line ends and decoding -----------------------------------------------------------


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_wrapped_locus_keeps_its_lines(tmp_path: Path, ending: str):
    """A wrapped locus's text_raw keeps its continuation line and the terminator between them; its
    text is joined; the validators read the same text_raw from the source."""
    lines = [
        "#=IVTFF Eva- 2.0 M 5",
        "<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>",
        "<f1r.1,@P0>       qokedy.dal /",
        "/ shedy.[a:o]l",
        "<f1r.2,+P0>       daiin",
        "",
    ]
    text = ending.join(lines)
    page = next(IVTFFParser(strict=True).parse_string(text))
    locus = page.loci[0]
    assert locus.text_raw == "qokedy.dal /" + ending + "/ shedy.[a:o]l"
    assert locus.text == "qokedy.dalshedy.[a:o]l"
    assert [t.kind for t in locus.markup.tokens].count(mk.WRAP) == 1
    assert locus.markup.fields()["alternates"] == [["a", "o"]]
    assert page.loci[1].source_line == 5

    out = write_build(tmp_path, text)
    row = rows_of(out)[0]
    assert row["text_raw"] == locus.text_raw and row["source_line"] == 3
    phase_errors, invariant_failures = both_validators(out)
    assert not phase_errors and not invariant_failures, (phase_errors, invariant_failures)


def test_crlf_source_keeps_text_raw_without_terminator():
    text = HEADER.replace("\n", "\r\n") + "<f1r.1,@P0>       qokedy.dal\r\n"
    locus = next(IVTFFParser(strict=True).parse_string(text)).loci[0]
    assert locus.text_raw == "qokedy.dal"


def test_undecodable_line_is_reported(tmp_path: Path, synthetic_accounted: str):
    """A line that is not UTF-8 is a strict error and otherwise a warning under its locus id; the
    build accounts for it and both validators accept the build (AP2 F5, Q24)."""
    source = synthetic_accounted.encode("utf-8") + b"<f1v.9,+P0>       a\xffb\n"
    path = tmp_path / "bad.txt"
    path.write_bytes(source)
    with pytest.raises(ValueError, match="UTF-8"):
        list(IVTFFParser(strict=True).parse_file(path))
    parser = IVTFFParser()
    list(parser.parse_file(path))
    assert [w.locus_id for w in parser.warnings] == ["f1v:9"]

    out = write_build(tmp_path / "build", source)
    report = json.loads((out / "eva_lines_build_report.json").read_text())
    assert report["reported_loci"] == ["f1v:9"] and not report["unaccounted_loci"]


# --- parser warnings on every path (B-029) ----------------------------------------------------


BAD_SOURCE = HEADER + "<f1r.1,@P0>       good\n<f1r.2,@Pz>       rejected\n"


def test_parse_ivtff_issues_each_warning(tmp_path: Path):
    path = tmp_path / "source.txt"
    path.write_text(BAD_SOURCE, encoding="utf-8")
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        pages = parse_ivtff(path)
    assert [locus.locus_id for page in pages for locus in page.loci] == ["f1r:1"]
    assert [str(n.message) for n in notices if issubclass(n.category, IVTFFWarning)] == [
        "line 4 (f1r:2): locus type 'Pz' is not in IVTFF Table 9"
    ]


def test_parser_command_line_fails_on_warnings(tmp_path: Path):
    path = tmp_path / "source.txt"
    path.write_text(BAD_SOURCE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "parsers.ivtff_parser", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "f1r:2" in result.stderr
    clean = tmp_path / "clean.txt"
    clean.write_text(HEADER + "<f1r.1,@P0>       good\n", encoding="utf-8")
    ok = subprocess.run(
        [sys.executable, "-m", "parsers.ivtff_parser", str(clean)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stderr


def test_metadata_build_reports_parser_warnings(tmp_path: Path):
    path = tmp_path / "source.txt"
    path.write_text(BAD_SOURCE + "<fXYZ>\n", encoding="utf-8")
    result = build_metadata_datasets(path, tmp_path / "out")
    assert result.report.reported_loci == ["f1r:2"]
    assert result.report.reported_pages == ["fXYZ"]
    assert len(result.report.warnings) == 2
    written = json.loads((tmp_path / "out" / "metadata_report.json").read_text())
    assert written["reported_loci"] == ["f1r:2"]
    cli = subprocess.run(
        [sys.executable, "-m", "builders.build_metadata", str(path), "-o", str(tmp_path / "cli")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert cli.returncode == 1
    assert "f1r:2" in cli.stdout
    assert (tmp_path / "cli" / "metadata_report.json").is_file()


def test_metadata_quires_list_every_folio_of_their_pages():
    """Each quire's folio_ids are exactly the folios whose records name that quire (AP2 F6), on
    the real ZL source, where fRos covers f85 and f86."""
    result = build_metadata_datasets(ZL)
    assert not result.report.warnings
    for quire in result.quires:
        expected = {f.folio_id for f in result.folios if f.quire_id == quire.quire_id}
        assert set(quire.folio_ids) == expected, quire.quire_id
        assert quire.folio_count == len(expected)


# --- the validators check the structured layer -----------------------------------------------


def _mutate_row(row: dict, field: str) -> None:
    if field == "text_raw":
        row["text_raw"] = row["text_raw"] + "x"
    elif field == "source_line":
        row["source_line"] = row["source_line"] + 1
    elif field == "locus_type":
        row["locus_type"] = "@L0" if row["locus_type"] != "@L0" else "@P0"
    elif field == "char_count":
        row["char_count"] = row["char_count"] + 1
    elif field == "text":
        row["text"] = row["text"] + "x"
    elif field in ("uncertain_spaces",):
        row[field] = row[field] + 1
    else:
        row[field] = row[field][1:] if row[field] else ["x"]


MUTATED = [
    "text_raw",
    "source_line",
    "locus_type",
    "char_count",
    "text",
    *phase.MARKUP_FIELDS,
]

MARKUP_SOURCE = (
    HEADER
    + "<f1r.1,@P0>       <%><@H=2>qo{ct}y.[a:o]l,dar<->ok@192;?ar<!note>\n"
    + "<f1r.2,+P0>       daiin.???<~>ol<$>\n"
)


@pytest.mark.parametrize("field", MUTATED)
def test_both_validators_reject_a_row_that_disagrees_with_its_source(tmp_path: Path, field: str):
    out = write_build(tmp_path, MARKUP_SOURCE)
    assert both_validators(out) == ([], [])
    rows = rows_of(out)
    _mutate_row(rows[0], field)
    (out / "eva_lines.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    phase_errors, invariant_failures = both_validators(out)
    assert phase_errors and invariant_failures, field


@pytest.mark.parametrize("field", ["total_characters", "lines_by_type"])
def test_both_validators_reject_report_totals_that_disagree_with_the_rows(
    tmp_path: Path, field: str
):
    out = write_build(tmp_path, MARKUP_SOURCE)
    path = out / "eva_lines_build_report.json"
    report = json.loads(path.read_text())
    report[field] = {"paragraph": 1} if field == "lines_by_type" else report[field] + 1
    path.write_text(json.dumps(report))
    phase_errors, invariant_failures = both_validators(out)
    assert phase_errors and invariant_failures, field


# --- the committed output is the builders' ---------------------------------------------------


def test_committed_eva_lines_are_a_fresh_build(zl_build: Path):
    """`output/eva_lines.jsonl` and `output/SHA256SUMS` are byte for byte what the builder writes
    now (Q28), and both validators accept the committed output."""
    import hashlib

    fresh = zl_build / "eva_lines.jsonl"
    assert (OUTPUT / "eva_lines.jsonl").read_bytes() == fresh.read_bytes()
    digest = hashlib.sha256(fresh.read_bytes()).hexdigest()
    assert (OUTPUT / "SHA256SUMS").read_text() == f"{digest}  eva_lines.jsonl\n"
    phase_errors, invariant_failures = both_validators(OUTPUT)
    assert not phase_errors and not invariant_failures, (phase_errors[:5], invariant_failures[:5])


#: The metadata tables the builder writes, each a JSONL, a Parquet and a `<stem>_file` path in the report
OUTPUT_STEMS = ("pages", "folios", "quires", "bifolia", "page_orders", "page_canvases", "layers")


def test_committed_metadata_is_a_fresh_build(tmp_path: Path):
    """`output/metadata/*.jsonl` are byte for byte what the metadata builder writes now (Q28), every table (item 2.5:
    the bifolia and the page orders too), and each Parquet file holds the rows the builder writes (B-095).
    """
    import pyarrow.parquet as pq

    from builders.build_metadata import export_to_parquet

    result = build_metadata_datasets(ZL, tmp_path)
    export_to_parquet(result, tmp_path)
    for stem in OUTPUT_STEMS:
        name = f"{stem}.jsonl"
        assert (OUTPUT / "metadata" / name).read_bytes() == (tmp_path / name).read_bytes(), name
        parquet = f"{stem}.parquet"
        assert (
            pq.read_table(OUTPUT / "metadata" / parquet).to_pylist()
            == pq.read_table(tmp_path / parquet).to_pylist()
        ), parquet

    # and the report, all of it but the build's time and the paths it was written to (reach 6e91b4a2 gap 2)
    def content(path: Path) -> dict:
        report = json.loads(path.read_text(encoding="utf-8"))
        # the output paths only: `source_file` is the input's provenance and is compared (review caac4571 finding 2)
        drop = {"build_timestamp", "output_dir", *(f"{stem}_file" for stem in OUTPUT_STEMS)}
        return {k: v for k, v in report.items() if k not in drop}

    committed, fresh = (
        OUTPUT / "metadata" / "metadata_report.json",
        tmp_path / "metadata_report.json",
    )
    assert content(committed) == content(fresh)
