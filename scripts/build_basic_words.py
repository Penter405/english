#!/usr/bin/env python3
"""
Build the Basic Word database (~10,000 words).

Per spec Sections 7-9:
  - Start from frequency-ranked common English words
  - Filter out words with known morphological decomposition
  - Filter out words with known affix structure
  - Filter out words with known etymological decomposition
  - Score remaining candidates
  - Process in batches of ~1,000
  - Quality over quantity

A Basic Word is a computational search anchor — a word the Engine considers
a useful stopping point because it doesn't have a sufficiently supported
decomposition into other meaningful English components.
"""

import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))

from models import DEFAULT_DB_PATH, create_database


def build_basic_words(db_path: str = DEFAULT_DB_PATH, target: int = 10000):
    """Build the Basic Word database."""
    conn = create_database(db_path)

    # Load all known affixes for filtering
    prefix_rows = conn.execute("SELECT text FROM affixes WHERE type='prefix'").fetchall()
    suffix_rows = conn.execute("SELECT text FROM affixes WHERE type='suffix'").fetchall()
    prefixes = sorted([r[0] for r in prefix_rows], key=len, reverse=True)
    suffixes = sorted([r[0] for r in suffix_rows], key=len, reverse=True)

    print(f"  📋 Known prefixes: {len(prefixes)}, suffixes: {len(suffixes)}")

    # Get candidate words: ordered by frequency, English only
    candidates = conn.execute(
        "SELECT text, frequency FROM words "
        "WHERE language = 'en' AND LENGTH(text) >= 2 "
        "ORDER BY frequency DESC"
    ).fetchall()

    print(f"  📊 Total candidate words: {len(candidates):,}")

    # Words with known morphological decomposition
    morph_words = set()
    morph_rows = conn.execute("SELECT word FROM morphology").fetchall()
    for r in morph_rows:
        morph_words.add(r[0])
    print(f"  📝 Words with morphological decompositions: {len(morph_words):,}")

    # Words with known etymological decomposition (derived from something)
    etym_decomp = set()
    etym_rows = conn.execute(
        "SELECT source_term FROM relationships "
        "WHERE source_lang = 'en' OR source_lang = 'English'"
    ).fetchall()
    for r in etym_rows:
        etym_decomp.add(r[0].lower())

    basic_count = 0
    rejected_morph = 0
    rejected_affix = 0
    batch_num = 0
    batch = []

    for word_text, frequency in candidates:
        if basic_count >= target:
            break

        word = word_text.lower().strip()

        # Skip very short or very long words as candidates initially
        if len(word) < 2 or len(word) > 20:
            continue

        # Skip words with numbers or special chars
        if not word.isalpha():
            continue

        # === FILTER 1: Known morphological decomposition ===
        # If MorphoLex tells us this word decomposes into multiple morphemes,
        # it's probably NOT a basic word (spec Section 8)
        if word in morph_words:
            # Check if decomposition has >1 morphemes
            decomp = conn.execute(
                "SELECT morphemes FROM morphology WHERE word = ?", (word,)
            ).fetchone()
            if decomp:
                try:
                    morphemes = json.loads(decomp[0])
                    if len(morphemes) > 1:
                        rejected_morph += 1
                        continue
                except Exception:
                    pass

        # === FILTER 2: Known affix structure ===
        # If the word clearly starts with a known prefix or ends with a known suffix,
        # and the remainder is also a known word, reject it
        has_affix = False
        for pfx in prefixes:
            if word.startswith(pfx) and len(word) > len(pfx) + 2:
                remainder = word[len(pfx):]
                # Check if remainder is itself a word
                rem_exists = conn.execute(
                    "SELECT 1 FROM words WHERE text = ?", (remainder,)
                ).fetchone()
                if rem_exists:
                    has_affix = True
                    break

        if not has_affix:
            for sfx in suffixes:
                if word.endswith(sfx) and len(word) > len(sfx) + 2:
                    remainder = word[:-len(sfx)]
                    rem_exists = conn.execute(
                        "SELECT 1 FROM words WHERE text = ?", (remainder,)
                    ).fetchone()
                    if rem_exists:
                        has_affix = True
                        break

        if has_affix:
            rejected_affix += 1
            continue

        # === SCORING ===
        # Higher score = more likely to be a good Basic Word
        score = 0.0

        # Frequency bonus (common words are better anchors)
        if frequency > 0:
            score += min(40, frequency * 100000)

        # Length bonus (shorter words tend to be more basic, but not exclusively)
        if len(word) <= 4:
            score += 20
        elif len(word) <= 6:
            score += 15
        elif len(word) <= 8:
            score += 10
        else:
            score += 5

        # Not in etymological decomposition set = more likely basic
        if word not in etym_decomp:
            score += 10

        # Stability: common Anglo-Saxon / Germanic words score higher
        # (approximated by frequency + short length)
        if frequency > 1e-4 and len(word) <= 6:
            score += 15

        # Minimum score threshold
        if score < 10:
            continue

        batch.append((score, word))
        basic_count += 1

        if len(batch) >= 1000:
            batch_num += 1
            _flush_basic_batch(conn, batch)
            accepted = len(batch)
            print(f"    Batch {batch_num}: {accepted} basic words "
                  f"(total: {basic_count:,}/{target:,})")
            batch.clear()

    # Final batch
    if batch:
        batch_num += 1
        _flush_basic_batch(conn, batch)
        print(f"    Batch {batch_num}: {len(batch)} basic words "
              f"(total: {basic_count:,}/{target:,})")

    conn.commit()

    # Stats
    final_count = conn.execute(
        "SELECT COUNT(*) FROM words WHERE is_basic = 1"
    ).fetchone()[0]

    print(f"\n  ✓ Basic Words created: {final_count:,}")
    print(f"  📊 Rejected (morphological): {rejected_morph:,}")
    print(f"  📊 Rejected (affix structure): {rejected_affix:,}")

    if final_count < target:
        print(f"  ⚠ Could not reach target of {target:,} — "
              f"candidate pool exhausted at {final_count:,}")
        print("    (Quality over quantity per spec Section 9)")

    conn.close()
    return True


def _flush_basic_batch(conn, batch):
    """Mark words as basic words with their scores."""
    for score, word in batch:
        conn.execute(
            "UPDATE words SET is_basic = 1, basic_score = ? WHERE text = ?",
            (score, word)
        )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=10000, help="Target basic word count")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    args = parser.parse_args()

    print("=" * 60)
    print("🔤 Building Basic Word Database")
    print("=" * 60)

    if args.stats:
        conn = create_database()
        count = conn.execute("SELECT COUNT(*) FROM words WHERE is_basic = 1").fetchone()[0]
        print(f"  Basic words in database: {count:,}")
        # Show some examples
        rows = conn.execute(
            "SELECT text, basic_score, frequency FROM words "
            "WHERE is_basic = 1 ORDER BY basic_score DESC LIMIT 20"
        ).fetchall()
        print("\n  Top 20 Basic Words:")
        for r in rows:
            print(f"    {r[0]:15s}  score={r[1]:.1f}  freq={r[2]:.6f}")
        conn.close()
    else:
        success = build_basic_words(target=args.target)
        if success:
            print("\n✅ Basic Word generation complete!")
        else:
            print("\n❌ Basic Word generation failed!")
            sys.exit(1)
