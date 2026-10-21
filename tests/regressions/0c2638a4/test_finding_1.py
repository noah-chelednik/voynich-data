# tests/regressions/0c2638a4/test_finding_1.py
import json
from dataclasses import replace

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants
from vcat.loss_accounting import census_source


SOURCE = """#=IVTFF Eva- 2.0 M 5
<f1r>      <! $I=H $Q=A $P=A $L=A $H=1>
<f1r.1,@P0>       fachys.ykal
<f1r.2,+P0>       sory.ckhar
"""


def test_phase_rejects_locus_fields_with_a_stale_line_id(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(SOURCE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    records, report = build_eva_lines(source, out)
    jsonl = out / "eva_lines.jsonl"
    export_to_jsonl(records, jsonl)
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )

    valid, errors = validate_outputs(out)
    assert valid, errors
    control = verify_all_invariants(out)
    assert control.passed, control.failures

    replacement = replace(
        records[-1],
        line_number=max(record.line_number for record in records) + 1,
    )
    source_ids = set(census_source(source).loci)
    assert replacement.line_id in source_ids
    assert (
        f"{replacement.page_id}:{replacement.line_number}"
        not in source_ids
    )
    export_to_jsonl(records[:-1] + [replacement], jsonl)

    invariant_result = verify_all_invariants(out)
    assert not invariant_result.passed, invariant_result.failures

    valid, errors = validate_outputs(out)
    assert not valid, f"Accepted nonexistent locus behind stale line_id: {errors}"
