# tests/regressions/cad4bcad/test_finding_5.py
from parsers import IVTFFParser
from tests import test_data_model_doc as checks


def test_identifier_rejection_claim_matches_strict_parser():
    source = "#=IVTFF Eva- 2.0\n<f01r>\n<f01r.1,@P0> a\n"
    try:
        pages = list(IVTFFParser(strict=True).parse_string(source))
    except ValueError:
        pages = []
    accepted = any(page.page_id == "f01r" for page in pages)
    description = checks.section("Identifiers")
    assert not accepted or "No other spelling is accepted." not in description
