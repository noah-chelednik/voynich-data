# tests/regressions/0fcd9966/test_finding_2.py
from pathlib import Path

from tests import test_profiles
from vcat.sources import cached_sources


def test_live_profile_check_selects_every_registered_source():
    expected = {record.path.resolve() for record in cached_sources()}
    marks = test_profiles.test_every_rule_on_every_locus.pytestmark
    source_parameters = next(
        mark
        for mark in marks
        if mark.name == "parametrize" and mark.args[0] == "source"
    )
    selected = {Path(path).resolve() for path in source_parameters.args[1]}

    assert expected and selected
    assert expected <= selected, sorted(str(path) for path in expected - selected)
