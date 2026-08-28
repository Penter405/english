#!/usr/bin/env python3
"""
Import MorphoLex-en morphological decompositions into the SQLite database.

Reads MorphoLEX_en.xlsx and extracts:
  - Word entries with morphological segmentations
  - Prefix, root, suffix identification
  - Morpheme counts and structures
"""

import os
import sys
import json

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

    print("  📖 Reading MorphoLEX_en.xlsx...")
    try:
        df = pd.read_excel(xlsx_path, engine="openpyxl")
    except Exception as e:
        print(f"  ✗ Failed to read Excel file: {e}")
        return False

    print(f"  📊 Total entries: {len(df):,}")
    print(f"  📋 Columns: {list(df.columns)}")

    conn = create_database(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    morph_count = 0
    word_count = 0
    affix_set = set()

    morph_batch = []
    word_batch = []

    for _, row in df.iterrows():
        try:
            # MorphoLex columns typically include:
            # Word, MorphoLexSegm (segmentation), nMorph, etc.
            word = None
            segmentation = None

            # Try common column names
            for col in df.columns:
                col_lower = str(col).lower().strip()
                if col_lower in ("word", "item", "entry"):
                    word = str(row[col]).strip().lower()
                elif "segm" in col_lower or "morpho" in col_lower:
                    val = str(row[col]).strip()
                    if val and val != "nan":
                        segmentation = val

            if not word or word == "nan":
                continue

            # Add word
            word_batch.append((word, "en", "", "", "morpholex"))
            word_count += 1

            # Parse segmentation if available
            if segmentation:
                morphemes = _parse_segmentation(segmentation)
                if morphemes and len(morphemes) > 1:
                    structure = _classify_structure(morphemes)
                    morph_batch.append((
                        word,
                        json.dumps(morphemes),
                        structure,
                        "morpholex"
                    ))
                    morph_count += 1

                    # Extract affixes
                    for m in morphemes:
                        m_clean = m.strip("{}<>()").lower()
                        if m.startswith("{") or m.startswith("<"):
                            affix_set.add(("prefix", m_clean))
                        elif m.endswith("}") or m.endswith(">"):
                            affix_set.add(("suffix", m_clean))

        except Exception:
            continue

        # Flush every 5000 rows
        if len(morph_batch) >= 5000:
            _flush_morph_batch(conn, word_batch, morph_batch)
            word_batch.clear()
            morph_batch.clear()

    # Final flush
    _flush_morph_batch(conn, word_batch, morph_batch)

    # Import discovered affixes
    affix_count = 0
    for affix_type, affix_text in affix_set:
        if len(affix_text) >= 2:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO affixes (text, type, meaning, meaning_zh, source) "
                    "VALUES (?, ?, '', '', 'morpholex')",
                    (affix_text, affix_type)
                )
                affix_count += 1
            except Exception:
                pass

    conn.commit()

    print(f"  ✓ Imported {word_count:,} words")
    print(f"  ✓ Imported {morph_count:,} morphological decompositions")
    print(f"  ✓ Discovered {affix_count} affixes")
    conn.close()
    return True


def _parse_segmentation(seg: str) -> list:
    """Parse MorphoLex segmentation format into morpheme list.
    
    MorphoLex uses formats like:
      {un}{happi}<ness>  (prefix, root, suffix)
      {re}{act}<ion>
      happy              (no segmentation = single morpheme)
    """
    if not seg or seg == "nan":
        return []

    morphemes = []
    current = ""
    for ch in seg:
        if ch in "{}()<>":
            if current.strip():
                morphemes.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        morphemes.append(current.strip())

    # Filter out empty morphemes
    return [m for m in morphemes if m and m != "nan"]


def _classify_structure(morphemes: list) -> str:
    """Classify the morphological structure (e.g. 'prefix+root+suffix')."""
    if len(morphemes) == 1:
        return "root"
    elif len(morphemes) == 2:
        return "prefix+root" if len(morphemes[0]) <= 3 else "root+suffix"
    else:
        return "+".join(["morpheme"] * len(morphemes))


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
