def test_f3_raw_validation_reports_tokenizer_problems():
    from parsers.ivtff_markup import parse_markup
    from vcat import validate_eva_text

    control = validate_eva_text("@192;", strict=True)
    assert control.is_valid and not control.warnings and not control.errors

    for raw in ("@127;", "{ch", "a<bogus>b"):
        assert parse_markup(raw).problems
        strict_result = validate_eva_text(raw, strict=True)
        assert not strict_result.is_valid, raw
        assert strict_result.errors, raw

        permissive_result = validate_eva_text(raw, strict=False)
        assert permissive_result.warnings or permissive_result.errors, raw
