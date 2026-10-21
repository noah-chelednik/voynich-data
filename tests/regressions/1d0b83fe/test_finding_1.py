# tests/regressions/1d0b83fe/test_finding_1.py
"""Review 1d0b83fe finding 1 (claim 3): "a link with no visible text (empty, white space or zero-width characters only)
links no document". `_Shown.handle_endtag` decides visibility by Unicode general category (Cf, Zs, Zl, Zp) and
`isspace`, not by whether a character is shown. Zero-width characters of other categories pass: U+034F COMBINING
GRAPHEME JOINER and U+FE0F VARIATION SELECTOR-16 (both Mn, zero-width, Default_Ignorable_Code_Point), and the Hangul
filler U+3164 (Lo, Default_Ignorable_Code_Point, rendered blank). A link whose only text is one of them is as invisible
as `[](url)`, yet `_linked_documents` counts it as linking STABILITY.md."""
from tests import test_stability as checks

URL = "https://github.com/noah-chelednik/voynich-data/blob/main/STABILITY.md"


def test_a_link_of_zero_width_characters_links_nothing():
    linked = {
        hex(ord(invisible)): checks._linked_documents(f"[{invisible}]({URL})", None)
        for invisible in ("͏", "️", "ㅤ")
    }
    assert all(found == set() for found in linked.values()), linked
