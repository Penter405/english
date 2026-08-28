#!/usr/bin/env python3
"""
Import Etymology DB (droher/etymology-db) into the SQLite database.

Reads the CSV file and extracts:
  - English words and their etymological relationships
  - Root forms from various languages
  - derived_from, inherited_from, borrowed_from relationships
"""

import csv
import os
import sys
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))

from models import DEFAULT_DB_PATH, create_database

RAW_CSV = os.path.join(PROJECT_ROOT, "data", "raw", "etymology-db", "etymology.csv")

# Relationship types we care about
RELEVANT_RELTYPES = {
    "derived", "inherited", "borrowed",
    "has_derived_form", "etymological_origin_of",
    "etymologically_related", "cognate",
    "root",
}


def import_etymology(db_path: str = DEFAULT_DB_PATH, csv_path: str = RAW_CSV):
    """Import etymology data from CSV into SQLite."""
    if not os.path.exists(csv_path):
        print(f"  ✗ Etymology DB CSV not found at: {csv_path}")
        print("    Run: python scripts/download_datasets.py --only etymology")
        return False

    print("  📖 Reading Etymology DB CSV...")
    conn = create_database(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    # Count lines for progress
    total_lines = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        for _ in f:
            total_lines += 1
    print(f"  📊 Total rows: {total_lines:,}")

    # Track unique English words and roots
    english_words = set()
    roots_added = set()
    rel_count = 0
    batch_size = 10000

    rel_batch = []
    root_batch = []
    word_batch = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        print(f"  📋 CSV fields: {fields}")

        for i, row in enumerate(reader):
            if i % 100000 == 0 and i > 0:
                print(f"    ... processed {i:,}/{total_lines:,} rows")
                # Flush batches
                _flush_batches(conn, word_batch, root_batch, rel_batch)
                word_batch.clear()
                root_batch.clear()
                rel_batch.clear()

            try:
                term = row.get("term", "").strip().lower()
                lang = row.get("lang", "").strip()
                reltype = row.get("reltype", "").strip()
                related_term = row.get("related_term", "").strip().lower()
                related_lang = row.get("related_lang", "").strip()

                if not term or not related_term:
                    continue

                # We focus on English words and their etymological sources
                if lang == "English" and term not in english_words:
                    english_words.add(term)
                    word_batch.append((term, "en", "", "", "etymology-db"))

                # Store roots from other languages
                if related_lang and related_lang != "English" and related_term not in roots_added:
                    roots_added.add(related_term)
                    root_batch.append((
                        related_term, related_lang, "", "", "",
                        1 if related_lang.startswith("Proto") else 0,
                        0.5, "etymology-db"
                    ))

                # Store the relationship
                # Normalize relationship type
                norm_reltype = _normalize_reltype(reltype)
                if norm_reltype:
                    rel_batch.append((
                        term, lang, related_term, related_lang,
                        norm_reltype, 0.6, "", "etymology-db"
                    ))
                    rel_count += 1

            except Exception:
                continue

    # Final flush
    _flush_batches(conn, word_batch, root_batch, rel_batch)
    conn.commit()

    print(f"  ✓ Imported {len(english_words):,} English words")
    print(f"  ✓ Imported {len(roots_added):,} root forms")
    print(f"  ✓ Imported {rel_count:,} relationships")
    conn.close()
    return True


def _normalize_reltype(reltype: str) -> str:
    """Normalize etymology relationship types."""
    rt = reltype.lower().strip()
    if "derived" in rt:
        return "derived_from"
    elif "inherited" in rt:
        return "inherited_from"
    elif "borrowed" in rt or "loan" in rt:
        return "borrowed_from"
    elif "cognate" in rt:
        return "cognate_of"
    elif "root" in rt:
        return "has_root"
    elif "related" in rt:
        return "related_to"
    return ""


def _flush_batches(conn, word_batch, root_batch, rel_batch):
    """Flush accumulated batches to the database."""
    if word_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO words (text, language, pos, definition, source) "
            "VALUES (?, ?, ?, ?, ?)",
            word_batch
        )
    if root_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO roots "
            "(canonical_form, language, meaning, meaning_zh, description, "
            "reconstructed, confidence, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            root_batch
        )
    if rel_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO relationships "
            "(source_term, source_lang, target_term, target_lang, "
            "relationship_type, confidence, explanation, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rel_batch
        )


if __name__ == "__main__":
    print("=" * 60)
    print("📚 Importing Etymology DB")
    print("=" * 60)
    success = import_etymology()
    if success:
        print("\n✅ Etymology import complete!")
    else:
        print("\n❌ Etymology import failed!")
        sys.exit(1)
