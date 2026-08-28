#!/usr/bin/env python3
"""
Import WordNet data into the SQLite database.

Uses NLTK's WordNet interface to extract:
  - English lexical entries
  - Definitions
  - Parts of speech
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))

from models import DEFAULT_DB_PATH, create_database

WORDNET_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "wordnet")


def import_wordnet(db_path: str = DEFAULT_DB_PATH):
    """Import WordNet lexical data."""
    try:
        import nltk
        nltk.data.path.insert(0, WORDNET_DIR)
        # Try to load wordnet, download if missing
        try:
            from nltk.corpus import wordnet as wn
            wn.synsets("test")
        except LookupError:
            print("  ⬇ Downloading WordNet data...")
            nltk.download("wordnet", download_dir=WORDNET_DIR, quiet=True)
            nltk.download("omw-1.4", download_dir=WORDNET_DIR, quiet=True)
            from nltk.corpus import wordnet as wn
    except ImportError:
        print("  ✗ NLTK not installed. Run: pip install nltk")
        return False

    print("  📖 Reading WordNet...")

    conn = create_database(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    # POS mapping
    pos_map = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb", "s": "adjective"}

    word_count = 0
    batch = []

    # Get all lemma names (unique words in WordNet)
    all_lemmas = set()
    for synset in wn.all_synsets():
        for lemma in synset.lemmas():
            name = lemma.name().lower().replace("_", " ")
            if name.isalpha() and len(name) > 1:
                all_lemmas.add(name)

    print(f"  📊 Total unique words in WordNet: {len(all_lemmas):,}")

    for word in all_lemmas:
        synsets = wn.synsets(word)
        if not synsets:
            continue

        # Use the first synset for primary definition and POS
        first_syn = synsets[0]
        pos = pos_map.get(first_syn.pos(), "")
        definition = first_syn.definition() or ""

        # Truncate long definitions
        if len(definition) > 200:
            definition = definition[:197] + "..."

        batch.append((word, "en", pos, definition, "wordnet"))
        word_count += 1

        if len(batch) >= 5000:
            conn.executemany(
                "INSERT OR IGNORE INTO words (text, language, pos, definition, source) "
                "VALUES (?, ?, ?, ?, ?)",
                batch
            )
            conn.commit()
            batch.clear()
            if word_count % 20000 == 0:
                print(f"    ... imported {word_count:,} words")

    # Final flush
    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO words (text, language, pos, definition, source) "
            "VALUES (?, ?, ?, ?, ?)",
            batch
        )

    conn.commit()
    print(f"  ✓ Imported {word_count:,} words from WordNet")
    conn.close()
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("📖 Importing WordNet")
    print("=" * 60)
    success = import_wordnet()
    if success:
        print("\n✅ WordNet import complete!")
    else:
        print("\n❌ WordNet import failed!")
        sys.exit(1)
