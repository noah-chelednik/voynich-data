# tests/regressions/f6661c36/test_finding_3.py
import re

import pytest

from parsers.ivtff_markup import parse_markup
from vcat import validate_eva_text


@pytest.mark.parametrize(
    "raw, reading",
    [
        ("@192;", "@192;"),
        ("{@192;}", "@192;"),
        ("a{@192;}b", "a@192;b"),
        ("[{@192;}:a]", "@192;"),
        ("{@192;@193;}", "@192;@193;"),
    ],
)
def test_high_ascii_inside_ligatures_counts_as_glyphs(raw, reading):
    assert not parse_markup(raw).problems
    result = validate_eva_text(raw, strict=True)
    assert result.is_valid, result.errors

    glyphs = re.sub(r"@\d{3};", "a", reading)
    assert result.char_count == len(glyphs)
    assert result.word_count == len(
        [word for word in re.split(r"[.,\s]+", glyphs) if word]
    )
