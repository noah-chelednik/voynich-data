# tests/regressions/8f69a2eb/test_finding_1.py
"""Claim 6 (B-113): a page header that occurs n times is accounted for by n emitted or reported entries. The parser
emits a repeated header as two pages and the EVA builder passes one entry per parsed page, so it certifies the build
(no unaccounted page). check_loss_accounting, which both validators run, passes the pages as a SET of the rows' page ids,
so a header emitted twice is covered once and the second occurrence is reported unaccounted: a faithful build that the
builder certifies is refused."""
from parsers import IVTFFParser
from builders.build_eva_lines import build_eva_lines
from validators.validate_phase1_outputs import check_loss_accounting

SOURCE = (
    "#=IVTFF Eva- 2.0\n"
    "<f1r>      <! $I=H>\n"
    "<f1r.1,@P0>       daiin\n"
    "<f1v>      <! $I=H>\n"
    "<f1v.1,@P0>       chol\n"
    "<f1r>      <! $I=H>\n"
    "<f1r.2,@P0>       okal\n"
)


def test_a_repeated_header_the_build_emitted_twice_is_accounted_by_the_validators(tmp_path):
    source = tmp_path / "repeat.txt"
    source.write_text(SOURCE, encoding="utf-8")
    parsed = list(IVTFFParser().parse_file(source))
    assert [p.page_id for p in parsed] == ["f1r", "f1v", "f1r"]  # the parser emits both occurrences
    records, report = build_eva_lines(source, tmp_path)
    assert report.unaccounted_pages == []  # the builder accounts the repeated header by its two emitted pages
    assert len(records) == 3
    errors = check_loss_accounting([r.to_dict() for r in records], report.to_dict())
    assert not [e for e in errors if "page" in e], errors
