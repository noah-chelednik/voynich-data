# tests/regressions/09e1ca3c/test_finding_2.py
import contextlib
import copy
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("mutation", ["missing", "float"])
def test_both_validators_require_integer_lines_by_type(mutation):
    out = ROOT / "output"
    original = json.loads((out / "eva_lines_build_report.json").read_text())

    def accepted(report):
        with patch.object(phase, "load_build_report", return_value=report):
            with contextlib.redirect_stdout(io.StringIO()):
                phase_valid, _ = phase.validate_outputs(out)
                invariants = inv.verify_all_invariants(out)
        return phase_valid, invariants.passed

    assert accepted(original) == (True, True)

    changed = copy.deepcopy(original)
    if mutation == "missing":
        del changed["lines_by_type"]
    else:
        changed["lines_by_type"] = {
            kind: float(count)
            for kind, count in changed["lines_by_type"].items()
        }

    assert accepted(changed) == (False, False)
