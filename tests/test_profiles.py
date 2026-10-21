"""
Normalization profiles (roadmap item 1.6): named, versioned rule sets over the raw layer.

Each rule is tested on the real reference lines of the roadmap (f1r:7, f1r:17, f1r:19, f10r:11,
read from the ZL source at test time) and, over every locus of every cached source, against a second
implementation of the same rules written here with regular expressions, independent of the
tokenizer. No count is hand-written (principle 2).
"""

from __future__ import annotations

import contextlib
import io
import json
import re
from pathlib import Path

import pytest

from builders.build_eva_lines import build_eva_lines, export_to_jsonl
from parsers import IVTFFParser
from validators import validate_phase1_outputs as phase
from validators import verify_invariants as inv
from vcat import profiles as vp
from vcat.loss_accounting import CACHE_DIR
from vcat.sources import cached_sources
from vcat.text_processing import clean_text_for_analysis

ROOT = Path(__file__).resolve().parent.parent
CACHE = CACHE_DIR
# every cached file the registry records, wherever under the cache it is (review 0fcd9966 finding 2: LSI is in latin-1/)
SOURCES = sorted(source.path for source in cached_sources())
ZL = CACHE / "ZL3b-n.txt"
OUTPUT = ROOT / "output"


def zl_text_raw(locus_id: str) -> str:
    """The text of a ZL locus line, read from the source without the parser."""
    page, number = locus_id.split(":")
    for line in ZL.read_text(encoding="utf-8").splitlines():
        if match := re.match(rf"^<{page}\.{number},[^>]*>[ \t]*(.*)$", line):
            return match.group(1)
    raise AssertionError(f"{locus_id} not in {ZL.name}")


# --- the reference lines, each rule written out --------------------------------------------

#: For each roadmap reference line: what each profile makes of it. Written by hand from the rule
#: table, so a rule that changes shows here.
REFERENCE = {
    "f1r:7": {
        "raw-v1": "<%><!@252;>odar.{c'y}.shol.cphoy.oydar.sh.s.cfhoaiin.shodary",
        "diplomatic-v1": "odar.{c'y}.shol.cphoy.oydar.sh.s.cfhoaiin.shodary",
        "analysis-v1": "odar.c'y.shol.cphoy.oydar.sh.s.cfhoaiin.shodary",
        "no-uncertain-spaces-v1": "odar.c'y.shol.cphoy.oydar.sh.s.cfhoaiin.shodary",
    },
    "f1r:17": {
        "raw-v1": "ycho.tchey.chekain.sheo,pshol.dydyd.cthy.dai[{cto}:@194;]y",
        "diplomatic-v1": "ycho.tchey.chekain.sheo,pshol.dydyd.cthy.dai[{cto}:@194;]y",
        "analysis-v1": "ycho.tchey.chekain.sheo,pshol.dydyd.cthy.daictoy",
        "no-uncertain-spaces-v1": "ycho.tchey.chekain.sheopshol.dydyd.cthy.daictoy",
    },
    "f1r:19": {
        "raw-v1": "dchar.shcthaiin.okaiir.chey.@192;chy.@130;tol.cthols.dlo{ct}o",
        "diplomatic-v1": "dchar.shcthaiin.okaiir.chey.@192;chy.@130;tol.cthols.dlo{ct}o",
        "analysis-v1": "dchar.shcthaiin.okaiir.chey.@192;chy.@130;tol.cthols.dlocto",
        "no-uncertain-spaces-v1": "dchar.shcthaiin.okaiir.chey.@192;chy.@130;tol.cthols.dlocto",
    },
    "f10r:11": {
        "raw-v1": "@135;otchoshor.qoty.qotor.cthyd<->otar",
        "diplomatic-v1": "@135;otchoshor.qoty.qotor.cthyd<->otar",
        "analysis-v1": "@135;otchoshor.qoty.qotor.cthyd.otar",
        "no-uncertain-spaces-v1": "@135;otchoshor.qoty.qotor.cthyd.otar",
    },
}


@pytest.mark.parametrize("locus_id", list(REFERENCE))
def test_reference_lines(locus_id: str):
    """Every profile on the roadmap's reference lines: comments and paragraph marks (f1r:7), an
    uncertain space and an alternate holding a ligature and a code (f1r:17), high-ASCII codes and a
    ligature (f1r:19), a drawing break (f10r:11)."""
    text_raw = zl_text_raw(locus_id)
    assert text_raw == REFERENCE[locus_id]["raw-v1"]
    for profile_id, expected in REFERENCE[locus_id].items():
        assert vp.apply_profile(profile_id, text_raw) == expected, profile_id


# --- every rule on every locus, against an independent implementation -----------------------


def diplomatic_by_regex(text_raw: str) -> str:
    """Comments, paragraph marks, text tags, wraps and whitespace removed."""
    text = re.sub(r"<![^>]*>|<[%$]>|<@[A-Z]=[^<>\s]>", "", text_raw)
    text = re.sub(r"[ \t]*/(?:(?:\r\n|\n|\r)/[ \t]*)+", "", text)
    return re.sub(r"[ \t]", "", text)


def analysis_by_regex(text_raw: str) -> str:
    """From the diplomatic text: the first reading of each alternate, ligature braces removed,
    drawing breaks as '.', '?' and the legacy markers '!' '*' removed."""
    text = diplomatic_by_regex(text_raw)
    text = re.sub(r"\[([^:\]]*)(?::[^\]]*)+\]", r"\1", text)
    text = re.sub(r"\{([^}]*)\}", r"\1", text)
    text = re.sub(r"<[-~]>", ".", text)
    return re.sub(r"[?!*]", "", text)


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_every_rule_on_every_locus(source: Path):
    """On every locus of every cached source, each profile is what the independent implementation
    gives: raw-v1 is text_raw; diplomatic-v1, analysis-v1 and no-uncertain-spaces-v1 follow their
    rules. Each kind of token the source holds is exercised."""
    parser = IVTFFParser()
    loci = [locus for page in parser.parse_file(source) for locus in page.loci]
    assert loci
    kinds = set()
    for locus in loci:
        text_raw = locus.text_raw
        kinds.update(token.kind for token in locus.markup.tokens)
        assert vp.apply_profile("raw-v1", text_raw) == text_raw
        assert vp.apply_profile("diplomatic-v1", locus.markup) == diplomatic_by_regex(text_raw)
        analysis = analysis_by_regex(text_raw)
        assert vp.apply_profile("analysis-v1", locus.markup) == analysis, locus.locus_id
        assert vp.apply_profile("no-uncertain-spaces-v1", text_raw) == analysis.replace(",", "")
    assert "glyphs" in kinds and "space" in kinds


def test_every_kind_of_rule_meets_a_real_line():
    """Each token kind that a rule rewrites (dropped, replaced or reduced) occurs in some ZL locus,
    so every rule of analysis-v1 and diplomatic-v1 is exercised on real text by the test above."""
    found = set()
    for page in IVTFFParser().parse_file(ZL):
        for locus in page.loci:
            found.update(token.kind for token in locus.markup.tokens)
    rewritten = {
        kind
        for profile_id in ("diplomatic-v1", "analysis-v1", "no-uncertain-spaces-v1")
        for kind, rule in vp.PROFILES[profile_id].rules.items()
        if rule != vp.KEEP
    }
    # whitespace, wraps and unknown markup occur in no ZL locus; they are covered synthetically
    assert rewritten - found <= {"whitespace", "wrap", "unknown"}


def test_whitespace_wraps_and_tags():
    """Whitespace, wraps and text tags are kept by raw and removed by the others; markup IVTFF does
    not define is kept as written by every profile, never dropped silently (the parser reports such
    a locus instead of emitting it; reach a17b6e30 gap 1)."""
    text = "da /\n/ i<@H=2>in <!c>.ol"
    assert vp.apply_profile("raw", text) == text
    assert vp.apply_profile("diplomatic", text) == "daiin.ol"
    assert vp.apply_profile("analysis", text) == "daiin.ol"

    unknown = vp.parse_markup("da<?>in.o}l")
    assert [t.raw for t in unknown.tokens if t.kind == "unknown"] == ["<?>", "}"]
    for profile_id in vp.PROFILES:
        rendered = vp.apply_profile(profile_id, unknown)
        assert "<?>" in rendered and "}" in rendered, profile_id


# --- names, versions, the rule table ---------------------------------------------------------


def test_profile_names_and_versions():
    assert sorted(vp.PROFILES) == sorted(
        ["raw-v1", "diplomatic-v1", "analysis-v1", "no-uncertain-spaces-v1"]
    )
    for profile_id, profile in vp.PROFILES.items():
        assert profile.id == profile_id
        assert vp.get_profile(profile.name) is max(
            (p for p in vp.PROFILES.values() if p.name == profile.name), key=lambda p: p.version
        )
        assert set(profile.rules) == set(vp.TOKEN_KINDS)
    with pytest.raises(KeyError):
        vp.get_profile("analysis-v9")
    with pytest.raises(KeyError):
        vp.get_profile("centralized_v0.3.0")


#: The published rule table. A published version never changes: a new rule is a new version. No profile has been
#: released yet (0.2.3 has none); before the first release the legacy markers' rule was stated as EVA's only (B-053,
#: DECISIONS Q102), the last change to version 1.
PUBLISHED_TABLE = """\
| token | raw-v1 | diplomatic-v1 | analysis-v1 | no-uncertain-spaces-v1 |
|---|---|---|---|---|
| glyphs | keep | keep | keep, without `!` `*` (EVA only) | keep, without `!` `*` (EVA only) |
| space | keep | keep | keep | keep |
| uncertain_space | keep | keep | keep | drop |
| illegible | keep | keep | drop | drop |
| high_ascii | keep | keep | keep | keep |
| ligature | keep | keep | glyphs, no braces, without `!` `*` (EVA only) | glyphs, no braces, without `!` `*` (EVA only) |
| alternates | keep | keep, whitespace inside removed | first reading | first reading |
| comment | keep | drop | drop | drop |
| drawing_break | keep | keep | `.` | `.` |
| paragraph_start | keep | drop | drop | drop |
| paragraph_end | keep | drop | drop | drop |
| text_tag | keep | drop | drop | drop |
| whitespace | keep | drop | drop | drop |
| wrap | keep | drop | drop | drop |
| unknown | keep | keep | keep | keep |"""


def test_published_rule_table_is_unchanged():
    assert vp.describe() == PUBLISHED_TABLE


# --- text_clean is an alias of analysis-v1 ---------------------------------------------------


def test_text_clean_is_the_analysis_profile():
    """The committed rows' text_clean is analysis-v1 of text_raw, and the build report names it."""
    report = json.loads((OUTPUT / "eva_lines_build_report.json").read_text())
    assert report["text_clean_policy"] == vp.TEXT_CLEAN_PROFILE == "analysis-v1"
    rows = [json.loads(line) for line in (OUTPUT / "eva_lines.jsonl").open()]
    assert rows
    for row in rows:
        assert row["text_clean"] == vp.apply_profile("analysis-v1", row["text_raw"])
        assert clean_text_for_analysis(row["text"]) == row["text_clean"]


def test_glyphs_are_kept_as_written():
    """No profile corrects the transliteration: ZL f57v.3's uppercase 'I' stays (DECISIONS Q39)."""
    text_raw = zl_text_raw("f57v:3")
    assert "I" in text_raw
    for profile_id in vp.PROFILES:
        assert "I" in vp.apply_profile(profile_id, text_raw), profile_id


# --- the validators read text_clean through the named profile --------------------------------

#: One locus holding every defined kind of markup: a paragraph start and end, a text tag, a
#: ligature, an uncertain space, an alternate, a drawing break, a wrap, a high-ASCII code, a word
#: space, a '?', a comment and whitespace (reach a17b6e30 gap 2).
SOURCE = (
    "#=IVTFF Eva- 2.0 M 5\n<f1r> <! $Q=A $L=A $H=1 $I=H>\n"
    "<f1r.1,@P0> <%><@H=2>da{ct}y,[a:o]l<->dy /\n/ ok@192;.?<!c> ol<$>\n"
)


def build(base: Path, content: str = SOURCE) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    source = base / "source.txt"
    source.write_text(content, encoding="utf-8")
    out = base / "out"
    out.mkdir()
    records, report = build_eva_lines(source, out)
    export_to_jsonl(records, out / "eva_lines.jsonl")
    (out / "eva_lines_build_report.json").write_text(json.dumps(report.to_dict()))
    return out


def both(out: Path) -> tuple[list[str], list]:
    with contextlib.redirect_stdout(io.StringIO()):
        _, phase_errors = phase.validate_outputs(out)
        failures = inv.verify_all_invariants(out).failures
    return phase_errors, failures


def test_validators_accept_a_build_and_its_profile(tmp_path: Path):
    out = build(tmp_path)
    row = json.loads((out / "eva_lines.jsonl").read_text())
    assert row["text_clean"] == "dacty,al.dyok@192;.ol"
    kinds = {token.kind for token in vp.parse_markup(row["text_raw"]).tokens}
    assert kinds == set(vp.TOKEN_KINDS) - {"unknown"}
    assert both(out) == ([], [])


@pytest.mark.parametrize(
    "policy, text_clean",
    [
        ("invented-policy", None),  # not a profile
        ("centralized_v0.3.0", None),  # the policy before item 1.6 is not a profile
        ("diplomatic-v1", None),  # a real profile the rows were not made with
        ("analysis-v1", "dacty.al.dyok@192;.ol"),  # the right profile, a text it does not give
    ],
)
def test_validators_reject_a_wrong_profile(tmp_path: Path, policy: str, text_clean: str | None):
    out = build(tmp_path)
    report_path = out / "eva_lines_build_report.json"
    report = json.loads(report_path.read_text())
    report_path.write_text(json.dumps({**report, "text_clean_policy": policy}))
    if text_clean is not None:
        rows_path = out / "eva_lines.jsonl"
        row = json.loads(rows_path.read_text())
        rows_path.write_text(json.dumps({**row, "text_clean": text_clean}) + "\n")
    phase_errors, failures = both(out)
    assert phase_errors and failures


@pytest.mark.parametrize(
    "text_clean, accepted",
    [
        ("Dacty,al.dyok@192;.ol", False),  # 'D' is not a glyph of this locus
        ("da{cty,al.dyok@192;.ol", False),  # leaked markup
    ],
)
def test_charset_invariant_accepts_only_the_sources_own_glyphs(
    tmp_path: Path, text_clean: str, accepted: bool
):
    out = build(tmp_path)
    rows_path = out / "eva_lines.jsonl"
    row = json.loads(rows_path.read_text())
    rows_path.write_text(json.dumps({**row, "text_clean": text_clean}) + "\n")
    with contextlib.redirect_stdout(io.StringIO()):
        failures = inv.verify_all_invariants(out).failures
    # the charset check's own invariants, not the separate correspondence check (review 06a3d8f8
    # finding 2)
    charset = {"TEXT_CLEAN_CHARSET", "TEXT_CLEAN_NO_MARKUP", "TEXT_CLEAN_NO_MARKERS"}
    assert any(f["invariant"] in charset for f in failures) is not accepted


def test_charset_invariant_accepts_an_uppercase_glyph_of_the_source(tmp_path: Path):
    out = build(tmp_path, SOURCE.replace("da{ct}y", "dI{ct}y"))
    row = json.loads((out / "eva_lines.jsonl").read_text())
    assert row["text_clean"].startswith("dIcty")
    assert both(out) == ([], [])
