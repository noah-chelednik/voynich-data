# tests/regressions/e85b7f33/test_reach_1.py
import hashlib
from dataclasses import replace

import pytest

from data_sources import verify_sources as verifier
from tests import test_sources as checks
from vcat import sources as registry


@pytest.mark.parametrize("gate", ["predicate", "verifier"])
def test_listing_version_checks_the_entire_preamble(tmp_path, monkeypatch, gate):
    original = next(r for r in checks.RECORDS if r.version_from == "listing")
    cache = tmp_path / "data_sources" / "cache"
    cache.mkdir(parents=True)
    path = cache / original.path.name
    payload = (
        b"#=IVTFF Eva- 2.0 D 9\n"
        b"\n\n\n\n"
        b"# Version 9z, explicitly supplied in the preamble\n"
        b"<f1r>\n"
        b"<f1r.1,@P0> daiin\n"
    )
    path.write_bytes(payload)
    record = replace(
        original,
        file=str(path),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    monkeypatch.setattr(registry, "cached_sources", lambda: [record])
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(
        verifier, "read_checksums", lambda: {path.name: record.sha256}
    )

    if gate == "predicate":
        with pytest.raises(AssertionError):
            checks.test_each_record_pins_its_file(record)
    else:
        result = verifier.verify_cache()
        assert result["_metadata"]["all_pass"] is False
