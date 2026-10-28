#!/usr/bin/env python3
"""
auto_fetch_images.py — Automated High-Quality Word Photo Fetcher

Fetches educational, open-license photos for vocabulary words from the
Wikipedia / Wikimedia API, resizes and optimizes them with Pillow, and
saves them to docs/data/images/{word}.png.

Usage:
    py scripts/auto_fetch_images.py --top 30        # Fetch images for top 30 missing words
    py scripts/auto_fetch_images.py --words orchid supercomputer rainforest scam
    py scripts/auto_fetch_images.py --all           # Fetch images for all missing words
"""

import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_DATA_PATH = os.path.join(BASE_DIR, "docs", "data", "vocab_data.json")
IMAGES_DIR = os.path.join(BASE_DIR, "docs", "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

USER_AGENT = "EnglishVocabularyExplorer/2.0 (education project; github.com/penter405/english)"

# Known title aliases for Wikipedia search
TITLE_ALIASES = {
    "backpacker": "Backpacking (travel)",
    "backpacking": "Backpacking (travel)",
    "scam": "Confidence trick",
    "blogger": "Blog",
    "trainer": "Coach (sport)"
}

def fetch_image_url(word):
    """Query Wikipedia REST summary API for a thumbnail image."""
    candidates = [word.capitalize()]
    if word.lower() in TITLE_ALIASES:
        candidates.insert(0, TITLE_ALIASES[word.lower()])
    candidates.append(word.lower())

    # Fallback to base form if noun ends with -er/-or
    if word.endswith("er") and len(word) > 4:
        candidates.append(word[:-2].capitalize())
        candidates.append((word[:-2] + "e").capitalize())
    elif word.endswith("or") and len(word) > 4:
        candidates.append(word[:-2].capitalize())

    for cand in candidates:
        query = urllib.parse.quote(cand.replace(" ", "_"), safe="()")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=8) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    thumb = data.get("thumbnail")
                    if thumb and thumb.get("source"):
                        return thumb["source"]
        except Exception:
            continue
    
    return None

def download_and_save_image(img_url, dest_path, max_dim=480):
    """Download image, resize maintaining aspect ratio, and save as optimized PNG."""
    req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as res:
        img_bytes = res.read()
    
    img = Image.open(io.BytesIO(img_bytes))
    
    # Convert RGBA / P to RGB if needed
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        # Keep transparency or convert to RGB on dark background
        bg = Image.new("RGBA", img.size, (15, 23, 42, 255))
        bg.paste(img, (0, 0), img.convert("RGBA"))
        img = bg.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # Resize preserving aspect ratio
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    img.save(dest_path, "PNG", optimize=True)

def main():
    parser = argparse.ArgumentParser(description="Auto fetch vocabulary photos")
    parser.add_argument("--words", nargs="+", help="Specific words to fetch")
    parser.add_argument("--top", type=int, default=0, help="Fetch top N missing words by exam frequency")
    parser.add_argument("--all", action="store_true", help="Fetch for all missing words")
    parser.add_argument("--force", action="store_true", help="Overwrite existing images")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between API requests in seconds")
    args = parser.parse_args()

    # Load vocab
    print(f"Loading vocabulary from {VOCAB_DATA_PATH}...")
    with open(VOCAB_DATA_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)

    # Determine targets
    STOP_WORDS = {"the", "to", "be", "of", "in", "and", "a", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me"}

    if args.words:
        targets = [w.lower().strip() for w in args.words]
    else:
        # Sort words by total appearances descending, prioritizing concrete content words (nouns/verbs/adj)
        def priority_score(item):
            w, v = item
            if w in STOP_WORDS or len(w) <= 2:
                return -999999
            cnt = v.get("cnt", 0)
            is_noun = 100 if any("n." in p for p in v.get("pos", [])) else 0
            return cnt + is_noun

        sorted_words = sorted(vocab.items(), key=priority_score, reverse=True)
        missing = [w for w, v in sorted_words if w not in STOP_WORDS and len(w) > 2 and (args.force or not os.path.exists(os.path.join(IMAGES_DIR, f"{w}.png")))]
        
        limit = args.top if args.top > 0 else (len(missing) if args.all else 30)
        targets = missing[:limit]

    print(f"Total target words to fetch: {len(targets)}")
    
    success = 0
    failed = 0
    
    for idx, w in enumerate(targets, start=1):
        dest_path = os.path.join(IMAGES_DIR, f"{w}.png")
        if os.path.exists(dest_path) and not args.force:
            print(f"[{idx}/{len(targets)}] {w:15} ➔ already exists (skipped)")
            continue

        print(f"[{idx}/{len(targets)}] {w:15} ➔ searching Wikipedia photo...", end="", flush=True)
        img_url = fetch_image_url(w)
        
        if img_url:
            try:
                download_and_save_image(img_url, dest_path)
                size_kb = os.path.getsize(dest_path) / 1024
                print(f" ✅ saved ({size_kb:.1f} KB)")
                success += 1
            except Exception as e:
                print(f" ❌ download failed ({e})")
                failed += 1
        else:
            print(" ⚠️ no photo found")
            failed += 1

        if idx < len(targets):
            time.sleep(args.delay)

    print("\nFetch Summary:")
    print(f"  Successfully fetched: {success}")
    print(f"  Failed / Not found:   {failed}")
    print(f"  Images directory:     {IMAGES_DIR}")

if __name__ == "__main__":
    main()
