"""
Paperwork (roadmap item 1.9): one version everywhere, read from the files at test time.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

import vcat
from builders.build_metadata import MetadataBuildReport

ROOT = Path(__file__).resolve().parent.parent


def package_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def test_one_version_everywhere():
    """pyproject.toml, `vcat.__version__`, CITATION.cff, the metadata build report and the EVA card state one version."""
    version = package_version()
    assert vcat.__version__ == version
    cff = re.search(r"^version: (\S+)$", (ROOT / "CITATION.cff").read_text(), re.M)
    assert cff and cff.group(1) == version
    assert (
        MetadataBuildReport(source_file="", source_hash="", build_timestamp="").build_version
        == version
    )
    # and the committed report, as built (reach b09d5b4b gap 1)
    committed = json.loads((ROOT / "output/metadata/metadata_report.json").read_text())
    assert committed["build_version"] == version
    card = (ROOT / "huggingface" / "voynich-eva" / "README.md").read_text(encoding="utf-8")
    assert f"**Current version:** v{version}" in card
    # the release manifest the EVA build writes states it too (review 9db38e3c finding 5)
    manifest = json.loads((ROOT / "output" / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["build"]["tool_version"] == manifest["dataset"]["version"] == version


def test_zenodo_metadata_states_the_version_and_the_citation_s_title():
    """`.zenodo.json` (Zenodo reads it at a GitHub release) states the package's version and the title and license of
    `CITATION.cff` (roadmap item 1.10)."""
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert zenodo["version"] == package_version()
    assert f'title: "{zenodo["title"]}"' in cff
    assert re.search(rf"^license: {re.escape(zenodo['license'])}$", cff, re.M)


def test_changelog_names_no_unreleased_version():
    """Every version heading of the CHANGELOG is a released version (no later than the package's), or Unreleased."""
    version = tuple(int(n) for n in package_version().split("."))
    for heading in re.findall(
        r"^## \[([^\]]+)\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M
    ):
        if heading == "Unreleased":
            continue
        number = re.match(r"(\d+)\.(\d+)\.(\d+)", heading)
        assert number, heading
        assert tuple(int(n) for n in number.groups()) <= version, heading


def test_readme_tables_are_the_build():
    """The README's dataset and source tables are rendered from the build and the cache (D8: every number from the build),
    each exactly its marked region."""
    from builders.cards import readme_datasets_table, readme_sources_table

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert rendered_region(readme, "readme:datasets") == readme_datasets_table()
    assert rendered_region(readme, "readme:sources") == readme_sources_table()


def rendered_region(text: str, name: str) -> str:
    """The text between a document's `<!-- {name}:start ... -->` and `<!-- {name}:end -->` lines, whole: a rendered table
    is compared with all of it, so a row added inside the region fails (reach e85b7f33 gap 4)."""
    match = re.search(
        rf"^<!-- {re.escape(name)}:start[^\n]*-->\n(.*?)^<!-- {re.escape(name)}:end -->$",
        text,
        re.S | re.M,
    )
    assert match, name
    return match.group(1).rstrip("\n")


def local_build_commands() -> list[str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Local Build", 1)[1].split("\n## ", 1)[0]
    block = re.search(r"```bash\n(.*?)```", section, re.S)
    assert block
    return [
        line.strip()
        for line in block.group(1).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_readme_commands_name_what_exists():
    """Each documented command names a module, script, console script or extra that exists (B-063, D8)."""
    import importlib.util

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    commands = local_build_commands()
    assert commands
    for command in commands:
        words = command.split()
        if words[:2] == ["python", "-m"] and words[2:]:
            spec = importlib.util.find_spec(words[2])
            assert spec and spec.origin, command
            assert 'if __name__ == "__main__"' in Path(spec.origin).read_text(), command
        elif words[0] == "python":
            assert (ROOT / words[1]).is_file(), command
        elif words[0] in project.get("scripts", {}):
            module, _, function = project["scripts"][words[0]].partition(":")
            assert callable(getattr(importlib.import_module(module), function)), command
        elif words[:2] == ["pip", "install"]:
            extras = re.findall(r"\[(\w+)\]", command)
            assert all(e in project["optional-dependencies"] for e in extras), command
        elif words[:2] in (["git", "clone"], ["cd", "voynich-data"]):
            continue
        else:
            assert words == ["pytest"], command  # no positional path


def test_metadata_command_runs_as_documented(tmp_path: Path):
    """`python -m builders.build_metadata` with no source argument builds from the cached ZL file (it exited 2; D8)."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "builders.build_metadata", "--output", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "pages.jsonl").is_file()


def test_vcat_verify_is_packaged():
    """The console script's module is in the packages setuptools installs (it was not: `vcat-verify` failed on import)."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    module = project["project"]["scripts"]["vcat-verify"].split(":")[0]
    package = module.split(".")[0]
    include = project["tool"]["setuptools"]["packages"]["find"]["include"]
    assert any(re.fullmatch(pattern.replace("*", ".*"), package) for pattern in include), include
    assert (ROOT / package / "__init__.py").is_file()


def test_pytest_is_configured_in_one_place():
    """pytest reads pytest.ini; a second configuration in pyproject.toml would be dead (B-005, DECISIONS Q5)."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "pytest" not in project.get("tool", {})
    assert (ROOT / "pytest.ini").is_file()


DOCS_WITH_PATHS = [
    "README.md",
    "CONTRIBUTING.md",
    "STABILITY.md",
    "ERRATA.md",
    "docs/sources.md",
    "docs/PUBLISHING.md",
    "docs/SOURCES_LICENSE.md",
    # every document the transliterations item changed (reach 0dea398a gap 7)
    "docs/data_model.md",
    "huggingface/voynich-transliterations/README.md",
]

#: The extensions of repository files a document names by a bare file name (`pytest.ini`, `ERRATA.md`).
FILE_SUFFIXES = (
    ".md",
    ".py",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".sh",
    ".json",
    ".ipynb",
)


def _link_destinations(text: str) -> list[str]:
    """The destination of every Markdown link that is not a URL, a mail address or an anchor: inline links, with or
    without a title or angle brackets, and reference definitions (`[x]: path`; reach e85b7f33 gap 5, B-085).
    """
    found = []
    inline = re.findall(
        r"\]\(\s*(?:<([^>]*)>|([^)\s]+))(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)", text
    )
    reference = re.findall(r"^ {0,3}\[[^\]]+\]:\s*(?:<([^>]*)>|(\S+))", text, re.M)
    for target in [a or b for a, b in inline + reference]:
        target = target.split("#", 1)[0]
        if target and not re.match(r"[a-z][a-z0-9+.-]*:", target):
            found.append(target)
    return found


@pytest.mark.parametrize("doc", DOCS_WITH_PATHS)
def test_documented_repository_paths_exist(doc: str):
    """Every repository path a current document names exists (B-063: `data_sources/raw_sources`,
    `data_sources/fetch_sources.py` and `output/README.md` did not).

    - A backticked token names a path from the repository root: under any directory of the repository, hidden ones such as
      `.github` included, or a bare file name of the root (reach b09d5b4b gap 8, reach dd4ff650 gap 6).
    - A Markdown link destination is resolved from the document's own directory, as a reader's browser resolves it, and
      always checked, whatever its form (`../x`, `dir/x`, `x`; review ea46bb38 finding 1)."""
    path_of_doc = ROOT / doc
    text = path_of_doc.read_text(encoding="utf-8")
    roots = {p.name for p in ROOT.iterdir() if p.is_dir()}
    checked = 0
    for path in re.findall(r"`([A-Za-z0-9_./-]+)`", text):
        if "*" in path:
            continue
        if ("/" in path and path.split("/", 1)[0] in roots) or (
            "/" not in path and path.endswith(FILE_SUFFIXES)
        ):
            assert (ROOT / path).exists(), (doc, path)
            checked += 1
    for destination in _link_destinations(text):
        assert (path_of_doc.parent / destination).exists(), (doc, destination)
        checked += 1
    assert checked or doc.startswith("docs/"), doc
