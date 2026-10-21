"""
The release staging (roadmap item 2.9): every Hugging Face repository built locally (`builders/stage_release.py`) with its
card, LICENSE and data files; every layer a configuration of `voynich-eva`; every configuration loads with the `datasets`
library, offline; and every configuration name and file users load today (the 0.2.3 cards) still loads.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from builders import stage_release as sr

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def staged(tmp_path_factory) -> Path:
    staging = tmp_path_factory.mktemp("staging")
    sr.stage(staging)
    return staging


def load(repository: Path, config: str, cache: Path):
    """A configuration of a staged repository, loaded as a user loads it, offline."""
    import datasets
    import huggingface_hub.constants as hub

    # the libraries' own flags, read at their import, set here: an environment variable set later changes nothing (reach
    # d4385eb4 gap 4)
    datasets.config.HF_HUB_OFFLINE = True
    datasets.config.HF_DATASETS_OFFLINE = True
    hub.HF_HUB_OFFLINE = True
    return datasets.load_dataset(str(repository), config, split="train", cache_dir=str(cache))


def test_the_staging_is_ignored_by_git():
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "release/staging/voynich-eva/README.md"],
        cwd=ROOT,
        check=False,
    )
    assert ignored.returncode == 0


def test_every_repository_is_staged_with_its_card_and_license(staged):
    assert sorted(p.name for p in staged.iterdir()) == sorted(sr.REPOSITORIES)
    for repository, (card, _directory) in sr.REPOSITORIES.items():
        for name in ("README.md", "LICENSE"):
            assert (staged / repository / name).read_bytes() == (ROOT / card / name).read_bytes()


def test_every_layer_is_a_configuration_of_voynich_eva():
    """The card's configs are the staging table's, and the table names every table the build publishes."""
    configs = sr.card_configs(ROOT / "huggingface" / "voynich-eva" / "README.md")
    assert configs == {name: [path] for name, (path, _b, _w) in sr.EVA_CONFIGS.items()}
    builds = {build for _p, build, _w in sr.EVA_CONFIGS.values()}
    published = {
        f"{p.parent.name}/{p.name}" if p.parent != ROOT / "output" else p.name
        for p in (ROOT / "output").rglob("*.parquet")
    }
    assert builds == published
    assert (
        sr.eva_configurations_table()
        in (ROOT / "huggingface" / "voynich-eva" / "README.md").read_text()
    )


def test_every_staged_file_is_its_build_file(staged):
    """Every file of every staged repository, the twins too (reach d4385eb4 gap 3), is its build file byte for byte, and
    nothing else is staged."""
    for repository in sr.REPOSITORIES:
        files = sr.staged_files(repository)
        present = {p.name for p in (staged / repository).iterdir()} - {"README.md", "LICENSE"}
        assert present == set(files), repository
        for name, source in files.items():
            assert (staged / repository / name).read_bytes() == source.read_bytes(), (
                repository,
                name,
            )


def test_every_repository_stages_its_build_reports(staged):
    """Each repository holds the reports `docs/PUBLISHING.md`'s table lists for it, read from the document, byte for byte
    the build's (B-129; review 9db38e3c finding 4: the expected list came from `REPORTS` alone)."""
    text = (sr.ROOT / "docs" / "PUBLISHING.md").read_text(encoding="utf-8")
    for repository in sr.REPOSITORIES:
        row = next(ln for ln in text.splitlines() if ln.startswith(f"| `Ched-ai/{repository}`"))
        promised = {
            Path(p).name for p in re.findall(r"`(output/[^`]+)`", row.split("|")[-2])
        }  # the reports column
        assert promised, repository
        assert promised == set(sr.REPORTS[repository]), repository
        for name in promised:
            built = sr.OUTPUT / sr.REPOSITORIES[repository][1] / name
            assert (staged / repository / name).read_bytes() == built.read_bytes(), (
                repository,
                name,
            )
    for repository, names in sr.REPORTS.items():
        _card, directory = sr.REPOSITORIES[repository]
        assert all(
            f"`{(Path('output') / directory / name).as_posix()}`" in text for name in names
        ), repository


def test_a_missing_report_stops_the_staging(tmp_path, monkeypatch):
    """A report the plan names and the build lacks stops the staging before anything is written (B-129)."""
    monkeypatch.setitem(sr.REPORTS, "voynich-transcription-mismatch", ("no_such_report.json",))
    with pytest.raises(FileNotFoundError, match="no_such_report.json"):
        sr.stage(tmp_path / "staging")
    assert not (tmp_path / "staging").exists()


def test_a_missing_configuration_file_stops_the_staging(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "OUTPUT", tmp_path / "empty")
    with pytest.raises(FileNotFoundError):
        sr.stage(tmp_path / "staged")
    assert not (tmp_path / "staged").exists()


def test_every_configuration_loads_offline(staged, tmp_path):
    for repository, (card, _directory) in sr.REPOSITORIES.items():
        for config, paths in sr.card_configs(ROOT / card / "README.md").items():
            data = load(staged / repository, config, tmp_path / "cache")
            source = sr.build_file(repository, paths[0])
            count = (
                pq.read_metadata(source).num_rows
                if source.suffix == ".parquet"
                else sum(
                    1 for line in source.read_text(encoding="utf-8").splitlines() if line.strip()
                )
            )
            assert data.num_rows == count, (repository, config)


@pytest.mark.parametrize(
    ("repository", "config", "path"),
    [(r, c, p) for r, configs in sr.PUBLISHED_CONFIGS.items() for c, p in configs.items()],
)
def test_the_published_configurations_still_load(staged, tmp_path, repository, config, path):
    """Backwards compatibility: every config name of the 0.2.3 cards is still a config, its file still in the repository
    under the same name, and it loads with the same columns the build's file has."""
    assert config in sr.card_configs(staged / repository / "README.md")
    assert (staged / repository / path).is_file()
    data = load(staged / repository, config, tmp_path / "cache")
    columns = pq.read_schema(staged / repository / path).names
    assert data.num_rows == pq.read_metadata(staged / repository / path).num_rows
    assert set(columns) <= set(data.column_names)


#: The published 0.2.3 state: the commit `main` held when 0.2.3 was published, and the SHA-256 of each Hub card in it.
#: Their bytes are committed under `tests/data/published_0_2_3/`, so the check needs no local `main` (a CI checkout has
#: none) and does not follow `main` when a release moves it (review 4c664493 finding 3).
PUBLISHED_COMMIT = "472ef7366606a799fc8f1044c037e06b413f6ddd"
PUBLISHED_CARDS = ROOT / "tests" / "data" / "published_0_2_3"
PUBLISHED_CARD_SHA256 = {
    "voynich-eva": "a05e5c6a119939707fec247833deb024634f9920ad8d43f79fa69d4952e37c6f",
    "voynich-manuscript-metadata": "984965532d93d673a243644ef6a4a79a5e9be085cc8883ff667e17857487d6bb",
    "voynich-transcription-mismatch": "5636dc9f8932ba108a551f4936343cc4a661f53fd4d05e2a25ac9f974d48ba73",
}


def test_the_published_configurations_are_the_0_2_3_cards():
    """`PUBLISHED_CONFIGS` is what the 0.2.3 cards (as published at `PUBLISHED_COMMIT`) define: the repositories are the
    committed cards' directories, not the mapping itself (reach d4385eb4 gap 5); each card is the published bytes
    (its pinned SHA-256, and git's copy wherever the commit is present)."""
    import hashlib

    import yaml

    published = sorted(p.parent.name for p in PUBLISHED_CARDS.glob("*/README.md"))
    assert published == sorted(PUBLISHED_CARD_SHA256)
    for repository in published:
        data = (PUBLISHED_CARDS / repository / "README.md").read_bytes()
        assert hashlib.sha256(data).hexdigest() == PUBLISHED_CARD_SHA256[repository], repository
    present = subprocess.run(
        ["git", "cat-file", "-e", f"{PUBLISHED_COMMIT}^{{commit}}"], cwd=ROOT, capture_output=True
    )
    if (
        present.returncode == 0
    ):  # the full history is here: the copies are the commit's cards, every one of them
        tree = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", PUBLISHED_COMMIT, "huggingface/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        assert sorted(p.split("/")[1] for p in tree if p.endswith("/README.md")) == published
        for repository in published:
            shown = subprocess.run(
                ["git", "show", f"{PUBLISHED_COMMIT}:huggingface/{repository}/README.md"],
                cwd=ROOT,
                capture_output=True,
                check=True,
            ).stdout
            assert shown == (PUBLISHED_CARDS / repository / "README.md").read_bytes(), repository
    assert set(sr.PUBLISHED_CONFIGS) == set(published)
    for repository, configs in sr.PUBLISHED_CONFIGS.items():
        card = (PUBLISHED_CARDS / repository / "README.md").read_text(encoding="utf-8")
        front = yaml.safe_load(card.split("---", 2)[1])
        assert {c["config_name"]: c["data_files"][0]["path"] for c in front["configs"]} == configs


def test_the_staging_holds_no_kit_file(staged):
    """The staging is what a repository on the Hub would hold: data, card, license; nothing of the build's tooling."""
    reports = {name for names in sr.REPORTS.values() for name in names}
    for path in staged.rglob("*"):
        if path.is_file():
            assert path.suffix in {".parquet", ".jsonl", ".md"} or path.name in {
                "LICENSE",
                *reports,
            }, path
    assert json.dumps(sorted(p.name for p in staged.rglob("*.py"))) == "[]"


def test_a_previous_staging_is_replaced_and_anything_else_in_it_is_refused(tmp_path, monkeypatch):
    """The positive control of the staging's refusal (review 2fb5415b finding 1): the command's own staging, as it wrote
    it, is replaced; the same staging with one file the command never writes is refused and kept."""
    staging = tmp_path / "release" / "staging"
    monkeypatch.setattr(sr, "STAGING", staging)
    first = sr.stage(staging)
    assert sr.stage(staging) == first
    extra = staging / "voynich-eva" / "notes.txt"
    extra.write_text("not the staging's\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        sr.stage(staging)
    assert extra.is_file()
