# tests/regressions/6e91b4a2/test_reach_3.py
import pytest

from tests.test_cards import whole_table


@pytest.mark.parametrize(
    "extra",
    [
        "#invented_field",
        "#invented_field | string | An undocumented field |",
    ],
)
def test_hash_prefixed_table_rows_are_checked(extra):
    rendered = "| Field | Type | Description |\n|---|---|---|\n| a | str | A |"
    displayed = rendered + "\n" + extra + "\n\n"

    # A hash without following whitespace does not start an ATX heading.
    assert whole_table(displayed, rendered) == rendered + "\n" + extra
