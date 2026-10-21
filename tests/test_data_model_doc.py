"""
The data model document (roadmap item 1.7) is the data's: every table in `docs/data_model.md` is checked against the
schema, the committed outputs, the source or the code at test time, and every guarantee names a test that exists. The EVA
alphabet document no longer states the old, wrong markup meanings or hand-typed counts. No count is hand-written here: each
number the document states about the data is derived from the source (principle 2).

Every table is read row by row, whatever a row's formatting, so a row cannot escape a check by its shape (reach cf1c8c6e).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from parsers import IVTFFParser
from parsers import ivtff_markup as mk
from vcat import profiles as vp
from vcat.loss_accounting import CACHE_DIR
from vcat.sources import cached_sources

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "docs" / "data_model.md").read_text(encoding="utf-8")
EVA_DOC = (ROOT / "docs" / "eva_alphabet.md").read_text(encoding="utf-8")
SCHEMA = json.loads((ROOT / "schemas" / "transcription_lines.schema.json").read_text())
ZL = CACHE_DIR / "ZL3b-n.txt"
OUTPUT = ROOT / "output"
NAMES = re.compile(r"`[a-z_]+`(?:, `[a-z_]+`)*")


def section(title: str) -> str:
    """The text of one '## <n>. title' section of the document (read from DOC at call time)."""
    match = re.search(rf"^## \d+\. {re.escape(title)}\n(.*?)(?=^## |\Z)", DOC, re.M | re.S)
    assert match, title
    return match.group(1)


def _cells(line: str) -> list[str]:
    line = line.strip()
    line = line[1:] if line.startswith("|") else line
    line = line[:-1] if line.endswith("|") else line
    return [cell.strip() for cell in line.split("|")]


def tables(text: str) -> list[list[list[str]]]:
    """Every Markdown table of a text, as its body rows, each row its cells. A table is a header row, a rule row of
    dashes, and every following line up to the first blank one, with or without the outer pipes, as Markdown renders it
    (reviews cad4bcad finding 2, 7ccc8927 finding 2)."""
    lines = text.splitlines()
    found = []
    i = 0
    while i + 1 < len(lines):
        rule = _cells(lines[i + 1]) if "|" in lines[i + 1] else []
        if "|" in lines[i] and rule and all(re.fullmatch(r":?-+:?", cell) for cell in rule):
            rows = []
            j = i + 2
            # A table's body runs to the first blank line; a line with no pipe is a row holding only its first cell
            # (GitHub-flavoured Markdown; review 7ccc8927 finding 2).
            while j < len(lines) and lines[j].strip():
                rows.append(_cells(lines[j]))
                j += 1
            found.append(rows)
            i = j
        else:
            i += 1
    return found


def first_cells(rows: list[list[str]]) -> list[str]:
    return [cells[0] for cells in rows]


def test_field_table_is_the_schema():
    """Section 3's table lists exactly the row schema's properties, in order: every row's first cell is one
    backticked field name (reach cf1c8c6e gap 1)."""
    found = tables(section("Fields of `eva_lines.jsonl`"))
    assert len(found) == 1, "the section has no single table"
    (rows,) = found
    cells = first_cells(rows)
    assert all(re.fullmatch(r"`[a-z_]+`", cell) for cell in cells), cells
    assert [cell.strip("`") for cell in cells] == list(SCHEMA["properties"])
    # each documented type is the schema's: a list of types is written "a or b" (reach d8d7a6b0 gap 2)
    for row in rows:
        kind = SCHEMA["properties"][row[0].strip("`")]["type"]
        expected = " or ".join(kind) if isinstance(kind, list) else kind
        assert row[1] == expected, (row[0], row[1], expected)


def test_every_guarantee_names_a_test_that_exists():
    """Every row of the guarantee table is G1, G2, ... in order, and its last cell is exactly one test node id
    (`tests/... .py::test_...`, a class allowed) whose test is defined in the named file (reach cf1c8c6e gap 2).
    """
    rows = tables(section("The faithfulness contract"))[0]
    assert [cells[0] for cells in rows] == [f"G{n}" for n in range(1, len(rows) + 1)]
    for cells in rows:
        gid, node_cell = cells[0], cells[-1]
        match = re.fullmatch(r"`((?:tests|tests/regressions)/[\w/]+\.py)((?:::\w+)+)`", node_cell)
        assert match, (gid, node_cell)
        path, names = match.group(1), match.group(2).split("::")[1:]
        assert names[-1].startswith("test_"), (gid, node_cell)
        scope: list[ast.stmt] = ast.parse((ROOT / path).read_text(encoding="utf-8")).body
        for name in names:
            found = next(
                (
                    n
                    for n in scope
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name
                ),
                None,
            )
            assert found is not None, (gid, node_cell)
            scope = found.body if isinstance(found, ast.ClassDef) else []


def test_profile_table_is_the_code():
    """Section 5's first table is the published rule table of `vcat.profiles`."""
    body = section("Normalization profiles")
    start = body.index("| token |")
    end = body.index("\n\n", start)
    assert body[start:end] == vp.describe()
    # nothing outside the pinned table is part of it: the first table has exactly describe()'s rows
    assert tables(body)[0] == [_cells(line) for line in vp.describe().splitlines()[2:]]
    # gap 5)
    test_field_table_is_the_schema()
    test_build_report_fields_are_the_report()
    # and the metadata field lists, which the same clause names (reach d8d7a6b0 gap 3)
    for name in ("pages", "folios", "quires", "bifolia", "page_orders", "page_canvases", "layers"):
        test_metadata_field_lists_are_the_outputs(name)


def test_reference_lines_through_the_text_clean_profile():
    """Every row of section 5's reference table (any locus) is the source's text and its analysis-v1 reading
    (reach cf1c8c6e gap 3)."""
    rows = tables(section("Normalization profiles"))[1]
    assert rows
    source = {
        f"{m.group(1)}:{int(m.group(2))}": m.group(3)
        for line in ZL.read_text(encoding="utf-8").splitlines()
        if (m := re.match(r"^<([^<>.,\s]+)\.(\d+),[^>]*>[ \t]*(.*)$", line))
    }
    for cells in rows:
        assert len(cells) == 3 and all(re.fullmatch(r"`[^`]+`", cell) for cell in cells), cells
        locus, text_raw, text_clean = (cell.strip("`") for cell in cells)
        assert locus in source, locus
        assert source[locus] == text_raw, locus
        assert vp.apply_profile(vp.TEXT_CLEAN_PROFILE, text_raw) == text_clean, locus


#: Every row field taken from the source: structure, text, markup and page variables.
FROM_SOURCE = [
    "page_id",
    "line_number",
    "line_id",
    "locus_type",
    "position",
    "line_type",
    "source_line",
    "text_raw",
    "text",
    "text_clean",
    "alternates",
    "ligatures",
    "uncertain_spaces",
    "illegible",
    "high_ascii",
    "comments",
    "drawing_breaks",
    "markers",
    "quire",
    "hand",
    "illustration_type",
    "currier_language",
    "section",
]


def test_mapping_table_reaches_every_markup_field():
    """Section 4 maps every row field taken from the source, structure fields included (reach cf1c8c6e gap 4)."""
    mapping = section("From IVTFF to the dataset")
    assert set(FROM_SOURCE) <= set(SCHEMA["properties"])
    for field in FROM_SOURCE:
        assert f"`{field}`" in mapping, field


@pytest.mark.parametrize(
    "name", ["pages", "folios", "quires", "bifolia", "page_orders", "page_canvases", "layers"]
)
def test_metadata_field_lists_are_the_outputs(name: str):
    """Section 9's field list of each metadata file is the keys, in order, of every committed row of that file
    (reach cf1c8c6e gap 5)."""
    rows = [
        json.loads(line)
        for line in (OUTPUT / "metadata" / f"{name}.jsonl").read_text().splitlines()
    ]
    # every table of the section, so a second table naming a file is read too (reach 6e91b4a2 gap 4)
    table = [
        row for found in tables(section("Metadata datasets (`output/metadata/`)")) for row in found
    ]
    names = [cells[0].strip("`") for cells in table]
    # One row per file: a second row for a file would otherwise replace the first unseen (B-062)
    assert len(names) == len(set(names)), names
    # and every file named is a published one (reach bef641e7 gap 5: a row for an unpublished file went unchecked)
    published = {p.name for p in (OUTPUT / "metadata").glob("*.jsonl")}
    assert set(names) <= published, sorted(set(names) - published)
    listed = dict(zip(names, (cells[1] for cells in table), strict=True))
    assert rows and f"{name}.jsonl" in listed
    assert NAMES.fullmatch(listed[f"{name}.jsonl"])
    fields = re.findall(r"`([^`]+)`", listed[f"{name}.jsonl"])
    for row in rows:
        assert list(row) == fields


def test_build_report_fields_are_the_report():
    """Every row's first cell in section 8 is a list of backticked field names, and together they name the
    committed build report's fields exactly, each once (reach cf1c8c6e gap 6)."""
    found = tables(section("The build report (`output/eva_lines_build_report.json`)"))
    assert len(found) == 1, "the section has no single table"
    (rows,) = found
    cells = first_cells(rows)
    assert all(NAMES.fullmatch(cell) for cell in cells), cells
    named = [name for cell in cells for name in re.findall(r"`([^`]+)`", cell)]
    report = json.loads((OUTPUT / "eva_lines_build_report.json").read_text())
    assert sorted(named) == sorted(report)


def test_stated_exceptions_are_the_sources():
    """Section 7's counted exception is counted from ZL here: the loci with a comment before their paragraph start."""
    stated = re.search(
        r"(\d+) ZL loci put a comment before `<%>`", section("The IVTFF rules the parser enforces")
    )
    assert stated
    counted = 0
    for page in IVTFFParser().parse_file(ZL):
        for locus in page.loci:
            kinds = [t.kind for t in locus.markup.tokens if t.kind != mk.WHITESPACE]
            if (
                mk.PARAGRAPH_START in kinds
                and mk.COMMENT in kinds[: kinds.index(mk.PARAGRAPH_START)]
            ):
                counted += 1
    assert counted == int(stated.group(1))


@pytest.mark.parametrize(
    "stale",
    [
        "{comment}",  # braces are ligatures (D1)
        "Line continuation",  # <-> is a drawing break (D2)
        "Editorial insertion",
        "Column separator",
        "lossless",
        "Processing instruction",
        "170,607",  # a hand-typed corpus count
    ],
)
def test_old_meanings_are_gone(stale: str):
    assert stale not in DOC
    assert stale not in EVA_DOC


def test_alphabet_document_types_no_corpus_percentages():
    """No glyph frequency is typed into the alphabet document (principle 2), whatever the spacing before the sign
    (reach cf1c8c6e gap 7)."""
    assert not re.search(r"\d+(\.\d+)?\s*%", EVA_DOC)


def test_schema_describes_text_clean_as_the_profile():
    """The schema's description of text_clean names the profile, not the old 'lossless' cleaning."""
    assert vp.TEXT_CLEAN_PROFILE in SCHEMA["properties"]["text_clean"]["description"]
    # the EVA `section` is the source's renaming, recorded as the layer `section_name` (DECISIONS Q72, B-118)
    assert "section_name" in SCHEMA["properties"]["section"]["description"]
    assert "interpretation" not in SCHEMA["properties"]["section"]["description"]


def test_section_names_are_one_mapping():
    """The validator's section name for each `$I` code is the builder's, and its names are the ones section 3 documents for
    `section` (AV9 F2): one mapping, stated three times, checked here."""
    from builders.build_eva_lines import SECTION_MAPPING
    from validators.validate_phase1_outputs import SECTION_OF_ILLUSTRATION

    assert SECTION_OF_ILLUSTRATION == SECTION_MAPPING
    row = next(
        cells
        for cells in tables(section("Fields of `eva_lines.jsonl`"))[0]
        if cells[0] == "`section`"
    )
    documented = re.search(r"\(([^)]*)\)", row[2]).group(1).split(", ")
    assert sorted(documented) == sorted(SECTION_OF_ILLUSTRATION.values())


def test_section_rule_is_the_builders_on_every_page():
    """The validator's section rule gives the builder's section on every page of every cached source (review 28813a2e
    finding 2: pages without an `$I` code take a folio range)."""
    from builders.build_eva_lines import derive_section
    from parsers import IVTFFParser
    from validators.validate_phase1_outputs import section_of_page

    checked = 0
    for path in sorted(source.path for source in cached_sources()):
        for page in IVTFFParser().parse_file(path):
            assert section_of_page(page.page_id, page.variables.illustration) == derive_section(
                page
            ), page.page_id
            checked += 1
    assert checked


def test_word_field_table_is_the_schema():
    """Section 11's table lists exactly the word schema's properties, in order, each with the schema's type (item 2.6)."""
    words = json.loads((ROOT / "schemas" / "eva_words.schema.json").read_text(encoding="utf-8"))
    found = tables(section("The word level (`output/eva_words.jsonl`)"))
    assert len(found) == 1, "the section has no single table"
    (rows,) = found
    assert [cell.strip("`") for cell in first_cells(rows)] == list(words["properties"])
    for row in rows:
        kind = words["properties"][row[0].strip("`")]["type"]
        assert row[1] == (" or ".join(kind) if isinstance(kind, list) else kind), row
