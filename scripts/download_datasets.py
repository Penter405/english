#!/usr/bin/env python3
"""
Download external linguistic datasets for the English Root Explorer.

Datasets:
  1. Etymology DB     — Wiktionary-derived etymology (Parquet from GitHub releases)
  2. MorphoLex-en     — English morphological decompositions (Excel from GitHub)
  3. WordNet          — English lexical database (via NLTK)
  4. wordfreq         — Word frequency data (pip package, no download needed)

Usage:
    python scripts/download_datasets.py
    python scripts/download_datasets.py --only etymology
    python scripts/download_datasets.py --only morpholex
    python scripts/download_datasets.py --only wordnet
"""

import os
import sys
import argparse
import urllib.request
import gzip
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

# Size limit from spec Section 3 (500 MB compressed)
MAX_SIZE_BYTES = 500 * 1024 * 1024


def sizeof_fmt(num):
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def download_file(url, dest_path, description=""):
    """Download a file with progress reporting. Returns True on success."""
    if os.path.exists(dest_path):
        size = os.path.getsize(dest_path)
        print(f"  ✓ Already exists: {os.path.basename(dest_path)} ({sizeof_fmt(size)})")
        return True

    print(f"  ⬇ Downloading {description or os.path.basename(dest_path)}...")
    print(f"    URL: {url}")

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    try:
        # Check size first with HEAD request
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "English-Root-Explorer/1.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_SIZE_BYTES:
                print(f"  ⚠ SKIPPED: {description} is {sizeof_fmt(int(content_length))}")
                print(f"    Exceeds 500 MB limit (spec Section 3).")
                print(f"    Dataset: {description}")
                print(f"    Size: {sizeof_fmt(int(content_length))}")
                return False
            if content_length:
                print(f"    Size: {sizeof_fmt(int(content_length))}")
    except Exception:
        # HEAD may not be supported, continue with download
        pass

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "English-Root-Explorer/1.0")
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(dest_path, "wb") as f:
                shutil.copyfileobj(resp, f)
        size = os.path.getsize(dest_path)
        print(f"  ✓ Downloaded: {os.path.basename(dest_path)} ({sizeof_fmt(size)})")
        return True
    except Exception as e:
        print(f"  ✗ Failed to download: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def download_etymology_db():
    """Download Etymology DB from GitHub releases (gzipped CSV)."""
    print("\n" + "=" * 60)
    print("📚 Etymology DB (droher/etymology-db)")
    print("=" * 60)
    print("  Source: https://github.com/droher/etymology-db")
    print("  Contains ~3.8M entries, 1.8M terms, 2900 languages")

    dest_dir = os.path.join(RAW_DIR, "etymology-db")
    os.makedirs(dest_dir, exist_ok=True)

    # Download the gzipped CSV from the latest release
    url = "https://github.com/droher/etymology-db/releases/download/2023-12/etymology.csv.gz"
    gz_path = os.path.join(dest_dir, "etymology.csv.gz")
    csv_path = os.path.join(dest_dir, "etymology.csv")

    if os.path.exists(csv_path):
        size = os.path.getsize(csv_path)
        print(f"  ✓ Already exists: etymology_db.csv ({sizeof_fmt(size)})")
        return True

    if download_file(url, gz_path, "Etymology DB (gzipped CSV)"):
        # Decompress
        print("  📦 Decompressing...")
        try:
            with gzip.open(gz_path, "rb") as f_in:
                with open(csv_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            size = os.path.getsize(csv_path)
            print(f"  ✓ Decompressed: etymology_db.csv ({sizeof_fmt(size)})")
            # Keep the gz for space efficiency
            return True
        except Exception as e:
            print(f"  ✗ Decompression failed: {e}")
            return False
    return False


def download_morpholex():
    """Download MorphoLex-en Excel file from GitHub."""
    print("\n" + "=" * 60)
    print("📝 MorphoLex-en (hugomailhot/MorphoLex-en)")
    print("=" * 60)
    print("  Source: https://github.com/hugomailhot/MorphoLex-en")
    print("  Contains English morphological decompositions")

    dest_dir = os.path.join(RAW_DIR, "morpholex")
    os.makedirs(dest_dir, exist_ok=True)

    url = "https://github.com/hugomailhot/MorphoLex-en/raw/master/MorphoLEX_en.xlsx"
    dest = os.path.join(dest_dir, "MorphoLEX_en.xlsx")

    return download_file(url, dest, "MorphoLEX_en.xlsx")


def download_wordnet():
    """Download WordNet data via NLTK."""
    print("\n" + "=" * 60)
    print("📖 WordNet (Princeton)")
    print("=" * 60)
    print("  Source: https://wordnet.princeton.edu/")
    print("  English lexical database with definitions and relationships")

    dest_dir = os.path.join(RAW_DIR, "wordnet")
    os.makedirs(dest_dir, exist_ok=True)

    try:
        import nltk
        # Set download directory to our raw data folder
        nltk.data.path.insert(0, dest_dir)
        print("  ⬇ Downloading WordNet via NLTK...")
        nltk.download("wordnet", download_dir=dest_dir, quiet=True)
        nltk.download("omw-1.4", download_dir=dest_dir, quiet=True)
        print("  ✓ WordNet downloaded successfully")
        return True
    except ImportError:
        print("  ✗ NLTK not installed. Run: pip install nltk")
        return False
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def check_wordfreq():
    """Verify wordfreq is installed (no download needed)."""
    print("\n" + "=" * 60)
    print("📊 wordfreq")
    print("=" * 60)
    print("  Source: https://github.com/rspeer/wordfreq")
    print("  Word frequency data (installed as pip package)")

    try:
        from wordfreq import word_frequency
        freq = word_frequency("hello", "en")
        print(f"  ✓ wordfreq is installed and working (test: 'hello' freq={freq:.6f})")
        return True
    except ImportError:
        print("  ✗ wordfreq not installed. Run: pip install wordfreq")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download datasets for English Root Explorer")
    parser.add_argument("--only", choices=["etymology", "morpholex", "wordnet", "wordfreq"],
                        help="Download only a specific dataset")
    args = parser.parse_args()

    print("╔════════════════════════════════════════════════════╗")
    print("║   English Root Explorer — Dataset Downloader      ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"\nRaw data directory: {RAW_DIR}")
    print(f"Max dataset size: {sizeof_fmt(MAX_SIZE_BYTES)}")

    results = {}

    if args.only is None or args.only == "etymology":
        results["Etymology DB"] = download_etymology_db()

    if args.only is None or args.only == "morpholex":
        results["MorphoLex-en"] = download_morpholex()

    if args.only is None or args.only == "wordnet":
        results["WordNet"] = download_wordnet()

    if args.only is None or args.only == "wordfreq":
        results["wordfreq"] = check_wordfreq()

    # Summary
    print("\n" + "=" * 60)
    print("📋 Download Summary")
    print("=" * 60)
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    failed = [n for n, s in results.items() if not s]
    if failed:
        print(f"\n  ⚠ {len(failed)} dataset(s) failed. Re-run to retry.")
        return 1
    else:
        print("\n  ✅ All datasets ready!")
        print("\n  Next step: Run the import scripts to build the database:")
        print("    python scripts/import_all.py")
        return 0


if __name__ == "__main__":
    sys.exit(main())
