#!/usr/bin/env python3
"""
Seed the database with the existing hand-crafted data from word_database.json.

This preserves the original sound-change rules data (roots, affixes, simple words)
as high-quality curated entries alongside the imported dataset data.
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))

from models import DEFAULT_DB_PATH, create_database

JSON_DB = os.path.join(PROJECT_ROOT, "api", "word_database.json")


def seed_from_json(db_path: str = DEFAULT_DB_PATH, json_path: str = JSON_DB):
    """Seed the SQLite database from the existing word_database.json."""
    if not os.path.exists(json_path):
        print(f"  ✗ word_database.json not found at: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = create_database(db_path)

    # === Import simple words as Basic Words ===
    simple_words = data.get("simple_words", {})
    for word, info in simple_words.items():
        conn.execute(
            "INSERT OR REPLACE INTO words "
            "(text, language, frequency, pos, definition, is_basic, basic_score, source) "
            "VALUES (?, 'en', 0.01, '', ?, 1, 100.0, 'curated')",
            (word.lower(), info.get("meaning", ""))
        )
    print(f"  ✓ Seeded {len(simple_words)} simple/basic words")

    # === Import roots ===
    roots = data.get("roots", {})
    for root_key, root_data in roots.items():
        # Insert root
        conn.execute(
            "INSERT OR REPLACE INTO roots "
            "(canonical_form, language, meaning, meaning_zh, description, "
            "reconstructed, confidence, source) "
            "VALUES (?, 'Latin/Greek', ?, ?, ?, 0, 0.9, 'curated')",
            (
                root_key.lower(),
                root_data.get("meaning", ""),
                root_data.get("meaning_zh", ""),
                root_data.get("explanation", "")
            )
        )

        # Insert sound-change relationship (origin_word → root)
        origin = root_data.get("origin_word", "").lower()
        if origin:
            conn.execute(
                "INSERT OR IGNORE INTO relationships "
                "(source_term, source_lang, target_term, target_lang, "
                "relationship_type, confidence, explanation, source) "
                "VALUES (?, 'en', ?, 'Latin/Greek', 'sound_change', 0.9, ?, 'curated')",
                (origin, root_key, root_data.get("explanation", ""))
            )

        # Insert derived words as relationships
        for derived in root_data.get("derived_words", []):
            conn.execute(
                "INSERT OR IGNORE INTO relationships "
                "(source_term, source_lang, target_term, target_lang, "
                "relationship_type, confidence, explanation, source) "
                "VALUES (?, 'en', ?, 'Latin/Greek', 'derived_from', 0.8, '', 'curated')",
                (derived.lower(), root_key)
            )
            # Also add derived word to words table
            conn.execute(
                "INSERT OR IGNORE INTO words (text, language, source) "
                "VALUES (?, 'en', 'curated')",
                (derived.lower(),)
            )

        # Insert friend word relationships
        for derived in root_data.get("derived_words", []):
            for other_derived in root_data.get("derived_words", []):
                if derived.lower() != other_derived.lower():
                    conn.execute(
                        "INSERT OR IGNORE INTO friend_words "
                        "(word, friend, shared_root, confidence) "
                        "VALUES (?, ?, ?, 0.9)",
                        (derived.lower(), other_derived.lower(), root_key)
                    )

    print(f"  ✓ Seeded {len(roots)} roots with relationships")

    # === Import affixes ===
    prefixes = data.get("affixes", {}).get("prefixes", {})
    for pfx, info in prefixes.items():
        meaning = info["meaning"] if isinstance(info, dict) else info
        meaning_zh = info.get("meaning_zh", "") if isinstance(info, dict) else ""
        conn.execute(
            "INSERT OR REPLACE INTO affixes (text, type, meaning, meaning_zh, source) "
            "VALUES (?, 'prefix', ?, ?, 'curated')",
            (pfx, meaning, meaning_zh)
        )

    suffixes = data.get("affixes", {}).get("suffixes", {})
    for sfx, info in suffixes.items():
        meaning = info["meaning"] if isinstance(info, dict) else info
        meaning_zh = info.get("meaning_zh", "") if isinstance(info, dict) else ""
        conn.execute(
            "INSERT OR REPLACE INTO affixes (text, type, meaning, meaning_zh, source) "
            "VALUES (?, 'suffix', ?, ?, 'curated')",
            (sfx, meaning, meaning_zh)
        )

    print(f"  ✓ Seeded {len(prefixes)} prefixes, {len(suffixes)} suffixes")

    # === Set metadata ===
    conn.execute(
        "INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('seed_version', '1.0')"
    )
    conn.execute(
        "INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('seed_source', 'word_database.json')"
    )

    conn.commit()
    conn.close()
    print("  ✓ Seeding complete!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🌱 Seeding database from word_database.json")
    print("=" * 60)
    success = seed_from_json()
    if success:
        print("\n✅ Seed complete!")
    else:
        print("\n❌ Seed failed!")
        sys.exit(1)
