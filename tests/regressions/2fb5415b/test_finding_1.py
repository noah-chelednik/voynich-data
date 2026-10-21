# tests/regressions/2fb5415b/test_finding_1.py
from builders import stage_release as sr


def test_restaging_keeps_a_hub_clone_made_inside_the_default_staging(tmp_path, monkeypatch):
    """Clause 18: only `release/staging/` "in a staging's shape" is replaced; "any other directory is refused and kept,
    ... a directory of Hub clones too". `is_staging` looks only at the top level (repository names, each with README.md
    and LICENSE), never inside: a repository directory of the default staging that holds what `stage` never writes (a
    Hub clone's `.git`, a maintainer's upload notes) still passes and is deleted whole. Here the default staging is a
    temporary path, so the repository is not touched."""
    staging = tmp_path / "release" / "staging"
    monkeypatch.setattr(sr, "STAGING", staging)
    clone = staging / "voynich-eva"
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (clone / "README.md").write_text("card\n", encoding="utf-8")
    (clone / "LICENSE").write_text("license\n", encoding="utf-8")
    (clone / "UPLOAD_NOTES.txt").write_text("not pushed yet\n", encoding="utf-8")
    try:
        sr.main(["--staging", str(staging)])
    except (OSError, ValueError, SystemExit):
        pass
    assert (clone / ".git" / "HEAD").is_file()
    assert (clone / "UPLOAD_NOTES.txt").is_file()
