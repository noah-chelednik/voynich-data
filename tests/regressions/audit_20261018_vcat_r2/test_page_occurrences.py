from vcat.loss_accounting import account, census_text


def test_account_requires_every_page_header_occurrence():
    raw = (
        "#=IVTFF Eva- 2.0\n"
        "<f1r> <! $I=H>\n"
        "<f1r.1,@L0> a\n"
        "<f1r> <! $I=H>\n"
    )
    census = census_text(raw)

    assert account(census, census.loci, census.pages).complete
    assert not account(census, census.loci, []).complete

    missing = account(census, census.loci, census.pages[:-1])
    assert not missing.complete
    assert missing.unaccounted_pages == list(census.pages[-1:])
