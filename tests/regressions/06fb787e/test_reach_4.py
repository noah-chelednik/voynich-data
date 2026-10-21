# tests/regressions/06fb787e/test_reach_4.py
from parsers import MetadataParser, Page, PageVariables


def test_spanning_page_creates_both_folio_references():
    pages = [Page(page_id="fRos", variables=PageVariables())]
    folios = {
        record.folio_id: record
        for record in MetadataParser().extract_folios(pages)
    }

    assert {"f85", "f86"} <= folios.keys()
    assert "fRos" in folios["f85"].verso_page_ids
    assert folios["f86"].recto_page_ids == ["fRos"]
    assert folios["f86"].recto_page_id == "fRos"
