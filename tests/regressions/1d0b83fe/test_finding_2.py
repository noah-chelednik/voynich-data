# tests/regressions/1d0b83fe/test_finding_2.py
"""Review 1d0b83fe finding 2 (claim 1, the narrowing of reach dec3e688 gap 1): the plan says "a record made from one
page alone leaves [the total] unknown, since one page cannot know its side's other panels". The public
`MetadataParser.extract_pages` makes a record from whatever pages it is given and states the highest panel number among
THEM as the side's total: one page f67r1 becomes panel 1 of 1 (the source's f67 recto has 2), and f86v3 with f86v4
becomes "of 4", the very total audit 20261021-parsers F1 condemned. A total is either the source's or unknown."""
import re
from collections import defaultdict
from pathlib import Path

from parsers import IVTFFParser
from parsers.metadata_parser import MetadataParser
from vcat.sources import source_file

ROOT = Path(__file__).resolve().parents[3]


def test_a_total_from_part_of_a_side_is_the_sources_or_unknown():
    pages = list(IVTFFParser().parse_file(ROOT / source_file("ZL")))
    highest = defaultdict(int)
    for page in pages:
        m = re.fullmatch(r"f(\d+)([rv])(\d+)", page.page_id)
        if m:
            highest[(m.group(1), m.group(2))] = max(highest[(m.group(1), m.group(2))], int(m.group(3)))
    assert highest, "the source names panel pages"
    wrong = []
    for page in pages:
        m = re.fullmatch(r"f(\d+)([rv])(\d+)", page.page_id)
        if not m:
            continue
        record = MetadataParser().extract_pages([page])[0]
        if record.total_panels not in (None, highest[(m.group(1), m.group(2))]):
            wrong.append((record.page_id, record.panel_number, record.total_panels))
    assert wrong == [], wrong
