# tests/regressions/dec3e688/test_reach_2.py
"""Reach dec3e688 gap 2 (claim 3): a link "whose text shows nothing" is decided by `str.strip()`, which keeps the
zero-width and invisible format characters (U+200B, U+2060). A link whose only text is one of them is as empty
to a reader as `[](url)`, yet `_linked_documents` counts it as linking the document."""
from tests import test_stability as checks

URL = "https://github.com/noah-chelednik/voynich-data/blob/main/STABILITY.md"


def test_an_invisible_link_links_nothing_a_reader_can_see():
    for invisible in ("​", "⁠", "&#8203;"):
        assert checks._linked_documents(f"[{invisible}]({URL})", None) == set(), repr(invisible)
