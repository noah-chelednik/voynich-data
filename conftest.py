"""
The no-skip, no-xfail policy at run time (DECISIONS Q6, Q56): every test that is collected runs and its outcome is pass or
fail. A skipped or xfailed outcome, however it was produced (a marker, `pytest.skip`, `unittest`'s `skipTest` or
`expectedFailure`, an empty parameter set, a module-level skip), is turned into a failure that names it. The static guard
`tests/test_ci_checks.py::test_no_skips_and_no_xfails` remains, so a skip is also refused before it runs (AT4 F1).
"""

from __future__ import annotations

import pytest


def _forbidden(kind: str, nodeid: str) -> str:
    return f"VCAT runs every test: {nodeid} was {kind}, which the suite forbids (DECISIONS Q6, Q56)"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.skipped:
        kind = "xfailed" if hasattr(report, "wasxfail") else "skipped"
        report.outcome = "failed"
        report.longrepr = _forbidden(kind, item.nodeid)
        # pytest's session counter does not count a report that still carries wasxfail as a failure (reach 3f9c87ec
        # gap 1), so the converted report must not carry it
        if hasattr(report, "wasxfail"):
            del report.wasxfail


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    outcome = yield
    report = outcome.get_result()
    if report.skipped:
        report.outcome = "failed"
        report.longrepr = _forbidden("skipped at collection", collector.nodeid)
