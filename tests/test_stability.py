"""
The stability policy and the errata path (roadmap items 2.2, 2.11): `STABILITY.md`, `ERRATA.md` and the issue templates
agree with the schemas, the profiles and the roadmap. Read from the files at test time.
"""

from __future__ import annotations

import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml
from markdown_it import MarkdownIt

from vcat.profiles import PROFILES

ROOT = Path(__file__).resolve().parent.parent
STABILITY = (ROOT / "STABILITY.md").read_text(encoding="utf-8")
ERRATA = (ROOT / "ERRATA.md").read_text(encoding="utf-8")
SCHEMAS = sorted((ROOT / "schemas").glob("*.schema.json"))
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, heading
    return match.group(1)


def table(text: str) -> tuple[list[str], list[list[str]]]:
    """The first Markdown table of a text: its header cells and its rows (a row with a missing cell keeps its short width,
    so a test can see it; reach dd4ff650 gap 2)."""
    rows = []
    for line in text.splitlines():
        if line.startswith("|") and not re.fullmatch(r"\|[-| ]+\|", line.strip()):
            rows.append([c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]])
    return (rows[0], rows[1:]) if rows else ([], [])


def table_rows(text: str) -> list[list[str]]:
    return table(text)[1]


#: The columns the two tables must have: what each version part allows and means; what each erratum records
VERSION_COLUMNS = [
    "part",
    "goes up when a release...",
    "a user's code or analysis written for the previous release...",
]
ERRATA_COLUMNS = ["id", "affects", "what was wrong in 0.2.3", "corrected by", "how to tell"]


def test_the_version_parts_are_defined():
    """MAJOR, MINOR and PATCH, each with what raises it and what it means for a user (reach dd4ff650 gap 1)."""
    header, rows = table(section(STABILITY, "Versions"))
    # the columns are the policy's, not whatever the document's header says (review 9fa0ae04 finding 1)
    assert header == VERSION_COLUMNS, header
    assert [r[0] for r in rows] == ["MAJOR", "MINOR", "PATCH"]
    for row in rows:
        assert len(row) == len(header) and all(row), row


def test_documented_identifier_patterns_are_the_schemas():
    """The patterns STABILITY.md gives for `page_id` and `line_id` are the row schema's, exactly."""
    schema = json.loads((ROOT / "schemas" / "transcription_lines.schema.json").read_text())
    rows = {r[0].strip("`"): r for r in table_rows(section(STABILITY, "Identifiers"))}
    for name in ("page_id", "line_id"):
        documented = rows[name][2].strip("`").replace("\\|", "|")
        assert documented == schema["properties"][name]["pattern"], name


def test_every_profile_id_is_named_and_versioned():
    """Every profile the package defines is listed as a permanent identifier, and every id has the form name-vN."""
    row = next(
        r for r in table_rows(section(STABILITY, "Identifiers")) if r[0].startswith("a profile id")
    )
    listed = set(re.findall(r"`([a-z-]+-v\d+)`", row[0]))
    assert listed == set(PROFILES)
    assert all(re.fullmatch(r"[a-z]+(-[a-z]+)*-v\d+", pid) for pid in PROFILES)


def test_deprecations_are_the_schemas():
    """The deprecation table lists exactly the schema properties marked deprecated (none today)."""
    deprecated = {
        f"{path.name}:{name}"
        for path in SCHEMAS
        for name, spec in json.loads(path.read_text())["properties"].items()
        if spec.get("deprecated")
    }
    rows = table_rows(section(STABILITY, "Deprecations"))
    assert {r[0].strip("`") for r in rows} == deprecated
    if not deprecated:
        assert "No deprecation is in force." in section(STABILITY, "Deprecations")


def test_every_roadmap_defect_has_an_erratum():
    """Each defect D1..Dn of the roadmap's starting table is one ERRATA entry, newest first, ids unique."""
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    defects = re.findall(r"^\| (D\d+) \|", roadmap, re.M)
    header, rows = table(ERRATA.split("## Retired identifiers")[0])
    assert header == ERRATA_COLUMNS, header  # review 9fa0ae04 finding 1
    ids = [r[0] for r in rows]
    for row in rows:
        assert len(row) == len(header), row  # every declared column (reach dd4ff650 gap 2)
    assert len(ids) == len(set(ids)) == len(defects)
    named = [re.fullmatch(r"E-(\d{3}) \((D\d+)\)", i) for i in ids]
    assert all(named), ids
    assert sorted(m.group(2) for m in named) == sorted(defects)
    numbers = [int(m.group(1)) for m in named]
    assert numbers == sorted(numbers, reverse=True)
    for row in rows:
        assert all(cell for cell in row), row  # what was wrong, what corrects it, how to tell


def test_retired_identifiers_are_listed():
    assert "## Retired identifiers" in ERRATA


def templates() -> dict[str, dict]:
    return {
        p.name: yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(TEMPLATES.glob("*.yml"))
    }


@pytest.mark.parametrize("name", ["data_bug.yml", "transcription_error.yml"])
def test_issue_templates_are_forms_with_required_fields(name: str):
    form = templates()[name]
    assert form["name"] and form["description"] and form["body"]
    fields = [item for item in form["body"] if item.get("type") != "markdown"]
    ids = [item["id"] for item in fields]
    assert len(ids) == len(
        set(ids)
    ), ids  # a duplicate could hide an optional field (reach dd4ff650 gap 3)
    assert "line_id" in ids
    assert all(item.get("validations", {}).get("required") for item in fields)


#: Unicode's Default_Ignorable_Code_Point ranges (DerivedCoreProperties.txt): code points a renderer draws as nothing,
#: assigned or reserved (review b8d5e9c6 finding 2: a hand list missed the reserved ones); and the blank Braille pattern,
#: drawn blank though not ignorable (review 1d0b83fe finding 1)
_DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD),
    (0x034F, 0x034F),
    (0x061C, 0x061C),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)
_DRAWN_BLANK = {"\u2800"}


def _visible(char: str) -> bool:
    """Whether a reader sees the character: not white space; not a format, control, unassigned, separator or
    combining-only character; not default-ignorable; not drawn blank."""
    point = ord(char)
    return (
        not char.isspace()
        and unicodedata.category(char) not in ("Cf", "Cc", "Cn", "Zs", "Zl", "Zp", "Mn", "Me")
        and not any(low <= point <= high for low, high in _DEFAULT_IGNORABLE)
        and char not in _DRAWN_BLANK
    )


class _Shown(HTMLParser):
    """What a reader sees of rendered Markdown: its text and the targets of the links a reader can see. A comment is not
    shown (B-086); nor is the content of a script, style or template element, which GitHub strips; and a link whose text
    shows nothing links nothing a reader can follow (audit 20261021-tests F1)."""

    HIDDEN = {"script", "style", "template"}

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []
        self._hidden = 0
        self._link: str | None = None
        self._link_text: list[str] = []

    def handle_data(self, data: str) -> None:
        if self._hidden:
            return
        self.text.append(data)
        if self._link is not None:
            self._link_text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.HIDDEN:
            self._hidden += 1
        elif tag == "a" and not self._hidden:
            self._link = next((value for name, value in attrs if name == "href" and value), None)
            self._link_text = []
        elif tag == "img" and self._link is not None:
            # an image's alternative text is what a reader sees of it
            self._link_text.extend(value or "" for name, value in attrs if name == "alt")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.HIDDEN and self._hidden:
            self._hidden -= 1
        elif tag == "a" and self._link is not None:
            # visible: some character that is not white space and not a zero-width or other format character
            # (reach dec3e688 gap 2: a zero-width space passed `strip`)
            if any(_visible(char) for char in "".join(self._link_text)):
                self.links.append(self._link)
            self._link = None


def as_shown(markdown: str) -> _Shown:
    """Markdown as GitHub shows it to a reader, rendered by a CommonMark parser: text in an HTML comment is neither read
    nor linked (B-086, review 85247887 finding 2: instructions and links inside a comment satisfied the checks).
    """
    html = MarkdownIt("commonmark").render(markdown)
    # a comment never closed hides everything after it in a browser (reach 4fe7e6d6 gap 4: the parser returned it as text)
    opened = html.rfind("<!--")
    if opened != -1 and html.find("-->", opened + 4) == -1:
        html = html[:opened]
    page = _Shown()
    page.feed(html)
    page.close()
    return page


def test_transcription_errors_go_upstream():
    """A transcription error is reported upstream, never corrected here (roadmap 2.11), in what the form shows its reader:
    its instructions, and a field that asks where it was reported upstream (reach dd4ff650 gap 4; not in comments).
    """
    form = yaml.safe_load((TEMPLATES / "transcription_error.yml").read_text(encoding="utf-8"))
    instructions = " ".join(
        "".join(as_shown(i["attributes"]["value"]).text)
        for i in form["body"]
        if i.get("type") == "markdown"
    )
    instructions = " ".join(instructions.split())
    assert "upstream" in instructions and "never corrects" in instructions
    upstream = next(i for i in form["body"] if i.get("id") == "upstream")
    # the field's description is Markdown as GitHub shows it, a comment hiding (reach 4fe7e6d6 gap 3); its label is text
    shown = (
        upstream["attributes"]["label"]
        + " "
        + "".join(as_shown(upstream["attributes"].get("description", "")).text)
    )
    assert "upstream" in shown.lower()
    assert upstream["validations"]["required"]
    assert "reported upstream" in section(STABILITY, "Corrections")


#: This repository's documents on GitHub, as the issue forms link them
REPOSITORY_URL = re.compile(
    r"https://github\.com/noah-chelednik/voynich-data/blob/[^/\s)]+/([^\s)#]+)"
)


def _linked_documents(text: str, base: Path | None) -> set[Path]:
    """The repository files a text links, as its reader sees them (the Markdown rendered: a link inside an HTML comment
    links nothing, B-086): a relative link resolved from `base`, or a link to this repository's file on GitHub; a link
    anywhere else names no repository file (review ea46bb38 finding 2)."""
    found = set()
    for target in as_shown(text).links:
        target = target.split("#", 1)[0]
        url = REPOSITORY_URL.fullmatch(target)
        if url:
            found.add((ROOT / url.group(1)).resolve())
        elif base is not None and target and not re.match(r"[a-z][a-z0-9+.-]*:", target):
            found.add((base / target).resolve())
    return {path for path in found if path.is_file()}


def test_the_documents_are_linked():
    """README, CONTRIBUTING and the data-bug form link both documents (a link, not a bare name; reach dd4ff650 gap 5)."""
    documents = {(ROOT / "STABILITY.md").resolve(), (ROOT / "ERRATA.md").resolve()}
    for path in ("README.md", "CONTRIBUTING.md"):
        linked = _linked_documents((ROOT / path).read_text(encoding="utf-8"), (ROOT / path).parent)
        assert documents <= linked, path
    form = yaml.safe_load((TEMPLATES / "data_bug.yml").read_text(encoding="utf-8"))
    shown = "\n".join(i["attributes"]["value"] for i in form["body"] if i.get("type") == "markdown")
    # a form is shown on GitHub, away from the files: only this repository's URLs count, no path of any kind (review
    # 9fa0ae04 finding 2)
    assert documents <= _linked_documents(shown, None)
