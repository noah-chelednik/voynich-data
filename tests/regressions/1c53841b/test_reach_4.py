# tests/regressions/1c53841b/test_reach_4.py
import pytest

from tests import test_validators as checks


@pytest.mark.parametrize("damage", ["invalid_status", "later_committed_row"])
def test_status_predicate_covers_its_whole_clause(monkeypatch, damage):
    instance = checks.TestValidateMismatchIndex()
    instance.test_validate_all_status_values()

    rows = instance.committed_rows()
    later_id = next(
        row["line_id"] for row in rows
        if row["line_id"] != rows[0]["line_id"]
    )
    original = checks.validate_mismatch_index

    def broken_validator(data):
        if damage == "invalid_status":
            if any(row["status"] == "invalid_status" for row in data):
                return True, []
        elif any(row["line_id"] == later_id for row in data):
            return False, ["Synthetic rejection of a committed row"]
        return original(data)

    monkeypatch.setattr(checks, "validate_mismatch_index", broken_validator)
    with pytest.raises(AssertionError):
        instance.test_validate_all_status_values()
