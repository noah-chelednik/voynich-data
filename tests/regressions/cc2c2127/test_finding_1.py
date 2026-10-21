# tests/regressions/cc2c2127/test_finding_1.py
from copy import deepcopy
import json

from data_sources import verify_sources as verifier
from vcat import sources


def test_online_verification_preserves_registry_failure(tmp_path, monkeypatch):
    registry = sources.load_sources()

    def online_success():
        return {
            "probe": {
                "is_success": True,
                "url": "mock://reachable",
                "errors": [],
            },
            "_metadata": {"all_pass": True},
        }

    monkeypatch.setattr(verifier, "run_all_verifications", online_success)
    args = ["--online", "--reports-dir", str(tmp_path)]

    # Positive control: successful cache and online checks are accepted.
    assert verifier.main(args) == 0

    broken = deepcopy(registry)
    broken["cached"].append(deepcopy(broken["cached"][0]))
    monkeypatch.setattr(sources, "load_sources", lambda *a, **kw: broken)

    assert verifier.verify_cache()["_metadata"]["all_pass"] is False
    assert verifier.main(args) != 0

    receipt = json.loads(
        (tmp_path / "source_verification.json").read_text()
    )
    assert receipt["_metadata"]["all_pass"] is False
    assert "- Result: FAIL" in (
        tmp_path / "source_verification_report.md"
    ).read_text()
