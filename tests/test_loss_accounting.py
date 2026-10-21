"""
Loss accounting (roadmap item 1.5).

Every source locus is emitted or explicitly reported; an unaccounted locus fails the build. The
expected populations come from the cached source files at test time, counted by
``vcat.loss_accounting``'s own recognizer, never from hand-written numbers.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import pytest

from builders import build_eva_lines
from parsers import IVTFFParser
from vcat.loss_accounting import CACHE_DIR, account, census_source, census_text
from vcat.sources import cached_sources, source_encoding

# every cached file the registry records, wherever under the cache it is (S13: LSI under latin-1/)
SOURCES = sorted(source.path for source in cached_sources())
# The package re-exports the function under the module's name; this is the module.
build_module = importlib.import_module("builders.build_eva_lines")

# Synthetic sources: the `synthetic_accounted` and `synthetic_lossy` fixtures in conftest.py.


def parse_and_account(path: Path):
    parser = IVTFFParser()
    pages = list(parser.parse_file(path))
    emitted = [f"{p.page_id}:{locus.locus_number}" for p in pages for locus in p.loci]
    # a line the parser rejected is reported under its id (S13: LSI's four `44a` loci), as a build reports it
    reported = [w.locus_id for w in parser.warnings if w.locus_id and w.emitted_id is None]
    return account(census_source(path), emitted, [p.page_id for p in pages], reported_loci=reported)


def test_sources_are_cached():
    assert SOURCES, f"no cached IVTFF source under {CACHE_DIR}"


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: p.name)
def test_census_covers_every_angle_line(source: Path):
    """Every line starting with '<' is a locus or a page header, and each is counted once."""
    lines = source.read_text(
        encoding=source_encoding(source), errors="surrogateescape"
    ).splitlines()
    angle_lines = [line for line in lines if line.startswith("<")]
    census = census_source(source)
    assert census.unrecognized == ()
    assert len(census.loci) + len(census.pages) == len(angle_lines)
    # Each reading is one locus line: an id repeats only as the readings of an interlinear file (one per transcriber,
    # S13), so the full identifiers, transcriber included, are unique
    identifiers = [
        line.split(">", 1)[0] for line in angle_lines if re.match(r"<[^<>.,\s]+\.", line)
    ]
    assert (
        len(set(identifiers)) == len(identifiers) == len(census.loci)
    ), "duplicate locus identifiers in the source"
    assert census.pages_with_loci <= set(census.pages)


def test_census_counts_synthetic_text(synthetic_lossy: str):
    census = census_text(synthetic_lossy + "<bogus line\n")
    assert census.loci == ("f1r:1", "f1r:2", "f1v:1", "f1v:2")
    assert census.pages == ("f1r", "f1v")
    assert census.unrecognized == (len(synthetic_lossy.splitlines()) + 1,)


def test_account_names_unaccounted_and_unexpected(synthetic_lossy: str):
    census = census_text(synthetic_lossy)
    result = account(census, ["f1r:1", "f1v:1", "f9r:1"], ["f1r"])
    assert result.unaccounted_loci == ["f1r:2", "f1v:2"]
    assert result.unexpected_loci == ["f9r:1"]
    assert result.unaccounted_pages == ["f1v"]
    assert result.loci_emitted == len(census.loci) - len(result.unaccounted_loci)
    assert not result.complete
    assert len(result.problems()) == len(["loci", "unexpected", "pages"])


def test_account_counts_reported_as_accounted(synthetic_lossy: str):
    census = census_text(synthetic_lossy)
    emitted = list(census.loci[:-1])
    result = account(census, emitted, census.pages, reported_loci=[census.loci[-1]])
    assert result.complete, result.problems()
    assert result.loci_emitted == len(emitted)
    assert result.loci_reported == len(census.loci) - len(emitted)


def test_account_flags_unrecognized_lines(synthetic_accounted: str):
    census = census_text(synthetic_accounted + "<bogus\n")
    result = account(census, census.loci, census.pages)
    assert not result.complete


def test_real_sources_have_no_unaccounted_loci():
    """Every locus and page of every cached source is emitted or reported after parsing."""
    assert SOURCES
    problems = {}
    for source in SOURCES:
        result = parse_and_account(source)
        if not result.complete:
            problems[source.name] = result.problems()
    assert not problems, problems


def test_build_report_accounts_for_real_source(zl_file: Path, tmp_path: Path):
    records, report = build_eva_lines(zl_file, tmp_path)
    census = census_source(zl_file)
    assert report.source_loci == len(census.loci)
    assert report.source_page_headers == len(census.pages)
    assert report.loci_emitted == len(records) == report.total_lines
    assert report.loci_emitted + len(report.unaccounted_loci) == report.source_loci
    assert set(report.unaccounted_loci) == set(census.loci) - {r.line_id for r in records}
    assert report.unexpected_loci == []


def run_cli(monkeypatch, source: Path, out: Path) -> int:
    monkeypatch.setattr(
        sys, "argv", ["build_eva_lines", "--source", str(source), "--output-dir", str(out)]
    )
    try:
        build_module.main()
    except SystemExit as stop:
        return 0 if stop.code is None else int(stop.code)
    return 0


def test_build_cli_refuses_unaccounted_loci(monkeypatch, tmp_path: Path, synthetic_lossy: str):
    source = tmp_path / "lossy.txt"
    source.write_text(synthetic_lossy, encoding="utf-8")
    out = tmp_path / "out"
    assert run_cli(monkeypatch, source, out) != 0
    assert not out.exists() or not any(out.iterdir())


def test_build_cli_writes_when_accounted(monkeypatch, tmp_path: Path, synthetic_accounted: str):
    source = tmp_path / "ok.txt"
    source.write_text(synthetic_accounted, encoding="utf-8")
    out = tmp_path / "out"
    assert run_cli(monkeypatch, source, out) == 0
    rows = (out / "eva_lines.jsonl").read_text().splitlines()
    report = json.loads((out / "eva_lines_build_report.json").read_text())
    assert len(rows) == len(census_text(synthetic_accounted).loci)
    assert report["unaccounted_loci"] == []
    assert report["source_loci"] == len(rows)


def test_account_flags_reported_loci_absent_from_source(synthetic_lossy: str):
    """A reported id that is not a source locus cannot account for anything."""
    census = census_text(synthetic_lossy)
    result = account(census, census.loci[:-1], census.pages, reported_loci=["f9r:1"])
    assert result.unknown_reported == ["f9r:1"]
    assert result.unaccounted_loci == [census.loci[-1]]
    assert not result.complete


def test_build_reports_parser_warnings(monkeypatch, tmp_path: Path, synthetic_accounted: str):
    """A locus the parser rejects is reported in the build, accounted, and the build is written."""
    bad = "<f1v.2,@Pz>       rejected"
    source = tmp_path / "warned.txt"
    source.write_text(synthetic_accounted + bad + "\n", encoding="utf-8")
    records, report = build_eva_lines(source, tmp_path)
    assert report.reported_loci == ["f1v:2"]
    assert report.loci_reported == 1
    assert report.unaccounted_loci == []
    assert "f1v:2" not in {r.line_id for r in records}
    assert any("f1v:2" in w for w in report.warnings), report.warnings
    out = tmp_path / "out"
    assert run_cli(monkeypatch, source, out) == 0
    written = json.loads((out / "eva_lines_build_report.json").read_text())
    assert written["reported_loci"] == ["f1v:2"]


def test_real_build_emits_every_locus(zl_file: Path, tmp_path: Path):
    records, report = build_eva_lines(zl_file, tmp_path)
    census = census_source(zl_file)
    assert report.loss_problems() == []
    assert report.reported_loci == [] and report.unaccounted_pages == []
    assert sorted(r.line_id for r in records) == sorted(census.loci)
    pages = {r.page_id for r in records}
    zodiac = {p for p in census.pages if re.match(r"^f7[0-3][rv]", p)}
    assert zodiac and zodiac <= pages
    assert "fRos" in pages


def test_account_counts_occurrences(synthetic_accounted: str):
    """Each source locus line is emitted or reported once: a duplicate is flagged, a second reading is not."""
    census = census_text(synthetic_accounted)
    doubled = account(census, [*census.loci, census.loci[0]], census.pages)
    assert doubled.overcounted == 1 and not doubled.complete
    both = account(census, census.loci, census.pages, reported_loci=[census.loci[0]])
    assert both.overcounted == 1 and not both.complete

    readings = census_text(synthetic_accounted + "<f1v.1,@Pz;C>     rejected.reading\n")
    assert readings.loci.count("f1v:1") == len(["emitted", "reported"])
    split = account(readings, census.loci, census.pages, reported_loci=["f1v:1"])
    assert split.complete, split.problems()
    assert split.loci_emitted + split.loci_reported == split.source_loci
