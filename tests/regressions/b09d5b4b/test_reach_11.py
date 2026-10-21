# tests/regressions/b09d5b4b/test_reach_11.py
import pytest

from tests.test_ci_checks import _skip_and_xfail_uses


@pytest.mark.parametrize(
    "source",
    [
        "from pytest import skip as skip_test\nskip_test('reason')\n",
        "from pytest import xfail\nxfail('reason')\n",
    ],
)
def test_policy_guard_reaches_imported_skip_and_xfail(source):
    assert any(
        _skip_and_xfail_uses(
            "tests/probe.py",
            "import pytest\npytest.skip('reason')\n",
        )
    )
    assert any(_skip_and_xfail_uses("tests/probe.py", source))
