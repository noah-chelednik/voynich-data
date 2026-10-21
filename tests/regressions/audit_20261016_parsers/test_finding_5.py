# tests/regressions/audit_20261016_parsers/test_finding_5.py
import pytest

from parsers import IVTFFParser


def test_strict_file_parse_rejects_undecodable_input(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(
        b"#=IVTFF Eva- 2.0 M\n<f1r>\n<f1r.1,@P0> ab\n"
    )
    assert list(IVTFFParser(strict=True).parse_file(source))[0].loci[0].text == "ab"

    source.write_bytes(
        b"#=IVTFF Eva- 2.0 M\n<f1r>\n<f1r.1,@P0> a\xffb\n"
    )
    with pytest.raises((UnicodeError, ValueError)):
        list(IVTFFParser(strict=True).parse_file(source))
