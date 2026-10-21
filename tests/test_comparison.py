"""
The comparison rules of the mismatch index (roadmap item 1.8, defect D5), each tested on real loci read from ZL and IT at
test time and on small synthetic texts. No count is hand-written (principle 2).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from parsers import IVTFFParser
from vcat import comparison as cmp
from vcat.loss_accounting import CACHE_DIR
from vcat.profiles import apply_profile

ROOT = Path(__file__).resolve().parent.parent
CACHE = CACHE_DIR


def loci(name: str) -> dict[str, str]:
    """locus id -> text_raw of a cached source."""
    return {
        locus.locus_id: locus.text_raw
        for page in IVTFFParser().parse_file(CACHE / name)
        for locus in page.loci
    }


@pytest.fixture(scope="module")
def zl_it() -> tuple[dict[str, str], dict[str, str]]:
    return loci("ZL3b-n.txt"), loci("IT_ivtff_1a.txt")


@pytest.mark.parametrize(
    "a, b, verdict",
    [
        ("daiin.ol", "daiin.ol", cmp.IDENTICAL),
        ("daiin,ol", "daiin.ol", cmp.SAME_READING),  # an uncertain space is a word space (D5)
        ("daiin<->ol", "daiin.ol", cmp.SAME_READING),  # a drawing break separates words
        ("<%>dlo{ct}o<$>", "dlocto", cmp.SAME_READING),  # ligature glyphs, marks removed
        ("da[a:o]in", "daoin", cmp.ALTERNATE_READING),  # either reading of an alternate
        ("da[a:o:y]in", "dayin", cmp.ALTERNATE_READING),
        ("da[a:o]in", "daain", cmp.SAME_READING),  # the first reading is the profile's
        ("daiin.ol", "daiin.or", cmp.DIFFERENT),
        ("daiin.ol", "daiinol", cmp.DIFFERENT),  # a missing word space is a difference
        ("<!a comment>daiin", "daiin", cmp.SAME_READING),
    ],
)
def test_verdicts(a: str, b: str, verdict: str):
    assert cmp.compare(a, b)[0] == verdict
    assert cmp.compare(b, a)[0] == verdict  # symmetric


def test_similarity_describes_but_never_decides():
    status, score = cmp.compare("daiin.ol", "daiin.or")
    assert status == cmp.DIFFERENT and 0 < score < 1
    assert cmp.compare("daiin", "daiin")[1] == 1.0


def test_words_split_at_every_separator():
    assert cmp.words("a.b,c..d") == ["a", "b", "c", "d"]


def _independent_readings(text_raw: str) -> set[tuple[str, ...]]:
    """Every word sequence a text can be read as, one per choice among its alternates, by regular expressions written here
    (independent of the tokenizer): comments, marks and tags removed, wraps and whitespace joined, ligature braces dropped,
    '?' and the legacy markers removed, drawing breaks, '.' and ',' as word boundaries."""
    import itertools

    text = re.sub(r"<![^>]*>|<[%$]>|<@[A-Z]=[^<>\s]>", "", text_raw)
    text = re.sub(r"[ \t]*/(?:(?:\r\n|\n|\r)/[ \t]*)+", "", text)
    text = re.sub(r"<[-~]>", ".", re.sub(r"[ \t]", "", text))
    parts = re.split(r"(\[[^\]]*\])", text)
    options = [part[1:-1].split(":") if part.startswith("[") else [part] for part in parts]
    readings = set()
    for choice in itertools.product(*options):
        reading = re.sub(r"\{([^}]*)\}", r"\1", "".join(choice))
        reading = re.sub(r"[?!*]", "", reading)
        readings.add(tuple(w for w in re.split(r"[.,]", reading) if w))
    return readings


def test_every_real_verdict_follows_its_rule(zl_it):
    """On every locus both ZL and IT hold, the verdict is the one the rules give, checked against an independent
    reading: identical text_raw, then equal analysis-v1 word sequences, then equality for some alternate choice.
    """
    zl, it = zl_it
    seen = set()

    def split(text: str) -> list[str]:
        return [w for w in re.split(r"[.,]", apply_profile("analysis-v1", text)) if w]

    for locus_id in set(zl) & set(it):
        a, b = zl[locus_id], it[locus_id]
        verdict, score = cmp.compare(a, b)
        seen.add(verdict)
        if a == b:
            assert verdict == cmp.IDENTICAL, locus_id
        elif split(a) == split(b):
            assert verdict == cmp.SAME_READING, locus_id
        elif _independent_readings(a) & _independent_readings(b):
            assert verdict == cmp.ALTERNATE_READING, locus_id
        else:
            assert verdict == cmp.DIFFERENT, locus_id  # reach 1c53841b gap 1
    assert seen <= set(cmp.VERDICTS)
    assert {
        cmp.IDENTICAL,
        cmp.SAME_READING,
        cmp.DIFFERENT,
    } <= seen  # the real data exercises the rules
