from pathlib import Path
import re


def test_documented_source_files_exist():
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/sources.md").read_text()
    paths = re.findall(r"\*\*File\*\*: `([^`]+)`", text)
    assert paths
    assert all((root / path).is_file() for path in paths), paths
