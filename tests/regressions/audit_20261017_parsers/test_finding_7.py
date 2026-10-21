from parsers import IVTFFParser

def test_completed_wrap_crosses_slash_only_line():
    prefix = "#=IVTFF Eva- 2.0 M\n<f1r>\n<f1r.1,@P0> "
    control = prefix + "da /\n/ /\n/ iin\n"
    assert list(
        IVTFFParser(strict=True).parse_string(control)
    )[0].loci[0].text == "daiin"

    parser = IVTFFParser()
    pages = list(parser.parse_string(prefix + "da /\n/\n/ iin\n"))
    assert not parser.warnings
    assert pages[0].loci[0].text == "daiin"
