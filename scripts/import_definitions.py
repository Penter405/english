"""
Import Chinese definitions from ECDICT (skywind3000/ECDICT) into exam_words.json.

ECDICT CSV columns:
  word, phonetic, definition, translation, pos, collins, oxford, tag, bnc, frq, exchange, detail, audio

The 'translation' column contains Chinese (Simplified) definitions.
We store them directly — for Traditional Chinese conversion, OpenCC can be used later.

Updates: database/exam_words.json (fills in 'definitions' field)
"""
import csv
import json
import os
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM_WORDS_PATH = os.path.join(PROJECT_ROOT, "database", "exam_words.json")
ECDICT_PATH = os.path.join(PROJECT_ROOT, "database", "ecdict.csv")


def load_ecdict(path, target_words):
    """Load Chinese definitions from ECDICT CSV for target words only.

    Returns: dict of {word: translation_string}
    """
    definitions = {}
    target_set = set(target_words)

    print(f"  Loading ECDICT from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        # Find column indices
        col_map = {name: idx for idx, name in enumerate(header)}
        word_col = col_map.get("word", 0)
        trans_col = col_map.get("translation", 3)

        count = 0
        matched = 0
        for row in reader:
            count += 1
            if len(row) <= max(word_col, trans_col):
                continue

            word = row[word_col].strip().lower()
            translation = row[trans_col].strip()

            if word in target_set and translation:
                definitions[word] = translation
                matched += 1

        print(f"  ECDICT rows: {count}")
        print(f"  Matched words: {matched}")

    return definitions


def main():
    if not os.path.exists(ECDICT_PATH):
        print(f"ERROR: ECDICT file not found: {ECDICT_PATH}")
        print("Download it from: https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv")
        return

    # Load exam words
    print(f"Loading vocabulary: {EXAM_WORDS_PATH}")
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    vocab = data["words"]
    print(f"Vocabulary size: {len(vocab)} words")

    # Load ECDICT definitions
    print("\n--- Loading ECDICT definitions ---")
    definitions = load_ecdict(ECDICT_PATH, vocab.keys())

    # Merge definitions
    print("\n--- Merging definitions ---")
    filled = 0
    for word, entry in vocab.items():
        if word in definitions:
            # Parse: ECDICT translation is like "n. 放弃;抛弃\nv. 放纵;沉溺"
            # Split by newline, each line is a definition
            trans = definitions[word]
            # Clean up: split by \n, filter empty
            def_lines = [line.strip() for line in trans.split("\\n") if line.strip()]
            if not def_lines:
                def_lines = [line.strip() for line in trans.split("\n") if line.strip()]
            entry["definitions"] = def_lines
            filled += 1

    print(f"  Words with definitions: {filled}")
    print(f"  Words without definitions: {len(vocab) - filled}")

    # Show samples (handle encoding for terminals that can't display Chinese)
    print("\n--- Sample definitions ---")
    for w in ["want", "achieve", "happy", "abandon", "chocolate", "scrutiny"]:
        if w in vocab and vocab[w]["definitions"]:
            try:
                print(f"  {w}: {vocab[w]['definitions'][:3]}")
            except UnicodeEncodeError:
                print(f"  {w}: [{len(vocab[w]['definitions'])} definition(s) loaded]")

    # Update metadata
    data["meta"]["updated"] = str(date.today())

    # Write updated JSON
    with open(EXAM_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {EXAM_WORDS_PATH}")


if __name__ == "__main__":
    main()
