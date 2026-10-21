import pytest
from parsers import IVTFFParser

def test_invalid_page_variables_are_not_silent():
    head = "#=IVTFF Eva- 2.0 M\n"
    valid = head + "<f1r> <! $L=A $B=1>\n<f1r.1,@P0> daiin\n"
    assert list(IVTFFParser(strict=True).parse_string(valid))[0].variables.language == "A"

    invalid = head + "<f1r> <! $L=AB $B=x>\n<f1r.1,@P0> daiin\n"
    with pytest.raises(ValueError):
        list(IVTFFParser(strict=True).parse_string(invalid))

    parser = IVTFFParser()
    list(parser.parse_string(invalid))
    assert parser.warnings
