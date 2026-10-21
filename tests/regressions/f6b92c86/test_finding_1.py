# tests/regressions/f6b92c86/test_finding_1.py
from builders.build_eva_lines import build_eva_lines


def test_undecodable_page_header_ends_previous_page_context(tmp_path):
    source = tmp_path / "source.txt"
    prefix = (
        b"#=IVTFF Eva- 2.0 M 5\n"
        b"<f1r> <! $L=A>\n"
        b"<f1r.1,@P0> qokedy\n"
    )
    tail = (
        b"<f1r.2,+P0> daiin\n"
        b"<f2r> <! $L=B>\n"
        b"<f2r.1,@P0> shedy\n"
    )

    for damaged in (False, True):
        header = (
            b"<f1v> <! \xff>\n"
            if damaged
            else b"<f1v> <! $L=B>\n"
        )
        source.write_bytes(prefix + header + tail)
        records, report = build_eva_lines(source, tmp_path / "out")

        assert [record.line_id for record in records] == [
            "f1r:1",
            "f2r:1",
        ]
        assert report.reported_loci == ["f1r:2"]
        assert report.reported_pages == (["f1v"] if damaged else [])
        assert not report.loss_problems()
