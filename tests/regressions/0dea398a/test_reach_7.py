# tests/regressions/0dea398a/test_reach_7.py
from pathlib import Path

import pytest

from tests import test_paperwork as checks


@pytest.mark.parametrize(
    "document",
    [
        "docs/data_model.md",
        "huggingface/voynich-transliterations/README.md",
    ],
)
def test_document_path_guard_reaches_item_documents(monkeypatch, document):
    target = checks.ROOT / document
    missing = "output/reach_missing_documented_file.jsonl"
    assert not (checks.ROOT / missing).exists()

    original_read_text = Path.read_text
    changed = (
        original_read_text(target, encoding="utf-8")
        + f"\nThe documented output is `{missing}`.\n"
    )

    def read_text(path, *args, **kwargs):
        if path == target:
            return changed
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(AssertionError):
        for selected in checks.DOCS_WITH_PATHS:
            checks.test_documented_repository_paths_exist(selected)
