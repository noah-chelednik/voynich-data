import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
from builders.build_metadata import build_metadata_datasets
from parsers import IVTFFParser
from validators.validate_phase1_outputs import check_metadata, validate_outputs
from validators.verify_invariants import verify_all_invariants
from vcat.sources import ROOT, source_file

OUT = ROOT / 'output'
READ_TEXT = Path.read_text
READ_TABLE = pq.read_table


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@contextlib.contextmanager
def candidate(tables=None, report=None, mismatch=None):
    tables = tables or {}

    def text(path, *args, **kwargs):
        p = path.resolve()
        if p.parent == OUT / 'metadata':
            if p.name == 'metadata_report.json' and report is not None:
                return json.dumps(report)
            if p.suffix == '.jsonl' and p.stem in tables:
                return ''.join(json.dumps(r) + '\n' for r in tables[p.stem])
        return READ_TEXT(path, *args, **kwargs)

    def table(path, *args, **kwargs):
        p = Path(path).resolve()
        if p == OUT / 'mismatch_index.parquet' and mismatch is not None:
            return pa.Table.from_pylist(mismatch)
        if p.parent == OUT / 'metadata' and p.stem in tables:
            return pa.Table.from_pylist(tables[p.stem])
        return READ_TABLE(path, *args, **kwargs)

    with patch.object(Path, 'read_text', text), patch.object(pq, 'read_table', table):
        yield


def decisions():
    with contextlib.redirect_stdout(io.StringIO()):
        phase, _ = validate_outputs(OUT)
        invariant = verify_all_invariants(OUT).passed
    return phase, invariant


def test_rejects_empty_quire_memberships():
    assert check_metadata(OUT) == []
    quires = rows(OUT / 'metadata/quires.jsonl')
    assert all(r['folio_ids'] for r in quires)
    for row in quires:
        row.update(folio_ids=[], folio_count=0, page_count=0, total_lines=0)
    with candidate(tables={'quires': quires}):
        actual = decisions()
    assert actual == (False, False), actual


def test_rejects_one_character_source_hash():
    report = json.loads((OUT / 'metadata/metadata_report.json').read_text())
    report['source_hash'] = report['source_hash'][0]
    with candidate(report=report):
        actual = decisions()
    assert actual == (False, False), actual


def test_rejects_reversed_mismatch_parquet():
    original = rows(OUT / 'mismatch_index.jsonl')
    reversed_rows = list(reversed(original))
    assert reversed_rows != original
    with candidate(mismatch=reversed_rows):
        actual = decisions()
    assert actual == (False, False), actual


def test_rejects_emitted_locus_as_rejected_page():
    source = ROOT / source_file('CD')
    parser = IVTFFParser()
    pages = list(parser.parse_file(source))
    warning = next(w for w in parser.warnings if w.emitted_id and not w.page_id and not w.locus_id)
    identifier = warning.emitted_id
    assert identifier in {l.locus_id for p in pages for l in p.loci}
    assert identifier not in {p.page_id for p in pages}
    result = build_metadata_datasets(source)
    tables, report = result.tables(), result.report.to_dict()
    assert report['reported_pages'] == []
    with candidate(tables=tables, report=report):
        assert check_metadata(OUT) == []
    report['reported_pages'] = [identifier]
    with candidate(tables=tables, report=report):
        actual = decisions()
    assert actual == (False, False), actual


if __name__ == '__main__':
    for test in (
        test_rejects_empty_quire_memberships,
        test_rejects_one_character_source_hash,
        test_rejects_reversed_mismatch_parquet,
        test_rejects_emitted_locus_as_rejected_page,
    ):
        try:
            test()
        except AssertionError as error:
            print(test.__name__, 'FAIL', str(error), flush=True)
        else:
            print(test.__name__, 'PASS', flush=True)
