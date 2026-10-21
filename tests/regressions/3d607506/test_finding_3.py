# tests/regressions/3d607506/test_finding_3.py
import hashlib
import json

from builders import build_variants as builder


def test_report_hashes_the_bytes_used_for_the_reading(tmp_path, monkeypatch):
    row = json.loads(
        (builder.DIRECTORY / "zl.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    source_id = row["source"]
    source_path = tmp_path / f"{source_id.lower()}.jsonl"
    consumed = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
    replacement = dict(row, text_raw=row["text_raw"] + ".qokedy")
    replaced = (
        json.dumps(replacement, ensure_ascii=False) + "\n"
    ).encode("utf-8")

    source_path.write_bytes(consumed)
    (tmp_path / "transliterations_report.json").write_text(
        json.dumps({"source_order": [source_id]}),
        encoding="utf-8",
    )
    original_variant_tables = builder.vv.variant_tables

    def replace_after_consumption(rows, order):
        result = original_variant_tables(rows, order)
        source_path.write_bytes(replaced)
        return result

    monkeypatch.setattr(
        builder.vv, "variant_tables", replace_after_consumption
    )
    report = builder.build(tmp_path, parquet=False)

    emitted = json.loads(
        (tmp_path / builder.LOCI).read_text(encoding="utf-8").splitlines()[0]
    )
    assert emitted["readings"][0]["words"] == builder.vv.reading_words(
        row["text_raw"]
    )
    assert source_path.read_bytes() == replaced
    assert report["inputs"][source_id]["sha256"] == hashlib.sha256(
        consumed
    ).hexdigest()
