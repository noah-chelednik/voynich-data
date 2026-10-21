import pytest
from parsers import IVTFFParser

@pytest.mark.parametrize("body", [
    "<f1r>\n<f1r.1,@L0> <%>daiin<$>\n",
    "<f1r>\n<f1r.1,@P0> <%>daiin\n<f2r>\n<f2r.1,@P0> ol<$>\n",
])
def test_paragraph_structure_is_checked(body):
    header = "#=IVTFF Eva- 2.0 M\n"
    valid = header + "<f1r>\n<f1r.1,@P0> <%>daiin<$>\n"
    assert list(IVTFFParser(strict=True).parse_string(valid))[0].loci
    with pytest.raises(ValueError):
        list(IVTFFParser(strict=True).parse_string(header + body))
