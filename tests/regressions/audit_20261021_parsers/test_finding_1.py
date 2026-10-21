# tests/regressions/audit_20261021_parsers/test_finding_1.py
"""Audit 20261021-parsers finding 1: a page record's foldout panel fields are the source's.

A panel page is named f<folio><side><panel> (IVTFF 2.0 section 4.2). Whatever the side's true panel count, a panel
page's `total_panels` (data_model: "Total panels if foldout") is a number, no smaller than its own `panel_number` and no
smaller than the number of panels the source gives that side. `parsers.metadata_parser` takes `total_panels` from a
hand-written table (`FOLDOUT_PAGES`) that names panels the source does not have, so f86v6 is published as panel 6 of 4.
"""
import re
from collections import Counter
from pathlib import Path

from parsers import IVTFFParser
from parsers.metadata_parser import extract_all_metadata
from vcat.sources import source_file

ROOT = Path(__file__).resolve().parents[3]


def test_every_panel_page_has_a_total_that_holds_it_and_its_sides_panels():
    pages = list(IVTFFParser().parse_file(ROOT / source_file("ZL")))
    panels = Counter(
        (m.group(1), m.group(2))
        for page in pages
        if (m := re.fullmatch(r"f(\d+)([rv])(\d+)", page.page_id))
    )
    assert panels, "the source names panel pages"
    records = extract_all_metadata(pages).pages
    wrong = []
    for record in records:
        m = re.fullmatch(r"f(\d+)([rv])(\d+)", record.page_id)
        if not m:
            continue
        in_source = panels[(m.group(1), m.group(2))]
        total = record.total_panels
        if total is None or total < record.panel_number or total < in_source:
            wrong.append((record.page_id, record.panel_number, total, in_source))
    assert wrong == [], wrong
