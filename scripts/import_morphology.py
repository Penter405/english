#!/usr/bin/env python3
"""
Import MorphoLex-en morphological decompositions into the SQLite database.

Reads MorphoLEX_en.xlsx which contains multiple sheets organized by
morpheme pattern. Key columns: Word, MorphoLexSegm, POS, Nmorph.

Segmentation format: <un<{<ob<(trude)}>ive>>ness>
  - <...< = prefix
  - (...) = root
  - >...> = suffix
  - {...} = groups

Also imports the "All prefixes", "All suffixes", "All roots" sheets.
"""

import os
import sys
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))

from models import DEFAULT_DB_PATH, create_database

RAW_XLSX = os.path.join(PROJECT_ROOT, "data", "raw", "morpholex", "MorphoLEX_en.xlsx")


def import_morphology(db_path: str = DEFAULT_DB_PATH, xlsx_path: str = RAW_XLSX):
    """Import MorphoLex morphological data."""
    if not os.path.exists(xlsx_path):
        print(f"  ✗ MorphoLex file not found at: {xlsx_path}")
        print("    Run: python scripts/download_datasets.py --only morpholex")
        return False

    try:
        import pandas as pd
    except ImportError:
        print("  ✗ pandas not installed. Run: pip install pandas openpyxl")
        return False

    print("  📖 Reading MorphoLEX_en.xlsx (all sheets)...")
    try:
        all_sheets = pd.read_excel(xlsx_path, engine="openpyxl", sheet_name=None)
    except Exception as e:
        print(f"  ✗ Failed to read Excel file: {e}")
        return False

    print(f"  📋 Found {len(all_sheets)} sheets: {list(all_sheets.keys())}")

    conn = create_database(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    morph_count = 0
    word_count = 0

    # === Import word decompositions from numbered sheets ===
    morph_batch = []
    word_batch = []

    for sheet_name, df in all_sheets.items():
        # Skip the summary sheets (handled separately below)
        if sheet_name.startswith("All "):
            continue

        cols = [str(c).strip() for c in df.columns]

        # Find the Word and MorphoLexSegm columns
        word_col = None
        segm_col = None
        pos_col = None
        for c in cols:
            cl = c.lower()
            if cl == "word":
                word_col = c
            elif "morpholexsegm" in cl or "segm" in cl:
                segm_col = c
            elif cl == "pos":
                pos_col = c

        if word_col is None or segm_col is None:
            continue

        for _, row in df.iterrows():
            try:
                word = str(row[word_col]).strip().lower()
                segm = str(row[segm_col]).strip()

                if not word or word == "nan" or not segm or segm == "nan":
                    continue

                pos = str(row[pos_col]).strip() if pos_col else ""
                if pos == "nan":
                    pos = ""

                # Parse the segmentation
                morphemes = _parse_morpholex_segm(segm)
                if morphemes and len(morphemes) >= 1:
                    structure = _build_structure(segm)
                    morph_batch.append((
                        word,
                        json.dumps(morphemes),
                        structure,
                        "morpholex"
                    ))
                    morph_count += 1

                # Add word
                word_batch.append((word, "en", pos, "", "morpholex"))
                word_count += 1

            except Exception:
                continue

        # Flush periodically
        if len(morph_batch) >= 5000:
            _flush_morph_batch(conn, word_batch, morph_batch)
            word_batch.clear()
            morph_batch.clear()

    # Final flush for decompositions
    _flush_morph_batch(conn, word_batch, morph_batch)
    word_batch.clear()
    morph_batch.clear()

    # === Import "All prefixes" sheet ===
    prefix_count = 0
    if "All prefixes" in all_sheets:
        pfx_df = all_sheets["All prefixes"]
        for _, row in pfx_df.iterrows():
            try:
                morpheme = str(row.get("morpheme", "")).strip()
                # Clean: remove < > markers
                clean = morpheme.strip("<>").lower()
                if clean and len(clean) >= 1 and clean.isalpha():
                    conn.execute(
                        "INSERT OR IGNORE INTO affixes (text, type, meaning, meaning_zh, source) "
                        "VALUES (?, 'prefix', '', '', 'morpholex')",
                        (clean,)
                    )
                    prefix_count += 1
            except Exception:
                continue
        print(f"  ✓ Imported {prefix_count} prefixes from MorphoLex")

    # === Import "All suffixes" sheet ===
    suffix_count = 0
    if "All suffixes" in all_sheets:
        sfx_df = all_sheets["All suffixes"]
        for _, row in sfx_df.iterrows():
            try:
                morpheme = str(row.get("morpheme", "")).strip()
                clean = morpheme.strip("<>").lower()
                if clean and len(clean) >= 1 and clean.isalpha():
                    conn.execute(
                        "INSERT OR IGNORE INTO affixes (text, type, meaning, meaning_zh, source) "
                        "VALUES (?, 'suffix', '', '', 'morpholex')",
                        (clean,)
                    )
                    suffix_count += 1
            except Exception:
                continue
        print(f"  ✓ Imported {suffix_count} suffixes from MorphoLex")

    # === Import "All roots" sheet ===
    root_count = 0
    if "All roots" in all_sheets:
        root_df = all_sheets["All roots"]
        for _, row in root_df.iterrows():
            try:
                morpheme = str(row.get("morpheme", "")).strip()
                clean = morpheme.strip("()").lower()
                if clean and len(clean) >= 2 and clean.isalpha():
                    conn.execute(
                        "INSERT OR IGNORE INTO roots "
                        "(canonical_form, language, meaning, meaning_zh, description, "
                        "reconstructed, confidence, source) "
                        "VALUES (?, 'English', '', '', '', 0, 0.4, 'morpholex')",
                        (clean,)
                    )
                    root_count += 1
            except Exception:
                continue
        print(f"  ✓ Imported {root_count} roots from MorphoLex")

    conn.commit()

    print(f"  ✓ Total: {word_count:,} words, {morph_count:,} decompositions")
    conn.close()
    return True


def _parse_morpholex_segm(segm: str) -> list:
    """Parse MorphoLex segmentation format into a flat list of morphemes.

    Format: <un<{<ob<(trude)}>ive>>ness>
    - (xxx) = root morpheme
    - <xxx< = prefix
    - >xxx> = suffix
    """
    # Extract all morphemes using regex
    # Roots are in parentheses: (word)
    # Prefixes are between < markers
    # Suffixes are between > markers
    morphemes = []

    # Find roots first: (morpheme)
    roots = re.findall(r'\(([^)]+)\)', segm)
    morphemes.extend(roots)

    # Find prefixes: text between < and <
    prefixes = re.findall(r'<([a-zA-Z]+)<', segm)
    for p in prefixes:
        if p not in morphemes:
            morphemes.insert(0, p)

    # Find suffixes: text between > and >
    suffixes = re.findall(r'>([a-zA-Z]+)>', segm)
    for s in suffixes:
        if s not in morphemes:
            morphemes.append(s)

    return [m.lower() for m in morphemes if m]


def _build_structure(segm: str) -> str:
    """Build a structure string like 'prefix+root+suffix'."""
    parts = []
    if '<' in segm and re.search(r'<[a-zA-Z]+<', segm):
        parts.append("prefix")
    if '(' in segm:
        parts.append("root")
    if '>' in segm and re.search(r'>[a-zA-Z]+>', segm):
        parts.append("suffix")
    return "+".join(parts) if parts else "root"


def _flush_morph_batch(conn, word_batch, morph_batch):
    """Flush batches to database."""
    if word_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO words (text, language, pos, definition, source) "
            "VALUES (?, ?, ?, ?, ?)",
            word_batch
        )
    if morph_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO morphology (word, morphemes, structure, source) "
            "VALUES (?, ?, ?, ?)",
            morph_batch
        )


if __name__ == "__main__":
    print("=" * 60)
    print("📝 Importing MorphoLex-en")
    print("=" * 60)
    success = import_morphology()
    if success:
        print("\n✅ Morphology import complete!")
    else:
        print("\n❌ Morphology import failed!")
        sys.exit(1)
