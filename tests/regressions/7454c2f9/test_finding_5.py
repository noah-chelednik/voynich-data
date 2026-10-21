# tests/regressions/7454c2f9/test_finding_5.py
import copy
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from validators.validate_phase1_outputs import check_metadata


def test_metadata_rejects_a_folio_outside_its_population(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    output = root / "output"
    meta = output / "metadata"
    assert check_metadata(output) == []

    folios = [
        json.loads(line)
        for line in (meta / "folios.jsonl").read_text().splitlines()
    ]
    extra = copy.deepcopy(folios[0])
    number = max(row["folio_number"] for row in folios) + 1
    extra.update(
        folio_id=f"f{number}",
        folio_number=number,
        recto_page_id=None,
        recto_page_ids=[],
        verso_page_ids=[],
        total_lines=0,
    )
    assert extra["folio_id"] not in {row["folio_id"] for row in folios}
    folios.append(extra)

    report = json.loads((meta / "metadata_report.json").read_text())
    report["total_folios"] = len(folios)
    texts = {
        (meta / "folios.jsonl").resolve():
            "".join(json.dumps(row) + "\n" for row in folios),
        (meta / "metadata_report.json").resolve(): json.dumps(report),
    }
    original_read = Path.read_text
    original_table = pq.read_table

    def read(path, *args, **kwargs):
        if path.resolve() in texts:
            return texts[path.resolve()]
        return original_read(path, *args, **kwargs)

    def table(path, *args, **kwargs):
        if Path(path).resolve() == (meta / "folios.parquet").resolve():
            return pa.Table.from_pylist(folios)
        return original_table(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(pq, "read_table", table)
    assert check_metadata(output), "Invented folio passed metadata validation"
