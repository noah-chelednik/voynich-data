# tests/regressions/0fcd9966/test_finding_1.py
from pathlib import Path

import pytest

from parsers import IVTFFParser
from parsers.ivtff_roundtrip import rebuild_source
from vcat.sources import cached_sources, nonconforming_lines, source_encoding


@pytest.mark.parametrize("alias_kind", ["symlink", "copy"])
def test_registered_identity_survives_a_conflicting_basename(tmp_path, alias_kind):
    records = cached_sources()
    source = next(record for record in records if record.id == "LSI")
    other = next(record for record in records if record.encoding != source.encoding)
    alias = tmp_path / Path(other.file).name

    if alias_kind == "symlink":
        alias.symlink_to(source.path)
    else:
        alias.write_bytes(source.path.read_bytes())

    assert alias.read_bytes() == source.path.read_bytes()
    assert source_encoding(source.path) == source.encoding

    canonical = IVTFFParser()
    expected = [
        (locus.source_line, locus.identifier, locus.text_raw)
        for page in canonical.parse_file(source.path)
        for locus in page.loci
    ]
    through_alias = IVTFFParser()
    observed = [
        (locus.source_line, locus.identifier, locus.text_raw)
        for page in through_alias.parse_file(alias)
        for locus in page.loci
    ]

    assert expected
    assert rebuild_source(through_alias.document) == source.path.read_bytes()
    assert observed == expected
    assert source_encoding(alias) == source.encoding
    assert nonconforming_lines(alias) == nonconforming_lines(source.path)
