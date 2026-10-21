# tests/regressions/caac4571/test_finding_3.py
import pytest

from tests.test_cards import whole_table


@pytest.mark.parametrize(
    "extra",
    [
        "<em>invented_field</em> | str | An undocumented field |",
        "<https://example.invalid> | str | An undocumented field |",
    ],
)
def test_angle_prefixed_table_rows_are_checked(extra):
    rendered = (
        "| Field | Type | Description |\n"
        "|---|---|---|\n"
        "| a | str | A |"
    )

    assert whole_table(rendered + "\n## Next", rendered) == rendered
    assert whole_table(
        rendered + "\nordinary_extra\n\n", rendered
    ) == rendered + "\nordinary_extra"

    displayed = rendered + "\n" + extra + "\n\n"
    assert whole_table(displayed, rendered) == rendered + "\n" + extra
