# tests/regressions/bef641e7/test_reach_2.py
from copy import deepcopy

import pytest

from tests import test_layers as checks
from vcat.sources import load_sources


def test_layer_field_must_name_an_existing_dataset(monkeypatch):
    checks.test_every_layer_field_is_a_field_of_its_dataset()

    unknown = "voynich-reach-nonexistent"
    assert unknown not in {row["name"] for row in load_sources()["datasets"]}

    layer = deepcopy(
        next(row for row in checks.LAYERS if row["layer"] == "section")
    )
    layer["fields"] = [f"{unknown}:pages.section"]
    monkeypatch.setattr(checks, "LAYERS", [layer])

    with pytest.raises((AssertionError, ValueError)):
        checks.test_every_layer_field_is_a_field_of_its_dataset()
