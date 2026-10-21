# tests/regressions/audit_20261016_parsers/test_finding_6.py
from parsers import IVTFFParser, extract_all_metadata


def test_quire_index_includes_folios_represented_by_spanning_pages():
    content = (
        "#=IVTFF Eva- 2.0 M\n"
        "<fRos> <! $Q=N>\n"
        "<fRos.1,@Cc> daiin\n"
    )
    result = extract_all_metadata(
        list(IVTFFParser(strict=True).parse_string(content))
    )

    for quire in result.quires:
        expected = {
            folio.folio_id
            for folio in result.folios
            if folio.quire_id == quire.quire_id
        }
        assert expected
        assert set(quire.folio_ids) == expected
        assert quire.folio_count == len(expected)
