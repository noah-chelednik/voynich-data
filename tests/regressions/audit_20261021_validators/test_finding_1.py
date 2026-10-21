# tests/regressions/audit_20261021_validators/test_finding_1.py
"""Audit 20261021-validators finding 1: both validators accept the metadata folios' and pages' physical fields erased.

`check_metadata` ties a page's folio, lines, labels, section and header fields, and a folio's lines and section, to the
source; nothing ties a folio's `recto_page_ids`, `verso_page_ids` and `recto_page_id`, or a page's `side`,
`folio_number` and panel fields, to anything. Every folio's page lists erased and every page's side, folio number and
panel fields falsified (Parquet beside JSONL, so the Parquet parity check holds) passes both validators.
"""
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from validators.validate_phase1_outputs import check_metadata, validate_outputs
from validators.verify_invariants import verify_all_invariants

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output"
READ_TEXT = Path.read_text
READ_TABLE = pq.read_table


def rows(path):
    return [json.loads(line) for line in READ_TEXT(path, encoding="utf-8").splitlines() if line.strip()]


@contextlib.contextmanager
def candidate(tables):
    def text(path, *args, **kwargs):
        p = Path(path).resolve()
        if p.parent == OUT / "metadata" and p.suffix == ".jsonl" and p.stem in tables:
            return "".join(json.dumps(r) + "\n" for r in tables[p.stem])
        return READ_TEXT(path, *args, **kwargs)

    def table(path, *args, **kwargs):
        p = Path(path).resolve()
        if p.parent == OUT / "metadata" and p.stem in tables:
            return pa.Table.from_pylist(tables[p.stem])
        return READ_TABLE(path, *args, **kwargs)

    with patch.object(Path, "read_text", text), patch.object(pq, "read_table", table):
        yield


def test_both_validators_refuse_erased_folio_page_lists_and_false_page_sides():
    assert check_metadata(OUT) == []
    folios = rows(OUT / "metadata/folios.jsonl")
    pages = rows(OUT / "metadata/pages.jsonl")
    assert any(f["recto_page_ids"] or f["verso_page_ids"] for f in folios)
    for row in folios:
        row.update(recto_page_id=None, recto_page_ids=[], verso_page_ids=[])
    for row in pages:
        row.update(
            side="verso" if row["side"] == "recto" else "recto",
            folio_number=row["folio_number"] + 1,
            is_foldout_panel=not row["is_foldout_panel"],
            panel_number=7,
            total_panels=1,
        )
    with candidate({"folios": folios, "pages": pages}):
        metadata_errors = check_metadata(OUT)
        with contextlib.redirect_stdout(io.StringIO()):
            phase, _ = validate_outputs(OUT)
            invariant = verify_all_invariants(OUT).passed
    assert metadata_errors and (phase, invariant) == (False, False), (metadata_errors, phase, invariant)
