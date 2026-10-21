import ast
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pytest

from parsers import (
    IVTFFParser,
    MISSING_FOLIOS,
    MetadataParser,
    Page,
    PageVariables,
)

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
    and (parent / "data_sources/cache").is_dir()
)
CACHE = ROOT / "data_sources/cache"
SOURCES = sorted(CACHE.glob("*.txt"))
ZL = CACHE / "ZL3b-n.txt"


@pytest.mark.parametrize(
    "relative",
    ["tests/conftest.py", "tests/test_parsers.py"],
)
def test_f02_real_source_fixture_resolves(relative):
    source_file = ROOT / relative
    tree = ast.parse(source_file.read_text())
    fixture = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "zl_file"
    )
    assignment = next(
        node
        for node in ast.walk(fixture)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "path"
            for target in node.targets
        )
    )
    expression = ast.Expression(body=assignment.value)
    resolved = eval(
        compile(expression, str(source_file), "eval"),
        {"Path": Path, "__file__": str(source_file)},
    )
    assert resolved.is_file(), resolved
    assert resolved.read_bytes() == ZL.read_bytes()


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_f01_source_loci_survive(source):
    expected = Counter(
        match.group(0)
        for line in source.read_text().splitlines()
        if (match := re.match(r"^<[^>]+\.\d+,[^>]+>", line))
    )
    assert expected, "The independent source recognizer found no loci"
    actual = Counter(
        locus.raw_locator
        for page in IVTFFParser().parse_file(source)
        for locus in page.loci
    )
    assert actual == expected, {
        "missing": expected - actual,
        "unexpected": actual - expected,
    }


def test_f01_metadata_accepts_source_page_names():
    pages = [
        Page(
            page_id=match.group(1),
            variables=PageVariables.from_header(line),
        )
        for line in ZL.read_text().splitlines()
        if (match := re.match(r"^<([^.,>]+)>", line))
    ]
    assert pages
    records = MetadataParser().extract_pages(pages)
    assert {record.page_id for record in records} == {
        page.page_id for page in pages
    }


def test_f04_transcribed_folios_are_not_missing():
    transcribed = {
        int(match.group(1))
        for line in ZL.read_text().splitlines()
        if (match := re.match(r"^<f(\d+)[rv]\d*\.\d+,", line))
    }
    assert transcribed
    assert transcribed.isdisjoint(MISSING_FOLIOS), (
        transcribed.intersection(MISSING_FOLIOS)
    )


def test_f05_quire_with_missing_folio_is_not_complete():
    pages = list(IVTFFParser().parse_file(ZL))
    quire = next(
        record
        for record in MetadataParser().extract_quires(pages)
        if record.quire_id == "qB"
    )
    assert 12 in MISSING_FOLIOS
    assert "f11" in quire.folio_ids
    assert "f13" in quire.folio_ids
    assert "f12" not in quire.folio_ids
    assert quire.is_complete is not True


def _string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _string_values(child)


def test_f06_folio_records_reference_all_input_pages():
    pages = list(IVTFFParser().parse_file(ZL))
    records = MetadataParser().extract_folios(pages)
    expected = {page.page_id for page in pages}
    represented = {
        value
        for record in records
        for value in _string_values(record.to_dict())
        if value in expected
    }
    assert represented == expected, expected - represented


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_f08_version_matches_source_header(source):
    header = source.read_text().splitlines()[0].split()
    assert header[0] == "#=IVTFF"
    parser = IVTFFParser()
    list(parser.parse_file(source))
    assert parser.format_version == header[2]


def test_f09_strict_rejects_wrong_page_context():
    content = "<f1r>\n<f2r.1,@P0> fachys"
    with pytest.raises(ValueError):
        list(IVTFFParser(strict=True).parse_string(content))


@pytest.mark.parametrize("strict", [False, True])
def test_f10_wrapped_locus_keeps_continuation(strict):
    content = (
        "#=IVTFF Eva- 2.0 M\n"
        "<f1r>\n"
        "<f1r.1,@P0> fachys. /\n"
        "/ ykal"
    )
    pages = list(IVTFFParser(strict=strict).parse_string(content))
    locus = pages[0].loci[0]
    assert "fachys" in locus.text
    assert "ykal" in locus.text


@pytest.mark.parametrize("clean", [False, True])
def test_f03_ligature_glyphs_survive(clean):
    result = IVTFFParser().extract_text("dlo{ct}o", clean=clean)
    assert "ct" in result


def test_f03_drawing_boundary_survives():
    result = IVTFFParser().extract_text("a<~>b")
    assert result in {"a b", "a.b", "a<~>b"}


@pytest.mark.parametrize("value", ["X", "Z"])
def test_f07_currier_hand_letters_survive(value):
    variables = PageVariables.from_header(f"$C={value}")
    assert value in asdict(variables).values()
