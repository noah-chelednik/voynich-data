# tests/regressions/b09d5b4b/test_reach_6.py
import pytest

from tests import test_sources as checks


def test_cache_path_guard_reaches_nested_test_modules(tmp_path, monkeypatch):
    tree = tmp_path / "tests"
    tree.mkdir()
    direct = tree / "test_cache_probe.py"
    direct.write_text(
        'from pathlib import Path\n'
        'CACHE = Path("data_sources") / "cache"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(checks, "ROOT", tmp_path)

    with pytest.raises(AssertionError):
        checks.test_tests_name_the_cache_through_the_shared_constant()

    nested = tree / "nested"
    nested.mkdir()
    direct.rename(nested / direct.name)

    with pytest.raises(AssertionError):
        checks.test_tests_name_the_cache_through_the_shared_constant()
