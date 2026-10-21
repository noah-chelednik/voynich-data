"""
Metadata structure follows the source (roadmap item 1.1; audit findings AP F4, F5, F6).

Missing folios, quire completeness and the folio-to-page index are checked against the page headers
of the cached ZL source at test time; folio and quire identifiers below are identities, not counts.
"""

from __future__ import annotations

import re

import pytest

from parsers import MISSING_FOLIOS, IVTFFParser, MetadataParser
from vcat.loss_accounting import CACHE_DIR, census_source
from vcat.sources import cached_sources

# every cached file the registry records, wherever under the cache it is (S13: LSI under latin-1/)
SOURCES = sorted(source.path for source in cached_sources())
FOLIO = re.compile(r"^f(\d+)[rv]\d*$")


@pytest.fixture(scope="module")
def zl_pages():
    return list(IVTFFParser().parse_file(CACHE_DIR / "ZL3b-n.txt"))


def folio_numbers(page_ids) -> set[int]:
    return {int(m.group(1)) for page_id in page_ids if (m := FOLIO.match(page_id))}


def test_missing_folios_follow_the_source():
    headers = folio_numbers(census_source(CACHE_DIR / "ZL3b-n.txt").pages)
    assert headers
    assert sorted(MISSING_FOLIOS) == sorted(set(range(1, max(headers) + 1)) - headers)
    for source in SOURCES:
        census = census_source(source)
        transcribed = folio_numbers(locus.rsplit(":", 1)[0] for locus in census.loci)
        assert transcribed, source.name
        assert transcribed.isdisjoint(MISSING_FOLIOS), (
            source.name,
            transcribed & set(MISSING_FOLIOS),
        )


def test_quire_completeness_on_the_source(zl_pages):
    quires = MetadataParser().extract_quires(zl_pages)
    spans = {
        q.quire_id: (min(int(f[1:]) for f in q.folio_ids), max(int(f[1:]) for f in q.folio_ids))
        for q in quires
    }
    letters = {q.quire_id: q.quire_letter for q in quires}

    inside = {qid: [m for m in MISSING_FOLIOS if lo < m < hi] for qid, (lo, hi) in spans.items()}
    # A run of missing folios between two quires whose letters are consecutive could belong to either.
    undecided: dict[str, list[int]] = {qid: [] for qid in spans}
    ordered = sorted(spans, key=lambda qid: spans[qid][0])
    for left, right in zip(ordered, ordered[1:], strict=False):
        between = [m for m in MISSING_FOLIOS if spans[left][1] < m < spans[right][0]]
        if between and ord(letters[right]) == ord(letters[left]) + 1:
            undecided[left] += between
            undecided[right] += between

    assert any(inside.values()) and any(undecided.values())
    for q in quires:
        if inside[q.quire_id]:
            expected, named = False, inside[q.quire_id]
        elif undecided[q.quire_id]:
            expected, named = None, undecided[q.quire_id]
        else:
            expected, named = True, []
        assert q.is_complete is expected, (q.quire_id, q.is_complete)
        for folio in named:
            assert any(f"f{folio}" in note for note in q.notes), (q.quire_id, folio, q.notes)


def test_folio_records_list_every_panel(zl_pages):
    folios = {f.folio_id: f for f in MetadataParser().extract_folios(zl_pages)}
    panel = re.compile(r"^f(\d+)r(\d*)$")
    for folio_id, record in folios.items():
        rectos = [
            p.page_id
            for p in zl_pages
            if (m := panel.match(p.page_id)) and f"f{m.group(1)}" == folio_id
        ]
        rectos.sort(key=lambda page_id: int(panel.match(page_id).group(2) or 0))
        if folio_id == "f86":
            rectos = ["fRos", *rectos]
        assert record.recto_page_ids == rectos, folio_id
        assert record.recto_page_id == (rectos[0] if rectos else None), folio_id
    assert "fRos" in folios["f85"].verso_page_ids
    assert "fRos" in folios["f86"].recto_page_ids
    indexed = {p for f in folios.values() for p in [*f.recto_page_ids, *f.verso_page_ids]}
    assert indexed == {p.page_id for p in zl_pages}


def test_page_records_keep_source_page_names(zl_pages):
    records = MetadataParser().extract_pages(zl_pages)
    assert [r.page_id for r in records] == [p.page_id for p in zl_pages]
    ros = next(r for r in records if r.page_id == "fRos")
    assert (ros.folio_id, ros.side) == ("f85", "verso")
    assert ros.notes
