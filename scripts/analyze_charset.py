#!/usr/bin/env python3
"""
Empirical charset analysis for VCAT.

Run this BEFORE finalizing the charset definition to see what characters
actually appear in the transcription after markup stripping.

Usage:
    python scripts/analyze_charset.py

This will:
1. Parse the ZL transcription
2. Strip all IVTFF markup using the authoritative stripping function
3. Report all unique characters found
4. Highlight any characters not in the expected EVA set
5. Specifically check for apostrophes and other edge cases
"""

import sys
from collections import Counter
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vcat.text_processing import strip_ivtff_markup


def main():
    # Load and parse transcription
    source_path = Path(__file__).parent.parent / "data_sources" / "cache" / "ZL3b-n.txt"
    if not source_path.exists():
        print(f"ERROR: Source file not found: {source_path}")
        print("Run fetch_sources.py first.")
        return 1

    # Quick parse to extract text content
    all_text = []
    with source_path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            # Skip comments and page headers
            if not line or line.startswith("#"):
                continue
            # Match locus lines: <f1r.1,@P0> text...
            if line.startswith("<f") and ">" in line:
                # Find the closing bracket of the locus identifier
                close_bracket_pos = line.index(">")
                text = line[close_bracket_pos + 1 :].strip()
                if text:
                    # Use the authoritative stripping function
                    stripped = strip_ivtff_markup(text)
                    all_text.append(stripped)

    # Analyze characters
    all_chars = set()
    char_counts = Counter()
    for text in all_text:
        for char in text:
            all_chars.add(char)
            char_counts[char] += 1

    # Expected EVA characters (before VARIANT_CHARS decision)
    eva_expected = set("abcdefghiklmnopqrstuvxyz., @;0123456789")

    print("=" * 60)
    print("VCAT Charset Empirical Analysis")
    print("=" * 60)
    print()
    print(f"Total text segments analyzed: {len(all_text)}")
    print(f"Unique characters found: {len(all_chars)}")
    print()

    print("All characters found (with counts):")
    for char, count in sorted(char_counts.items(), key=lambda x: -x[1]):
        desc = repr(char) if char in " \t\n" else char
        in_expected = "✓" if char in eva_expected else "?"
        print(f"  {in_expected} '{desc}' (U+{ord(char):04X}): {count:,}")

    print()
    unexpected = all_chars - eva_expected
    if unexpected:
        print("⚠ Characters NOT in expected EVA set:")
        for char in sorted(unexpected):
            print(f"  - '{char}' (U+{ord(char):04X}): {char_counts[char]:,} occurrences")
        print()
        print("DECISION REQUIRED:")
        print("For each unexpected character, decide:")
        print("  A) Add to VARIANT_CHARS in vcat/charset.py (if legitimate EVA)")
        print("  B) Strip during cleaning (if it's noise)")
        print("  C) Investigate (if it indicates a parser bug)")
        print()
        print("Document your decision in docs/charset_decisions.md")
    else:
        print("✓ All characters are in expected EVA set")
        print("  No changes needed to VARIANT_CHARS")

    # Specific checks
    print()
    print("Specific edge case checks:")
    apostrophe_present = "'" in all_chars
    print(f"  Apostrophe (') present: {'YES - DECIDE!' if apostrophe_present else 'No'}")
    print(f"  Question mark (?) present: {'YES' if '?' in all_chars else 'No'}")
    print(f"  Exclamation (!) present: {'YES' if '!' in all_chars else 'No'}")
    print(f"  Asterisk (*) present: {'YES' if '*' in all_chars else 'No'}")

    if apostrophe_present:
        print()
        print("APOSTROPHE DECISION NEEDED:")
        print(f"  Occurrences: {char_counts.get(chr(39), 0)}")
        print("  If legitimate EVA variant marker: add to VARIANT_CHARS")
        print("  If transcription noise: add to strip logic")
        print("  Document decision in docs/charset_decisions.md")

    # Note about uncertainty markers
    uncertainty_present = any(c in all_chars for c in "?!*")
    if uncertainty_present:
        print()
        print("NOTE: Uncertainty markers (?, !, *) found in stripped text.")
        print("This is expected - they are stripped AFTER flag computation,")
        print("not during markup stripping. They will NOT appear in text_clean.")

    print()
    print("=" * 60)
    print("Copy this output to docs/charset_decisions.md")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
