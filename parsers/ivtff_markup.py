"""
IVTFF in-line markup
====================

The structured layer of a locus (roadmap item 1.2): the transliterated text of one locus, exactly as
written (``text_raw``), cut into tokens by IVTFF 2.0 (sections 5.5 to 5.7, Tables 3, 10 and 11).

The tokens cover every character: joining their ``raw`` strings gives ``text_raw`` back, so nothing
is dropped while the markup is read. Markup the specification does not define is not guessed at:
it becomes an ``unknown`` token and a problem, which the parser turns into an error (strict mode)
or a recorded warning (DECISIONS Q25).

Only the characters of Table 3 (``< > . , { } [ : ] @ ; ? /``) have a meaning of their own. Every
other character belongs to the file's transliteration alphabet and is kept as glyph text, whatever
the alphabet is (``*`` and ``!`` are glyphs in the v101 alphabet, for example).

Example:
    >>> markup = parse_markup("dlo{ct}o.[a:o]<->@192;")
    >>> [token.kind for token in markup.tokens]
    ['glyphs', 'ligature', 'glyphs', 'space', 'alternates', 'drawing_break', 'high_ascii']
    >>> markup.problems
    []
    >>> markup.fields()["ligatures"], markup.fields()["alternates"]
    (['ct'], [['a', 'o']])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

#: The longest free textual comment, '<' and '>' included (IVTFF 2.0, Table 11; review 09e1ca3c
#: finding 3).
COMMENT_LIMIT = 80

#: Characters with a special meaning in transliterated text (IVTFF 2.0, Table 3).
SPECIAL = frozenset("<>.,{}[:]@;?/")

# Token kinds.
GLYPHS = "glyphs"
SPACE = "space"  # '.' an apparent word space
UNCERTAIN_SPACE = "uncertain_space"  # ',' an uncertain word space
ILLEGIBLE = "illegible"  # '?' one unreadable character, '???' an unknown number
HIGH_ASCII = "high_ascii"  # '@NNN;' with NNN from 128 to 255
LIGATURE = "ligature"  # '{...}'
ALTERNATES = "alternates"  # '[a:b]' or '[a:b:c]' (two or three readings), the most likely first
COMMENT = "comment"  # '<!...>' a free textual comment
DRAWING_BREAK = "drawing_break"  # '<->' or '<~>': interrupted by a drawing, a word space
PARAGRAPH_START = "paragraph_start"  # '<%>'
PARAGRAPH_END = "paragraph_end"  # '<$>'
TEXT_TAG = "text_tag"  # '<@X=y>'
WHITESPACE = "whitespace"  # no meaning (section 5.6), kept so the text is complete
WRAP = "wrap"  # ' /' line end, the line terminator, '/ ' at the start of the next line
UNKNOWN = "unknown"  # markup the specification does not define

# A wrap: ' /' at a line end, the terminator, '/' at the start of the next line. A continuation line
# holding only '/' (and whitespace, which has no meaning) both starts and ends a line of the wrap,
# so one wrap token runs on through it (review 47b59c81 finding 1, B-037; review 6ca5c86f
# finding 1).
_WRAP = re.compile(r"[ \t]*/(?:(?:\r\n|\n|\r)/[ \t]*)+")
_HIGH_ASCII = re.compile(r"@(\d{3});")
_TEXT_TAG = re.compile(r"<@([A-Z])=([^<>\s])>")
_WHITESPACE = re.compile(r"[ \t]+")
# A run of alphabet characters: anything that is neither special, whitespace nor a line end.
_GLYPHS = re.compile(r"[^<>.,{}\[:\]@;?/\s]+")


@dataclass(frozen=True)
class Token:
    """One piece of transliterated text.

    Attributes:
        kind: One of the token kinds of this module.
        raw: The characters as written.
        value: The parsed value: the comment text, the ligature's characters, the readings of an
            alternate, the high-ASCII code, the text tag's (variable, value); None otherwise.
    """

    kind: str
    raw: str
    value: Any = None


@dataclass
class Markup:
    """The tokens of one locus text and the problems found while reading it."""

    tokens: list[Token] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def raw(self) -> str:
        """The text the tokens came from: their ``raw`` strings joined."""
        return "".join(token.raw for token in self.tokens)

    @property
    def text(self) -> str:
        """The text without its wraps, stripped: the parser's ``Locus.text`` for this text."""
        return "".join(token.raw for token in self.tokens if token.kind != WRAP).strip()

    def fields(self) -> dict[str, Any]:
        """The markup as row fields (DECISIONS Q25).

        Every field lists each occurrence at any depth (a ligature or a code inside an alternate
        counts), in text order; comments are free text and contribute nothing but themselves.

        Returns:
            ``alternates`` (the readings of each, as written), ``ligatures`` (their characters),
            ``uncertain_spaces`` (how many ``,``), ``illegible`` (each ``?`` run as written),
            ``high_ascii`` (the codes), ``comments`` (their text), ``drawing_breaks`` (``<->`` and
            ``<~>`` as written), ``markers`` (``<%>``, ``<$>`` and text tags as written).
        """
        result: dict[str, Any] = {
            "alternates": [],
            "ligatures": [],
            "uncertain_spaces": 0,
            "illegible": [],
            "high_ascii": [],
            "comments": [],
            "drawing_breaks": [],
            "markers": [],
        }
        for token in _walk(self.tokens):
            if token.kind == ALTERNATES:
                result["alternates"].append(list(token.value))
            elif token.kind == LIGATURE:
                result["ligatures"].append(token.value)
            elif token.kind == UNCERTAIN_SPACE:
                result["uncertain_spaces"] += 1
            elif token.kind == ILLEGIBLE:
                result["illegible"].append(token.raw)
            elif token.kind == HIGH_ASCII:
                result["high_ascii"].append(token.value)
            elif token.kind == COMMENT:
                result["comments"].append(token.value)
            elif token.kind == DRAWING_BREAK:
                result["drawing_breaks"].append(token.raw)
            elif token.kind in (PARAGRAPH_START, PARAGRAPH_END, TEXT_TAG):
                result["markers"].append(token.raw)
        return result


def _walk(tokens: list[Token]) -> list[Token]:
    """The tokens in text order, each alternate followed by the tokens of its readings and each
    ligature by the codes inside it."""
    out: list[Token] = []
    for token in tokens:
        out.append(token)
        if token.kind == ALTERNATES:
            for reading in token.value:
                out.extend(_walk(_reading_tokens(reading)))
        elif token.kind == LIGATURE:
            out.extend(_ligature_codes(token.value))
    return out


def _ligature_codes(content: str) -> list[Token]:
    return [
        Token(HIGH_ASCII, match.group(0), int(match.group(1)))
        for match in _HIGH_ASCII.finditer(content)
    ]


def _high_ascii_problem(raw: str) -> str | None:
    match = _HIGH_ASCII.fullmatch(raw)
    if not match:
        return f"'@' must be followed by three digits and ';': {raw!r}"
    if not 128 <= int(match.group(1)) <= 255:
        return f"high-ASCII code {raw!r} is not from 128 to 255"
    return None


def _ligature_problem(content: str) -> str | None:
    """Only alphabet characters and high-ASCII codes may appear inside a ligature (Table 10)."""
    if not content:
        return "empty ligature '{}'"
    rest = _HIGH_ASCII.sub("", content)
    for match in _HIGH_ASCII.finditer(content):
        problem = _high_ascii_problem(match.group(0))
        if problem:
            return problem
    if not _GLYPHS.fullmatch(rest) and rest:
        return f"ligature {{{content}}} holds characters that are not glyphs or high-ASCII codes"
    return None


def _reading_tokens(reading: str) -> list[Token]:
    """The tokens of one reading of an alternate (no problems: checked by ``_reading_problem``)."""
    return _tokenize(reading, inside_alternate=True).tokens


def _reading_problem(reading: str) -> str | None:
    """A reading may be empty or hold glyphs, ligatures, high-ASCII codes, ``?`` and word spaces."""
    inner = _tokenize(reading, inside_alternate=True)
    if inner.problems:
        return inner.problems[0]
    return None


def parse_markup(text_raw: str) -> Markup:
    """Cut one locus text into tokens.

    Args:
        text_raw: The transliterated text of a locus as written (for a wrapped locus, with its
            continuation lines and line terminators).

    Returns:
        The tokens (their ``raw`` strings join to ``text_raw``) and the problems found; a text
        with no problems contains only markup IVTFF 2.0 defines.
    """
    return _tokenize(text_raw, inside_alternate=False)


def _tokenize(text: str, inside_alternate: bool) -> Markup:
    markup = Markup()
    tokens, problems = markup.tokens, markup.problems
    i, n = 0, len(text)

    def unknown(raw: str, problem: str) -> None:
        tokens.append(Token(UNKNOWN, raw))
        problems.append(problem)

    while i < n:
        char = text[i]
        if not inside_alternate and (wrap := _WRAP.match(text, i)):
            tokens.append(Token(WRAP, wrap.group(0)))
            i = wrap.end()
            continue
        if char == "<":
            end = text.find(">", i)
            line_end = min(
                (p for p in (text.find("\n", i), text.find("\r", i)) if p >= 0), default=n
            )
            if inside_alternate:
                unknown(text[i:], "an in-line comment cannot appear inside an alternate reading")
                break
            if end < 0 or end > line_end:
                stop = line_end
                unknown(text[i:stop], f"'<' is not closed by '>' on its line: {text[i:stop]!r}")
                i = stop
                continue
            tag = text[i : end + 1]
            if tag.startswith("<!") and len(tag) > COMMENT_LIMIT:
                unknown(tag, f"in-line comment of {len(tag)} characters (at most {COMMENT_LIMIT})")
            elif tag.startswith("<!"):
                tokens.append(Token(COMMENT, tag, tag[2:-1]))
            elif tag in ("<->", "<~>"):
                tokens.append(Token(DRAWING_BREAK, tag))
            elif tag == "<%>":
                tokens.append(Token(PARAGRAPH_START, tag))
            elif tag == "<$>":
                tokens.append(Token(PARAGRAPH_END, tag))
            elif tag_match := _TEXT_TAG.fullmatch(tag):
                tokens.append(Token(TEXT_TAG, tag, (tag_match.group(1), tag_match.group(2))))
            else:
                unknown(tag, f"unknown in-line comment {tag!r}")
            i = end + 1
        elif char == "{":
            end = text.find("}", i)
            if end < 0:
                unknown(text[i:], f"'{{' is not closed by '}}': {text[i:]!r}")
                break
            content = text[i + 1 : end]
            problem = _ligature_problem(content)
            if problem:
                unknown(text[i : end + 1], problem)
            else:
                tokens.append(Token(LIGATURE, text[i : end + 1], content))
            i = end + 1
        elif char == "[" and not inside_alternate:
            end = text.find("]", i)
            if end < 0:
                unknown(text[i:], f"'[' is not closed by ']': {text[i:]!r}")
                break
            readings = text[i + 1 : end].split(":")
            problem = None
            if not 2 <= len(readings) <= 3:
                # IVTFF 2.0 Table 10: "two or three options" (reach 5bb6a8d4 gaps 1 and 2)
                problem = f"alternate {text[i : end + 1]!r} does not have two or three readings"
            else:
                problem = next(filter(None, map(_reading_problem, readings)), None)
            if problem:
                unknown(text[i : end + 1], problem)
            else:
                tokens.append(Token(ALTERNATES, text[i : end + 1], tuple(readings)))
            i = end + 1
        elif char == "@":
            raw = text[i : i + 5]
            problem = _high_ascii_problem(raw)
            if problem:
                unknown(char, problem)
                i += 1
            else:
                tokens.append(Token(HIGH_ASCII, raw, int(raw[1:4])))
                i += 5
        elif char == ".":
            tokens.append(Token(SPACE, char))
            i += 1
        elif char == ",":
            tokens.append(Token(UNCERTAIN_SPACE, char))
            i += 1
        elif char == "?":
            end = i
            while end < n and text[end] == "?":
                end += 1
            tokens.append(Token(ILLEGIBLE, text[i:end]))
            i = end
        elif whitespace := _WHITESPACE.match(text, i):
            tokens.append(Token(WHITESPACE, whitespace.group(0)))
            i = whitespace.end()
        elif glyphs := _GLYPHS.match(text, i):
            tokens.append(Token(GLYPHS, glyphs.group(0)))
            i = glyphs.end()
        else:
            what = {"\n": "a line end", "\r": "a line end", "/": "'/'"}.get(char, repr(char))
            where = "inside an alternate reading" if inside_alternate else "here"
            unknown(char, f"{what} has no meaning {where}")
            i += 1
    _check_drawing_breaks(markup)
    return markup


def _check_drawing_breaks(markup: Markup) -> None:
    """A drawing break implies a word space and must not be preceded or followed by '.' or ','
    (IVTFF 2.0 Table 11, for both <-> and <~>; review f6b92c86 finding 2)."""
    spaces = (SPACE, UNCERTAIN_SPACE)
    tokens = markup.tokens
    # Whitespace and wraps have no meaning (IVTFF 2.0 section 5.6), so a neighbor is looked for
    # across them (review 46badb98 finding 1).
    meaningful = [i for i, t in enumerate(tokens) if t.kind not in (WHITESPACE, WRAP)]
    for position, index in enumerate(meaningful):
        token = tokens[index]
        if token.kind != DRAWING_BREAK:
            continue
        before = tokens[meaningful[position - 1]].kind if position > 0 else None
        after = tokens[meaningful[position + 1]].kind if position + 1 < len(meaningful) else None
        if before in spaces or after in spaces:
            tokens[index] = Token(UNKNOWN, token.raw)
            markup.problems.append(f"{token.raw} next to a word space ('.' or ',')")
    # A paragraph start comes at the start of the line, before any text (Table 11). Comments, text
    # tags and whitespace may precede it: ZL places a comment before <%> in 12 loci, and the spec's
    # "before any text tags or textual comments" is read as a recommendation for them (DECISIONS
    # Q31, review 46badb98 finding 2).
    allowed_before = (COMMENT, TEXT_TAG, WHITESPACE, WRAP)
    for index, token in enumerate(tokens):
        if token.kind == PARAGRAPH_START and any(
            t.kind not in allowed_before for t in tokens[:index]
        ):
            tokens[index] = Token(UNKNOWN, token.raw)
            markup.problems.append("<%> after the start of the text")


#: Transliterated text, between which a word space stands (IVTFF 2.0 section 6.7).
_TEXT_KINDS = frozenset({GLYPHS, LIGATURE, ALTERNATES, ILLEGIBLE, HIGH_ASCII})
#: The four word spaces of IVTFF 2.0 section 6.7: '.', ',', '<->' and '<~>'.
_WORD_SPACE_KINDS = frozenset({SPACE, UNCERTAIN_SPACE, DRAWING_BREAK})


def word_space_problems(markup: Markup) -> list[str]:
    """Where the word spaces of a locus text break IVTFF 2.0 section 6.7.

    A word space ('.', ',', '<->', '<~>') stands only between transliterated text (glyphs,
    ligatures, alternates, '?' runs, high-ASCII codes): it is never the first or the last of them in
    the locus text, and two never follow each other. Comments, paragraph marks, text tags and
    whitespace stand outside this rule. A wrap only lays the text out over several lines (section
    5.5) and has no meaning (section 5.6), so a wrapped locus is one line of text here, as for the
    drawing-break rule of Table 11 (review 46badb98 finding 1; the S01 proof
    ``test_f10_wrapped_locus_keeps_continuation`` accepts ``fachys. /`` continued by ``/ ykal``).
    Inside an alternate reading the rule is not applied. The section says files of format 1.7 or
    earlier did not follow these rules, so the parser applies them to format 2.0 and later only.

    Returns:
        One problem per break of the rules, in text order; none when the text follows them.
    """
    problems: list[str] = []
    line = [t for t in markup.tokens if t.kind in _TEXT_KINDS or t.kind in _WORD_SPACE_KINDS]
    if not line:
        return problems
    if line[0].kind in _WORD_SPACE_KINDS:
        problems.append(f"word space {line[0].raw!r} first in the text (IVTFF 2.0 section 6.7)")
    for before, after in zip(line, line[1:], strict=False):
        if before.kind in _WORD_SPACE_KINDS and after.kind in _WORD_SPACE_KINDS:
            problems.append(
                f"word spaces {before.raw!r} and {after.raw!r} in sequence (IVTFF 2.0 section 6.7)"
            )
    if len(line) > 1 and line[-1].kind in _WORD_SPACE_KINDS:
        problems.append(f"word space {line[-1].raw!r} last in the text (IVTFF 2.0 section 6.7)")
    return problems


def locus_code(position: str, locus_type: str, subtype: str) -> str:
    """The locus code as written, without the transcriber: ``@P0``, ``&Lz``."""
    return f"{position}{locus_type}{subtype}"
