# tests/regressions/8dc8e2d0/test_finding_2.py
from parsers import IVTFFParser


def test_header_metadata_belongs_to_the_current_parse():
    reused = IVTFFParser()
    list(
        reused.parse_string(
            "#=IVTFF Eva- 2.0 M 5\n"
            "<f1r>\n"
            "<f1r.1,@P0> daiin\n"
        )
    )
    assert reused.alphabet == "Eva-"

    content = "<f2r>\n<f2r.1,@P0> ol\n"
    fresh = IVTFFParser()
    fresh_pages = list(fresh.parse_string(content))
    reused_pages = list(reused.parse_string(content))

    assert [p.page_id for p in reused_pages] == [
        p.page_id for p in fresh_pages
    ]
    expected = (
        fresh.alphabet,
        fresh.format_version,
        fresh.format_options,
    )
    assert expected == (None, None, None)
    assert (
        reused.alphabet,
        reused.format_version,
        reused.format_options,
    ) == expected
