"""
Convert all Simplified Chinese text in exam_words.json to Traditional Chinese.
Uses OpenCC (s2t: Simplified → Traditional).
"""
import json
import os
from opencc import OpenCC

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM_WORDS_PATH = os.path.join(PROJECT_ROOT, "database", "exam_words.json")

cc = OpenCC("s2t")

def convert_value(val):
    """Recursively convert strings in any JSON structure."""
    if isinstance(val, str):
        return cc.convert(val)
    elif isinstance(val, list):
        return [convert_value(v) for v in val]
    elif isinstance(val, dict):
        return {k: convert_value(v) for k, v in val.items()}
    return val

def main():
    print(f"Loading: {EXAM_WORDS_PATH}")
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    vocab = data["words"]
    converted = 0

    for word, entry in vocab.items():
        # Convert definitions
        if entry.get("definitions"):
            entry["definitions"] = [cc.convert(d) for d in entry["definitions"]]
            converted += 1

    print(f"Converted definitions for {converted} words")

    # Write back
    with open(EXAM_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved: {EXAM_WORDS_PATH}")

    # Show samples
    samples = ["abandon", "want", "achieve", "happy", "chocolate", "scrutiny"]
    for w in samples:
        if w in vocab and vocab[w]["definitions"]:
            defs = vocab[w]["definitions"]
            print(f"  {w}: {defs[:2]}")

if __name__ == "__main__":
    main()

