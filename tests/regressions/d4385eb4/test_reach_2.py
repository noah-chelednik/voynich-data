# tests/regressions/d4385eb4/test_reach_2.py
from builders import stage_release as sr


def test_staging_cli_cannot_succeed_without_configured_data(tmp_path, monkeypatch):
    empty_output = tmp_path / "empty-output"
    empty_output.mkdir()
    monkeypatch.setattr(sr, "OUTPUT", empty_output)

    try:
        status = sr.main(["--staging", str(tmp_path / "staged")])
    except (FileNotFoundError, ValueError):
        return

    assert status != 0, "staging reported success without its configured data files"
