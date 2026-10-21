# tests/regressions/audit_20261017_tests_r5/test_findings.py
import pytest

from tests.test_coverage_gaps import TestLoggingModule
from vcat.logging import ColoredFormatter


def test_f2_color_probe_rejects_plain_output(monkeypatch):
    check = TestLoggingModule().test_colored_formatter_with_colors_enabled
    check()

    monkeypatch.setattr(
        ColoredFormatter,
        "format",
        lambda self, record: record.getMessage(),
    )
    with pytest.raises(AssertionError):
        check()
