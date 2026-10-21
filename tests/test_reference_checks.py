"""Reference checks (roadmap item 2.10): VCAT's counts and entropies against published values, as acceptance tests.

Each published value, its page, the words it is quoted from and the tolerance argued for it are in
`data_sources/references.yaml` (no count is written here); the statistics are `vcat/reference.py`'s, over the committed
build. The positive controls show each kind of check can fail: markup left in the reading, uncertain readings kept, a
whole class of loci lost by the parser. That the quotes are on the pinned pages is `scripts/check_references.py`'s check
(the pages are kept offline, git-ignored).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

import pytest
import yaml

from vcat import api
from vcat.reference import character_statistics, statistics, word_statistics, words_of
from vcat.sources import load_sources

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = yaml.safe_load((ROOT / "data_sources" / "references.yaml").read_text(encoding="utf-8"))
REFERENCES = {r["id"]: r for r in REGISTRY["references"]}
MEASURES = ("characters", "h1", "h2", "tokens", "types")


@functools.cache
def measured(source: str, profile: str = api.DEFAULT_PROFILE) -> dict[str, float]:
    return statistics(source, profile)


def quoted_numbers(quote: str) -> list[float]:
    """The numbers a quote writes, as numbers: `188,862` is 188862, `3.862` is 3.862; a digit run inside a longer
    number is not a number of its own."""
    tokens = re.findall(
        r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d,.]\d)|(?<![\d.,])\d+(?:\.\d+)?(?![\d,.]\d)",
        quote,
    )
    return [float(t.replace(",", "")) for t in tokens]


def allowed(reference: dict) -> float:
    """How far VCAT's value may be from the published one: the tolerance as an absolute difference."""
    tolerance = reference["tolerance"]
    if "relative" in tolerance:
        return float(tolerance["relative"]) * float(reference["value"])
    return float(tolerance["absolute"])


def within(ours: float, reference: dict) -> bool:
    return abs(ours - float(reference["value"])) <= allowed(reference)


def test_the_registry_is_well_formed():
    """Every page is voynich.nu's (the upstream the roadmap names), pinned by SHA-256 with its update and retrieval
    dates; every reference names its page, a cached source, a measure VCAT computes, a positive tolerance of one kind
    with its argument, and a quote that holds its value as the page writes it."""
    pages = {p["id"]: p for p in REGISTRY["pages"]}
    assert len(pages) == len(REGISTRY["pages"])
    for page in pages.values():
        assert page["url"].startswith("https://www.voynich.nu/"), page["id"]
        assert re.fullmatch(r"[0-9a-f]{64}", page["sha256"]), page["id"]
        assert page["file"].startswith("docs/reference/"), page["id"]
        assert (
            page["updated"]
            and page["retrieved"]
            and page["method"]
            and page["title"]
            and page["author"]
        )
    cached = {entry["id"] for entry in load_sources()["cached"]}
    ids = [r["id"] for r in REGISTRY["references"]]
    assert len(set(ids)) == len(ids), "a reference id is repeated"
    for reference in REGISTRY["references"]:
        assert reference["page"] in pages, reference["id"]
        assert reference["source"] in cached, reference["id"]
        assert reference["measure"] in MEASURES, reference["id"]
        assert len(reference["tolerance"]) == 1 and set(reference["tolerance"]) <= {
            "relative",
            "absolute",
        }
        assert allowed(reference) > 0, reference["id"]
        assert reference["why"].strip() and reference["where"].strip(), reference["id"]
        assert reference["control"] and set(reference["control"]) <= set(DAMAGES), reference["id"]
        # the value is one of the quote's numbers exactly, as a number: not a rounding of it, not a fragment of one
        # (reach 7ea91938 gap 2)
        assert reference["value"] in quoted_numbers(reference["quote"]), (
            reference["id"],
            reference["quote"],
        )


@pytest.mark.parametrize("reference_id", sorted({r["id"] for r in REGISTRY["references"]}))
def test_each_published_value_is_met(reference_id):
    """VCAT's statistic is within the reference's argued tolerance of the published value: every registry entry with
    this id, so a repeated id hides no value (reach 7ea91938 gap 1; the registry test also refuses the repetition).
    """
    entries = [r for r in REGISTRY["references"] if r["id"] == reference_id]
    assert entries, reference_id
    for reference in entries:
        ours = measured(reference["source"])[reference["measure"]]
        assert within(ours, reference), (
            f"{reference_id}: VCAT {ours} against published {reference['value']} ({reference['where']}); "
            f"allowed {allowed(reference)}: {reference['why']}"
        )


def _damaged(source: str, damage: str) -> dict[str, float]:
    """A source's statistics after one kind of damage a parser or profile could do."""
    if damage == "markup-kept":
        return measured(source, "raw-v1")
    if damage == "uncertain-kept":
        return measured(source, "diplomatic-v1")
    readings = [line["reading"] for line in api.load(source=source, unit="line")]
    if damage == "loci-lost":  # every tenth locus lost
        readings = [r for i, r in enumerate(readings) if i % 10]
    elif damage == "paragraphs-only":  # every locus that is not paragraph text lost
        lines = api.load(source=source, unit="line")
        readings = [line["reading"] for line in lines if (line.get("locus_type") or "")[1:2] == "P"]
    elif damage == "word-division-lost":  # a reading's words fused: no word space read
        readings = ["".join(words_of([r])) for r in readings]
    else:
        raise ValueError(f"unknown damage {damage!r}")
    words = words_of(readings)
    return {**character_statistics(words), **word_statistics(words)}


#: The kinds of damage a reference's `control` may name
DAMAGES = ("markup-kept", "uncertain-kept", "loci-lost", "paragraphs-only", "word-division-lost")


@pytest.mark.parametrize("reference_id", sorted({r["id"] for r in REGISTRY["references"]}))
def test_each_check_fails_on_its_named_damage(reference_id):
    """Every check has teeth: under each kind of damage its `control` names, VCAT's statistic leaves the tolerance
    (review c5c2dbe8 finding 2: the controls ran on ZL only)."""
    for reference in [r for r in REGISTRY["references"] if r["id"] == reference_id]:
        for damage in reference["control"]:
            got = _damaged(reference["source"], damage)[reference["measure"]]
            assert not within(got, reference), (reference_id, damage, got)


def test_markup_left_in_the_reading_fails_the_entropy_check():
    """Positive control: the raw profile keeps the IVTFF markup in the reading; ZL's h1 then fails its check."""
    assert not within(measured("ZL", "raw-v1")["h1"], REFERENCES["zl-h1"])


def test_uncertain_readings_kept_fail_the_entropy_checks():
    """Positive control: the diplomatic profile keeps uncertain readings and their marks; ZL's h1 and h2 fail."""
    diplomatic = measured("ZL", "diplomatic-v1")
    assert not within(diplomatic["h1"], REFERENCES["zl-h1"])
    assert not within(diplomatic["h2"], REFERENCES["zl-h2"])


def test_a_class_of_loci_lost_fails_the_count_checks():
    """Positive control: a parser that loses every locus but paragraph text (labels, circular and radial text, as the
    pre-1.1 parser lost letter-subtype loci) fails ZL's character and word-token checks."""
    lines = api.load(source="ZL", unit="line")
    paragraphs = [line["reading"] for line in lines if (line.get("locus_type") or "")[1:2] == "P"]
    assert paragraphs and len(paragraphs) < len(lines)
    words = words_of(paragraphs)
    assert not within(character_statistics(words)["characters"], REFERENCES["zl-characters"])
    assert not within(word_statistics(words)["tokens"], REFERENCES["zl-word-tokens"])


def test_the_document_states_the_registry():
    """`docs/reference_checks.md` states every published value as the registry has it, rendered whole."""
    from tests.test_cards import whole_table
    from vcat.reference import references_table

    rendered = references_table(REGISTRY)
    text = (ROOT / "docs" / "reference_checks.md").read_text(encoding="utf-8")
    assert whole_table(text, rendered) == rendered


def test_the_statistics_are_counted_as_stated():
    """Words by the EVA tokenizer; a `@NNN;` code one character; spaces not characters; pairs within words; h2 the pair
    entropy less h1. On constructed words, against the definitions computed by hand."""
    import math
    from collections import Counter

    words = words_of(["ab.a@192;b,c'y"])
    assert words == ["ab", "a@192;b", "c'y"]
    chars = ["a", "b", "a", "@192;", "b", "c", "'", "y"]
    pairs = [("a", "b"), ("a", "@192;"), ("@192;", "b"), ("c", "'"), ("'", "y")]

    def h(events):
        counts = Counter(events)
        total = sum(counts.values())
        return -sum(n / total * math.log2(n / total) for n in counts.values())

    got = character_statistics(words)
    assert got["characters"] == len(chars)
    assert math.isclose(got["h1"], h(chars))
    assert math.isclose(got["h2"], h(pairs) - h(chars))
    assert word_statistics(words) == {"tokens": len(words), "types": len(set(words))}
    assert word_statistics(["ab", "ab"]) == {"tokens": len(["ab", "ab"]), "types": len({"ab"})}


def test_the_pin_check_refuses_a_changed_page_and_a_missing_quote(tmp_path, monkeypatch):
    """`scripts/check_references.py` passes a page whose bytes are pinned and hold every quote, and refuses a changed
    byte and a quote the page does not hold."""
    import hashlib

    from scripts import check_references as checker

    page = tmp_path / "docs" / "reference" / "page.html"
    page.parent.mkdir(parents=True)
    page.write_bytes(b"<p>Method sentence.</p><td>Row</td> <td>3.862</td>")
    registry = {
        "pages": [
            {
                "id": "p",
                "url": "https://www.voynich.nu/x.html",
                "file": "docs/reference/page.html",
                "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                "method": "Method sentence.",
            }
        ],
        "references": [{"page": "p", "quote": "Row 3.862"}],
    }
    path = tmp_path / "references.yaml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "REGISTRY", path)
    assert checker.main([]) == 0
    registry["references"].append({"page": "p", "quote": "Row 3.863"})
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    assert checker.main([]) == 1
    registry["references"].pop()
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    page.write_bytes(page.read_bytes() + b" ")
    assert checker.main([]) == 1


#: How a `why` names each damage
DAMAGE_NAMES = {
    "markup left in": "markup-kept",
    "uncertain readings kept": "uncertain-kept",
    "a tenth of the loci lost": "loci-lost",
    "paragraph text only": "paragraphs-only",
    "word division lost": "word-division-lost",
}


#: The words prose uses for each damage. An argument may use a damage's words only when its `control` tests that damage,
#: so a claim of teeth worded without the old verb list ("paragraph text only moves the count", "markup in the reading
#: raises h1") is refused too (B-122, review 7379c57a finding 1). Synonyms outside these lists are the boundary.
DAMAGE_WORDS = {
    "markup-kept": r"markup|tags?|comments?",
    "uncertain-kept": r"uncertain readings?|alternate readings?|alternates",
    "loci-lost": r"loci|locus|lines? lost",
    "paragraphs-only": r"paragraphs?|labels?",
    "word-division-lost": r"word[- ]divisions?|divid(?:ed|es|ing)|fus(?:ed|es|ing)|word[- ]boundar(?:y|ies)|word[- ]spaces?",
}


def test_each_why_names_the_damages_its_control_tests():
    """Every `why` ends with what its check fails on, naming exactly the damages of its `control`, and claims no damage
    elsewhere, so no argument claims teeth the suite does not show (review 07428068, review 14df5abd).
    """
    assert (
        set(DAMAGE_WORDS) == set(DAMAGES) == set(DAMAGE_NAMES.values())
    )  # every damage has its words
    for reference in REGISTRY["references"]:
        why = " ".join(reference["why"].split())
        # every argument ends with what it fails on; the prose before claims no damage of its own, so a claim of teeth
        # can only be made where it is checked (review 14df5abd finding 1)
        assert why.count("Fails on:") == 1, reference["id"]
        argument, listed = why.split("Fails on:")
        claimed = re.findall(
            r"\b(lost|losing|loses|lose|kept|keeping|left in|control|controls|fails?|failing|fused|fusing)\b",
            argument,
            re.IGNORECASE,
        )
        assert not claimed, (reference["id"], claimed)
        mentioned = {
            damage
            for damage, words in DAMAGE_WORDS.items()
            if re.search(rf"\b(?:{words})\b", argument, re.IGNORECASE)
        }
        assert mentioned <= set(reference["control"]), (reference["id"], sorted(mentioned))
        named = [n.strip() for n in listed.rstrip(".").split(",")]
        assert all(n in DAMAGE_NAMES for n in named), (reference["id"], named)
        assert sorted(DAMAGE_NAMES[n] for n in named) == sorted(reference["control"]), reference[
            "id"
        ]
