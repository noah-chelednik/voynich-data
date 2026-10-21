# tests/regressions/audit_20261017_builders/test_finding_4.py
import importlib
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path


def test_eva_build_timestamp_records_the_actual_instant(monkeypatch):
    module = importlib.import_module("builders.build_eva_lines")
    root = Path(__file__).resolve().parents[3]
    instant = datetime(2026, 10, 17, 12, tzinfo=UTC)
    local_zone = timezone(timedelta(hours=-4))

    class Clock:
        @staticmethod
        def now(tz=None):
            if tz is None:
                return instant.astimezone(local_zone).replace(tzinfo=None)
            return instant.astimezone(tz)

    monkeypatch.setattr(module, "datetime", Clock)
    _, report = module.build_eva_lines(
        root / "data_sources/cache/ZL3b-n.txt",
        root / "output",
    )
    assert datetime.fromisoformat(report.build_date) == instant
