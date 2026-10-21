# tests/regressions/b09d5b4b/test_reach_9.py
from unittest.mock import patch

from tests import test_output_validation as checks


def test_bound_report_predicate_exercises_both_validators(tmp_path):
    source = (
        "#=IVTFF Eva- 2.0\n"
        "<f1r>\n"
        "<f1r.1,@P0> daiin\n"
    )
    with patch.object(
        checks.phase,
        "validate_outputs",
        wraps=checks.phase.validate_outputs,
    ) as phase, patch.object(
        checks.inv,
        "verify_all_invariants",
        wraps=checks.inv.verify_all_invariants,
    ) as invariants:
        checks.test_check_build_report_rejects_failures(
            tmp_path, source
        )

    assert phase.called, "The bound predicate never calls validate_outputs"
    assert invariants.called, (
        "The bound predicate never calls verify_all_invariants"
    )
