# tests/regressions/cb967c21/test_finding_2.py
import json

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
<f1v>      <! $I=H $Q=A $P=B $L=A $H=1>
<f1v.1,@P0>       kchsy.chadaiin
"""


def test_invariants_accept_an_entirely_reported_page(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    jsonl = out / "eva_lines.jsonl"
    export_to_jsonl(records, jsonl)
    report_path = out / "eva_lines_build_report.json"
    payload = report.to_dict()
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert valid, errors
    control = verify_all_invariants(out)
    assert control.passed, control.failures

    kept = [record for record in records if record.page_id != "f1v"]
    reported = [record for record in records if record.page_id == "f1v"]
    assert kept and reported
    reported_pages = sorted({record.page_id for record in reported})

    payload.update(
        total_lines=len(kept),
        loci_emitted=len(kept),
        loci_reported=len(reported),
        reported_loci=[record.line_id for record in reported],
        pages_with_lines=len({record.page_id for record in kept}),
        pages_without_lines=len(reported_pages),
        page_ids_without_lines=reported_pages,
        total_characters=sum(record.char_count for record in kept),
        total_words=sum(record.word_count for record in kept),
        lines_with_high_ascii=sum(record.has_high_ascii for record in kept),
        lines_by_type={
            kind: sum(record.line_type == kind for record in kept)
            for kind in {record.line_type for record in kept}
        },
        warnings=[
            f"{record.line_id}: explicitly reported instead of emitted"
            for record in reported
        ],
    )
    export_to_jsonl(kept, jsonl)
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    valid, errors = validate_outputs(out)
    assert valid, errors

    result = verify_all_invariants(out)
    assert result.passed, result.failures
