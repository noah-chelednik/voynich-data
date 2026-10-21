import contextlib, copy, io, json
from pathlib import Path
from unittest.mock import patch
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from parsers import IVTFFParser
from vcat.charset import validate_text_clean
from vcat.loss_accounting import resolve_source

OUT=Path('output').resolve()
BASE=json.loads((OUT/'eva_lines_build_report.json').read_text())
ROWS=[json.loads(s) for s in (OUT/'eva_lines.jsonl').read_text().splitlines()]
parser=IVTFFParser()
pages=list(parser.parse_file(resolve_source(BASE['source_file'])))
languages={}
for page in pages:
    lang=page.variables.language or 'unknown'
    languages[lang]=languages.get(lang,0)+1
print('recomputed_pages_by_language',languages)
charset=[(r['line_id'],sorted(validate_text_clean(r['text_clean'])[1])) for r in ROWS if not validate_text_clean(r['text_clean'])[0]]
print('recomputed_charset_warnings',charset)

def observe(change):
    report=copy.deepcopy(BASE)
    if change=='erased_warnings': report['warnings']=[]
    elif change=='missing_warnings': report.pop('warnings')
    elif change=='false_languages': report['pages_by_language']={'A':len(pages)}
    elif change=='false_sections': report['pages_by_section']={'herbal':len(pages)}
    elif change=='missing_page_summaries':
        report.pop('pages_by_language'); report.pop('pages_by_section')
    elif change=='wrong_total_control': report['total_lines']+=1
    else: assert change=='baseline'
    original_text=Path.read_text
    def read_text(path,*args,**kwargs):
        if path==OUT/'eva_lines_build_report.json': return json.dumps(report)
        return original_text(path,*args,**kwargs)
    with patch.object(phase,'load_build_report',lambda path:copy.deepcopy(report)), patch.object(Path,'read_text',read_text):
        with contextlib.redirect_stdout(io.StringIO()):
            success,errors=phase.validate_outputs(OUT)
            invariant=inv.verify_all_invariants(OUT)
    return {'phase':success,'invariants':invariant.passed,'phase_errors':errors,'invariant_errors':invariant.failures}

for change in ['baseline','wrong_total_control','erased_warnings','missing_warnings','false_languages','false_sections','missing_page_summaries']:
    print(change,json.dumps(observe(change),sort_keys=True),flush=True)


def test_f1_eva_report_requires_true_warnings_and_page_summaries():
    baseline = observe("baseline")
    control = observe("wrong_total_control")
    for checker in ("phase", "invariants"):
        assert baseline[checker]
        assert not control[checker]
    for change in (
        "erased_warnings",
        "missing_warnings",
        "false_languages",
        "false_sections",
        "missing_page_summaries",
    ):
        result = observe(change)
        for checker in ("phase", "invariants"):
            assert not result[checker], (change, checker, result)
