# tests/regressions/c5c2dbe8/test_finding_1.py
"""Claim 3 (a quote holds its value as the page writes it, neither rounded nor a fragment) with claim 6 (the pin check
confirms each quote on its page): a quote cut short inside one of the page's numbers ("... 188,862 3.86" on a page that
writes "188,862 3.862") is a substring of the page, so the pin check confirms it, and the registry test then accepts
the rounded value 3.86, which VCAT's acceptance test also meets. A rounded value lands with every check green."""
import copy
import hashlib

import yaml

from scripts import check_references as checker
from tests import test_reference_checks as checks

ROW = "Voynich MS ZL transcr. (Eva) 188,862 3.862 3.206 2.541"
CUT = "Voynich MS ZL transcr. (Eva) 188,862 3.86"  # ends inside the page's 3.862


def test_a_quote_cut_inside_a_page_number_is_refused(tmp_path, monkeypatch):
    # the registry as committed, with zl-h1 rounded and its quote cut to match
    registry = copy.deepcopy(checks.REGISTRY)
    for r in registry["references"]:
        if r["id"] == "zl-h1":
            r["value"] = 3.86
            r["quote"] = CUT
    monkeypatch.setattr(checks, "REGISTRY", registry)
    monkeypatch.setattr(checks, "REFERENCES", {r["id"]: r for r in registry["references"]})
    try:
        checks.test_the_registry_is_well_formed()
        registry_refused = False
    except AssertionError:
        registry_refused = True

    # the pin check over a page that writes the row whole, as the pinned page does
    page = tmp_path / "docs" / "reference" / "page.html"
    page.parent.mkdir(parents=True)
    page.write_bytes(
        b"<p>In these figures, spaces have not been counted as characters.</p>"
        b"<tr><td>Voynich MS ZL transcr. (Eva)</td><td>188,862</td><td>3.862</td><td>3.206</td><td>2.541</td></tr>"
    )
    small = {
        "pages": [
            {
                "id": "zandbergen-entropy",
                "url": "https://www.voynich.nu/extra/sol_ent.html",
                "file": "docs/reference/page.html",
                "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                "method": "In these figures, spaces have not been counted as characters.",
            }
        ],
        "references": [{"id": "zl-h1", "page": "zandbergen-entropy", "quote": CUT}],
    }
    path = tmp_path / "references.yaml"
    path.write_text(yaml.safe_dump(small), encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "REGISTRY", path)
    assert ROW in checker.page_text(page.read_bytes())  # the page writes 3.862, not 3.86
    pin_refused = checker.main([]) != 0

    assert registry_refused or pin_refused, (
        "the rounded value 3.86, quoted by cutting the page's 3.862, passes the registry test and the pin check"
    )
