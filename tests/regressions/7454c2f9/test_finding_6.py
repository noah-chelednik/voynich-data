# tests/regressions/7454c2f9/test_finding_6.py
from builders.cards import layers_field_table
from tests.test_cards import whole_table


def test_later_extended_layer_table_is_rejected():
    rendered = layers_field_table()
    conflicting = rendered + "\n| `invented` | `str` | fabricated |"

    assert whole_table(rendered, rendered) == rendered
    assert whole_table(conflicting, rendered) != rendered

    candidate = rendered + "\n\n" + conflicting
    assert whole_table(candidate, rendered) != rendered
