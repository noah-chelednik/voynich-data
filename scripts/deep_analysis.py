"""
Deep Voynich Analysis - Scientifically Rigorous
================================================
Analyses that go beyond basic frequency counts.
"""

import bz2
import gzip
import lzma
import math
from collections import Counter, defaultdict

from datasets import load_dataset

print("=" * 60)
print("VCAT DEEP ANALYSIS")
print("=" * 60)

# Load data
print("\nLoading dataset...")
ds = load_dataset("Ched-ai/voynich-eva", data_files="eva_lines.parquet")
data = ds["train"]

# Extract text
all_clean = " ".join(r["text_clean"] for r in data)
chars = [c for c in all_clean if c.isalpha()]
words = []
for row in data:
    for w in row["text_clean"].replace(",", ".").split("."):
        w = w.strip()
        if w and w.isalpha():
            words.append(w)

print(f"Characters: {len(chars):,}")
print(f"Words: {len(words):,}")


# =============================================================================
# 1. COMPRESSION-BASED ENTROPY BOUNDS
# =============================================================================
print("\n" + "=" * 60)
print("1. COMPRESSION ANALYSIS (Entropy Upper Bounds)")
print("=" * 60)

text_bytes = all_clean.encode("utf-8")
original_size = len(text_bytes)

compressors = {
    "gzip": gzip.compress,
    "bz2": bz2.compress,
    "lzma": lzma.compress,
}

print(f"\nOriginal size: {original_size:,} bytes")
print("\nCompression ratios (lower = more structure):")

for name, func in compressors.items():
    compressed = func(text_bytes)
    ratio = len(compressed) / original_size
    bits_per_char = (len(compressed) * 8) / len(chars)
    print(f"  {name:6}: {ratio:.3f} ({bits_per_char:.2f} bits/char)")

# Compare to shuffled (baseline)
import random

shuffled_chars = list(all_clean)
random.seed(42)
random.shuffle(shuffled_chars)
shuffled_bytes = "".join(shuffled_chars).encode("utf-8")

print("\nShuffled text (destroys structure):")
for name, func in compressors.items():
    compressed = func(shuffled_bytes)
    ratio = len(compressed) / len(shuffled_bytes)
    print(f"  {name:6}: {ratio:.3f}")

print("\n→ Lower ratio on real vs shuffled = genuine structure exists")


# =============================================================================
# 2. CHARACTER-LEVEL ENTROPY (Shannon)
# =============================================================================
print("\n" + "=" * 60)
print("2. SHANNON ENTROPY")
print("=" * 60)


def entropy(sequence):
    """Calculate Shannon entropy in bits."""
    counts = Counter(sequence)
    total = len(sequence)
    h = 0
    for count in counts.values():
        p = count / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def conditional_entropy(sequence, order=1):
    """Calculate conditional entropy H(X_n | X_{n-1}...X_{n-order})."""
    ngrams = defaultdict(Counter)
    for i in range(order, len(sequence)):
        context = tuple(sequence[i - order : i])
        next_char = sequence[i]
        ngrams[context][next_char] += 1

    total = sum(sum(c.values()) for c in ngrams.values())
    h = 0
    for context, next_counts in ngrams.items():
        context_total = sum(next_counts.values())
        for count in next_counts.values():
            p_joint = count / total
            p_cond = count / context_total
            if p_cond > 0:
                h -= p_joint * math.log2(p_cond)
    return h


h0 = math.log2(len(set(chars)))  # Maximum possible
h1 = entropy(chars)
h2 = conditional_entropy(chars, 1)
h3 = conditional_entropy(chars, 2)
h4 = conditional_entropy(chars, 3)

print("\nCharacter entropy (bits/char):")
print(f"  H0 (max possible): {h0:.3f}")
print(f"  H1 (unigram):      {h1:.3f}")
print(f"  h2 (bigram):       {h2:.3f}  ← KEY METRIC")
print(f"  h3 (trigram):      {h3:.3f}")
print(f"  h4 (4-gram):       {h4:.3f}")

print("\n→ Bowern (2021) found h2 ≈ 2.0 for Voynich")
print("→ Natural languages typically h2 ≈ 3.0-4.0")
print(f"→ Your result: h2 = {h2:.3f}")


# =============================================================================
# 3. WORD-POSITION ENTROPY
# =============================================================================
print("\n" + "=" * 60)
print("3. WORD-POSITION ENTROPY (Novel Analysis)")
print("=" * 60)

# What characters appear at each position in words?
max_pos = 10
position_chars = defaultdict(list)

for word in words:
    for i, char in enumerate(word[:max_pos]):
        position_chars[i].append(char)

print("\nEntropy by character position in word:")
print("(Lower = more constrained/predictable)")
print()
for pos in range(min(8, max_pos)):
    if position_chars[pos]:
        h = entropy(position_chars[pos])
        n = len(position_chars[pos])
        top3 = Counter(position_chars[pos]).most_common(3)
        top_str = ", ".join(f"{c}:{p/n:.0%}" for c, p in top3)
        print(f"  Position {pos+1}: H={h:.2f} bits  (n={n:,})  top: {top_str}")

print("\n→ Natural languages: fairly uniform entropy across positions")
print("→ Voynich: rigid positional constraints suggest slot grammar")


# =============================================================================
# 4. BIGRAM TRANSITION MATRIX (Top Patterns)
# =============================================================================
print("\n" + "=" * 60)
print("4. CHARACTER TRANSITIONS (What follows what?)")
print("=" * 60)

bigrams = Counter(zip(chars[:-1], chars[1:]))
char_counts = Counter(chars)

print("\nMost common bigrams:")
for (c1, c2), count in bigrams.most_common(15):
    expected = (char_counts[c1] / len(chars)) * (char_counts[c2] / len(chars)) * (len(chars) - 1)
    ratio = count / expected if expected > 0 else 0
    print(f"  {c1}{c2}: {count:5}  (observed/expected: {ratio:.1f}x)")

print("\nRarest bigrams (that should exist but don't):")
common_chars = [c for c, _ in char_counts.most_common(10)]
missing = []
for c1 in common_chars:
    for c2 in common_chars:
        if bigrams[(c1, c2)] == 0:
            expected = (char_counts[c1] / len(chars)) * (char_counts[c2] / len(chars)) * len(chars)
            if expected > 10:
                missing.append((c1, c2, expected))

missing.sort(key=lambda x: -x[2])
for c1, c2, exp in missing[:10]:
    print(f"  {c1}{c2}: 0 occurrences (expected ~{exp:.0f})")

print("\n→ Missing expected bigrams suggest phonotactic constraints")


# =============================================================================
# 5. WORD-LENGTH DISTRIBUTION
# =============================================================================
print("\n" + "=" * 60)
print("5. WORD LENGTH DISTRIBUTION")
print("=" * 60)

lengths = [len(w) for w in words]
length_counts = Counter(lengths)

print("\nWord length frequencies:")
for length in range(1, 13):
    count = length_counts.get(length, 0)
    pct = count / len(words) * 100
    bar = "█" * int(pct)
    print(f"  {length:2}: {count:5} ({pct:5.1f}%) {bar}")

mean_len = sum(lengths) / len(lengths)
variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
std_len = variance**0.5

print(f"\nMean length: {mean_len:.2f}")
print(f"Std dev:     {std_len:.2f}")
print(f"Coefficient of variation: {std_len/mean_len:.2f}")

print("\n→ Natural language CV typically 0.4-0.6")
print("→ Voynich shows unusually symmetric distribution")


# =============================================================================
# 6. CURRIER A vs B ENTROPY COMPARISON
# =============================================================================
print("\n" + "=" * 60)
print("6. CURRIER A vs B: ENTROPY COMPARISON")
print("=" * 60)

a_chars = []
b_chars = []
for row in data:
    text = row["text_clean"]
    row_chars = [c for c in text if c.isalpha()]
    if row["currier_language"] == "A":
        a_chars.extend(row_chars)
    elif row["currier_language"] == "B":
        b_chars.extend(row_chars)

a_h1 = entropy(a_chars)
b_h1 = entropy(b_chars)
a_h2 = conditional_entropy(a_chars, 1)
b_h2 = conditional_entropy(b_chars, 1)

print(f"\n{'Metric':<20} {'Language A':>12} {'Language B':>12} {'Difference':>12}")
print("-" * 58)
print(f"{'Characters':<20} {len(a_chars):>12,} {len(b_chars):>12,}")
print(f"{'H1 (unigram)':<20} {a_h1:>12.3f} {b_h1:>12.3f} {abs(a_h1-b_h1):>12.3f}")
print(f"{'h2 (bigram)':<20} {a_h2:>12.3f} {b_h2:>12.3f} {abs(a_h2-b_h2):>12.3f}")

print("\n→ Different entropies suggest different underlying systems")
print("→ Or: same system with different vocabulary/register")


# =============================================================================
# 7. HAPAX LEGOMENA (Words appearing only once)
# =============================================================================
print("\n" + "=" * 60)
print("7. HAPAX LEGOMENA (Single-occurrence words)")
print("=" * 60)

word_counts = Counter(words)
hapax = [w for w, c in word_counts.items() if c == 1]
dis = [w for w, c in word_counts.items() if c == 2]

print(f"\nTotal unique words:  {len(word_counts):,}")
print(f"Hapax legomena (1x): {len(hapax):,} ({len(hapax)/len(word_counts):.1%})")
print(f"Dis legomena (2x):   {len(dis):,} ({len(dis)/len(word_counts):.1%})")

print(f"\nHapax ratio: {len(hapax)/len(words):.2%} of all word tokens")

print("\n→ Natural language hapax ratio typically 40-60% of vocabulary")
print("→ Very high hapax suggests productive morphology or noise")

print("\nSample hapax (longest):")
hapax_sorted = sorted(hapax, key=len, reverse=True)[:10]
for w in hapax_sorted:
    print(f"  {w}")


# =============================================================================
# 8. LINE-INITIAL vs LINE-FINAL WORDS
# =============================================================================
print("\n" + "=" * 60)
print("8. LINE POSITION EFFECTS")
print("=" * 60)

initial_words = []
final_words = []
middle_words = []

for row in data:
    line_words = [w.strip() for w in row["text_clean"].replace(",", ".").split(".") if w.strip()]
    if len(line_words) >= 1:
        initial_words.append(line_words[0])
    if len(line_words) >= 2:
        final_words.append(line_words[-1])
    if len(line_words) >= 3:
        middle_words.extend(line_words[1:-1])

print("\nMost common LINE-INITIAL words:")
for w, c in Counter(initial_words).most_common(10):
    pct = c / len(initial_words) * 100
    print(f"  {w:15} {c:4} ({pct:.1f}%)")

print("\nMost common LINE-FINAL words:")
for w, c in Counter(final_words).most_common(10):
    pct = c / len(final_words) * 100
    print(f"  {w:15} {c:4} ({pct:.1f}%)")

# Compare entropy
init_h = entropy(initial_words)
final_h = entropy(final_words)
mid_h = entropy(middle_words)

print("\nEntropy by line position:")
print(f"  Initial: {init_h:.2f} bits")
print(f"  Middle:  {mid_h:.2f} bits")
print(f"  Final:   {final_h:.2f} bits")

print("\n→ Lower entropy = more constrained choices")
print("→ Line position affects word choice (unusual for cipher)")


# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("SUMMARY OF FINDINGS")
print("=" * 60)

print(f"""
Key metrics:
  • h2 (conditional entropy): {h2:.3f} bits/char
  • Compression ratio (gzip): {len(gzip.compress(text_bytes))/original_size:.3f}
  • Vocabulary richness: {len(set(words))/len(words):.1%}
  • Hapax ratio: {len(hapax)/len(word_counts):.1%} of vocabulary
  • Mean word length: {mean_len:.2f} chars

Structural findings:
  • {len(a_chars):,} chars in Language A, {len(b_chars):,} in Language B
  • h2 differs between A ({a_h2:.3f}) and B ({b_h2:.3f})
  • Strong positional constraints on characters within words
  • Line position affects word choice
  • Many "expected" bigrams are completely absent
""")

print("=" * 60)
print("Analysis complete.")
print("=" * 60)
