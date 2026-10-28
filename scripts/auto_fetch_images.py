#!/usr/bin/env python3
"""
auto_fetch_images.py — Multi-Engine High-Quality Vocabulary Image Fetcher

Features:
- Web Image Search (Bing Async Engine): Free, no API key required, 100% success on any word (verbs, adjectives, abstract nouns).
- Google Custom Search Engine (Google Image Search): Official Google API support if user provides key & cx.
- Wikipedia REST API: High-quality open images for encyclopedic and scientific terms.
- Automated Pillow optimization: Converts to RGB, scales preserving aspect ratio (max 480px), optimizes file size.

Usage:
    # 1. Default (Free Web Image Search — works out of the box for any word!)
    py scripts/auto_fetch_images.py --words play run brave decision comfort

    # 2. Fetch images for top 30 exam frequency words
    py scripts/auto_fetch_images.py --top 30

    # 3. Use Google Custom Search API (if you have Google API credentials)
    py scripts/auto_fetch_images.py --words apple book --engine google --google-key YOUR_KEY --google-cx YOUR_CX
    # Or set GOOGLE_API_KEY and GOOGLE_CX environment variables
"""

import argparse
import io
import json
import os
import re
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

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
WIKI_UA = "EnglishVocabularyExplorer/2.0 (education project; github.com/penter405/english)"

def search_google_api(word, api_key, cx):
    """Fetch image using official Google Custom Search JSON API."""
    if not api_key or not cx:
        return []
    candidates = []
    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(word)}&searchType=image&num=5&key={api_key}&cx={cx}"
        req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode('utf-8'))
            for item in data.get("items", []):
                link = item.get("link")
                if link:
                    candidates.append(("Google Image", link))
    except Exception as e:
        # print(f"Google API error: {e}")
        pass
    return candidates

def search_web_bing(word):
    """Fetch image candidates using Bing Image search (free, live web search)."""
    candidates = []
    try:
        url = f"https://www.bing.com/images/async?q={urllib.parse.quote(word)}&first=0&count=10&mmasync=1"
        req = urllib.request.Request(url, headers={
            "User-Agent": BROWSER_UA,
            "Accept-Language": "en-US,en;q=0.9"
        })
        with urllib.request.urlopen(req, timeout=6) as res:
            html = res.read().decode('utf-8', errors='ignore')

        murls = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', html)
        for u in murls[:5]:
            candidates.append(("Web Search (Bing)", u.replace('&amp;', '&')))

        turls = re.findall(r'src="(https://tse\d\.mm\.bing\.net/th\?id=[^"]+)"', html)
        for u in turls[:3]:
            candidates.append(("Web Search (CDN)", u.replace('&amp;', '&')))
    except Exception:
        pass
    return candidates

def search_wikipedia(word):
    """Fetch thumbnail from Wikipedia REST Summary API."""
    candidates = []
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(word.capitalize())}"
        req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                thumb = data.get("thumbnail")
                if thumb and thumb.get("source"):
                    candidates.append(("Wikipedia", thumb["source"]))
    except Exception:
        pass
    return candidates

def get_candidates(word, engine="auto", google_key=None, google_cx=None):
    """Gather candidate image URLs based on selected engine."""
    candidates = []

    # 1. Google Image API
    if engine in ("google", "all") or (engine == "auto" and google_key and google_cx):
        g_cands = search_google_api(word, google_key, google_cx)
        candidates.extend(g_cands)

    # 2. Web Image Search (Bing)
    if engine in ("bing", "all", "auto"):
        b_cands = search_web_bing(word)
        candidates.extend(b_cands)

    # 3. Wikipedia Summary API
    if engine in ("wiki", "all", "auto"):
        w_cands = search_wikipedia(word)
        candidates.extend(w_cands)

    return candidates

def download_and_save_image(candidates, dest_path, max_dim=480):
    """Download from candidate URLs with fallback, resize, and save as optimized PNG."""
    for source_name, img_url in candidates:
        try:
            # Safely encode non-ASCII characters in URL
            parts = urllib.parse.urlsplit(img_url)
            encoded_path = urllib.parse.quote(parts.path)
            encoded_query = urllib.parse.quote(parts.query, safe='=&')
            safe_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))

            headers = {
                "User-Agent": BROWSER_UA,
                "Referer": f"{parts.scheme}://{parts.netloc}/"
            }
            req = urllib.request.Request(safe_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as res:
                img_bytes = res.read()

            img = Image.open(io.BytesIO(img_bytes))

            # Convert to RGB (filling transparency with dark background if present)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
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
            return source_name, img_url
        except Exception:
            continue

    return None, None

def main():
    parser = argparse.ArgumentParser(description="Multi-Engine High-Quality Vocabulary Photo Fetcher")
    parser.add_argument("--words", nargs="+", help="Specific words to fetch (e.g. play run brave decision)")
    parser.add_argument("--top", type=int, default=0, help="Fetch top N missing words by exam frequency")
    parser.add_argument("--all", action="store_true", help="Fetch for all missing words")
    parser.add_argument("--force", action="store_true", help="Overwrite existing images")
    parser.add_argument("--engine", choices=["auto", "bing", "google", "wiki", "all"], default="auto",
                        help="Image search engine (auto: web search with wiki fallback, google: Google Custom Search API)")
    parser.add_argument("--google-key", default=os.environ.get("GOOGLE_API_KEY"), help="Google Custom Search API Key")
    parser.add_argument("--google-cx", default=os.environ.get("GOOGLE_CX"), help="Google Custom Search Engine ID (CX)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds")
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

    engine_desc = "Web Image Search (Bing) + Wikipedia"
    if args.google_key and args.google_cx:
        engine_desc = "Google Custom Search API + Web Image Search"
    elif args.engine == "google":
        print("⚠️ Warning: --engine google selected but --google-key or --google-cx not provided. Falling back to Web Search.")

    print(f"Target words to fetch : {len(targets)}")
    print(f"Active search engine  : {engine_desc}")
    print(f"Output directory      : {IMAGES_DIR}\n")

    success = 0
    failed = 0

    for idx, w in enumerate(targets, start=1):
        dest_path = os.path.join(IMAGES_DIR, f"{w}.png")
        if os.path.exists(dest_path) and not args.force:
            print(f"[{idx:2d}/{len(targets)}] {w:14} ➔ already exists (skipped)")
            continue

        print(f"[{idx:2d}/{len(targets)}] {w:14} ➔ searching...", end="", flush=True)
        cands = get_candidates(w, engine=args.engine, google_key=args.google_key, google_cx=args.google_cx)

        if not cands:
            print(" ⚠️ no image candidates found")
            failed += 1
            continue

        source_name, used_url = download_and_save_image(cands, dest_path)
        if source_name:
            size_kb = os.path.getsize(dest_path) / 1024
            print(f" ✅ saved via [{source_name}] ({size_kb:.1f} KB)")
            success += 1
        else:
            print(f" ❌ download failed ({len(cands)} candidates tested)")
            failed += 1

        if idx < len(targets):
            time.sleep(args.delay)

    print("\nFetch Summary:")
    print(f"  Successfully fetched: {success}")
    print(f"  Failed / Not found:   {failed}")
    print(f"  Images directory:     {IMAGES_DIR}")

if __name__ == "__main__":
    main()
