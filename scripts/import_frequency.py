#!/usr/bin/env python3
"""
Import word frequency data from the wordfreq package.

Updates the `frequency` field for all words already in the database.
Also adds common English words that may be missing.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))

from models import DEFAULT_DB_PATH, create_database


def import_frequency(db_path: str = DEFAULT_DB_PATH):
    """Import word frequency data from wordfreq."""
    try:
        from wordfreq import word_frequency, top_n_list
    except ImportError:
        print("  ✗ wordfreq not installed. Run: pip install wordfreq")
        return False

    print("  📖 Loading word frequency data...")

    conn = create_database(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    # Step 1: Update frequencies for existing words
    print("  📊 Updating frequencies for existing words...")
    cursor = conn.execute("SELECT text FROM words")
    existing_words = [row[0] for row in cursor.fetchall()]
    print(f"    {len(existing_words):,} existing words to update")

    updated = 0
    batch = []
    for word in existing_words:
        freq = word_frequency(word, "en")
        if freq > 0:
            batch.append((freq, word))
            updated += 1

        if len(batch) >= 5000:
            conn.executemany("UPDATE words SET frequency = ? WHERE text = ?", batch)
            batch.clear()

    if batch:
        conn.executemany("UPDATE words SET frequency = ? WHERE text = ?", batch)
    conn.commit()
    print(f"  ✓ Updated frequency for {updated:,} words")

    # Step 2: Add top English words that may be missing
    print("  📊 Adding top English words from wordfreq...")
    try:
        top_words = top_n_list("en", 50000)
    except Exception:
        top_words = top_n_list("en", 20000)

    added = 0
    batch = []
    for word in top_words:
        if not word.isalpha() or len(word) < 2:
            continue
        freq = word_frequency(word, "en")
        batch.append((word, "en", freq, "wordfreq"))
        added += 1

        if len(batch) >= 5000:
            conn.executemany(
                "INSERT OR IGNORE INTO words (text, language, frequency, source) "
                "VALUES (?, ?, ?, ?)",
                batch
            )
            conn.commit()
            batch.clear()

    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO words (text, language, frequency, source) "
            "VALUES (?, ?, ?, ?)",
            batch
        )
    conn.commit()

    print(f"  ✓ Added up to {added:,} top English words")
    conn.close()
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("📊 Importing Word Frequencies")
    print("=" * 60)
    success = import_frequency()
    if success:
        print("\n✅ Frequency import complete!")
    else:
        print("\n❌ Frequency import failed!")
        sys.exit(1)
