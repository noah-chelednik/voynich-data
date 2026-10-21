"""
Normalization profiles (roadmap item 1.6)
=========================================

A profile is a named, versioned rule set that derives one reading of a locus from its raw layer
(``text_raw`` cut into tokens by ``parsers.ivtff_markup``). Each rule says what one kind of token
becomes; nothing else happens, so a profile is exactly its rule table. Glyph characters are kept as
written in every profile, whatever the alphabet: only the markup of IVTFF 2.0 Tables 3, 10 and 11
is rewritten, so no profile corrects, case-folds or interprets the transliteration (principle 1).
One exception, named in its rule: ``analysis-v1`` drops ``!`` and ``*``, the legacy EVA illegibility
markers that the ``has_illegible`` flag also reads, from an EVA text only; a text in another alphabet
keeps them as written (``Profile.for_alphabet``; v101 writes ``*`` as a glyph; DECISIONS Q39, B-053).

The profiles (``PROFILES``; ``describe()`` prints the table):

========================  =========================================================================
``raw-v1``                ``text_raw`` exactly as written, wraps included.
``diplomatic-v1``         Every glyph-level fact kept as written (``.``, ``,``, ``?``, ``@NNN;``,
                          ``{ct}``, ``[a:o]``, ``<->``); comments, paragraph marks, text tags,
                          whitespace and wraps removed.
``analysis-v1``           One plain reading: a ligature's glyphs without braces, the first reading
                          of an alternate, ``<->`` and ``<~>`` as ``.``, ``?``, ``!``, ``*`` dropped,
                          ``,`` kept;
                          comments, marks, tags, whitespace and wraps removed. ``text_clean``.
``no-uncertain-spaces-v1``  ``analysis-v1`` with ``,`` removed: an uncertain space is not a space.
========================  =========================================================================

A bare name (``raw``, ``diplomatic``, ``analysis``, ``no-uncertain-spaces``) means its latest
version. A new rule never changes a published version: it is a new version (``analysis-v2``).

Example:
    >>> apply_profile("analysis-v1", "<%><!@252;>odar.{c'y}.shol,da[a:o]<->@192;?")
    "odar.c'y.shol,daa.@192;"
    >>> apply_profile("diplomatic-v1", "<%><!@252;>odar.{c'y}.shol,da[a:o]<->@192;?")
    "odar.{c'y}.shol,da[a:o]<->@192;?"
    >>> apply_profile("no-uncertain-spaces", "shol,da")
    'sholda'
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from parsers import ivtff_markup as mk
from parsers.ivtff_markup import Markup, Token, parse_markup

__all__ = [
    "KEEP",
    "DROP",
    "PROFILES",
    "TEXT_CLEAN_PROFILE",
    "TOKEN_KINDS",
    "Profile",
    "apply_profile",
    "describe",
    "get_profile",
    "parse_markup",
]

#: What a rule does with a token: keep it as written, drop it, write a fixed text, or a function.
Rule = str | Callable[[Token, "Profile"], str]
KEEP = "keep"
DROP = "drop"


def _ligature_glyphs(token: Token, profile: Profile) -> str:
    """A ligature's characters without its braces (the glyphs and any high-ASCII codes inside), the
    legacy markers '!' and '*' removed as from any glyphs (review 06a3d8f8 finding 1)."""
    return "".join(char for char in str(token.value) if char not in profile.legacy_markers)


#: The legacy EVA illegibility markers, read as '?' is by the ``has_illegible`` flag (DECISIONS Q39).
LEGACY_MARKERS = "!*"


def _glyphs_without_legacy_markers(token: Token, profile: Profile) -> str:
    """The glyphs as written, without the legacy EVA markers '!' and '*'."""
    return "".join(char for char in token.raw if char not in profile.legacy_markers)


def _alternate_as_written(token: Token, profile: Profile) -> str:
    """An alternate with its brackets and colons as written, each reading read by the same profile, so whitespace inside
    the brackets goes as it does everywhere else (AC1 F4, B-058)."""
    return (
        "[" + ":".join(profile.render(mk._reading_tokens(reading)) for reading in token.value) + "]"
    )


def _first_reading(token: Token, profile: Profile) -> str:
    """The first (most likely, IVTFF 2.0 Table 10) reading of an alternate, read by the same
    profile."""
    return profile.render(mk._reading_tokens(token.value[0]))


@dataclass(frozen=True)
class Profile:
    """A named, versioned rule set over the token kinds of ``parsers.ivtff_markup``.

    Attributes:
        name: The profile family (``analysis``).
        version: Its version; a published version never changes.
        summary: One line for the profile table.
        rules: For every token kind, ``"keep"``, ``"drop"``, a replacement text, or a function.
    """

    name: str
    version: int
    summary: str
    rules: dict[str, Rule]
    #: The characters its rules drop as legacy EVA markers: EVA's '!' and '*'; none in another alphabet, where they
    #: are glyphs or the transliteration's own signs (v101 writes '*' as a glyph; B-053)
    legacy_markers: str = LEGACY_MARKERS

    @property
    def id(self) -> str:
        """The versioned name: ``analysis-v1``."""
        return f"{self.name}-v{self.version}"

    def render(self, tokens: list[Token]) -> str:
        """The reading of a token list under this profile."""
        out = []
        for token in tokens:
            rule = self.rules[token.kind]
            if rule == KEEP:
                out.append(token.raw)
            elif rule == DROP:
                continue
            elif callable(rule):
                out.append(rule(token, self))
            else:
                out.append(rule)
        return "".join(out)

    def for_alphabet(self, alphabet: str) -> Profile:
        """This profile for a text in ``alphabet``: as it is for EVA; for any other alphabet the legacy EVA markers are
        kept as written, since no profile maps or corrects another alphabet's characters (B-053)."""
        return self if alphabet == "EVA" else replace(self, legacy_markers="")

    def apply(self, text_raw: str | Markup, alphabet: str = "EVA") -> str:
        """The reading of one locus text (``text_raw``, or its markup) in ``alphabet`` under this profile."""
        markup = text_raw if isinstance(text_raw, Markup) else parse_markup(text_raw)
        return self.for_alphabet(alphabet).render(markup.tokens)


#: Every token kind; each profile has a rule for each (checked at import).
TOKEN_KINDS = (
    mk.GLYPHS,
    mk.SPACE,
    mk.UNCERTAIN_SPACE,
    mk.ILLEGIBLE,
    mk.HIGH_ASCII,
    mk.LIGATURE,
    mk.ALTERNATES,
    mk.COMMENT,
    mk.DRAWING_BREAK,
    mk.PARAGRAPH_START,
    mk.PARAGRAPH_END,
    mk.TEXT_TAG,
    mk.WHITESPACE,
    mk.WRAP,
    mk.UNKNOWN,
)

#: The short name of each rule function, for the profile table.
RULE_LABELS = {
    "_ligature_glyphs": "glyphs, no braces, without `!` `*` (EVA only)",
    "_first_reading": "first reading",
    "_alternate_as_written": "keep, whitespace inside removed",
    "_glyphs_without_legacy_markers": "keep, without `!` `*` (EVA only)",
}

_RAW: dict[str, Rule] = dict.fromkeys(TOKEN_KINDS, KEEP)

_DIPLOMATIC: dict[str, Rule] = {
    mk.GLYPHS: KEEP,
    mk.SPACE: KEEP,
    mk.UNCERTAIN_SPACE: KEEP,
    mk.ILLEGIBLE: KEEP,
    mk.HIGH_ASCII: KEEP,
    mk.LIGATURE: KEEP,
    mk.ALTERNATES: _alternate_as_written,
    mk.DRAWING_BREAK: KEEP,
    mk.COMMENT: DROP,
    mk.PARAGRAPH_START: DROP,
    mk.PARAGRAPH_END: DROP,
    mk.TEXT_TAG: DROP,
    mk.WHITESPACE: DROP,
    mk.WRAP: DROP,
    # Text the parser does not accept never reaches a row; kept as written, never dropped silently.
    mk.UNKNOWN: KEEP,
}

_ANALYSIS: dict[str, Rule] = {
    **_DIPLOMATIC,
    mk.GLYPHS: _glyphs_without_legacy_markers,
    mk.ILLEGIBLE: DROP,
    mk.LIGATURE: _ligature_glyphs,
    mk.ALTERNATES: _first_reading,
    mk.DRAWING_BREAK: ".",
}

_NO_UNCERTAIN_SPACES: dict[str, Rule] = {**_ANALYSIS, mk.UNCERTAIN_SPACE: DROP}

PROFILES: dict[str, Profile] = {
    profile.id: profile
    for profile in (
        Profile("raw", 1, "text_raw exactly as written, wraps included", _RAW),
        Profile(
            "diplomatic",
            1,
            "glyph-level facts as written; comments, marks, tags, whitespace, wraps removed",
            _DIPLOMATIC,
        ),
        Profile(
            "analysis",
            1,
            "ligature glyphs, first readings, <-> and <~> as '.', '?' dropped, '!' '*' dropped from EVA, ',' kept",
            _ANALYSIS,
        ),
        Profile(
            "no-uncertain-spaces",
            1,
            "analysis-v1 with ',' removed (an uncertain space is not a space)",
            _NO_UNCERTAIN_SPACES,
        ),
    )
}

for _profile in PROFILES.values():
    assert set(_profile.rules) == set(TOKEN_KINDS), _profile.id

#: The profile ``text_clean`` is an alias for (the build report's ``text_clean_policy``).
TEXT_CLEAN_PROFILE = "analysis-v1"


def get_profile(name: str) -> Profile:
    """A profile by its versioned name (``analysis-v1``) or bare name (``analysis``: the latest).

    Raises:
        KeyError: The name is not a profile.
    """
    if name in PROFILES:
        return PROFILES[name]
    versions = [p for p in PROFILES.values() if p.name == name]
    if not versions:
        raise KeyError(f"no normalization profile {name!r}; profiles: {sorted(PROFILES)}")
    return max(versions, key=lambda p: p.version)


def apply_profile(name: str, text_raw: str | Markup, alphabet: str = "EVA") -> str:
    """The reading of one locus text in ``alphabet`` (EVA unless named) under the named profile."""
    return get_profile(name).apply(text_raw, alphabet)


def describe() -> str:
    """The profile table: every profile and what it does with every token kind (Markdown)."""
    ids = list(PROFILES)
    lines = ["| token | " + " | ".join(ids) + " |", "|---|" + "---|" * len(ids)]
    for kind in TOKEN_KINDS:
        cells = []
        for profile_id in ids:
            rule = PROFILES[profile_id].rules[kind]
            if callable(rule):
                cells.append(RULE_LABELS[rule.__name__])
            else:
                cells.append(rule if rule in (KEEP, DROP) else f"`{rule}`")
        lines.append(f"| {kind} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
