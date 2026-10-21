import pytest
from parsers import IVTFFParser

@pytest.mark.parametrize("raw", ["da<-><~>iin", "<->daiin", "daiin."])
def test_current_format_rejects_invalid_word_space_placement(raw):
    prefix = "#=IVTFF Eva- 2.0 M\n<f1r>\n<f1r.1,@P0> "
    assert list(
        IVTFFParser(strict=True).parse_string(prefix + "da<->iin\n")
    )[0].loci
    with pytest.raises(ValueError):
        list(IVTFFParser(strict=True).parse_string(prefix + raw + "\n"))
