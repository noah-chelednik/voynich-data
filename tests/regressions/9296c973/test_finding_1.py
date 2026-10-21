# tests/regressions/9296c973/test_finding_1.py
import json
import re
import shutil
from pathlib import Path

from validators.validate_phase1_outputs import check_manifest_files


def test_documented_eva_publication_satisfies_its_manifest(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output = root / "output"
    guide = (root / "docs/PUBLISHING.md").read_text()
    row = next(
        line for line in guide.splitlines()
        if line.startswith("| `Ched-ai/voynich-eva` |")
    )
    published = re.findall(r"`(output/[^`]+)`", row)
    assert published
    records = [
        json.loads(line)
        for line in (output / "eva_lines.jsonl").read_text().splitlines()
    ]

    # Positive control: the complete build satisfies its own manifest.
    assert check_manifest_files(output, records) == []

    # Stage exactly the files the publishing table instructs us to upload.
    for relative in published:
        source = root / relative
        assert source.is_file(), relative
        shutil.copy2(source, tmp_path / source.name)

    assert (tmp_path / "release_manifest.json").is_file()
    errors = check_manifest_files(tmp_path, records)
    assert not errors, errors
