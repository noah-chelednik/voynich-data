import builtins, contextlib, copy, hashlib, io, json
from pathlib import Path
from unittest.mock import patch
import pyarrow as pa
import pyarrow.parquet as pq
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
OUT=Path('output').resolve()
BASE_ROWS=[json.loads(s) for s in (OUT/'eva_lines.jsonl').read_text().splitlines()]
BASE_MANIFEST=json.loads((OUT/'release_manifest.json').read_text())

def observe(change):
    rows=copy.deepcopy(BASE_ROWS)
    row=next(r for r in rows if r['illustration_type']=='H' and r['section']=='herbal')
    if change=='wrong_section': row['section']='biological'
    elif change=='missing_section': row.pop('section')
    elif change=='wrong_illustration_control': row['illustration_type']='B'
    else: assert change=='baseline'
    encoded=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':')) for r in rows)+'\n').encode()
    manifest=copy.deepcopy(BASE_MANIFEST)
    for entry in manifest['files']:
        if entry['name']=='eva_lines.jsonl':entry['sha256']=hashlib.sha256(encoded).hexdigest()
    contents={OUT/'eva_lines.jsonl':encoded,OUT/'release_manifest.json':json.dumps(manifest).encode()}
    old_builtin,old_io,old_table=builtins.open,io.open,pq.read_table
    def open_with(original):
        def wrapped(file,mode='r',*args,**kwargs):
            path=Path(file).resolve() if isinstance(file,(str,Path)) else None
            if path in contents:
                assert mode in ('r','rb')
                return io.BytesIO(contents[path]) if 'b' in mode else io.StringIO(contents[path].decode())
            return original(file,mode,*args,**kwargs)
        return wrapped
    def table(path,*args,**kwargs):
        if Path(path).resolve()==OUT/'eva_lines.parquet':return pa.Table.from_pylist(rows)
        return old_table(path,*args,**kwargs)
    with patch.object(builtins,'open',open_with(old_builtin)),patch.object(io,'open',open_with(old_io)),patch.object(pq,'read_table',table):
        with contextlib.redirect_stdout(io.StringIO()):
            ok,errors=phase.validate_outputs(OUT)
            invariant=inv.verify_all_invariants(OUT)
    return {'phase':ok,'invariants':invariant.passed,'phase_errors':errors[:1],'invariant_errors':invariant.failures[:1]}

for change in ['baseline','wrong_illustration_control','wrong_section','missing_section']:
    print(change,json.dumps(observe(change),sort_keys=True),flush=True)


def test_f2_section_matches_the_documented_illustration_mapping():
    baseline = observe("baseline")
    control = observe("wrong_illustration_control")
    changed = observe("wrong_section")
    for checker in ("phase", "invariants"):
        assert baseline[checker]
        assert not control[checker]
        assert not changed[checker], (checker, changed)
