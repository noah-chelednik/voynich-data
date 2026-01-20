"""Quick Voynich analysis using published dataset."""

from collections import Counter

from datasets import load_dataset

# Load YOUR published dataset
print("Loading dataset from HuggingFace...")
ds = load_dataset("Ched-ai/voynich-eva", data_files="eva_lines.parquet")
data = ds["train"]
print(f"Loaded {len(data)} records\n")

# Extract all words
words = []
for row in data:
    text = row["text_clean"].replace(",", ".")
    for word in text.split("."):
        word = word.strip()
        if word:
            words.append(word)

print("=== BASIC STATS ===")
print(f"Total words: {len(words):,}")
print(f"Unique words: {len(set(words)):,}")
print(f"Vocabulary richness: {len(set(words)) / len(words):.2%}")

print("\n=== TOP 20 MOST COMMON WORDS ===")
for word, count in Counter(words).most_common(20):
    print(f"  {word:15} {count:5}")

print("\n=== WORD-INITIAL CHARACTERS ===")
initials = Counter(w[0] for w in words if w)
for char, count in initials.most_common(10):
    print(f"  {char}: {count:5} ({count/len(words):.1%})")

print("\n=== WORD-FINAL CHARACTERS ===")
finals = Counter(w[-1] for w in words if w)
for char, count in finals.most_common(10):
    print(f"  {char}: {count/len(words):.1%})")

print("\n=== CURRIER LANGUAGE A vs B ===")
a_words = []
b_words = []
for row in data:
    text = row["text_clean"].replace(",", ".")
    ws = [w.strip() for w in text.split(".") if w.strip()]
    if row["currier_language"] == "A":
        a_words.extend(ws)
    elif row["currier_language"] == "B":
        b_words.extend(ws)

print(f"Language A: {len(a_words):,} words")
print(f"Language B: {len(b_words):,} words")

a_top = [w for w, c in Counter(a_words).most_common(5)]
b_top = [w for w, c in Counter(b_words).most_common(5)]
print(f"A top words: {a_top}")
print(f"B top words: {b_top}")

a_only = set(a_words) - set(b_words)
b_only = set(b_words) - set(a_words)
print(f"\nWords ONLY in A: {len(a_only)}")
print(f"Words ONLY in B: {len(b_only)}")
print(f"A-only examples: {list(a_only)[:8]}")
print(f"B-only examples: {list(b_only)[:8]}")

