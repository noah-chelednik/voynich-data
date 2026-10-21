# tests/regressions/audit_20261021_tests/test_finding_1.py
"""AT 20261021 F1: the issue-form checks' "what a reader sees" (B-086) still counts content GitHub never shows.

A link whose text is empty renders as nothing, yet `_linked_documents` counts it as linking the document; text inside a
`<script>` element is removed with its contents by GitHub's sanitizer (and never displayed by a browser), yet `as_shown`
returns it as shown text, so it satisfies `test_transcription_errors_go_upstream`'s instruction check."""

from tests import test_stability as checks

URL = "https://github.com/noah-chelednik/voynich-data/blob/main/STABILITY.md"


def test_an_empty_link_links_nothing_a_reader_can_see():
    assert checks._linked_documents(f"[]({URL})", None) == set()


def test_script_text_is_not_shown():
    shown = " ".join(checks.as_shown("<script>never corrects; report upstream</script>").text)
    assert "never corrects" not in shown, shown
