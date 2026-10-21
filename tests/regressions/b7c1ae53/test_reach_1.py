# tests/regressions/b7c1ae53/test_reach_1.py
import base64

import pytest

from tests import test_iiif as checks


def test_no_image_guard_reaches_docs(tmp_path, monkeypatch):
    checks.test_links_are_links_never_images()

    (tmp_path / "data_sources").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    image = docs / "manuscript.png"
    image.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
        )
    )
    monkeypatch.setattr(checks, "ROOT", tmp_path)

    with pytest.raises(AssertionError):
        checks.test_links_are_links_never_images()
