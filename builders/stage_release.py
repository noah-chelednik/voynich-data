"""The release staging (roadmap item 2.9): each Hugging Face dataset repository as it would be published, built into a
LOCAL directory only (`release/staging/<repository>/`, git-ignored): its card, its LICENSE, the data files its configs
load and its build reports (`REPORTS`), copied from the committed build (`output/`). Nothing here uploads anything; publishing is a separate, manual step (`docs/PUBLISHING.md`).

Every layer is folded into `voynich-eva` as a configuration (`EVA_CONFIGS`), beside its `default` (the lines, as
published since 0.2.3). The other repositories keep their own configurations, so every config name and file path users
have today still loads (`PUBLISHED_CONFIGS`, read from the 0.2.3 cards; `tests/test_staging.py` proves it).

    python -m builders.stage_release            # into release/staging/
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
STAGING = ROOT / "release" / "staging"

#: The configurations of `voynich-eva`, in card order: name -> (the file in the repository, the build file it is, what a
#: row is). A file name is the build file's own; the names do not collide.
EVA_CONFIGS: dict[str, tuple[str, str, str]] = {
    "default": ("eva_lines.parquet", "eva_lines.parquet", "one locus of ZL (the lines)"),
    "words": ("eva_words.parquet", "eva_words.parquet", "one word of ZL's lines"),
    "pages": ("pages.parquet", "metadata/pages.parquet", "one page"),
    "folios": ("folios.parquet", "metadata/folios.parquet", "one folio"),
    "quires": ("quires.parquet", "metadata/quires.parquet", "one quire"),
    "bifolia": ("bifolia.parquet", "metadata/bifolia.parquet", "one sheet (conjugate leaves)"),
    "page_orders": (
        "page_orders.parquet",
        "metadata/page_orders.parquet",
        "one page in one named order",
    ),
    "page_canvases": (
        "page_canvases.parquet",
        "metadata/page_canvases.parquet",
        "one link from a page to Yale's images",
    ),
    "layers": (
        "layers.parquet",
        "metadata/layers.parquet",
        "one interpretive layer and its attribution",
    ),
    "mismatch": (
        "mismatch_index.parquet",
        "mismatch_index.parquet",
        "one locus of ZL or IT, compared",
    ),
    **{
        f"transliteration_{source.lower()}": (
            f"{source.lower()}.parquet",
            f"transliterations/{source.lower()}.parquet",
            f"one reading of {source}",
        )
        for source in ("ZL", "IT", "IT2a", "CD", "FG", "GC", "RF1b", "VT", "LSI")
    },
    "locus_variants": (
        "locus_variants.parquet",
        "transliterations/locus_variants.parquet",
        "one locus, every EVA reading side by side (not a consensus)",
    ),
    "word_alignments": (
        "word_alignments.parquet",
        "transliterations/word_alignments.parquet",
        "one reader's words of a locus aligned to the frame",
    ),
}

#: The repositories staged: name -> (the card directory, the build directory its files come from)
REPOSITORIES: dict[str, tuple[str, str]] = {
    "voynich-eva": ("huggingface/voynich-eva", ""),
    "voynich-manuscript-metadata": ("huggingface/voynich-manuscript-metadata", "metadata"),
    "voynich-transcription-mismatch": ("huggingface/voynich-transcription-mismatch", ""),
    "voynich-transliterations": ("huggingface/voynich-transliterations", "transliterations"),
}

#: The build's reports staged beside each repository's data, as `docs/PUBLISHING.md` lists them: provenance, totals and
#: checksums a user can check the data against (B-129, audit 20261021-builders F1). Paths under the repository's output
#: directory.
REPORTS: dict[str, tuple[str, ...]] = {
    "voynich-eva": (
        "eva_lines_build_report.json",
        "eva_words_report.json",
        "SHA256SUMS",
        "release_manifest.json",
    ),
    "voynich-manuscript-metadata": ("metadata_report.json",),
    "voynich-transcription-mismatch": ("mismatch_report.json",),
    "voynich-transliterations": (
        "transliterations_report.json",
        "variants_report.json",
        "coverage_matrix.csv",
    ),
}

#: The configurations users load today, as the 0.2.3 cards on `main` define them: repository -> {config: path}
PUBLISHED_CONFIGS: dict[str, dict[str, str]] = {
    "voynich-eva": {"default": "eva_lines.parquet"},
    "voynich-manuscript-metadata": {
        "pages": "pages.parquet",
        "folios": "folios.parquet",
        "quires": "quires.parquet",
    },
    "voynich-transcription-mismatch": {"default": "mismatch_index.parquet"},
}


def card_configs(card: Path) -> dict[str, list[str]]:
    """A card's configurations: name -> the paths of its data files, from its front matter."""
    text = card.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if match is None:
        raise ValueError(f"{card}: no front matter")
    front = yaml.safe_load(match.group(1))
    return {
        c["config_name"]: [f["path"] for f in c["data_files"]] for c in front.get("configs", [])
    }


def eva_front_matter_configs() -> str:
    """The `configs:` block of the `voynich-eva` card, rendered from `EVA_CONFIGS`."""
    lines = ["configs:"]
    for name, (path, _build, _what) in EVA_CONFIGS.items():
        lines += [
            f"  - config_name: {name}",
            "    data_files:",
            "      - split: train",
            f"        path: {path}",
        ]
    return "\n".join(lines)


def eva_configurations_table() -> str:
    """The card's table of its configurations, from `EVA_CONFIGS` and the layer registry's licenses."""
    lines = ["| Config | File | One row is |", "|---|---|---|"]
    for name, (path, _build, what) in EVA_CONFIGS.items():
        lines.append(f"| `{name}` | `{path}` | {what} |")
    return "\n".join(lines)


def build_file(repository: str, path: str) -> Path:
    """The build file a staged repository's data file is."""
    if repository == "voynich-eva":
        build = next(b for p, b, _ in EVA_CONFIGS.values() if p == path)
        return OUTPUT / build
    _card, directory = REPOSITORIES[repository]
    return OUTPUT / directory / path


def staged_files(repository: str) -> dict[str, Path]:
    """Every data file a repository's staging holds, by name, with the build file it is: each file its configurations
    load (required), that file's JSONL or Parquet twin where the build has one, and the repository's build reports
    (`REPORTS`, required)."""
    card, _directory = REPOSITORIES[repository]
    files: dict[str, Path] = {}
    for paths in card_configs(ROOT / card / "README.md").values():
        for path in paths:
            source = build_file(repository, path)
            if not source.is_file():
                # a configuration's file the build lacks fails the staging (reach d4385eb4 gap 2)
                raise FileNotFoundError(
                    f"{repository}: configuration file {path} is not built ({source})"
                )
            files[source.name] = source
            for twin in (source.with_suffix(".jsonl"), source.with_suffix(".parquet")):
                if twin.is_file():
                    files[twin.name] = twin
    _card, directory = REPOSITORIES[repository]
    for name in REPORTS[repository]:
        report = OUTPUT / directory / name
        if not report.is_file():
            # a report the documents promise and the build lacks fails the staging, as a configuration's file does
            raise FileNotFoundError(f"{repository}: report {name} is not built ({report})")
        files[name] = report
    return files


def is_staging(directory: Path, plan: dict[str, dict[str, Path]]) -> bool:
    """True for a directory holding only what `stage` writes: repository directories, each holding regular files named
    as this staging's plan names them (README.md, LICENSE and the staged files) and nothing else at any depth. A Hub
    clone's `.git`, a note, a subdirectory or a link is not the command's, so the directory is not a staging (review
    fc83f28e finding 1, 2fb5415b finding 1)."""
    if not directory.is_dir() or directory.is_symlink():
        return False
    for entry in directory.iterdir():
        if entry.name not in plan or entry.is_symlink() or not entry.is_dir():
            return False
        allowed = {"README.md", "LICENSE", *plan[entry.name]}
        for item in entry.iterdir():
            if item.name not in allowed or item.is_symlink() or not item.is_file():
                return False
    return True


def replaceable(staging: Path, plan: dict[str, dict[str, Path]]) -> bool:
    """A staging target may be replaced when it is an empty directory, or the default `release/staging/` (git-ignored,
    written only by this command) holding only what a staging holds."""
    if staging.is_symlink() or not staging.is_dir():
        return False
    if not any(staging.iterdir()):
        return True
    return staging.resolve() == STAGING.resolve() and is_staging(staging, plan)


def stage(staging: Path = STAGING) -> dict[str, list[str]]:
    """Stage every repository into `staging` (replaced whole): its card, LICENSE and `staged_files` (data and build
    reports). A missing configuration file or report stops it before anything is written. Returns repository -> the files staged.
    """
    plan = {repository: staged_files(repository) for repository in REPOSITORIES}
    staged: dict[str, list[str]] = {}
    if staging.exists():
        if not replaceable(staging, plan):
            # only this command's own staging is ever replaced: `--staging` names any directory, and a shape is not an
            # owner (the committed `huggingface/` and a directory of Hub clones have a staging's shape), so deleting
            # one this command did not write would lose a user's files (review 4c664493 finding 2, fc83f28e finding 1)
            raise FileExistsError(
                f"{staging} exists and is neither empty nor the command's own staging ({STAGING}); refusing to "
                "replace it"
            )
        shutil.rmtree(staging)
    for repository, (card, _directory) in REPOSITORIES.items():
        target = staging / repository
        target.mkdir(parents=True)
        for name in ("README.md", "LICENSE"):
            shutil.copy2(ROOT / card / name, target / name)
        for name, source in plan[repository].items():
            shutil.copy2(source, target / name)
        staged[repository] = sorted(p.name for p in target.iterdir())
    return staged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--staging", type=Path, default=STAGING)
    args = parser.parse_args(argv)
    try:
        staged = stage(args.staging)
    except FileExistsError as error:
        print(f"stage_release: {error}", file=sys.stderr)
        return 1
    for repository, files in staged.items():
        print(f"{repository}: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
