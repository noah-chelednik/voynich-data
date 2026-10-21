# tests/regressions/4c664493/test_finding_2.py
from builders import stage_release as sr


def test_staging_into_a_directory_holding_other_files_keeps_them(tmp_path):
    """`--staging` takes any directory; staging into one that holds files the staging did not write must refuse or
    leave them, never delete them."""
    target = tmp_path / "work"
    target.mkdir()
    keep = target / "notes.txt"
    keep.write_text("not the staging's\n", encoding="utf-8")
    try:
        sr.main(["--staging", str(target)])
    except (ValueError, FileExistsError, SystemExit):
        pass
    assert keep.is_file() and keep.read_text(encoding="utf-8") == "not the staging's\n"
