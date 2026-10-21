# tests/regressions/020f7450/test_finding_3.py
import pytest

from tests.test_cards import whole_table


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
def test_unicode_separators_do_not_create_markdown_fences(separator):
    rendered = (
        "| Field | Type | Description |\n"
        "|---|---|---|\n"
        "| a | str | A |"
    )

    assert whole_table(rendered + "\n## Next", rendered) == rendered
    assert whole_table(rendered + "\n```", rendered) == rendered

    ordinary = "ordinary_extra | str | An undocumented field |"
    assert whole_table(
        rendered + "\n" + ordinary + "\n\n", rendered
    ) == rendered + "\n" + ordinary

    extra = (
        "```"
        + separator
        + "invented`field | str | An undocumented field |"
    )
    displayed = rendered + "\n" + extra + "\n\n"

    assert whole_table(displayed, rendered) == rendered + "\n" + extra
