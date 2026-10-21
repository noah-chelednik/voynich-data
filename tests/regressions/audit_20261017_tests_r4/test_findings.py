# tests/regressions/audit_20261017_tests_r4/test_findings.py
import pytest

from tests.test_ci_checks import _skip_and_xfail_uses


@pytest.mark.parametrize(
    "source",
    [
        (
            "import unittest\n"
            "class TestProbe(unittest.TestCase):\n"
            "    def test_probe(self):\n"
            "        self.skipTest('unavailable')\n"
            "        self.fail('must run')\n"
        ),
        (
            "from unittest import TestCase\n"
            "class TestProbe(TestCase):\n"
            "    def setUp(self):\n"
            "        self.skipTest('unavailable')\n"
            "    def test_probe(self):\n"
            "        self.fail('must run')\n"
        ),
    ],
)
def test_f1_unittest_skip_test_is_rejected(source):
    control = (
        "import pytest\n"
        "def test_probe():\n"
        "    pytest.skip('unavailable')\n"
    )
    assert _skip_and_xfail_uses("tests/probe.py", control)[0]
    assert _skip_and_xfail_uses("tests/probe.py", source)[0], source
