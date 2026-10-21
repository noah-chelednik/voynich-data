"""Reference statistics (roadmap item 2.10): the counts and entropies that published values are compared with.

Acceptance tests, not a statistics suite: `tests/test_reference_checks.py` compares each statistic below with a value
published in the literature (`data_sources/references.yaml`: the value, its source, the words it is quoted from, and the
tolerance argued for it). A statistic is computed from the committed build through `vcat.load`, as a user reads it:

- the words of a reading are the EVA tokenizer's (`vcat/words.py`): maximal runs between word spaces (`.`, `,`, space);
- a character is a glyph of a word; a high-ASCII code `@NNN;` is one character (one glyph the source names by number),
  and the apostrophe of a ligature's glyphs (`c'y`) is a character as written;
- word spaces are not characters, and character pairs are counted within words only, as the published tables count
  them ("In these figures, spaces have not been counted as characters", Zandbergen, `extra/sol_ent.html`);
- `h1` is the single-character entropy, in bits; `h2` is the conditional character entropy, the character pair entropy
  less `h1` (the published table's definition).

Nothing here interprets the text: the statistics are counts over a named profile's reading.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from vcat.api import DEFAULT_PROFILE, load
from vcat.words import split_words

#: A high-ASCII glyph code, one character
CODE = re.compile(r"@\d+;")


def characters(word: str) -> list[str]:
    """The characters of a word: each `@NNN;` code is one, every other character is one."""
    out: list[str] = []
    position = 0
    for code in CODE.finditer(word):
        out.extend(word[position : code.start()])
        out.append(code.group())
        position = code.end()
    out.extend(word[position:])
    return out


def entropy(counts: Counter[Any]) -> float:
    """The Shannon entropy, in bits, of a frequency distribution."""
    total = sum(counts.values())
    if total == 0:
        raise ValueError("no events: the entropy of an empty distribution is undefined")
    return -sum(n / total * math.log2(n / total) for n in counts.values() if n)


def words_of(readings: list[str]) -> list[str]:
    """Every word of the readings, in order."""
    return [word for reading in readings for word, _space in split_words(reading)]


def character_statistics(words: list[str]) -> dict[str, float]:
    """`characters` (how many), `h1` and `h2` (conditional) of the words' characters, pairs within words."""
    singles: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()
    for word in words:
        chars = characters(word)
        singles.update(chars)
        pairs.update(zip(chars, chars[1:], strict=False))
    h1 = entropy(singles)
    return {"characters": sum(singles.values()), "h1": h1, "h2": entropy(pairs) - h1}


def word_statistics(words: list[str]) -> dict[str, int]:
    """`tokens` (how many words) and `types` (how many distinct words)."""
    return {"tokens": len(words), "types": len(set(words))}


def statistics(
    source: str, profile: str = DEFAULT_PROFILE, output_dir: str | Path | None = None
) -> dict[str, float]:
    """Every reference statistic of one source's lines under one profile, read from the committed build."""
    lines = load(source=source, unit="line", profile=profile, output_dir=output_dir)
    words = words_of([line["reading"] for line in lines])
    return {**character_statistics(words), **word_statistics(words)}


def references_table(registry: dict[str, Any]) -> str:
    """The table of `docs/reference_checks.md`: every published value with its source, measure, tolerance and page."""
    pages = {p["id"]: p for p in registry["pages"]}
    lines = [
        "| Check | Source | Measure | Published value | Tolerance | Where |",
        "|---|---|---|---|---|---|",
    ]
    for r in registry["references"]:
        page = pages[r["page"]]
        tolerance = r["tolerance"]
        # every number as the registry holds it, never rounded (reach 7ea91938 gap 3)
        allowed = (
            f"{tolerance['relative']} of the value"
            if "relative" in tolerance
            else f"{tolerance['absolute']} bits"
        )
        value = f"{r['value']:,}" if isinstance(r["value"], int) else repr(r["value"])
        lines.append(
            f"| `{r['id']}` | {r['source']} | {r['measure']} | {value} | {allowed} | "
            f"[{page['title']}]({page['url']}), {r['where']} |"
        )
    return "\n".join(lines)
