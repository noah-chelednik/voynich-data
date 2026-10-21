# tests/regressions/47b59c81/test_finding_1.py
import contextlib
import io
import json

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from parsers import IVTFFParser, parse_markup
from validators.validate_phase1_outputs import validate_outputs
from validators.verify_invariants import verify_all_invariants


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_completed_wrap_crosses_a_slash_only_line(tmp_path, ending):
    prefix = ending.join(
        ["#=IVTFF Eva- 2.0 M 5", "<f1r>", "<f1r.1,@P0> "]
    )
    control = ending.join(["qokedy /", "/ /", "/ daiin"])
    control_pages = list(
        IVTFFParser(strict=True).parse_string(prefix + control + ending)
    )
    assert control_pages[0].loci[0].text == "qokedydaiin"

    unfinished = prefix + ending.join(["qokedy /", "/"]) + ending
    with pytest.raises(ValueError, match="file ends inside its wrap"):
        list(IVTFFParser(strict=True).parse_string(unfinished))

    raw = ending.join(["qokedy /", "/", "/ daiin"])
    markup = parse_markup(raw)
    assert markup.raw == raw
    assert not markup.problems
    assert markup.text == "qokedydaiin"

    content = prefix + raw + ending
    for strict in (False, True):
        parser = IVTFFParser(strict=strict)
        loci = [
            locus
            for page in parser.parse_string(content)
            for locus in page.loci
        ]
        assert not parser.warnings
        assert [locus.locus_id for locus in loci] == ["f1r:1"]
        assert loci[0].text_raw == raw
        assert loci[0].text == "qokedydaiin"

    source = tmp_path / "source.txt"
    source.write_bytes(content.encode("utf-8"))
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    assert not report.warnings
    assert not report.loss_problems()
    assert [record.line_id for record in records] == ["f1r:1"]

    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(
        json.dumps(report.to_dict()), encoding="utf-8"
    )
    with contextlib.redirect_stdout(io.StringIO()):
        valid, errors = validate_outputs(out)
        invariants = verify_all_invariants(out)
    assert valid, errors
    assert invariants.passed, invariants.failures
