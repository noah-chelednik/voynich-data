# tests/regressions/cf1c8c6e/test_reach_2.py
import re

import pytest

from tests import test_data_model_doc as checks


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        "`tests/test_structured_layer.py`",
        "`vcat/profiles.py::describe`",
    ],
)
def test_every_guarantee_requires_an_actual_test_reference(monkeypatch, replacement):
    checks.test_every_guarantee_names_a_test_that_exists()
    row = next(line for line in checks.DOC.splitlines() if line.startswith("| G11 |"))
    changed = re.sub(r"`[^`]+`(?= \|$)", replacement, row)
    assert changed != row
    monkeypatch.setattr(checks, "DOC", checks.DOC.replace(row, changed, 1))

    with pytest.raises(AssertionError):
        checks.test_every_guarantee_names_a_test_that_exists()
