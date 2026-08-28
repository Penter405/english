#!/usr/bin/env python3
"""
Master import script — runs all import steps in order.

Usage:
    python scripts/import_all.py              # Run everything
    python scripts/import_all.py --skip-download   # Skip dataset download
    python scripts/import_all.py --only seed       # Run only seed step
"""

import os
import sys
import time
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "api"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from models import DEFAULT_DB_PATH, create_database


def run_step(name, func, *args, **kwargs):
    """Run a step with timing and error handling."""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    start = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        status = "✅" if result else "⚠️"
        print(f"\n  {status} {name} — {elapsed:.1f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n  ❌ {name} FAILED — {elapsed:.1f}s")
        print(f"     Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Master import for English Root Explorer")
    parser.add_argument("--skip-download", action="store_true", help="Skip dataset download")
    parser.add_argument("--only", type=str, help="Run only a specific step",
                        choices=["download", "seed", "etymology", "morphology",
                                 "wordnet", "frequency", "basic_words"])
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="Database path")
    args = parser.parse_args()

    total_start = time.time()

    print("╔════════════════════════════════════════════════════════╗")
    print("║   English Root Explorer — Full Database Build         ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"\nDatabase: {args.db}")

    # Ensure database exists
    create_database(args.db)

    results = {}

    # Step 0: Download datasets
    if not args.skip_download and (args.only is None or args.only == "download"):
        from download_datasets import main as download_main
        # Temporarily override sys.argv
        old_argv = sys.argv
        sys.argv = ["download_datasets.py"]
        results["Download"] = run_step("📥 Download Datasets", download_main) == 0
        sys.argv = old_argv

    # Step 1: Seed from existing hand-crafted data
    if args.only is None or args.only == "seed":
        from seed_from_json import seed_from_json
        results["Seed"] = run_step("🌱 Seed from word_database.json",
                                    seed_from_json, args.db)

    # Step 2: Import WordNet (gives us word definitions)
    if args.only is None or args.only == "wordnet":
        from import_wordnet import import_wordnet
        results["WordNet"] = run_step("📖 Import WordNet", import_wordnet, args.db)

    # Step 3: Import word frequencies
    if args.only is None or args.only == "frequency":
        from import_frequency import import_frequency
        results["Frequency"] = run_step("📊 Import Frequencies", import_frequency, args.db)

    # Step 4: Import MorphoLex morphology
    if args.only is None or args.only == "morphology":
        from import_morphology import import_morphology
        results["Morphology"] = run_step("📝 Import MorphoLex", import_morphology, args.db)

    # Step 5: Import Etymology DB
    if args.only is None or args.only == "etymology":
        from import_etymology import import_etymology
        results["Etymology"] = run_step("📚 Import Etymology DB", import_etymology, args.db)

    # Step 6: Build Basic Words
    if args.only is None or args.only == "basic_words":
        from build_basic_words import build_basic_words
        results["Basic Words"] = run_step("🔤 Build Basic Words",
                                           build_basic_words, args.db)

    # Summary
    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"  📋 IMPORT SUMMARY — Total time: {total_elapsed:.1f}s")
    print(f"{'=' * 60}")
    for step, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {step}")

    # Database stats
    try:
        import sqlite3
        conn = sqlite3.connect(args.db)
        for table in ["words", "roots", "affixes", "morphology", "relationships", "friend_words"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  📊 {table}: {count:,} rows")
        basic = conn.execute("SELECT COUNT(*) FROM words WHERE is_basic = 1").fetchone()[0]
        print(f"  📊 basic_words: {basic:,}")
        conn.close()
    except Exception:
        pass

    failed = [n for n, s in results.items() if not s]
    if failed:
        print(f"\n  ⚠ {len(failed)} step(s) failed: {', '.join(failed)}")
        return 1
    else:
        print("\n  ✅ All steps completed successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
