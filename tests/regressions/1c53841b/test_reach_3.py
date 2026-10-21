# tests/regressions/1c53841b/test_reach_3.py
import pytest

from builders.build_mismatch_index import MismatchIndexBuilder
from tests import test_mismatch_index as checks


@pytest.mark.parametrize("damage", ["record_payload", "warning_entry"])
def test_object_predicate_checks_records_and_each_source(monkeypatch, damage):
    checks.test_the_builder_object_loads_and_reports()
    original = MismatchIndexBuilder.build

    def damaged_build(self):
        records = original(self)
        if damage == "record_payload":
            record = next(r for r in records if r.zl_text_raw is not None)
            record.zl_text_raw += "a"
        else:
            self.stats["warnings"].pop("zl")
        return records

    monkeypatch.setattr(MismatchIndexBuilder, "build", damaged_build)
    with pytest.raises(AssertionError):
        checks.test_the_builder_object_loads_and_reports()
