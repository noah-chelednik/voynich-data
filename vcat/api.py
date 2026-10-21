"""The minimal Python API (roadmap item 2.9): `vcat.load(source=, unit=, profile=)`.

    >>> import vcat
    >>> lines = vcat.load()                                   # ZL's lines, read under analysis-v1
    >>> words = vcat.load(source="IT", unit="word")           # IT's words, cut by the EVA tokenizer
    >>> raw = vcat.load(source="LSI", unit="line", profile="raw-v1")

It reads the committed build (`output/`, or `output_dir`), never the network, and returns plain rows (a list of dicts):

- `source`: a cached source's id (`ZL`, `IT`, `IT2a`, `CD`, `FG`, `GC`, `RF1b`, `VT`, `LSI`; `data_sources/sources.yaml`).
- `unit`: `line` (one row per locus, or per transcriber's reading in an interlinear source), `word` (one row per word) or
  `page` (the metadata's page rows; ZL only, the source the metadata is built from).
- `profile`: a normalization profile (`vcat/profiles.py`, `raw-v1`, `diplomatic-v1`, `analysis-v1`, ...): a line row gains
  `reading`, its `text_raw` under the profile (a new field: no row field is replaced); words are cut from that reading by the EVA tokenizer (`vcat/words.py`).

ZL's lines are the EVA dataset's rows (`eva_lines.jsonl`); ZL's words under `analysis-v1` are its word level
(`eva_words.jsonl`, with positions and joined fields). Every other source's lines are its rows in the transliterations
dataset, and its words are cut here: `word_id`, `line_id`, `page_id`, `source`, `transcriber`, `word_index`, `word`,
`space_after`. The reading of a non-EVA source keeps its own alphabet: no profile maps one alphabet to another.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vcat.profiles import PROFILES, apply_profile, get_profile
from vcat.words import split_words

ROOT = Path(__file__).resolve().parent.parent
#: The units `load` serves
UNITS = ("line", "word", "page")
#: The profile `load` reads under unless told otherwise
DEFAULT_PROFILE = "analysis-v1"


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _sources(output: Path) -> list[str]:
    report = json.loads(
        (output / "transliterations" / "transliterations_report.json").read_text(encoding="utf-8")
    )
    return list(report["source_order"])


def load(
    source: str = "ZL",
    unit: str = "line",
    profile: str = DEFAULT_PROFILE,
    output_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """The rows of one source at one unit, read under one profile (module docstring). An unknown source, unit or profile
    is a ValueError naming what is known."""
    output = Path(output_dir) if output_dir is not None else ROOT / "output"
    known = _sources(output)
    if source not in known:
        raise ValueError(f"unknown source {source!r}; known: {', '.join(known)}")
    if unit not in UNITS:
        raise ValueError(f"unknown unit {unit!r}; known: {', '.join(UNITS)}")
    try:
        get_profile(profile)
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"unknown profile {profile!r}; known: {', '.join(sorted(PROFILES))}"
        ) from error
    if unit == "page":
        if source != "ZL":
            raise ValueError("the page unit is ZL's: the metadata is built from ZL")
        return _rows(output / "metadata" / "pages.jsonl")
    if source == "ZL":
        lines = _rows(output / "eva_lines.jsonl")
        # the word level is analysis-v1's words exactly: a later analysis version (or the bare family name, which
        # resolves to the newest version) is cut from its own reading below (review 4c664493 finding 1)
        if unit == "word" and get_profile(profile).id == DEFAULT_PROFILE:
            return _rows(output / "eva_words.jsonl")
    else:
        lines = _rows(output / "transliterations" / f"{source.lower()}.jsonl")
    for line in lines:
        # in the source's own alphabet: EVA's legacy markers '!' and '*' are dropped only from EVA (B-053)
        line["reading"] = apply_profile(
            profile, line["text_raw"], str(line.get("alphabet") or "EVA")
        )
    if unit == "line":
        return lines
    words: list[dict[str, Any]] = []
    for line in lines:
        for index, (word, space) in enumerate(split_words(line["reading"]), start=1):
            reader = f".{line['transcriber']}" if line.get("transcriber") else ""
            words.append(
                {
                    "word_id": f"{line['line_id']}{reader}.{index}",
                    "line_id": line["line_id"],
                    "page_id": line["page_id"],
                    "source": source,
                    "transcriber": line.get("transcriber"),
                    "word_index": index,
                    "word": word,
                    "space_after": space,
                }
            )
    return words
