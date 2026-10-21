# tests/regressions/b8d5e9c6/test_finding_2.py
"""Review b8d5e9c6 finding 2 (claim 3): "A link with no visible text (empty, or only white space, format, combining-only
or blank-drawn characters) links no document". `_visible` excludes some general categories and a hand list of six
blank-drawn characters plus the variation selectors, but treats every unassigned (Cn) character as visible. Unicode
reserves U+2065, U+FFF0..U+FFF8 and U+E0002..U+E001F as Default_Ignorable_Code_Point, which a conformant renderer
(HarfBuzz, as browsers use) draws as nothing even unassigned. A link whose only text is one of them is as invisible as
`[](url)`, yet `_linked_documents` counts it as linking STABILITY.md."""
from tests import test_stability as checks

URL = "https://github.com/noah-chelednik/voynich-data/blob/main/STABILITY.md"


def test_a_link_of_reserved_default_ignorable_characters_links_nothing():
    linked = {
        hex(ord(invisible)): checks._linked_documents(f"[{invisible}]({URL})", None)
        for invisible in ("⁥", "￰", "\U000e0002")
    }
    assert all(found == set() for found in linked.values()), linked
