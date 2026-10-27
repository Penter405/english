#!/usr/bin/env python3
"""
upload_word_image.py — 為單字上傳並處理關聯圖片

使用方式：
  1. 互動模式（直接執行）：
     py scripts/upload_word_image.py

  2. 參數模式（單一單字）：
     py scripts/upload_word_image.py -w apple -i C:/path/to/apple.jpg

  3. 批量模式（資料夾內所有以單字命名的圖片）：
     py scripts/upload_word_image.py --batch C:/path/to/images_folder

  4. 查詢現有圖片清單：
     py scripts/upload_word_image.py -l
"""

import argparse
import json
import os
import sys
from pathlib import Path
from PIL import Image

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = BASE_DIR / "docs" / "data" / "images"
EXAM_WORDS_PATH = BASE_DIR / "database" / "exam_words.json"
MAX_SIZE = (800, 800)


def load_known_words():
    """載入資料庫內所有已知單字（用於檢查與防呆提示）"""
    if not EXAM_WORDS_PATH.exists():
        return set()
    try:
        with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(w.lower() for w in data.get("words", {}).keys())
    except Exception:
        return set()


def process_image(src_path: Path, dest_path: Path):
    """讀取、縮放並另存為 PNG"""
    with Image.open(src_path) as img:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest_path, "PNG", optimize=True)


def upload_single_word(word: str, image_path_str: str, known_words: set):
    """處理單一單字的圖片上傳"""
    word = word.strip().lower()
    if not word:
        print("[Error] Word cannot be empty!")
        return False

    src_path = Path(image_path_str).resolve()
    if not src_path.exists() or not src_path.is_file():
        print(f"[Error] Image file not found: {src_path}")
        return False

    if known_words and word not in known_words:
        print(f"[Notice] '{word}' is not in exam_words.json, saving anyway.")

    target_path = IMAGE_DIR / f"{word}.png"

    try:
        process_image(src_path, target_path)
        rel_path = target_path.relative_to(BASE_DIR)
        print(f"[Success] Image for '{word}' saved to: {rel_path}")
        return True
    except Exception as e:
        print(f"[Error] Failed to process image ({src_path.name}): {e}")
        return False


def upload_batch(folder_path_str: str, known_words: set):
    """批量上傳資料夾內的所有圖片"""
    folder = Path(folder_path_str).resolve()
    if not folder.exists() or not folder.is_dir():
        print(f"[Error] Folder not found: {folder}")
        return

    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]

    if not files:
        print(f"[Notice] No valid image files in: {folder}")
        return

    print(f"Found {len(files)} image(s), processing...")
    success_count = 0
    for f in sorted(files):
        word = f.stem.strip().lower()
        if upload_single_word(word, str(f), known_words):
            success_count += 1

    print(f"\n[Done] Finished. {success_count}/{len(files)} image(s) processed.")


def interactive_mode(known_words: set):
    """互動式上傳模式"""
    print("=" * 55)
    print("      單字圖片上傳小工具 (Word Image Uploader)")
    print("=" * 55)
    print("Tips: Enter 'q' to quit at any time.\n")

    while True:
        try:
            word = input("Enter word (e.g. apple): ").strip()
            if word.lower() in ("q", "quit", "exit"):
                break
            if not word:
                continue

            img_path = input("Enter image path (or drag file here): ").strip().strip('"').strip("'")
            if img_path.lower() in ("q", "quit", "exit"):
                break
            if not img_path:
                continue

            upload_single_word(word, img_path, known_words)
            print("-" * 55)
        except (KeyboardInterrupt, EOFError):
            print("\nExited.")
            break


def main():
    parser = argparse.ArgumentParser(description="Upload and process images for vocabulary words")
    parser.add_argument("-w", "--word", help="Target English word (e.g. 'apple')")
    parser.add_argument("-i", "--image", help="Path to image file")
    parser.add_argument("-b", "--batch", help="Path to folder containing word-named images")
    parser.add_argument("-l", "--list", action="store_true", help="List all words currently with images")

    args = parser.parse_args()

    known_words = load_known_words()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    if args.list:
        images = sorted(IMAGE_DIR.glob("*.png"))
        print(f"Words with images ({len(images)} total):")
        for img in images:
            print(f"  - {img.stem}")
        return

    if args.batch:
        upload_batch(args.batch, known_words)
    elif args.word and args.image:
        upload_single_word(args.word, args.image, known_words)
    elif args.word or args.image:
        print("[Error] Please provide both -w/--word and -i/--image, or run without args for interactive mode.")
    else:
        interactive_mode(known_words)


if __name__ == "__main__":
    main()

