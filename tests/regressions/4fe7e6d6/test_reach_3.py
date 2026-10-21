# tests/regressions/4fe7e6d6/test_reach_3.py
"""Clause 3: instructions hidden in an HTML comment satisfy neither issue-form check. A comment opened and not closed
(`<!--` with no `-->`) hides everything after it on GitHub (an HTML parser ends the comment at the end of the input),
and CommonMark passes it through as a raw HTML block; but `as_shown` feeds it to Python's HTMLParser, which on close()
reports an unterminated comment as data, so the hidden instructions count as shown text."""
from pathlib import Path

import pytest
import yaml

from tests import test_stability as checks


def test_instructions_in_an_unclosed_comment_are_refused(monkeypatch):
    target = checks.TEMPLATES / "transcription_error.yml"
    original_read = Path.read_text
    checks.test_transcription_errors_go_upstream()  # passes as committed
    form = yaml.safe_load(original_read(target, encoding="utf-8"))
    for item in form["body"]:
        if item.get("type") == "markdown":
            item["attributes"]["value"] = "<!--\n" + item["attributes"]["value"]
    rendered = checks.MarkdownIt("commonmark").render(
        next(i for i in form["body"] if i.get("type") == "markdown")["attributes"]["value"]
    )
    assert rendered.startswith("<!--") and "-->" not in rendered  # one comment, open to the end: nothing shown
    replacement = yaml.safe_dump(form, sort_keys=False)

    def read_text(path, *args, **kwargs):
        if Path(path).resolve() == target.resolve():
            return replacement
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(AssertionError):
        checks.test_transcription_errors_go_upstream()
