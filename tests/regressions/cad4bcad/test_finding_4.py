# tests/regressions/cad4bcad/test_finding_4.py
from builders.build_eva_lines import build_eva_lines
from tests import test_data_model_doc as checks


def test_parser_page_total_is_not_claimed_as_independent_census(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0\n<f1r>\n<invalid>\n",
        encoding="utf-8",
    )
    _, report = build_eva_lines(source, tmp_path)
    rows = checks.tables(
        checks.section("The build report (`output/eva_lines_build_report.json`)")
    )[0]
    description = next(
        cells[-1] for cells in rows if "`total_pages_in_source`" in cells[0]
    )
    assert (
        "counted without the parser" not in description
        or report.total_pages_in_source == report.source_page_headers
    ), (description, report.total_pages_in_source, report.source_page_headers)
