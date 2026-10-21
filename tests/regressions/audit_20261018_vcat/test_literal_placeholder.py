import pytest
from vcat.eva_charset import validate_eva_text


@pytest.mark.parametrize("raw", ["\x01", "{\x01}"])
def test_literal_placeholder_is_not_a_validated_high_ascii_code(raw):
    valid = validate_eva_text("@192;", strict=True)
    assert valid.is_valid
    assert not valid.errors

    rejected_control = validate_eva_text("\x02", strict=True)
    assert not rejected_control.is_valid
    assert rejected_control.errors

    result = validate_eva_text(raw, strict=True)
    assert not result.is_valid
    assert result.errors
