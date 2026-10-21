"""The EVA tokenizer (roadmap item 2.6): the one rule that cuts a reading into words, used by the word dataset and by the
lines' `word_count`.

A word is a maximal run of characters between word spaces in a reading of the profile `analysis-v1` (`text_clean`, see
`vcat/profiles.py`). The word spaces are the reading's separators:

- `.` a certain space (IVTFF 2.0 Table 3), which `analysis-v1` also writes for `<->` and `<~>` (a drawing interrupts the
  text) and for the end of a wrapped line;
- `,` an uncertain space: the transliterator was not sure a space is there; it is a word boundary here, and the word
  before it records `space_after: uncertain`, so a reader who joins across uncertain spaces can (the profile
  `no-uncertain-spaces-v1` does);
- whitespace, which a profile reading does not contain, counts as a certain space for any other text.

Runs of separators are one boundary (certain if any of them is), so no word is empty; separators at the start or end of a
reading bound nothing. Everything else is part of a word, as written: glyphs, a high-ASCII code `@NNN;` (a word made only
of codes is a word), and the apostrophe of a ligature's glyphs (`c'y`). The tokenizer reads glyphs only as characters: it
does not decide what an EVA glyph is, nor split or join any word the reading does not separate.

    >>> split_words("fachys.ykal.ar,ataiin")
    [('fachys', 'certain'), ('ykal', 'certain'), ('ar', 'uncertain'), ('ataiin', None)]
    >>> split_words(".@192;chy..tol,")
    [('@192;chy', 'certain'), ('tol', None)]
"""

from __future__ import annotations

import re

#: The space a separator records: `.` and whitespace certain, `,` uncertain
CERTAIN = "certain"
UNCERTAIN = "uncertain"
_BOUNDARY = re.compile(r"[.,\s]+")


def split_words(reading: str) -> list[tuple[str, str | None]]:
    """Each word of a reading with the space after it: `certain`, `uncertain`, or None for the last word."""
    words: list[tuple[str, str | None]] = []
    position = 0
    for boundary in _BOUNDARY.finditer(reading):
        word = reading[position : boundary.start()]
        if word:
            words.append((word, CERTAIN if re.search(r"[.\s]", boundary.group()) else UNCERTAIN))
        position = boundary.end()
    if reading[position:]:
        words.append((reading[position:], None))
    if words and words[-1][1] is not None:
        words[-1] = (words[-1][0], None)
    return words


def word_count(reading: str) -> int:
    """How many words the reading holds."""
    return len(split_words(reading))
