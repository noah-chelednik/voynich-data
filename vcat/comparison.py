"""
Comparing two transliterations of one locus (roadmap item 1.8)
=============================================================

The rules the mismatch index applies, each one named, so that its numbers mean one thing (defect D5). Two loci are compared
through a named normalization profile (`vcat.profiles`, ``analysis-v1`` by default), as word sequences:

- a word space ``.``, an uncertain word space ``,`` and a drawing break (``.`` in the profile) all separate words, so an
  uncertain space in one transliteration matches a word space in the other (D5: "``,`` is a space");
- an alternate reading ``[a:b]`` matches either of its readings (D5: alternates are kept, not deleted);
- everything else is the profile's rule (ligature glyphs, ``?`` dropped, comments and marks removed).

The verdicts, from closest to farthest; each is exact, none is a similarity threshold:

``identical``          the two ``text_raw`` are the same string
``same_reading``       the profile's word sequences are the same
``alternate_reading``  the word sequences are the same for some choice among the alternate readings
``different``          none of the above

A similarity score (``difflib`` ratio of the two readings, first readings taken) is reported beside the verdict as a
description, never used to decide it. Nothing here is a consensus or a correction: the index says where the two sources
differ and how, and leaves the reading to the user (principle 4).
"""

from __future__ import annotations

import itertools
import re
from difflib import SequenceMatcher

from parsers import ivtff_markup as mk
from parsers.ivtff_markup import Markup, Token, parse_markup
from vcat.profiles import Profile, get_profile

#: The profile the index compares through, unless another is named.
COMPARISON_PROFILE = "analysis-v1"

IDENTICAL = "identical"
SAME_READING = "same_reading"
ALTERNATE_READING = "alternate_reading"
DIFFERENT = "different"
#: The verdicts, closest first; a locus present in both sources gets exactly one.
VERDICTS = (IDENTICAL, SAME_READING, ALTERNATE_READING, DIFFERENT)
#: Agreement, as the index counts it: every verdict but ``different``.
AGREEING = (IDENTICAL, SAME_READING, ALTERNATE_READING)


def words(reading: str) -> list[str]:
    """A profile reading cut into words at ``.`` and ``,`` (empty words dropped)."""
    return [word for word in re.split(r"[.,]", reading) if word]


def _readings(tokens: list[Token], profile: Profile) -> list[str]:
    """Every reading of a token list under the profile, one per choice among its alternates, first readings first."""
    parts: list[list[str]] = []
    for token in tokens:
        if token.kind == mk.ALTERNATES:
            parts.append([profile.render(mk._reading_tokens(reading)) for reading in token.value])
        else:
            parts.append([profile.render([token])])
    return ["".join(choice) for choice in itertools.product(*parts)]


def compare(
    text_raw_a: str, text_raw_b: str, profile_name: str = COMPARISON_PROFILE
) -> tuple[str, float]:
    """The verdict and the similarity score of two transliterations of one locus.

    Args:
        text_raw_a: The first source's ``text_raw`` (ZL in the index).
        text_raw_b: The second source's ``text_raw`` (IT in the index).
        profile_name: The normalization profile both are read through.

    Returns:
        (verdict, similarity): one of ``VERDICTS``, and the ratio of the two first-reading word sequences joined by
        ``.`` (1.0 for equal sequences).
    """
    profile = get_profile(profile_name)
    a, b = parse_markup(text_raw_a), parse_markup(text_raw_b)
    first_a, first_b = words(profile.apply(a)), words(profile.apply(b))
    similarity = SequenceMatcher(None, ".".join(first_a), ".".join(first_b)).ratio()
    if text_raw_a == text_raw_b:
        return IDENTICAL, 1.0
    if first_a == first_b:
        return SAME_READING, similarity
    readings_a = {tuple(words(r)) for r in _readings(a.tokens, profile)}
    if any(tuple(words(r)) in readings_a for r in _readings(b.tokens, profile)):
        return ALTERNATE_READING, similarity
    return DIFFERENT, similarity


def alternates_in(markup: Markup) -> int:
    """How many alternates a locus text holds (top level)."""
    return sum(1 for token in markup.tokens if token.kind == mk.ALTERNATES)
