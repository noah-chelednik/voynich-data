# tests/regressions/f6b7579c/test_finding_3.py
import re

import yaml

from vcat.sources import ROOT


def test_metadata_summary_configuration_count_is_accurate():
    card = (
        ROOT / "huggingface/voynich-manuscript-metadata/README.md"
    ).read_text(encoding="utf-8")
    front = yaml.safe_load(card.split("---", 2)[1])
    summary = card.split("## Dataset Summary", 1)[1].split(
        "## Dataset Structure", 1
    )[0]
    match = re.search(r"\b([A-Za-z]+|\d+)\s+configurations:", summary)
    if match is not None:
        token = match.group(1).lower()
        words = (
            "zero one two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen sixteen seventeen "
            "eighteen nineteen twenty"
        ).split()
        stated = int(token) if token.isdecimal() else words.index(token)
        assert stated == len(front["configs"])
