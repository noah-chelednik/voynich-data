# tests/regressions/cbb8806f/test_finding_1.py
"""Claim 6 and the loss accounting (B-113, review 8f69a2eb finding 1's fix): check_loss_accounting now passes as emitted
pages only the parser's accepted page headers whose id the build holds, so an id the build holds that the source has no
header for never reaches `account` and is never an unexpected page. A build report that lists an invented page `f9r`
among its pages without lines (its page totals raised to match) was refused by both validators before cbb8806f (review
ce645765 finding 3, whose committed proof now fails) and is accepted by both at cbb8806f."""
import json

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import check_loss_accounting, validate_outputs
from validators.verify_invariants import verify_all_invariants

SOURCE = (
    "#=IVTFF Eva- 2.0 M 5\n"
    "<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>\n"
    "<f1r.1,@P0>       fachys.ykal\n"
    "<f1r.2,+P0>       sory.ckhar\n"
    "<f1v>      <! $I=H $Q=A $P=B $L=A $H=1>\n"
)


def test_an_invented_page_without_lines_is_refused_by_both_validators(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    payload = report.to_dict()
    report_path = out / "eva_lines_build_report.json"
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    valid, errors = validate_outputs(out)
    assert valid, errors  # the faithful build passes
    assert verify_all_invariants(out).passed

    # the source has no page f9r: list it as a page without lines, the page totals raised to match
    payload["page_ids_without_lines"].append("f9r")
    for name in ("pages_without_lines", "total_pages", "total_pages_in_source"):
        payload[name] += 1
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    accounting = check_loss_accounting([r.to_dict() for r in records], payload)
    assert any("f9r" in e for e in accounting), accounting
    assert validate_outputs(out)[0] is False
    assert verify_all_invariants(out).passed is False
