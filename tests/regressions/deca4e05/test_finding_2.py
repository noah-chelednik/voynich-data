# tests/regressions/deca4e05/test_finding_2.py
import pytest

from tests.test_cards import whole_table


@pytest.mark.parametrize(
    "extra",
    [
        "```invented`field | str | An undocumented field |",
        "#\u00a0invented_field | str | An undocumented field |",
        "<!x | str | An undocumented field |",
    ],
)
def test_non_block_prefixes_remain_checked_table_rows(extra):
    rendered = (
        "| Field | Type | Description |\n"
        "|---|---|---|\n"
        "| a | str | A |"
    )

    assert whole_table(rendered + "\n## Next", rendered) == rendered
    assert whole_table(rendered + "\n```", rendered) == rendered
    assert whole_table(
        rendered + "\nordinary_extra\n\n", rendered
    ) == rendered + "\nordinary_extra"

    displayed = rendered + "\n" + extra + "\n\n"
    assert whole_table(displayed, rendered) == rendered + "\n" + extra
