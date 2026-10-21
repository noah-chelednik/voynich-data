# tests/regressions/ea46bb38/test_finding_3.py
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

# Historical 0.2.3 selector, inspected in the ancestor of the supplied base.
LEGACY_LOCUS = re.compile(
    r"^<(f\d+[rv]\d*)\.(\d+),([+@=*]?)([PLCR])(\d*)(?:;([A-Z]))?>(.*)$"
)


def historical_comma_counts():
    source = ROOT / "data_sources/cache/ZL3b-n.txt"
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        match = LEGACY_LOCUS.match(line)
        if not match:
            continue
        # Historical operations that can remove comma characters.
        text = re.sub(r"\{[^}]*\}", "", match.group(7))
        text = re.sub(
            r"\[([^:\]]*):([^\]]*)\]",
            lambda alternate: alternate.group(1),
            text,
        )
        text = re.sub(r"<[^>]*>", "", text)
        rows.append((match.group(1), text.count(",")))
    assert rows
    return rows


def erratum(defect):
    text = (ROOT / "ERRATA.md").read_text(encoding="utf-8")
    return next(
        line for line in text.splitlines()
        if line.startswith("| E-") and f"({defect})" in line
    )


def test_d6_distinguishes_uncertain_spaces_from_affected_rows():
    rows = historical_comma_counts()
    assert any(count for _, count in rows)
    total = sum(count for _, count in rows)
    affected = sum(bool(count) for _, count in rows)
    statement = erratum("D6")
    assert (
        f"kept {total:,} uncertain spaces" in statement
        or f"uncertain spaces in {affected:,} rows" in statement
    ), statement


def test_d3_does_not_describe_all_zodiac_pages_as_empty():
    rows = historical_comma_counts()
    retained = [
        page for page, _ in rows
        if re.fullmatch(r"f7[0-3][rv]\d*", page)
    ]
    assert retained, "The historical selector must demonstrate retained coverage"
    assert "the zodiac pages f70 to f73 empty" not in erratum("D3")
