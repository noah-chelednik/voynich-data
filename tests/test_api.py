"""
The minimal Python API (roadmap item 2.9): `vcat.load(source=, unit=, profile=)` returns the committed build's rows, read
under the profile and cut by the EVA tokenizer, and refuses what it does not know.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import vcat
from vcat.profiles import apply_profile
from vcat.words import split_words

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
ORDER = json.loads((OUTPUT / "transliterations" / "transliterations_report.json").read_text())[
    "source_order"
]


def rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_load_is_exported_from_the_package():
    assert vcat.load is vcat.api.load and "load" in vcat.__all__


def test_the_default_is_zl_s_lines_under_the_analysis_profile():
    lines = vcat.load()
    committed = rows(OUTPUT / "eva_lines.jsonl")
    # every committed field unchanged, and the reading beside them (no field replaced: EVA rows have their own `text`)
    assert [{k: v for k, v in r.items() if k != "reading"} for r in lines] == committed
    assert all(r["reading"] == r["text_clean"] for r in lines)


def test_zl_s_words_under_the_analysis_profile_are_the_word_level():
    assert vcat.load(unit="word") == rows(OUTPUT / "eva_words.jsonl")


def test_the_page_unit_is_the_metadata_s_pages_and_zl_s_only():
    assert vcat.load(unit="page") == rows(OUTPUT / "metadata" / "pages.jsonl")
    with pytest.raises(ValueError, match="ZL"):
        vcat.load(source="IT", unit="page")


@pytest.mark.parametrize("source", ORDER)
@pytest.mark.parametrize("profile", ["raw-v1", "analysis-v1"])
def test_every_source_s_lines_and_words_under_a_profile(source, profile):
    path = (
        OUTPUT / "eva_lines.jsonl"
        if source == "ZL"
        else OUTPUT / "transliterations" / f"{source.lower()}.jsonl"
    )
    committed = rows(path)
    lines = vcat.load(source=source, unit="line", profile=profile)
    assert len(lines) == len(committed)
    assert [r["reading"] for r in lines] == [
        apply_profile(profile, r["text_raw"], r.get("alphabet", "EVA")) for r in committed
    ]
    assert [{k: v for k, v in r.items() if k != "reading"} for r in lines] == committed
    words = vcat.load(source=source, unit="word", profile=profile)
    if source == "ZL" and profile == "analysis-v1":
        # the word level itself (reach d4385eb4 gap 1: this branch asserted nothing)
        assert words == rows(OUTPUT / "eva_words.jsonl")
        return
    expected = [
        (r["line_id"], r.get("transcriber"), i, w, s)
        for r in committed
        for i, (w, s) in enumerate(
            split_words(apply_profile(profile, r["text_raw"], r.get("alphabet", "EVA"))), start=1
        )
    ]
    assert [
        (w["line_id"], w["transcriber"], w["word_index"], w["word"], w["space_after"])
        for w in words
    ] == expected
    assert all(w["source"] == source for w in words)
    assert len({w["word_id"] for w in words}) == len(words)


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"source": "XX"}, "unknown source"),
        ({"unit": "glyph"}, "unknown unit"),
        ({"profile": "nope"}, "unknown profile"),
    ],
)
def test_unknown_names_are_refused(arguments, message):
    with pytest.raises(ValueError, match=message):
        vcat.load(**arguments)


def test_load_reads_another_build(tmp_path):
    """`output_dir` points at another build: what it holds is what is read."""
    (tmp_path / "transliterations").mkdir()
    (tmp_path / "transliterations" / "transliterations_report.json").write_text(
        json.dumps({"source_order": ["ZL"]})
    )
    line = rows(OUTPUT / "eva_lines.jsonl")[0]
    (tmp_path / "eva_lines.jsonl").write_text(json.dumps(line) + "\n")
    assert [r["line_id"] for r in vcat.load(output_dir=tmp_path)] == [line["line_id"]]
    with pytest.raises(ValueError, match="unknown source"):
        vcat.load(source="IT", output_dir=tmp_path)


def _glyph_characters(text_raw: str) -> str:
    """The characters of a text's glyph and ligature tokens, read from the markup itself (no profile)."""
    from parsers import ivtff_markup as mk

    return "".join(
        token.raw if token.kind == mk.GLYPHS else str(token.value)
        for token in mk.parse_markup(text_raw).tokens
        if token.kind in (mk.GLYPHS, mk.LIGATURE)
    )


@pytest.mark.parametrize("source", [s for s in ORDER if s != "ZL"])
def test_a_non_eva_reading_keeps_the_characters_eva_reads_as_markers(source):
    """'!' and '*' are EVA's legacy illegibility markers, dropped from an EVA reading; in another alphabet they are the
    transliteration's own characters (v101 writes '*' as a glyph) and every one written in a glyph is kept (B-053).
    """
    committed = rows(OUTPUT / "transliterations" / f"{source.lower()}.jsonl")
    lines = vcat.load(source=source, unit="line", profile="analysis-v1")
    for marker in "!*":
        written = [_glyph_characters(r["text_raw"]).count(marker) for r in committed]
        if committed[0].get("alphabet") == "EVA":
            assert all(r["reading"].count(marker) == 0 for r in lines), source
        else:
            assert [r["reading"].count(marker) for r in lines] == written, (source, marker)
