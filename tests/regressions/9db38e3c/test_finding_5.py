# tests/regressions/9db38e3c/test_finding_5.py
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def test_one_version_predicate_covers_the_release_manifest(tmp_path, monkeypatch):
    """Plan item 1 puts 1.0.0 in the release manifest; the version predicate must fail when the manifest says 0.2.3."""
    from tests import test_paperwork as tp

    for rel in (
        "pyproject.toml",
        "CITATION.cff",
        ".zenodo.json",
        "output/metadata/metadata_report.json",
        "output/release_manifest.json",
        "huggingface/voynich-eva/README.md",
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    manifest = tmp_path / "output" / "release_manifest.json"
    manifest.write_text(manifest.read_text().replace('"1.0.0"', '"0.2.3"'))
    assert '"0.2.3"' in manifest.read_text()
    monkeypatch.setattr(tp, "ROOT", tmp_path)
    caught = False
    try:
        tp.test_one_version_everywhere()
        tp.test_zenodo_metadata_states_the_version_and_the_citation_s_title()
    except AssertionError:
        caught = True
    assert caught, "the one-version predicates pass with a 0.2.3 release manifest"
