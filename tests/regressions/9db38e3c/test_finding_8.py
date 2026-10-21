# tests/regressions/9db38e3c/test_finding_8.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_stability_does_not_call_0_2_3_the_published_release():
    stability = (ROOT / "STABILITY.md").read_text(encoding="utf-8")
    assert "0.2.3 is the one published" not in stability
