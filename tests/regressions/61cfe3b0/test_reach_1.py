# tests/regressions/61cfe3b0/test_reach_1.py
import pytest

from parsers import IVTFFParser
from parsers.ivtff_roundtrip import main, rebuild_source, round_trip


CONTENT = (
    "#=IVTFF Eva- 2.0 M 5\n"
    "<f1r> <! $B=\u00b2>\n"
    "<f1r.1,@P0> daiin\n"
    "<f2r>\n"
    "<f2r.1,@P0> ol\n"
)


@pytest.mark.parametrize("entry", ["string", "file"])
def test_invalid_bifolio_keeps_the_page_and_complete_document(tmp_path, entry):
    with pytest.raises(ValueError, match="bifolio"):
        list(IVTFFParser(strict=True).parse_string(CONTENT))

    source = tmp_path / "invalid-bifolio.txt"
    source.write_bytes(CONTENT.encode("utf-8"))
    parser = IVTFFParser()
    if entry == "string":
        pages = list(parser.parse_string(CONTENT))
    else:
        pages = list(parser.parse_file(source))

    assert [page.page_id for page in pages] == ["f1r", "f2r"]
    assert [
        locus.locus_id for page in pages for locus in page.loci
    ] == ["f1r:1", "f2r:1"]
    assert [warning.emitted_id for warning in parser.warnings] == ["f1r"]
    assert all(
        warning.page_id is None and warning.locus_id is None
        for warning in parser.warnings
    )
    assert rebuild_source(parser.document) == source.read_bytes()
    assert round_trip(source).identical


def test_round_trip_cli_summarizes_invalid_input_and_the_following_file(
    tmp_path, capsys
):
    invalid = tmp_path / "invalid.txt"
    valid = tmp_path / "valid.txt"
    invalid.write_bytes(CONTENT.encode("utf-8"))
    valid.write_bytes(
        b"#=IVTFF Eva- 2.0 M 5\n<f1r>\n<f1r.1,@P0> daiin\n"
    )

    assert main([str(invalid), str(valid)]) == 0
    summaries = capsys.readouterr().out.splitlines()
    assert [line.split(":", 1)[0] for line in summaries] == [
        invalid.name,
        valid.name,
    ]
    assert all(": identical (" in line for line in summaries)
