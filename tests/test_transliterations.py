"""
Every transliteration in one schema (roadmap item 2.3): `output/transliterations/`, built by
`builders/build_transliterations.py`, checked here against the cached sources themselves (their lines, an independent census,
the registry), never against the builder's own numbers.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from builders import build_transliterations as bt
from builders.cards import (
    committed_transliterations_report,
    schema_field_table,
    transliterations_schema,
    transliterations_statistics,
)
from tests.test_cards import whole_table
from tests.test_paperwork import rendered_region
from vcat import sources as registry
from vcat.loss_accounting import census_source

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "transliterations"
CARD = ROOT / "huggingface" / "voynich-transliterations" / "README.md"
RECORDS = registry.cached_sources()


def committed_rows(source_id: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (OUT / f"{source_id.lower()}.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_the_dataset_names_every_cached_source():
    entry = next(d for d in registry.load_sources()["datasets"] if d["name"] == bt.DATASET)
    assert entry["sources"] == [r.id for r in RECORDS]
    # the variant tables are VCAT's comparison (item 2.7, DECISIONS Q84)
    assert entry["vcat_annotations"] is True


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_every_row_is_its_source_line(record):
    """Each row's identifier fields and text are its source line at `source_line`, as written (the text may continue on
    the lines after it); the row's alphabet is its record's."""
    lines = record.path.read_text(encoding=record.encoding).splitlines()
    alphabet = next(
        e["alphabet"] for e in registry.load_sources()["cached"] if e["id"] == record.id
    )
    rows = committed_rows(record.id)
    assert rows
    for row in rows:
        assert row["source"] == record.id and row["alphabet"] == alphabet
        line = lines[row["source_line"] - 1]
        match = re.match(r"^<([^<>.,\s]+)\.(\d+),([^<>;]+)(?:;([^<>]+))?>([ \t]*)(.*)$", line)
        assert match, (record.id, row["source_line"])
        page, number, code, transcriber, _, rest = match.groups()
        assert (page, int(number), code, transcriber) == (
            row["page_id"],
            row["line_number"],
            row["locus_type"],
            row["transcriber"],
        ), row
        assert row["line_id"] == f"{page}:{int(number)}"
        # the whole text, not a prefix (reach 0dea398a gap 1); no cached source continues a locus on a following
        # `/` line, and one that did would fail here rather than pass on its first line
        assert row["source_line"] == len(lines) or not lines[row["source_line"]].startswith(
            "/"
        ), row
        assert row["text_raw"] == rest, row


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_every_reading_is_a_row_or_reported(record):
    """Rows plus the reported lines are every locus line of the source, by an independent census; the reported lines are
    exactly those its record lists as breaking IVTFF."""
    census = census_source(record.path)
    report = committed_transliterations_report()["sources"][record.id]
    rows = committed_rows(record.id)
    reported = {item["line"]: item["id"] for item in report["reported"]}
    assert reported == registry.nonconforming_lines(record.path)
    assert Counter(r["line_id"] for r in rows) + Counter(reported.values()) == Counter(census.loci)
    assert report["rows"] == len(rows) and report["source_loci"] == len(census.loci)


@pytest.mark.parametrize("record", RECORDS, ids=lambda r: r.id)
def test_every_line_kept_with_a_warning_is_named_with_its_reason(record):
    """Each line the parser kept with a warning is in the report with its line, the id of its row and the parser's
    reason, and its row exists; the count is the list's (B-102, AB6 F2: only the count was kept)."""
    from parsers import IVTFFParser

    parser = IVTFFParser()
    list(parser.parse_file(record.path, encoding=record.encoding))
    report = committed_transliterations_report()["sources"][record.id]
    expected = [
        {"line": w.line_number, "id": w.emitted_id, "reason": w.reason}
        for w in parser.warnings
        if w.emitted_id is not None
    ]
    assert report["kept"] == expected
    assert report["kept_with_warning"] == len(expected)
    row_ids = {(r["source_line"], r["line_id"]) for r in committed_rows(record.id)}
    assert all((k["line"], k["id"]) in row_ids for k in report["kept"]), record.id


def test_the_coverage_matrix_is_the_sources_census():
    """Each cell is the number of a source's locus lines on that page, counted from the source file without the parser,
    less its reported lines; pages in manuscript order."""
    table = list(csv.reader(io.StringIO((OUT / bt.MATRIX).read_text(encoding="utf-8"))))
    header, body = table[0], table[1:]
    assert header == ["page_id", *[r.id for r in RECORDS]]
    expected: dict[str, Counter] = {}
    for record in RECORDS:
        reported = Counter(
            locus.rsplit(":", 1)[0] for locus in registry.nonconforming_lines(record.path).values()
        )
        per_page = (
            Counter(locus.rsplit(":", 1)[0] for locus in census_source(record.path).loci) - reported
        )
        expected[record.id] = per_page
    pages = sorted({p for c in expected.values() for p in c}, key=bt.page_order_key)
    assert [row[0] for row in body] == pages
    for row in body:
        assert [int(cell) for cell in row[1:]] == [expected[r.id][row[0]] for r in RECORDS], row[0]


def test_the_report_is_the_registry():
    report = committed_transliterations_report()
    assert report["source_order"] == [r.id for r in RECORDS]
    for record in RECORDS:
        entry = report["sources"][record.id]
        assert entry["sha256"] == record.sha256 and entry["encoding"] == record.encoding
        assert entry["upstream_version"] == record.upstream_version


def test_committed_rows_conform_to_the_schema():
    from validators.schema import validate_against_schema

    for record in RECORDS:
        valid, errors = validate_against_schema(
            committed_rows(record.id), "transliteration_loci.schema.json"
        )
        assert valid, (record.id, errors[:3])


def test_the_committed_output_is_a_fresh_build(tmp_path: Path):
    """Built again, every file is byte for byte the committed one (the Parquet by its rows)."""
    import pyarrow.parquet as pq

    bt.build_transliterations(tmp_path)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == sorted(p.name for p in OUT.iterdir())
    for name in names:
        if name.endswith(".parquet"):
            assert (
                pq.read_table(tmp_path / name).to_pylist() == pq.read_table(OUT / name).to_pylist()
            ), name
        # every file byte for byte, the Parquet too (reach 92b55594 gap 1: a Parquet that differed in its bytes passed)
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name


def test_the_build_refuses_a_rejection_its_record_does_not_list(monkeypatch, tmp_path: Path):
    """A line the parser rejects that the source's record does not list fails the build before anything is written."""
    monkeypatch.setattr(bt, "nonconforming_lines", lambda path: {})
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="LSI"):
        bt.build_transliterations(out)
    assert not out.exists()


def test_the_card_states_the_schema_and_the_build():
    """The card's field table and source table are their renderings, whole (B-096), one config per source names its
    built file, and the rows it shows are committed rows."""
    card = CARD.read_text(encoding="utf-8")
    for rendered in (
        schema_field_table(transliterations_schema()),
        transliterations_statistics(committed_transliterations_report()),
        *VARIANT_RENDERINGS(),
    ):
        assert whole_table(card, rendered) == rendered
    meta = re.match(r"---\n(.*?)\n---\n", card, re.S)
    import yaml

    configs = yaml.safe_load(meta.group(1))["configs"]
    # one config per source, then the variant tables (roadmap item 2.7), each loading exactly its own file
    names = [r.id.lower() for r in RECORDS] + ["locus_variants", "word_alignments"]
    assert [c["config_name"] for c in configs] == names
    assert [[f["path"] for f in c["data_files"]] for c in configs] == [
        [f"{n}.parquet"] for n in names
    ]
    committed = [row for r in RECORDS for row in committed_rows(r.id)]
    for name in ("locus_variants", "word_alignments"):
        committed += [
            json.loads(x)
            for x in (ROOT / "output" / "transliterations" / f"{name}.jsonl")
            .read_text()
            .splitlines()
        ]
    # every fenced JSON example a CommonMark parser finds, compared as JSON (reach 92b55594 gaps 4 and 5)
    from tests.test_cards import as_json, json_blocks

    shown = json_blocks(card)
    known = {as_json(row) for row in committed}
    assert shown and all(as_json(row) in known for row in shown)


def VARIANT_RENDERINGS() -> list[str]:
    """The variant tables' renderings in the card (roadmap item 2.7): both field tables and the statistics."""
    from builders.cards import committed_variants_report, variants_schemas, variants_statistics

    return [
        *(schema_field_table(s) for s in variants_schemas()),
        variants_statistics(committed_variants_report()),
    ]


def test_the_card_states_no_count_outside_its_renderings():
    text = CARD.read_text(encoding="utf-8")
    for rendered in (
        schema_field_table(transliterations_schema()),
        transliterations_statistics(committed_transliterations_report()),
        *VARIANT_RENDERINGS(),
    ):
        text = text.replace(rendered, "")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    # identifiers in backticks, links and the shelfmark are not counts; any other digit is (reach 0dea398a gap 5: a
    # one-digit count is a count too)
    # an inline code span is an identifier only if it holds a letter: a number in backticks is still a count (reach
    # 92b55594 gap 6)
    # (and only one with no whitespace: a count with words beside it in backticks is prose, its number still a count;
    # review 3d607506 finding 2)
    text = re.sub(
        r"`[^`\s]*[A-Za-z][^`\s]*`|\(https?://[^)]*\)|https?://\S+|Beinecke MS 408", "", text
    )
    # names, not counts: the registry's source ids and alphabets, and the license names
    alphabets = {e["alphabet"] for e in registry.load_sources()["cached"]}
    for name in sorted(
        {r.id for r in RECORDS} | alphabets | {"CC-BY-4.0", "CC0-1.0", "CC0", "MIT"},
        key=len,
        reverse=True,
    ):
        text = re.sub(rf"(?<![\w-]){re.escape(name)}(?![\w-])", "", text)
    assert not re.findall(r"\d", text), re.findall(r".{0,30}\d.{0,30}", text)


def test_the_sources_document_has_the_coverage_and_every_dependency():
    """docs/sources.md renders the per-source coverage from the report, and its dependency table has a row per cached
    source (principle 4: the sources are not independent)."""
    text = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
    assert rendered_region(text, "sources:coverage") == transliterations_statistics(
        committed_transliterations_report()
    )
    section = text.split("## How the sources depend on each other", 1)[1].split("\n## ", 1)[0]
    named = {
        cell.strip()
        for row in re.findall(r"^\| ([^|]+) \|", section, re.M)
        for cell in row.split(",")
    }
    assert {r.id for r in RECORDS} <= named, {r.id for r in RECORDS} - named


def test_the_mismatch_loader_refuses_repeated_readings(tmp_path: Path):
    """The mismatch index compares one reading per id; a source with two readings of one id fails loudly, never keeps
    the last (B-076, B-089)."""
    import importlib

    bmi = importlib.import_module(
        "builders.build_mismatch_index"
    )  # the package re-exports the function

    zl = next(r for r in RECORDS if r.id == "ZL")
    (tmp_path / zl.path.name).write_text(
        "#=IVTFF Eva- 2.0\n<f1r>\n<f1r.1,@P0;H> daiin\n<f1r.1,@P0;C> otol\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="repeated locus ids"):
        bmi.load_source("zl", tmp_path)


@pytest.mark.parametrize("flag", ["license_verified", "redistributed"])
def test_a_registry_flag_must_be_a_boolean(monkeypatch, flag: str):
    """A quoted "false" is truthy; the loader refuses any verdict that is not true or false (B-092)."""
    data = deepcopy(registry.load_sources())
    data["cached"][0][flag] = "false"
    monkeypatch.setattr(registry, "load_sources", lambda *a, **k: data)
    with pytest.raises(ValueError, match=flag):
        registry.cached_sources()


def test_the_data_model_documents_every_source_rule():
    """docs/data_model.md states what the parser does for LSI (its encoding, the format-1.6 paragraph rule, its listed
    lines; B-097) and which sources `sources_present` evaluates (B-090), each named from the registry.
    """
    text = (ROOT / "docs" / "data_model.md").read_text(encoding="utf-8")
    rules = text.split("## 7.", 1)[1].split("\n## ", 1)[0]
    assert "Latin-1" in rules and "format 1.6" in rules and "`nonconforming`" in rules
    mismatch = text.split("## 10.", 1)[1].split("\n## ", 1)[0]
    entry = next(
        d
        for d in registry.load_sources()["datasets"]
        if d["name"] == "voynich-transcription-mismatch"
    )
    assert f"`sources_present`: {', '.join(entry['sources'])}" in mismatch
    assert "not evaluated" in mismatch
