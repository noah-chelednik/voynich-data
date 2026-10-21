# tests/regressions/audit_20261016_parsers/test_finding_1.py
import warnings

from parsers import parse_ivtff


def test_parse_ivtff_does_not_hide_rejected_loci(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0> good\n",
        encoding="utf-8",
    )
    assert [
        locus.locus_id
        for page in parse_ivtff(source)
        for locus in page.loci
    ] == ["f1r:1"]

    source.write_text(
        source.read_text(encoding="utf-8")
        + "<f1r.2,@Pz> rejected\n",
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        try:
            parse_ivtff(source)
        except ValueError:
            return

    assert any("f1r:2" in str(w.message) for w in notices), (
        "A list-only parsing helper must raise or expose the rejected locus."
    )
