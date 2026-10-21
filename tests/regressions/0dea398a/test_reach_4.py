# tests/regressions/0dea398a/test_reach_4.py
import importlib

import pytest

from builders.cards import schema_field_table, transliterations_schema


@pytest.mark.parametrize(
    "module_name",
    ["tests.test_cards", "tests.test_transliterations"],
)
def test_whole_table_includes_rows_without_outer_pipe(module_name):
    checks = importlib.import_module(module_name)
    rendered = schema_field_table(transliterations_schema())
    extra = "`invented_field` | string | This field is absent from the dataset |"
    displayed = rendered + "\n" + extra + "\n\n"

    assert checks.whole_table(displayed, rendered) != rendered
