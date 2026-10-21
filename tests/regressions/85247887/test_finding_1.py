# tests/regressions/85247887/test_finding_1.py
from pathlib import Path

import pytest

from tests import test_paperwork as checks


@pytest.mark.parametrize("style", ("titled", "reference"))
def test_path_guard_checks_markdown_link_forms(monkeypatch, style):
    doc = "README.md"
    checks.test_documented_repository_paths_exist(doc)
    target = checks.ROOT / doc
    missing = "tests/__review_missing_85247887__.py"
    assert not (checks.ROOT / missing).exists()

    read_text = Path.read_text
    addition = f"\n[review control]({missing})\n"

    def replacement(self, *args, **kwargs):
        text = read_text(self, *args, **kwargs)
        return text + addition if self == target else text

    monkeypatch.setattr(Path, "read_text", replacement)

    # Positive control: the ordinary inline spelling is checked.
    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)

    if style == "titled":
        addition = f'\n[review destination]({missing} "proof")\n'
    else:
        addition = (
            "\n[review destination][review-85247887]\n\n"
            f"[review-85247887]: {missing}\n"
        )

    with pytest.raises(AssertionError):
        checks.test_documented_repository_paths_exist(doc)
