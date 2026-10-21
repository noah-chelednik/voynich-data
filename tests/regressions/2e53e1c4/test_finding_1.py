# tests/regressions/2e53e1c4/test_finding_1.py
import base64

import pytest

from tests import test_iiif as checks


def test_image_guard_reaches_hidden_repository_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    checks.test_links_are_links_never_images()

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
        "AAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )
    visible = tmp_path / "control.png"
    visible.write_bytes(png)
    with pytest.raises(AssertionError):
        checks.test_links_are_links_never_images()
    visible.unlink()

    hidden = tmp_path / ".github" / "manuscript.png"
    hidden.parent.mkdir()
    hidden.write_bytes(png)
    with pytest.raises(AssertionError):
        checks.test_links_are_links_never_images()
