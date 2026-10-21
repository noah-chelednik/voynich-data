from parsers import IVTFFParser

def test_malformed_page_header_ends_previous_page_context():
    source = (
        "#=IVTFF Eva- 2.0 M\n<f1r>\n"
        "<f1r.1,@P0> daiin\n<f2r\n<f1r.2,+P0> ol\n"
    )
    parser = IVTFFParser()
    pages = list(parser.parse_string(source))
    emitted = {l.locus_id for p in pages for l in p.loci}
    assert "f1r:1" in emitted
    assert "f1r:2" not in emitted
    assert any(w.page_id == "f2r" for w in parser.warnings)
    assert any(w.locus_id == "f1r:2" for w in parser.warnings)
