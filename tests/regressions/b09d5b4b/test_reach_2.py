# tests/regressions/b09d5b4b/test_reach_2.py
from dataclasses import replace

import pytest

from tests import test_sources as checks


def test_source_version_must_not_be_only_a_header_fragment():
    record = next(r for r in checks.RECORDS if r.id == "ZL")
    checks.test_each_record_pins_its_file(record)
    fragment = record.upstream_version.split()[0]
    assert fragment != record.upstream_version

    with pytest.raises(AssertionError):
        checks.test_each_record_pins_its_file(
            replace(record, upstream_version=fragment)
        )
