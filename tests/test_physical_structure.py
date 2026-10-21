"""
The physical structure layer (roadmap item 2.5): the bifolia and the named page orders of the metadata datasets, checked
against the source's own page headers, and the validators' check of every metadata table (B-095).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from parsers import page_order_key
from parsers.metadata_parser import PAGE_ORDERS, predominant
from validators.validate_phase1_outputs import check_metadata
from vcat.sources import source_file

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "output" / "metadata"
ZL = ROOT / source_file("ZL")


def rows(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (META / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def zl_headers() -> list[tuple[str, dict[str, str]]]:
    """Each page header of ZL and its settings, read without the parser."""
    import re

    found = []
    for line in ZL.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^<([^<>.,\s]+)>\s*(?:<!([^<>]*)>)?", line)
        if match:
            settings = dict(re.findall(r"\$([A-Z])=(\S)", match.group(2) or ""))
            found.append((match.group(1), settings))
    return found


def test_every_sheet_is_the_pages_sharing_a_quire_and_a_bifolio_number():
    groups: dict[tuple[str, str], set[str]] = {}
    for page_id, settings in zl_headers():
        groups.setdefault((settings["Q"], settings["B"]), set()).add(page_id)
    folio_of = {r["page_id"]: r["folio_id"] for r in rows("pages")}
    bifolia = rows("bifolia")
    assert {(b["quire_id"][1:], str(b["bifolio_number"])) for b in bifolia} == set(groups)
    for b in bifolia:
        pages = groups[(b["quire_id"][1:], str(b["bifolio_number"]))]
        assert set(b["page_ids"]) == pages
        assert set(b["folio_ids"]) == {folio_of[p] for p in pages}
        assert b["is_complete"] == (len(b["folio_ids"]) == 2)
        assert b["page_ids"] == sorted(b["page_ids"], key=page_order_key)
    # every folio is on exactly one sheet
    leaves = [f for b in bifolia for f in b["folio_ids"]]
    assert sorted(leaves) == sorted({r["folio_id"] for r in rows("folios")})


def test_the_page_orders_are_the_sources_and_attributed():
    from parsers.metadata_parser import file_order
    from vcat.sources import cached_sources

    listed = [page_id for page_id, _ in zl_headers()]
    zl = next(s for s in cached_sources() if s.id == "ZL")
    name, who = file_order(zl.id, zl.name)
    expected = {
        name: (listed, who),
        "foliation": (sorted(listed, key=page_order_key), PAGE_ORDERS["foliation"]),
    }
    orders: dict[str, list[dict]] = {}
    for row in rows("page_orders"):
        orders.setdefault(row["order"], []).append(row)
    assert name == "zl_file" and set(orders) == set(expected)
    for order, ordered in orders.items():
        assert [r["position"] for r in ordered] == list(range(1, len(ordered) + 1))
        assert [r["page_id"] for r in ordered] == expected[order][0]
        assert {r["attribution"] for r in ordered} == {expected[order][1]}


@pytest.mark.parametrize("languages", [["A", "B"], ["B", "A", "A", "B"]])
def test_a_language_tie_chooses_none_and_says_so(languages: list[str]):
    """A tie never depends on a set's iteration order (B-091)."""
    value, note = predominant(languages)
    assert value is None and note and "A, B" in note
    assert predominant(["A", "B", "B"]) == ("B", None)
    assert predominant([]) == (None, None)


def test_the_validators_accept_the_committed_metadata():
    assert check_metadata(ROOT / "output") == []


@pytest.mark.parametrize(
    "tamper",
    ["parquet_row", "order_swap", "bifolio_leaf", "missing_parquet"],
)
def test_the_validators_refuse_a_changed_metadata_table(tmp_path: Path, tamper: str):
    """Each table's Parquet must hold exactly its JSONL's rows (B-095), and the structure must be the source's."""
    out = tmp_path / "output"
    shutil.copytree(META, out / "metadata")
    meta = out / "metadata"
    if tamper == "parquet_row":
        import pyarrow as pa
        import pyarrow.parquet as pq

        data = rows("pages")
        data[0]["hand"] = "9"
        pq.write_table(pa.Table.from_pylist(data), meta / "pages.parquet")
    elif tamper == "order_swap":
        data = rows("page_orders")
        data[0]["page_id"], data[1]["page_id"] = data[1]["page_id"], data[0]["page_id"]
        _write(meta, "page_orders", data)
    elif tamper == "bifolio_leaf":
        data = rows("bifolia")
        data[0]["folio_ids"] = data[0]["folio_ids"][:1]
        _write(meta, "bifolia", data)
    else:
        (meta / "quires.parquet").unlink()
    assert check_metadata(out)


def _write(meta: Path, name: str, data: list[dict]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    with open(meta / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    pq.write_table(pa.Table.from_pylist(data), meta / f"{name}.parquet")


def test_a_table_row_without_a_pipe_is_part_of_the_table():
    """GitHub Markdown runs a table to its next blank line or block, so the card check compares such a row (B-104)."""
    from tests.test_cards import whole_table

    rendered = "| a | b |\n|---|---|\n| 1 | 2 |"
    assert whole_table(rendered + "\nextra cell\n\n## Next", rendered) == rendered + "\nextra cell"
    assert whole_table(rendered + "\n## Next", rendered) == rendered
