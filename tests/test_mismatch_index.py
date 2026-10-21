"""
The mismatch index (roadmap item 1.8): ZL against IT, locus by locus, through a named profile, with exact verdicts.

Every expectation is read from the cached sources, the committed output or a small synthetic source at test time; no count
is hand-written (principle 2). The comparison rules themselves are tested in `tests/test_comparison.py`.
"""

from __future__ import annotations

import json
import shutil
import statistics
from collections import Counter
from pathlib import Path

import pytest

from builders.build_mismatch_index import (
    SOURCES,
    STATUSES,
    MismatchIndexBuilder,
    build_mismatch_index,
    build_records,
    build_report,
    erratum_table,
    load_source,
)
from parsers import IVTFFParser, page_order_key
from validators.schema import validate_mismatch_index
from vcat.comparison import AGREEING, VERDICTS, compare
from vcat.loss_accounting import CACHE_DIR
from vcat.profiles import apply_profile

ROOT = Path(__file__).resolve().parent.parent
CACHE = CACHE_DIR
OUTPUT = ROOT / "output"


@pytest.fixture(scope="module")
def committed() -> tuple[list[dict], dict]:
    rows = [json.loads(line) for line in (OUTPUT / "mismatch_index.jsonl").read_text().splitlines()]
    report = json.loads((OUTPUT / "mismatch_report.json").read_text())
    return rows, report


def test_committed_rows_conform_to_the_schema(committed):
    rows, _ = committed
    assert rows
    valid, errors = validate_mismatch_index(rows)
    assert valid, errors[:5]


def test_committed_index_is_a_fresh_build(tmp_path: Path, committed):
    """The committed JSONL and report are byte for byte what the builder makes from the cached sources."""
    build_mismatch_index(CACHE, tmp_path)
    for name in ("mismatch_index.jsonl", "mismatch_report.json"):
        assert (tmp_path / name).read_bytes() == (OUTPUT / name).read_bytes(), name


def test_every_locus_of_either_source_is_one_row(committed):
    """One row per locus id that ZL or IT emits, in page order then locus number, none twice."""
    rows, _ = committed
    ids = {
        name: {
            locus.locus_id
            for page in IVTFFParser().parse_file(CACHE / SOURCES[name])
            for locus in page.loci
        }
        for name in ("zl", "it")
    }
    line_ids = [row["line_id"] for row in rows]
    assert len(line_ids) == len(set(line_ids))
    assert set(line_ids) == ids["zl"] | ids["it"]
    keys = [(*page_order_key(row["page_id"]), row["line_number"]) for row in rows]
    assert keys == sorted(keys)
    for row in rows:
        assert ("zl" in row["sources_present"]) == (row["line_id"] in ids["zl"])
        assert ("it" in row["sources_present"]) == (row["line_id"] in ids["it"])


def test_every_row_is_the_comparison_of_its_sources(committed):
    """Each row's raw texts are the sources', its readings the profile's, and its verdict and score compare()'s."""
    rows, _ = committed
    loci = {
        name: {
            locus.locus_id: locus
            for page in IVTFFParser().parse_file(CACHE / SOURCES[name])
            for locus in page.loci
        }
        for name in ("zl", "it")
    }
    for row in rows:
        a, b = loci["zl"].get(row["line_id"]), loci["it"].get(row["line_id"])
        profile = row["comparison_profile"]
        assert row["zl_text_raw"] == (a.text_raw if a else None)
        assert row["it_text_raw"] == (b.text_raw if b else None)
        assert row["zl_reading"] == (apply_profile(profile, a.text_raw) if a else None)
        assert row["it_reading"] == (apply_profile(profile, b.text_raw) if b else None)
        if a and b:
            verdict, score = compare(a.text_raw, b.text_raw, profile)
            assert (row["status"], row["similarity_score"]) == (verdict, round(score, 6))
        else:
            assert row["status"] == ("zl_only" if a else "it_only")
            assert row["similarity_score"] is None


def test_report_counts_are_the_rows(committed):
    """The report's counts, agreement and median are computed from the rows."""
    rows, report = committed
    counts = Counter(row["status"] for row in rows)
    assert report["status_counts"] == {status: counts.get(status, 0) for status in STATUSES}
    both = sum(counts[v] for v in VERDICTS)
    assert report["both_present"] == both
    assert report["agreeing"] == sum(counts[v] for v in AGREEING)
    assert report["agreement_rate"] == report["agreeing"] / both
    assert report["different_rate"] == counts["different"] / both  # reach 1c53841b gap 2
    assert report["total_lines"] == len(rows)
    different = sorted(row["similarity_score"] for row in rows if row["status"] == "different")
    assert report["different_similarity"] == {
        "count": len(different),
        "median": statistics.median(different),
    }


def test_report_lists_every_parser_warning(committed):
    """Never silent (B-038): each source's parser warnings and reported loci are in the report as the parser gives them."""
    _, report = committed
    for name, file in SOURCES.items():
        parser = IVTFFParser()
        list(parser.parse_file(CACHE / file))
        assert report["sources"][name]["warnings"] == [str(w) for w in parser.warnings]
        assert report["sources"][name]["reported_loci"] == [
            w.locus_id for w in parser.warnings if w.locus_id
        ]


def test_a_reported_locus_reaches_the_report_and_the_log(tmp_path: Path, caplog):
    """A locus the parser rejects is in the report's warnings and logged, and is not compared as if present."""
    cache = tmp_path / "cache"
    shutil.copytree(CACHE, cache)
    zl = cache / SOURCES["zl"]
    zl.write_text(
        zl.read_text(encoding="utf-8").replace("<f1r.1,@P0>", "<f1r.1,@X9>", 1), encoding="utf-8"
    )
    with caplog.at_level("WARNING"):
        result = build_mismatch_index(cache, tmp_path / "out")
    assert "f1r:1" in result["report"]["sources"]["zl"]["reported_loci"]
    assert "f1r:1" in caplog.text
    rows = [json.loads(line) for line in (tmp_path / "out" / "mismatch_index.jsonl").open()]
    assert next(row for row in rows if row["line_id"] == "f1r:1")["status"] == "it_only"


def test_the_builder_object_loads_and_reports():
    builder = MismatchIndexBuilder(cache_dir=CACHE)
    assert builder.load_transcription("zl") and not builder.load_transcription("xx")
    records = builder.build()
    fresh = build_records({k: load_source(k, CACHE) for k in SOURCES})
    # whole records, and every source's warnings (reach 1c53841b gap 3)
    assert [r.to_dict() for r in records] == [r.to_dict() for r in fresh]
    for name, file in SOURCES.items():
        parser = IVTFFParser()
        list(parser.parse_file(CACHE / file))
        assert name in builder.stats["warnings"], name
        assert builder.stats["warnings"][name] == [str(w) for w in parser.warnings], name


@pytest.mark.parametrize(
    "path",
    ["README.md", "CHANGELOG.md", "huggingface/voynich-transcription-mismatch/README.md"],
)
def test_the_erratum_quotes_the_build(path: str, committed):
    """The erratum in the README, the CHANGELOG and the dataset card is the table rendered from the committed report."""
    _, report = committed
    text = (ROOT / path).read_text(encoding="utf-8")
    assert erratum_table(report) in text
    assert "83.9%" in text  # the erratum names the number it corrects


def test_the_old_headline_is_gone_except_as_corrected():
    """The 0.2.3 headline table is no longer presented as the index's numbers."""
    for path in ("README.md", "huggingface/voynich-transcription-mismatch/README.md"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "Substantive disagreement (<95% similarity)" not in text
        assert "EVA substantive disagreements (<95%)" not in text


def test_build_report_is_reproducible_from_records():
    sources = {k: load_source(k, CACHE) for k in SOURCES}
    records = build_records(sources)
    report = json.loads((OUTPUT / "mismatch_report.json").read_text())
    assert json.loads(json.dumps(build_report(records, sources))) == report


def test_the_card_shows_a_committed_row(committed):
    """The dataset card's data instance is a committed row, byte for byte in its fields (it cannot drift from the data)."""
    import re

    rows, _ = committed
    card = (ROOT / "huggingface/voynich-transcription-mismatch/README.md").read_text(
        encoding="utf-8"
    )
    shown = json.loads(re.search(r"### Data Instance\s+```json\n(.*?)\n```", card, re.S).group(1))
    assert shown in rows
