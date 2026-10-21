# tests/regressions/729a5385/test_finding_3.py
import json
from pathlib import Path

from validators.validate_phase1_outputs import check_manifest_source


def test_repository_source_is_not_shadowed_by_cwd(
    tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[3]
    output = root / "output"
    report = json.loads(
        (output / "eva_lines_build_report.json").read_text()
    )
    manifest = json.loads(
        (output / "release_manifest.json").read_text()
    )
    recorded = Path(report["source_file"])
    assert not recorded.is_absolute()
    assert check_manifest_source(output, manifest) == []

    shadow = tmp_path / recorded
    shadow.parent.mkdir(parents=True)
    shadow.write_bytes(b"# unrelated checkout source\n")
    assert shadow.read_bytes() != (root / recorded).read_bytes()

    monkeypatch.chdir(tmp_path)
    assert check_manifest_source(output, manifest) == []
