# tests/regressions/26ba5c94/test_finding_1.py
import json

from builders import build_variants as builder


def test_report_records_the_source_order_used_for_alignment(tmp_path):
    original = json.loads(
        (builder.DIRECTORY / "transliterations_report.json").read_text(
            encoding="utf-8"
        )
    )
    order = original["source_order"]

    for source in order:
        name = f"{source.lower()}.jsonl"
        (tmp_path / name).write_bytes(
            (builder.DIRECTORY / name).read_bytes()
        )

    orders = [order, list(reversed(order))]
    reports = []
    frames = []

    for chosen_order in orders:
        (tmp_path / "transliterations_report.json").write_text(
            json.dumps({"source_order": chosen_order}),
            encoding="utf-8",
        )
        builder.build(tmp_path, parquet=False)
        reports.append(
            json.loads(
                (tmp_path / builder.REPORT).read_text(encoding="utf-8")
            )
        )
        alignments = [
            json.loads(line)
            for line in (tmp_path / builder.ALIGNMENTS)
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        frames.append(
            {row["line_id"]: row["frame_reader"] for row in alignments}
        )

    # Positive control: the consumed order changes a real fallback frame.
    assert frames[0] != frames[1]

    for chosen_order, report in zip(orders, reports, strict=True):
        assert report.get("source_order") == chosen_order
