"""
The dataset cards state the build (roadmap item 1.9, D8): their field tables, statistics and example rows are rendered from
the schema, the record classes and the committed output (`builders/cards.py`), so a card cannot state a number or a field
the build does not produce.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from builders.cards import (
    committed_eva_report,
    committed_metadata_report,
    eva_schema,
    eva_statistics,
    metadata_statistics,
    record_field_table,
    schema_field_table,
)
from parsers.metadata_parser import (
    BifolioRecord,
    FolioRecord,
    PageOrderRecord,
    PageRecord,
    QuireRecord,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
EVA_CARD = ROOT / "huggingface" / "voynich-eva" / "README.md"
METADATA_CARD = ROOT / "huggingface" / "voynich-manuscript-metadata" / "README.md"
RECORDS = {
    "pages": PageRecord,
    "folios": FolioRecord,
    "quires": QuireRecord,
    "bifolia": BifolioRecord,
    "page_orders": PageOrderRecord,
}


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def as_json(row: object) -> str:
    """A row as canonical JSON: two rows are the same only if their JSON is (a Boolean is not a number)."""
    return json.dumps(row, sort_keys=True, ensure_ascii=False)


def json_blocks(text: str) -> list[dict]:
    """Every JSON example a reader sees: each fenced code block whose info string's first word is `json`, as a CommonMark
    parser finds it (any fence length or character, a longer closing fence, spaces before the info string; reach 71660867
    gap 7, review f66f47d9 finding 2)."""
    from markdown_it import MarkdownIt

    return [
        json.loads(token.content)
        for token in MarkdownIt("commonmark").parse(text)
        if token.type == "fence" and token.info.split()[:1] == ["json"]
    ]


#: The start of a Markdown block that ends a table: an ATX heading (one to six `#` and then whitespace or the line's end; a
#: The start of a Markdown block that ends a table (GitHub Flavored Markdown): an ATX heading (one to six `#` and then
#: whitespace or the line's end; reach 6e91b4a2 gap 3), a code fence, a quote, a list item, or an HTML block as the spec
#: defines its start (raw-text tags, a comment, a processing instruction, a declaration, CDATA, or a block-level tag name).
#: Inline HTML and autolinks (`<em>`, `<https://...>`) do not start one, so a row beginning with them stays a row (review
#: caac4571 finding 3).
_HTML_BLOCK = (
    r"<(?i:script|pre|style|textarea)(?:[ \t>]|$)|<!--|<\?|<![A-Z]|<!\[CDATA\[|"
    r"</?(?i:address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:[ \t]|/?>|$)"
)
#: As the spec has them: a heading's `#` run is followed by a space, a tab or the line's end (not any Unicode space); a
#: backtick fence's info string holds no backtick; a declaration is `<!` and an upper-case letter (review deca4e05
#: finding 2)
BLOCK_START = re.compile(
    r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|`{3,}[^`]*$|~{3,}|>|[-*+](?:[ \t]|$)|" + _HTML_BLOCK + ")"
)


def whole_table(text: str, rendered: str) -> str:
    """The table of `text` that the rendering starts, every line of it to the next blank line or block start: what a
    reader sees, so a row added after the rendering is compared too (B-096), with or without pipes (reach 0dea398a gap 4,
    B-104). Empty when the rendering is not in the text."""
    # lines end only where Markdown ends them: `\n`, `\r\n`, `\r` (str.splitlines also splits at U+0085, U+2028 and
    # U+2029, which Markdown does not; review 020f7450 finding 3)
    lines, wanted = re.split(r"\r\n|\n|\r", text), re.split(r"\r\n|\n|\r", rendered)
    # every table that starts as the rendering does (header, rule, first row) is read whole, to the next blank line or
    # block start (a GitHub Markdown table runs that far, so a following line without a `|` is still one of its rows:
    # B-104, AT8 F1), and each must be the rendering: a wrong copy before the right one (reach bef641e7 gap 4) or a
    # longer one after it (review 7454c2f9 finding 6) is returned, so the comparison fails
    head = wanted[:3]
    found = ""
    for start in range(len(lines)):
        if lines[start : start + len(head)] != head:
            continue
        end = start
        while end < len(lines) and lines[end].strip() and not BLOCK_START.match(lines[end]):
            end += 1
        table = "\n".join(lines[start:end])
        if table != "\n".join(wanted):
            return table
        found = found or table
    return found


def _variant_renderings() -> list[str]:
    """The variant tables' renderings (roadmap item 2.7)."""
    from builders.cards import committed_variants_report, variants_schemas, variants_statistics

    return [
        *(schema_field_table(s) for s in variants_schemas()),
        variants_statistics(committed_variants_report()),
    ]


def card_tables() -> list[tuple[Path, str]]:
    """Every rendered table of every card, with its card (reach 0dea398a gap 6: the mismatch card's field table too)."""
    from builders.cards import (
        committed_transliterations_report,
        mismatch_schema,
        transliterations_schema,
        transliterations_statistics,
    )

    mismatch = ROOT / "huggingface" / "voynich-transcription-mismatch" / "README.md"
    transliterations = ROOT / "huggingface" / "voynich-transliterations" / "README.md"
    tables = [
        (EVA_CARD, schema_field_table(eva_schema())),
        (EVA_CARD, eva_statistics(committed_eva_report())),
    ]
    from builders.cards import committed_words_report, words_schema, words_statistics

    tables += [
        (EVA_CARD, schema_field_table(words_schema())),
        (EVA_CARD, words_statistics(committed_words_report())),
    ]
    tables += [
        (METADATA_CARD, record_field_table(RECORDS[n], rows(OUTPUT / "metadata" / f"{n}.jsonl")[0]))
        for n in RECORDS
    ]
    tables += [(METADATA_CARD, metadata_statistics(committed_metadata_report()))]
    tables += [(mismatch, schema_field_table(mismatch_schema()))]
    from builders.cards import layers_field_table, layers_table
    from vcat.layers import load_layers

    tables += [(METADATA_CARD, layers_table(load_layers())), (METADATA_CARD, layers_field_table())]
    from builders.cards import page_canvases_field_table

    tables += [(METADATA_CARD, page_canvases_field_table())]
    tables += [
        (transliterations, schema_field_table(transliterations_schema())),
        (transliterations, transliterations_statistics(committed_transliterations_report())),
        *((transliterations, r) for r in _variant_renderings()),
    ]
    return tables


def assert_every_card_table_is_whole() -> None:
    for card, rendered in card_tables():
        assert whole_table(card.read_text(encoding="utf-8"), rendered) == rendered, card.parent.name


def test_eva_card_states_the_schema_and_the_build():
    assert_every_card_table_is_whole()
    card = EVA_CARD.read_text(encoding="utf-8")
    for rendered in (schema_field_table(eva_schema()), eva_statistics(committed_eva_report())):
        assert whole_table(card, rendered) == rendered
    # each configuration loads its own file, read as YAML, every data file of every config (roadmap item 2.6; reach
    # 71660867 gap 6: a second file passed)
    import yaml

    front = yaml.safe_load(card.split("---", 2)[1])
    configs = {
        c["config_name"]: [(f.get("split"), f.get("path")) for f in c["data_files"]]
        for c in front["configs"]
    }
    # every layer folded in (roadmap item 2.9): the configs are the staging table's, each one file
    from builders.stage_release import EVA_CONFIGS

    assert configs == {
        name: [("train", path)] for name, (path, _b, _w) in EVA_CONFIGS.items()
    }, configs
    assert all((OUTPUT / build).is_file() for _p, build, _w in EVA_CONFIGS.values())
    # a shown row is a committed row: a line, or a word of the word level (roadmap item 2.6)
    committed = rows(OUTPUT / "eva_lines.jsonl") + rows(OUTPUT / "eva_words.jsonl")
    shown = json_blocks(card)
    # compared as canonical JSON, so `true` is not `1` (review 88bdfa1e finding 2)
    assert shown and all(as_json(row) in {as_json(r) for r in committed} for row in shown)


def test_eva_card_credits_every_transliteration_it_holds():
    """The card names the transliterators of every source the repository holds (its LICENSE tells users to cite them),
    as the registry has them (review 4c664493 finding 4)."""
    from builders.cards import dataset_credits_table

    rendered = dataset_credits_table("voynich-eva")
    citation = EVA_CARD.read_text(encoding="utf-8").split("## Citation", 1)[1]
    assert whole_table(citation, rendered) == rendered


def test_eva_card_field_table_is_every_schema_field():
    """The rendering itself: one row per schema property, in order, and no other."""
    table = schema_field_table(eva_schema())
    names = re.findall(r"^\| `([^`]+)` \|", table, re.M)
    assert names == list(eva_schema()["properties"])


@pytest.mark.parametrize("name", list(RECORDS))
def test_metadata_card_states_the_records_and_the_build(name: str):
    assert_every_card_table_is_whole()
    card = METADATA_CARD.read_text(encoding="utf-8")
    committed = rows(OUTPUT / "metadata" / f"{name}.jsonl")
    table = record_field_table(RECORDS[name], committed[0])
    assert whole_table(card, table) == table
    assert re.findall(r"^\| `([^`]+)` \|", table, re.M) == list(committed[0])
    # every field is described by its record class
    assert all(cells.split("|")[3].strip() for cells in table.splitlines()[2:]), table
    assert as_json(committed[0]) in {as_json(row) for row in json_blocks(card)}


def assert_metadata_configs_load_their_files() -> None:
    """Each configuration of the metadata card loads its own table: `<name>` from `<name>.jsonl` (reach b7c1ae53 gap 2: a
    config pointing at another built file passed), and every table the build writes has its configuration.
    """
    card = METADATA_CARD.read_text(encoding="utf-8")
    front = card.split("\n---\n", 1)[0]
    configs = re.findall(r"^  - config_name: (\S+)\n((?:    .*\n)+)", front + "\n", re.M)
    assert configs, "no configurations"
    for name, body in configs:
        paths = re.findall(r"^        path: (\S+)$", body, re.M)
        assert paths == [f"{name}.jsonl"], (name, paths)
    built = sorted(p.stem for p in (OUTPUT / "metadata").glob("*.jsonl"))
    assert sorted(name for name, _ in configs) == built


def test_metadata_card_statistics_are_the_report():
    assert_every_card_table_is_whole()
    assert_metadata_configs_load_their_files()
    card = METADATA_CARD.read_text(encoding="utf-8")
    rendered = metadata_statistics(committed_metadata_report())
    assert whole_table(card, rendered) == rendered


@pytest.mark.parametrize("card", [EVA_CARD, METADATA_CARD], ids=lambda p: p.parent.name)
def test_card_numbers_come_from_the_renderings(card: Path):
    """Outside the rendered tables and the example rows, a card's prose states no count (principle 2): every number of
    four or more digits in it is inside a rendered table or a shown row."""
    text = card.read_text(encoding="utf-8")
    rendered = [schema_field_table(eva_schema()), eva_statistics(committed_eva_report())]
    rendered += [metadata_statistics(committed_metadata_report())]
    from builders.cards import committed_words_report, words_schema, words_statistics

    rendered += [schema_field_table(words_schema()), words_statistics(committed_words_report())]
    rendered += [
        record_field_table(RECORDS[n], rows(OUTPUT / "metadata" / f"{n}.jsonl")[0]) for n in RECORDS
    ]
    from builders.cards import dataset_credits_table

    rendered += [
        dataset_credits_table("voynich-eva")
    ]  # the registry's credits (review 4c664493 finding 4)
    for block in rendered:
        text = text.replace(block, "")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)  # front matter
    # dates are not counts: a day/month/year date, and a year in parentheses, "Davis (2020)" (reach b09d5b4b gap 7: a
    # bare four-digit number is a count)
    text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{4}\b|\((19|20)\d\d\)", "", text)
    assert not re.findall(r"\b\d[\d,]{3,}\b", text)


def test_metadata_card_states_the_page_canvases():
    """The `page_canvases` configuration (roadmap item 2.4): its field table, whole, and its first committed row."""
    from builders.cards import page_canvases_field_table

    assert_every_card_table_is_whole()
    card = METADATA_CARD.read_text(encoding="utf-8")
    table = page_canvases_field_table()
    assert whole_table(card, table) == table
    committed = rows(OUTPUT / "metadata" / "page_canvases.jsonl")
    assert re.findall(r"^\| `([^`]+)` \|", table, re.M) == list(committed[0])
    assert as_json(committed[0]) in {as_json(row) for row in json_blocks(card)}
    assert "config_name: page_canvases" in card
    assert_metadata_configs_load_their_files()
