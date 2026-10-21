# tests/regressions/07428068/test_finding_3.py
"""The `why` of fg-h2 says "Markup left in and uncertain readings kept move FG's h2 by less than 0.005 bits", and of
cd-h2 "Markup and uncertain readings move CD's h2 by less than the tolerance". Measured, markup left in (raw-v1) moves
FG's h2 by 0.013 bits and uncertain readings kept by 0.010; markup left in moves CD's h2 by 0.056 bits, more than its
0.05 tolerance. The checks pass under those damages only because VCAT's undamaged h2 lies below the published value
and the damage pushes it toward it, not because the damage moves h2 little."""
from tests import test_reference_checks as checks

SENTENCES = {
    "fg-h2": ("move FG's h2 by less than 0.005 bits", lambda r: 0.005),
    "cd-h2": ("move CD's h2 by less than the tolerance", checks.allowed),
}


def test_each_why_states_the_move_its_damages_make():
    wrong = []
    for r in checks.REGISTRY["references"]:
        if r["id"] not in SENTENCES:
            continue
        sentence, bound = SENTENCES[r["id"]]
        if sentence not in " ".join(r["why"].split()):
            continue
        base = checks.measured(r["source"])[r["measure"]]
        for damage in ("markup-kept", "uncertain-kept"):
            move = abs(checks._damaged(r["source"], damage)[r["measure"]] - base)
            if not move < bound(r):
                wrong.append((r["id"], damage, round(move, 4), bound(r)))
    assert not wrong, f"the why says the damage moves h2 by less than the bound; measured: {wrong}"
