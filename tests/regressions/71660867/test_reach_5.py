# tests/regressions/71660867/test_reach_5.py
import pytest

from tests import test_words as checks
from validators import validate_phase1_outputs as phase


def test_phase_refusal_predicate_reaches_public_validator(tmp_path, monkeypatch):
    monkeypatch.setattr(phase, "validate_outputs", lambda output_dir: (True, []))

    with pytest.raises(AssertionError):
        checks.test_both_validators_refuse_changed_words(
            tmp_path, checks.change_word, "phase"
        )
