import contextlib
import copy
import io
import json
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from vcat.loss_accounting import census_source
from vcat.sources import source_file

ROOT = Path(phase.__file__).resolve().parents[1]
OUT = ROOT / 'output'


def rows(name):
    return [json.loads(line) for line in (OUT / name).read_text().splitlines()]


def scenario(name):
    text, tables = {}, {}
    if name in ('missing_cd', 'missing_zl'):
        changed = rows('mismatch_index.jsonl')
        sid = name.removeprefix('missing_')
        ids = set(census_source(ROOT / source_file(sid.upper())).loci)
        row = next(r for r in changed if sid in r['sources_present'] and r['line_id'] in ids)
        row['sources_present'].remove(sid)
        text['mismatch_index.jsonl'] = '\n'.join(json.dumps(r) for r in changed)
        tables['mismatch_index.parquet'] = changed
    elif name in ('false_mismatch_total', 'missing_mismatch_summary', 'erased_cd_warning'):
        report = json.loads((OUT / 'mismatch_report.json').read_text())
        if name == 'false_mismatch_total':
            report['total_lines'] = len(rows('mismatch_index.jsonl')) + 1
        elif name == 'missing_mismatch_summary':
            report = {'sources': report['sources']}
        else:
            assert report['sources']['cd']['warnings']
            report['sources']['cd']['warnings'] = []
        text['mismatch_report.json'] = json.dumps(report)
    elif name == 'false_manifest_total':
        manifest = json.loads((OUT / 'release_manifest.json').read_text())
        manifest['statistics']['total_records'] = len(rows('eva_lines.jsonl')) + 1
        text['release_manifest.json'] = json.dumps(manifest)
    elif name in ('listed_bad_parquet', 'unlisted_bad_parquet'):
        changed = rows('eva_lines.jsonl')
        changed[0]['text_raw'] += 'forged'
        tables['eva_lines.parquet'] = changed
        if name == 'unlisted_bad_parquet':
            manifest = json.loads((OUT / 'release_manifest.json').read_text())
            assert any(e['name'] == 'eva_lines.parquet' for e in manifest['files'])
            manifest['files'] = [e for e in manifest['files'] if e['name'] != 'eva_lines.parquet']
            text['release_manifest.json'] = json.dumps(manifest)
    else:
        assert name == 'baseline'
    return text, tables


def observe(name):
    text, tables = scenario(name)
    original_text, original_table = Path.read_text, pq.read_table
    def read_text(path, *args, **kwargs):
        if path.parent == OUT and path.name in text:
            return text[path.name]
        return original_text(path, *args, **kwargs)
    def read_table(path, *args, **kwargs):
        path = Path(path)
        if path.parent == OUT and path.name in tables:
            return pa.Table.from_pylist(tables[path.name])
        return original_table(path, *args, **kwargs)
    with patch.object(Path, 'read_text', read_text), patch.object(pq, 'read_table', read_table):
        with contextlib.redirect_stdout(io.StringIO()):
            phase_ok, _ = phase.validate_outputs(OUT)
            invariant_ok = inv.verify_all_invariants(OUT).passed
    return {'phase': phase_ok, 'invariants': invariant_ok}


@pytest.mark.parametrize('checker', ['phase', 'invariants'])
def test_f1_rejects_missing_cd_presence(checker):
    assert observe('baseline')[checker]
    assert not observe('missing_cd')[checker]


@pytest.mark.parametrize('checker', ['phase', 'invariants'])
@pytest.mark.parametrize('change', [
    'false_mismatch_total', 'missing_mismatch_summary',
    'erased_cd_warning', 'false_manifest_total',
])
def test_f2_rejects_false_or_missing_report_claims(checker, change):
    assert observe('baseline')[checker]
    assert not observe(change)[checker]


@pytest.mark.parametrize('checker', ['phase', 'invariants'])
def test_f3_rejects_unlisted_stale_eva_parquet(checker):
    assert observe('baseline')[checker]
    assert not observe('listed_bad_parquet')[checker]
    assert not observe('unlisted_bad_parquet')[checker]


if __name__ == '__main__':
    for name in (
        'baseline', 'missing_zl', 'missing_cd', 'false_mismatch_total',
        'missing_mismatch_summary', 'erased_cd_warning', 'false_manifest_total',
        'listed_bad_parquet', 'unlisted_bad_parquet',
    ):
        print(name, json.dumps(observe(name), sort_keys=True), flush=True)
