# tests/regressions/b09d5b4b/test_reach_5.py
import pytest

from tests import test_sources as checks


def test_card_copy_guard_reaches_subdirectories(tmp_path, monkeypatch):
    card = tmp_path / "card"
    data = card / "data"
    data.mkdir(parents=True)
    (data / "copy.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(checks, "ROOT", tmp_path)

    with pytest.raises(AssertionError):
        checks.test_card_directories_hold_no_copy_of_the_data(
            {"card": "card"}
        )
