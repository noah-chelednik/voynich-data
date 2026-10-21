# tests/regressions/fc83f28e/test_finding_1.py
import shutil
from pathlib import Path

from builders import stage_release as sr

ROOT = Path(__file__).resolve().parents[3]


def test_staging_into_the_card_directory_keeps_the_cards(tmp_path, monkeypatch):
    """`huggingface/` (the committed cards: four repository directories, each with README.md and LICENSE) has exactly
    the shape `is_staging` accepts. `python -m builders.stage_release --staging huggingface` must refuse or keep it,
    never delete the cards the staging is made from. Here the checkout is a copy, so the repository is not touched."""
    checkout = tmp_path / "checkout"
    shutil.copytree(ROOT / "huggingface", checkout / "huggingface")
    draft = checkout / "huggingface" / "voynich-eva" / "README.md"
    draft.write_text(draft.read_text(encoding="utf-8") + "\nan uncommitted edit\n", encoding="utf-8")
    monkeypatch.setattr(sr, "ROOT", checkout)
    try:
        sr.main(["--staging", str(checkout / "huggingface")])
    except (OSError, ValueError, SystemExit):
        pass
    assert draft.is_file() and draft.read_text(encoding="utf-8").endswith("an uncommitted edit\n")


def test_staging_into_a_directory_of_hub_clones_keeps_their_history(tmp_path):
    """A directory holding a clone of a Hub repository (its card, LICENSE and `.git`) passes `is_staging` too, and is
    deleted whole, the clone's history with it."""
    hub = tmp_path / "hub"
    clone = hub / "voynich-eva"
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (clone / "README.md").write_text("card\n", encoding="utf-8")
    (clone / "LICENSE").write_text("license\n", encoding="utf-8")
    try:
        sr.main(["--staging", str(hub)])
    except (OSError, ValueError, SystemExit):
        pass
    assert (clone / ".git" / "HEAD").is_file()
