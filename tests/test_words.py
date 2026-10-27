"""
The word level of the EVA dataset (roadmap item 2.6): the one EVA tokenizer (`vcat/words.py`), the word rows built from the
committed lines (`builders/build_eva_words.py`, `output/eva_words.jsonl`), their positions in the line and in the source's
paragraphs, the joined line fields, and both validators' refusals.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from builders import build_eva_words as bw
from vcat.words import split_words, word_count

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
LINES = [
    json.loads(x) for x in (OUTPUT / "eva_lines.jsonl").read_text(encoding="utf-8").splitlines()
]
WORDS = [
    json.loads(x) for x in (OUTPUT / "eva_words.jsonl").read_text(encoding="utf-8").splitlines()
]


def assert_same_rows(got: list[dict], want: list[dict], what: str) -> None:
    """Compare first, then assert on the result, so a failure names the first differing row instead of making pytest
    diff some 39,000 rows (under `pytest -v` that diff ran for hours in CI)."""
    if got == want:
        return
    first = next(
        (i for i, (a, b) in enumerate(zip(got, want, strict=False)) if a != b),
        min(len(got), len(want)),
    )
    message = f"{what}: {len(got)} rows, expected {len(want)}; first difference at row {first}"
    raise AssertionError(message)


@pytest.mark.parametrize(
    ("reading", "expected"),
    [
        ("fachys.ykal", [("fachys", "certain"), ("ykal", None)]),
        ("or,y", [("or", "uncertain"), ("y", None)]),
        ("a.,b", [("a", "certain"), ("b", None)]),
        (",,a,,", [("a", None)]),
        ("@192;chy.@130;", [("@192;chy", "certain"), ("@130;", None)]),
        ("c'y.daiin", [("c'y", "certain"), ("daiin", None)]),
        ("a b", [("a", "certain"), ("b", None)]),
        ("", []),
        ("...", []),
    ],
)
def test_the_tokenizer_cuts_at_word_spaces(reading, expected):
    assert split_words(reading) == expected
    assert word_count(reading) == len(expected)


def test_one_tokenizer_counts_every_line():
    """The lines' `word_count` (vcat/eva_charset.py) is the tokenizer's count of their `text_clean`."""
    from vcat.eva_charset import validate_eva_text

    for line in LINES:
        assert word_count(line["text_clean"]) == line["word_count"], line["line_id"]
    # every line, not a prefix (reach 71660867 gap 1)
    for line in LINES:
        assert validate_eva_text(line["text_raw"]).word_count == line["word_count"], line["line_id"]


def test_the_committed_words_are_the_build_of_the_committed_lines(tmp_path):
    shutil.copy2(OUTPUT / "eva_lines.jsonl", tmp_path / "eva_lines.jsonl")
    report = bw.build(tmp_path)
    for name in ("eva_words.jsonl", "eva_words_report.json"):
        assert (tmp_path / name).read_bytes() == (OUTPUT / name).read_bytes(), name
    assert_same_rows(
        pq.read_table(OUTPUT / "eva_words.parquet").to_pylist(), WORDS, "committed Parquet"
    )
    # the fresh build's Parquet too, not only the committed one (reach 71660867 gap 2)
    assert_same_rows(
        pq.read_table(tmp_path / "eva_words.parquet").to_pylist(), WORDS, "fresh Parquet"
    )
    assert report["total_words"] == len(WORDS) == sum(line["word_count"] for line in LINES)


def test_every_row_has_the_fields_in_order_and_meets_the_schema():
    from validators.schema import validate_against_schema

    assert all(list(bw.word_rows(LINES[:1])[0]) == list(bw.WORD_FIELDS) for _ in [0])
    assert all(set(row) == set(bw.WORD_FIELDS) for row in WORDS)
    valid, problems = validate_against_schema(WORDS, "eva_words.schema.json")
    assert valid, problems[:5]
    schema = json.loads((ROOT / "schemas" / "eva_words.schema.json").read_text())
    assert list(schema["properties"]) == list(bw.WORD_FIELDS)


def test_a_line_s_words_rebuild_its_reading():
    """Joined with the spaces they record, a line's words give its `text_clean` with each run of separators as one."""
    by_line: dict[str, list[dict]] = {}
    for row in WORDS:
        by_line.setdefault(row["line_id"], []).append(row)
    for line in LINES:
        rows = by_line.get(line["line_id"], [])
        assert [r["word_index"] for r in rows] == list(range(1, len(rows) + 1))
        joined = "".join(
            r["word"] + {"certain": ".", "uncertain": ",", None: ""}[r["space_after"]] for r in rows
        )
        normal = re.sub(
            r"[.,\s]+", lambda m: "." if re.search(r"[.\s]", m.group()) else ",", line["text_clean"]
        )
        assert joined == normal.strip(".,"), line["line_id"]
        if rows:
            assert rows[0]["line_initial"] and rows[-1]["line_final"]
            assert sum(r["line_initial"] for r in rows) == sum(r["line_final"] for r in rows) == 1


def membership(lines: list[dict]) -> dict[str, tuple[str | None, int | None]]:
    """Each line's paragraph and position in it, read here from the source's marks: a `P` line with `<%>` opens one, the
    `P` line with `<$>` closes it, on one page."""
    found: dict[str, tuple[str | None, int | None]] = {}
    page, number, position, inside = None, 0, 0, False
    for line in lines:
        if line["page_id"] != page:
            page, number, position, inside = line["page_id"], 0, 0, False
        text = line["locus_type"][1] == "P"
        if text and "<%>" in line["markers"]:
            number, position, inside = number + 1, 0, True
        if text and inside:
            position += 1
            found[line["line_id"]] = (f"{page}.p{number}", position)
        else:
            found[line["line_id"]] = (None, None)
        if text and inside and "<$>" in line["markers"]:
            inside = False
    return found


def test_every_word_is_in_its_line_s_paragraph():
    """The whole membership, line by line, from the marks: a line left out of its paragraph (and the positions closed up
    after it) is found (reach 71660867 gap 3)."""
    expected = membership(LINES)
    for row in WORDS:
        assert (row["paragraph_id"], row["line_in_paragraph"]) == expected[row["line_id"]], row[
            "word_id"
        ]


def test_paragraphs_are_the_source_s_marks():
    expected = membership(LINES)
    for row in WORDS:
        assert (row["paragraph_id"], row["line_in_paragraph"]) == expected[row["line_id"]], row[
            "word_id"
        ]
    lines = {line["line_id"]: line for line in LINES}
    paragraphs: dict[str, list[dict]] = {}
    for row in WORDS:
        if row["paragraph_id"]:
            paragraphs.setdefault(row["paragraph_id"], []).append(row)
    assert len(paragraphs) == sum("<%>" in line["markers"] for line in LINES)
    for paragraph_id, rows in paragraphs.items():
        assert paragraph_id.startswith(rows[0]["page_id"] + ".p")
        assert (
            sum(r["paragraph_initial"] for r in rows)
            == sum(r["paragraph_final"] for r in rows)
            == 1
        )
        assert rows[0]["paragraph_initial"] and rows[-1]["paragraph_final"]
        assert "<%>" in lines[rows[0]["line_id"]]["markers"]
        assert "<$>" in lines[rows[-1]["line_id"]]["markers"]
        positions = sorted({r["line_in_paragraph"] for r in rows})
        assert positions == list(range(1, len(positions) + 1))
        assert all(lines[r["line_id"]]["locus_type"][1] == "P" for r in rows)
    for row in WORDS:
        if row["paragraph_id"] is None:
            assert row["line_in_paragraph"] is None
            assert not row["paragraph_initial"] and not row["paragraph_final"]


def test_labels_and_unmarked_lines_are_in_no_paragraph():
    assert all(row["paragraph_id"] is None for row in WORDS if row["line_type"] != "paragraph")
    unmarked = {"f68r1:5", "f84v:42"}
    assert all(row["paragraph_id"] is None for row in WORDS if row["line_id"] in unmarked)


def test_each_word_carries_its_line_s_fields():
    lines = {line["line_id"]: line for line in LINES}
    for row in WORDS:
        line = lines[row["line_id"]]
        for name in (
            "page_id",
            "line_index",
            "line_type",
            "locus_type",
            "hand",
            "currier_language",
            "section",
            "quire",
        ):
            assert row[name] == line[name], (row["word_id"], name)
    assert len({row["word_id"] for row in WORDS}) == len(WORDS)


def candidate(tmp_path: Path) -> Path:
    out = tmp_path / "candidate"
    out.mkdir()
    for name in ("eva_lines.jsonl", "eva_lines_build_report.json", "eva_words_report.json"):
        shutil.copy2(OUTPUT / name, out / name)
    return out


def write_words(out: Path, rows: list[dict]) -> None:
    (out / "eva_words.jsonl").write_text(
        "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for r in rows
        ),
        encoding="utf-8",
    )
    pq.write_table(pa.Table.from_pylist(rows), out / "eva_words.parquet")


def change_word(rows):
    rows[0]["word"] = "x" + rows[0]["word"]
    return rows


def change_space(rows):
    rows[0]["space_after"] = "uncertain" if rows[0]["space_after"] == "certain" else "certain"
    return rows


def drop_row(rows):
    return rows[1:]


def float_index(rows):
    for row in rows:
        row["word_index"] = float(row["word_index"])
    return rows


def move_paragraph_start(rows):
    first = next(i for i, r in enumerate(rows) if r["paragraph_initial"])
    rows[first]["paragraph_initial"], rows[first + 1]["paragraph_initial"] = False, True
    return rows


def change_hand(rows):
    rows[0]["hand"] = "9"
    return rows


@pytest.mark.parametrize(
    "tamper",
    [change_word, change_space, drop_row, float_index, move_paragraph_start, change_hand],
    ids=lambda f: f.__name__,
)
@pytest.mark.parametrize("validator", ["phase", "invariants"])
def test_both_validators_refuse_changed_words(tmp_path, tamper, validator):
    from validators import validate_phase1_outputs as phase
    from validators import verify_invariants as invariants

    out = candidate(tmp_path)

    def problems():
        # through the public entry point, not the helper (reach 71660867 gap 5)
        if validator == "phase":
            return phase.validate_outputs(out)[1]
        return [
            f
            for f in invariants.verify_all_invariants(out).failures
            if "WORDS" in str(f) or "eva_words" in str(f)
        ]

    write_words(out, copy.deepcopy(WORDS))
    assert not problems()
    write_words(out, tamper(copy.deepcopy(WORDS)))
    assert problems()


def test_the_validators_refuse_a_report_of_other_lines(tmp_path):
    from validators.validate_phase1_outputs import check_words

    out = candidate(tmp_path)
    write_words(out, copy.deepcopy(WORDS))
    path = out / "eva_words_report.json"
    report = json.loads(path.read_text())
    report["lines_sha256"] = "0" * 64
    path.write_text(json.dumps(report), encoding="utf-8")
    assert any("lines_sha256" in p for p in check_words(out))
