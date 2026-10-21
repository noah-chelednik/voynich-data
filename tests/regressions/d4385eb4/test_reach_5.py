# tests/regressions/d4385eb4/test_reach_5.py
import pytest

from builders import stage_release as sr
from tests import test_staging as gate


def test_historical_mapping_predicate_rejects_an_omitted_repository(monkeypatch):
    reduced = {
        repository: dict(configs)
        for repository, configs in sr.PUBLISHED_CONFIGS.items()
        if repository != "voynich-transcription-mismatch"
    }
    monkeypatch.setattr(sr, "PUBLISHED_CONFIGS", reduced)

    with pytest.raises(AssertionError):
        gate.test_the_published_configurations_are_the_0_2_3_cards()
