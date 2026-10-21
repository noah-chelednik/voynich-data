# tests/regressions/8e09e8e7/test_reach_1.py
from parsers import IVTFFParser
from parsers.ivtff_roundtrip import rebuild_source
from vcat.sources import cached_sources, source_encoding


def test_registered_source_encoding_survives_a_symlink(tmp_path):
    record = next(source for source in cached_sources() if source.id == "LSI")
    alias = tmp_path / "registered-source-alias.txt"
    alias.symlink_to(record.path)
    assert alias.samefile(record.path)

    canonical = IVTFFParser()
    expected = [
        (locus.source_line, locus.identifier, locus.text_raw)
        for page in canonical.parse_file(record.path)
        for locus in page.loci
    ]

    through_alias = IVTFFParser()
    observed = [
        (locus.source_line, locus.identifier, locus.text_raw)
        for page in through_alias.parse_file(alias)
        for locus in page.loci
    ]

    # Preserved rejected bytes alone do not establish correct decoding.
    assert rebuild_source(through_alias.document) == record.path.read_bytes()
    assert observed == expected
    assert source_encoding(alias) == record.encoding
