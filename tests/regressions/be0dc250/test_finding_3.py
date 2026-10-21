# tests/regressions/be0dc250/test_finding_3.py
"""The Phase 0 checks are said to be gone from `vcat-verify` (B-087); each check the module keeps must be one a run
reaches, or its tests test nothing that runs."""
import inspect

from data_sources import verify_sources


def test_every_kept_verify_check_is_reached_by_a_run():
    reached = inspect.getsource(verify_sources.main) + inspect.getsource(verify_sources.run_all_verifications)
    reached += inspect.getsource(verify_sources.verify_cache)
    for name in ("verify_lsi_file", "verify_voynich_nu"):
        assert not hasattr(verify_sources, name) or f"{name}(" in reached, name
