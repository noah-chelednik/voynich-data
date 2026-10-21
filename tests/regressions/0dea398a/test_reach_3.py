# tests/regressions/0dea398a/test_reach_3.py
from dataclasses import replace

import pytest

from builders import build_transliterations as bt
from vcat.sources import nonconforming_lines


def test_unlisted_unidentified_rejections_fail_before_writing(monkeypatch, tmp_path):
    record = next(r for r in bt.dataset_sources() if r.id == "LSI")
    listed = nonconforming_lines(record.path)
    assert listed

    lines = record.path.read_bytes().splitlines(keepends=True)
    for number in listed:
        lines[number - 1] = b"# former malformed locus\n"
    payload = b"".join(lines)
    if not payload.endswith((b"\n", b"\r")):
        payload += b"\n"
    payload += b"unrecognized source record\n" * len(listed)

    candidate = tmp_path / record.path.name
    candidate.write_bytes(payload)
    changed = replace(record, file=str(candidate))
    monkeypatch.setattr(bt, "dataset_sources", lambda: [changed])

    output = tmp_path / "out"
    with pytest.raises(ValueError):
        bt.build_transliterations(output)
    assert not output.exists()
