"""
Output validation (roadmap item 1.5).

Each validator is first shown to ACCEPT a consistent build of a synthetic source (the positive
control), then to reject one specific defect. The committed rows are validated against their schema.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from validators.schema import validate_transcription_lines

OUTPUT = Path(__file__).resolve().parent.parent / "output"


def write_build(base: Path, text: str) -> Path:
    """Build `text` the way the builder's command line does, into base/out."""
    base.mkdir(parents=True, exist_ok=True)
    source = base / "source.txt"
    source.write_text(text, encoding="utf-8")
    out = base / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(json.dumps(report.to_dict()))
    return out


def rows(out: Path) -> list[dict]:
    return [json.loads(line) for line in (out / "eva_lines.jsonl").read_text().splitlines()]


def rewrite_rows(out: Path, new_rows: list[dict]) -> None:
    (out / "eva_lines.jsonl").write_text("".join(json.dumps(r) + "\n" for r in new_rows))


def rewrite_report(out: Path, **changes) -> None:
    path = out / "eva_lines_build_report.json"
    report = json.loads(path.read_text())
    report.update(changes)
    path.write_text(json.dumps(report))


def validate(out: Path) -> tuple[bool, list[str]]:
    with contextlib.redirect_stdout(io.StringIO()):
        return phase.validate_outputs(out)


def test_validate_outputs_accepts_consistent_build(tmp_path: Path, synthetic_accounted: str):
    out = write_build(tmp_path, synthetic_accounted)
    valid, errors = validate(out)
    assert valid, errors


def test_validate_outputs_rejects_unaccounted_loci(
    tmp_path: Path, synthetic_accounted: str, synthetic_lossy: str
):
    lossy = write_build(tmp_path / "lossy", synthetic_lossy)
    valid, errors = validate(lossy)
    assert not valid
    assert any("f1v:2" in e for e in errors), errors

    # A report with no accounting at all is rejected even when the rows are complete.
    out = write_build(tmp_path / "ok", synthetic_accounted)
    path = out / "eva_lines_build_report.json"
    report = json.loads(path.read_text())
    del report["unaccounted_loci"]
    path.write_text(json.dumps(report))
    valid, errors = validate(out)
    assert not valid
    assert any("unaccounted_loci" in e for e in errors), errors


def test_validate_outputs_rejects_empty_and_mismatched_rows(
    tmp_path: Path, synthetic_accounted: str
):
    out = write_build(tmp_path, synthetic_accounted)
    original = rows(out)

    rewrite_rows(out, [])
    assert not validate(out)[0]

    rewrite_rows(out, original[:-1])
    valid, errors = validate(out)
    assert not valid
    assert any("total_lines" in e for e in errors), errors


def test_validate_outputs_rejects_schema_invalid_row(tmp_path: Path, synthetic_accounted: str):
    out = write_build(tmp_path, synthetic_accounted)
    bad = rows(out)
    bad[0]["line_type"] = "INVALID"
    rewrite_rows(out, bad)
    valid, errors = validate(out)
    assert not valid
    assert any("schema" in e.lower() for e in errors), errors


def test_check_build_report_rejects_failures(tmp_path: Path, synthetic_accounted: str):
    """Both validators accept the consistent build and reject each failing report (reach b09d5b4b gap 9: through
    their entry points, not only the shared check)."""
    out = write_build(tmp_path, synthetic_accounted)
    path = out / "eva_lines_build_report.json"
    assert phase.check_build_report(path) == []
    assert validate(out)[0]
    assert inv.verify_all_invariants(out).passed

    for change in (
        {"errors": ["failed build"]},
        {"source_verified": False},
        {"total_lines": -1},
        {"total_lines": "3"},
        {"source_hash": "0" * 64},
        {"source_file": str(tmp_path / "nowhere" / "absent.txt")},
    ):
        original = path.read_text()
        rewrite_report(out, **change)
        assert phase.check_build_report(path), change
        assert not validate(out)[0], change
        assert not inv.verify_all_invariants(out).passed, change
        path.write_text(original)

    # The source's bytes changed after the build: the recorded hash no longer matches.
    (tmp_path / "source.txt").write_text(synthetic_accounted + "# edited\n", encoding="utf-8")
    assert phase.check_build_report(path)


def test_checkers_reject_replaced_text_clean(tmp_path: Path, synthetic_accounted: str):
    out = write_build(tmp_path, synthetic_accounted)
    assert inv.verify_all_invariants(out).passed
    rewrite_rows(out, [dict(r, text_clean="a") for r in rows(out)])
    report = inv.verify_all_invariants(out)
    assert not report.passed
    assert "TEXT_CLEAN_CORRESPONDS" in {f["invariant"] for f in report.failures}
    valid, errors = validate(out)
    assert not valid
    assert any("text_clean" in e for e in errors), errors


def test_invariants_follow_the_source(
    tmp_path: Path, synthetic_accounted: str, synthetic_lossy: str
):
    out = write_build(tmp_path / "ok", synthetic_accounted)
    report = inv.verify_all_invariants(out)
    assert report.passed, report.failures

    lossy = write_build(tmp_path / "lossy", synthetic_lossy)
    report = inv.verify_all_invariants(lossy)
    assert not report.passed
    assert "RECORD_COUNT" in {f["invariant"] for f in report.failures}


def test_committed_eva_rows_conform_to_schema():
    committed = rows(OUTPUT)
    assert committed
    valid, errors = validate_transcription_lines(committed)
    assert valid, errors[:5]


def test_validate_outputs_rejects_report_totals_that_disagree(
    tmp_path: Path, synthetic_accounted: str
):
    """Every total the report records is reconciled with the rows and the recount."""
    out = write_build(tmp_path, synthetic_accounted)
    path = out / "eva_lines_build_report.json"
    assert validate(out)[0]
    report = json.loads(path.read_text())
    for name in (
        "loci_emitted",
        "loci_reported",
        "source_loci",
        "source_page_headers",
        "total_pages",
        "total_pages_in_source",
        "pages_without_lines",
    ):
        original = path.read_text()
        rewrite_report(out, **{name: report[name] + 1})
        valid, errors = validate(out)
        assert not valid, name
        assert any(name in e for e in errors), (name, errors)
        path.write_text(original)


def replace_one_locus(out: Path) -> None:
    """Swap one row's locus for an id the source does not have, keeping counts and pages."""
    changed = rows(out)
    changed[-1]["line_number"] = changed[-1]["line_number"] + len(changed)
    changed[-1]["line_id"] = f"{changed[-1]['page_id']}:{changed[-1]['line_number']}"
    rewrite_rows(out, changed)


def test_checkers_reject_a_replaced_locus(tmp_path: Path, synthetic_accounted: str):
    out = write_build(tmp_path, synthetic_accounted)
    replace_one_locus(out)
    report = inv.verify_all_invariants(out)
    assert not report.passed
    assert "LOCI_ACCOUNTED" in {f["invariant"] for f in report.failures}
    assert not validate(out)[0]


def test_checkers_reject_an_unknown_reported_locus(tmp_path: Path, synthetic_lossy: str):
    """A reported id outside the source must not stand in for a dropped locus."""
    out = write_build(tmp_path, synthetic_lossy)
    rewrite_report(out, reported_loci=["f9r:1"], loci_reported=1, unaccounted_loci=[])
    report = inv.verify_all_invariants(out)
    assert not report.passed
    assert "LOCI_ACCOUNTED" in {f["invariant"] for f in report.failures}
    valid, errors = validate(out)
    assert not valid
    assert any("f9r:1" in e for e in errors), errors


def test_real_build_passes_both_validators(zl_file: Path, tmp_path: Path):
    """The real ZL build (every locus, `fRos`, all eight locators) conforms and validates."""
    out = tmp_path / "out"
    out.mkdir()
    records, report = build_eva_lines(zl_file, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(json.dumps(report.to_dict()))
    built = rows(out)
    assert {r["page_id"] for r in built} >= {"fRos"}
    schema_valid, schema_errors = validate_transcription_lines(built)
    assert schema_valid, schema_errors[:5]
    valid, errors = validate(out)
    assert valid, errors[:5]
    with contextlib.redirect_stdout(io.StringIO()):
        invariants = inv.verify_all_invariants(out)
    assert invariants.passed, invariants.failures[:5]


REPORTED_CASES = {
    "invalid subtype": "<f1v.2,@Pz>       rejected\n",
    "no comma": "<f1v.2 @P0>       rejected\n",
    "no closing caret": "<f1v.2,@P0       rejected\n",
    "second reading rejected": "<f1v.1,@Pz;C>     rejected.reading\n",
    "broken wrap at end": "<f1v.2,+P0>       otol /\n",
    "invalid page header": "<fXr>      <! $Q=A>\n",
    "malformed page header": "<f2r\n",
}


@pytest.mark.parametrize("case", REPORTED_CASES, ids=list(REPORTED_CASES))
def test_reported_lines_pass_both_validators(tmp_path: Path, synthetic_accounted: str, case: str):
    """Each kind of line the parser reports is accounted end to end: builder, report, validators."""
    out = write_build(tmp_path, synthetic_accounted + REPORTED_CASES[case])
    report = json.loads((out / "eva_lines_build_report.json").read_text())
    assert report["reported_loci"] or report["reported_pages"], report["warnings"]
    assert report["warnings"]
    valid, errors = validate(out)
    assert valid, errors
    with contextlib.redirect_stdout(io.StringIO()):
        invariants = inv.verify_all_invariants(out)
    assert invariants.passed, invariants.failures
