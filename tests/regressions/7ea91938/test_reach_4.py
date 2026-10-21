# tests/regressions/7ea91938/test_reach_4.py
"""Claim 6 (the pin check confirms each quote on its pinned page and refuses a missing quote): quotes are gathered per
page, so a reference whose page is not among the pinned pages is never checked, and the checker says OK and exits 0."""
import hashlib

import yaml

from scripts import check_references as checker


def test_a_quote_on_no_pinned_page_is_refused(tmp_path, monkeypatch, capsys):
    page = tmp_path / "docs" / "reference" / "page.html"
    page.parent.mkdir(parents=True)
    page.write_bytes(b"<p>Method sentence.</p><td>Row</td> <td>3.862</td>")
    registry = {
        "pages": [
            {
                "id": "p",
                "url": "https://www.voynich.nu/x.html",
                "file": "docs/reference/page.html",
                "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                "method": "Method sentence.",
            }
        ],
        "references": [
            {"page": "p", "quote": "Row 3.862"},
            {"page": "q", "quote": "Row 9.999"},  # on no page: not confirmed
        ],
    }
    path = tmp_path / "references.yaml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "REGISTRY", path)
    code = checker.main([])
    out = capsys.readouterr().out
    assert code == 1, out
