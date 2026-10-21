# tests/regressions/b8d5e9c6/test_finding_1.py
"""Review b8d5e9c6 finding 1 (claim 1): a foldout folio's `panel_count` is "the highest panel number on either of its
sides among its own pages, as its pages' totals say", and "from one page or part of a side it is left unknown". The
public `MetadataParser.extract_folios` has no notion of a whole source: handed part of a folio it states the highest
panel number among THOSE pages as the folio's count, while the same pages' records (`extract_pages`, default) say their
totals are unknown. f67r1 alone gives f67 one panel (the source has 2); f86v3 with f86v4 gives f86 "4", the count audit
20261021-parsers F1/F2 condemned. A folio's count is either the source's or unknown."""
from pathlib import Path

from parsers import IVTFFParser
from parsers.metadata_parser import MetadataParser
from vcat.sources import source_file

ROOT = Path(__file__).resolve().parents[3]


def test_a_folio_count_from_part_of_a_folio_is_the_sources_or_unknown():
    pages = list(IVTFFParser().parse_file(ROOT / source_file("ZL")))
    source_count = {f.folio_id: f.panel_count for f in MetadataParser().extract_folios(pages)}
    by_id = {p.page_id: p for p in pages}
    wrong = []
    for part in (["f67r1"], ["f86v3", "f86v4"], ["f68r1", "f68v1"]):
        for folio in MetadataParser().extract_folios([by_id[p] for p in part]):
            if folio.panel_count not in (None, source_count[folio.folio_id]):
                wrong.append((part, folio.folio_id, folio.panel_count, source_count[folio.folio_id]))
    assert wrong == [], wrong
