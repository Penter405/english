"""
Phase 1: Extract vocabulary words and levels from the 高中英文參考詞彙表 PDF.

Strategy: Parse the ALPHABETICAL section (pages 65–116, 0-indexed 64–115)
where each entry is on one line as: word pos level_number
This is far more reliable than parsing the multi-column by-level section.

Produces: database/exam_words.json
"""
import pdfplumber
import re
import json
import os
from datetime import date
from collections import defaultdict

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PDF_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "高中英文參考詞彙表(111學年度起適用).pdf",
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "exam_words.json",
)

# Alphabetical section pages (0-indexed): 64..115
ALPHA_START_PAGE = 64
ALPHA_END_PAGE = 115

# POS abbreviations
POS_SET = {"n", "v", "adj", "adv", "prep", "conj", "pron", "art", "aux", "interj", "det", "abbr"}

# Regex: a word entry line looks like:
#   word[/word] [POS_string] level_number
# e.g.:  "abandon v. 4"
#        "a/an art. 1"
#        "achieve(ment) v./(n.) 4"  (but level number might be on next line)
#        "afterward/afterwards adv. 3"
# POS string is things like: "n./v.", "adj.", "prep./conj./adv."
# The level number (1-6) is at the END of the entry
WORD_ENTRY = re.compile(
    r"""
    ^                               # start of token group
    ([a-zA-Z][a-zA-Z'/\-]*          # word (may contain apostrophe, hyphen)
      (?:\([a-zA-Z]+\))?            # optional parenthetical suffix like (ment)
      (?:/[a-zA-Z][a-zA-Z']*        # optional /alternate
        (?:\([a-zA-Z]+\))?          # alternate may also have (suffix)
      )*
    )
    \s+                             # space
    ((?:[a-z]+\./?)+                # POS like "n./v." or "adj."
      (?:/\([a-z]+\.\))*            # optional /(n.) pattern
    )
    \s+                             # space
    ([1-6])                         # level number
    $                               # end
    """,
    re.VERBOSE,
)

# Simpler: split approach — find English word, then POS tokens, then level digit
def parse_entry(text):
    """Try to parse a word entry from text. Returns (words, pos_list, level) or None."""
    text = text.strip()
    if not text:
        return None

    # The level number should be the last character
    # But in multi-column layouts, multiple entries may be on one "line"
    # We handle this by parsing all entries from the line

    results = []

    # Strategy: use extract_words with position info instead
    # But since we're working with text lines from extract_text(), let's use regex

    # Split line into potential entries using a pattern:
    # Each entry ends with a digit 1-6
    # Pattern: word POS digit
    # Find all entries in the line
    # The tricky part: "accommodate v. 5 adaptation n. 6" is TWO entries on one line

    # Use a greedy approach: find patterns of (word)(POS)(digit)
    pos_pattern = r"(?:[a-z]+\./?(?:\([a-z]+\.\))?)+(?:/(?:\([a-z]+\.\))?[a-z]*\.?)?"
    entry_pattern = re.compile(
        r"([a-zA-Z][a-zA-Z'()\-/]*)"  # word group
        r"\s+"
        r"(" + pos_pattern + r")"       # POS group
        r"\s+"
        r"([1-6])(?:\s|$)"             # level digit
    )

    for m in entry_pattern.finditer(text):
        word_raw = m.group(1)
        pos_raw = m.group(2)
        level = int(m.group(3))

        # Parse word
        words = parse_word(word_raw)
        if not words:
            continue

        # Parse POS
        pos_list = parse_pos(pos_raw)

        for w in words:
            results.append((w, pos_list, level))

    return results if results else None


def parse_word(word_raw):
    """Parse a word entry like 'achieve(ment)', 'airplane/plane', 'a/an'."""
    text = word_raw.strip()
    if not text:
        return []

    results = []

    # Handle slash variants: 'airplane/plane', 'a/an'
    # But NOT inside parentheses
    # And handle patterns like 'achieve(ment)' or 'accomplish(ment)'
    # And 'argue(argument)' which is base(full_form)

    # Split by / at top level (not inside parens)
    parts = split_slash(text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Pattern: word(suffix)
        m = re.match(r"^([a-zA-Z]+)\(([a-zA-Z]+)\)$", part)
        if m:
            base = m.group(1).lower()
            suffix = m.group(2).lower()
            results.append(base)
            # If suffix looks like it completes the word (e.g., agree + ment = agreement)
            if not suffix.startswith(base[:2]):  # suffix is an addition, not the full word
                results.append(base + suffix)
            else:
                results.append(suffix)  # it's a full alternate form
            continue

        # Simple word
        if re.match(r"^[a-zA-Z]+$", part):
            results.append(part.lower())
            continue

        # Word with hyphen or apostrophe
        if re.match(r"^[a-zA-Z][a-zA-Z'\-]+$", part):
            results.append(part.lower())
            continue

    return results


def split_slash(text):
    """Split by / but not inside parentheses."""
    parts = []
    depth = 0
    current = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "/" and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def parse_pos(pos_raw):
    """Parse POS like 'n./v.' or 'adj.' into list ['n.', 'v.']."""
    parts = []
    for token in re.split(r"[/]", pos_raw):
        token = token.strip().strip("()")
        if token and token.rstrip(".") in POS_SET:
            if not token.endswith("."):
                token += "."
            parts.append(token)
    return parts


def extract_from_alphabetical(pdf):
    """Extract all word entries from the alphabetical section."""
    all_entries = {}  # word -> {level, pos}
    orphan_lines = []  # lines that didn't parse (for debugging)

    for page_idx in range(ALPHA_START_PAGE, min(ALPHA_END_PAGE + 1, len(pdf.pages))):
        page = pdf.pages[page_idx]
        text = page.extract_text()
        if not text:
            continue

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip header lines (Chinese characters or page identifiers)
            if not re.search(r"[a-zA-Z]", line):
                continue
            # Skip page numbers
            if re.match(r"^\d+$", line):
                continue

            results = parse_entry(line)
            if results:
                for word, pos_list, level in results:
                    if word in all_entries:
                        # Merge: keep lowest level, combine POS
                        existing = all_entries[word]
                        if level < existing["level"]:
                            existing["level"] = level
                        for p in pos_list:
                            if p not in existing["pos"]:
                                existing["pos"].append(p)
                    else:
                        all_entries[word] = {
                            "level": level,
                            "pos": list(pos_list),
                        }
            else:
                # Check if this line contains any English words we should capture
                if re.match(r"^[a-zA-Z]", line) and not any(kw in line for kw in ["Ƨ", "Ѧ", "ŧO"]):
                    orphan_lines.append((page_idx + 1, line))

    return all_entries, orphan_lines


def handle_orphan_lines(orphan_lines, all_entries):
    """Try to rescue words from orphan lines.

    Orphan lines are typically continuation lines like:
      'v. 6'   (POS + level for a word on the previous line)
      'adv. 3' (same)
    Or wrapped word entries like:
      'administer/administrate'   (word only, POS+level on next line)
    """
    rescued = 0

    # Known manual fixes for entries that span lines or have unusual formatting
    manual_fixes = {
        "ok": {"level": 1, "pos": ["adj.", "adv.", "interj."]},
        "okay": {"level": 1, "pos": ["adj.", "adv.", "interj."]},
        "salesperson": {"level": 2, "pos": ["n."]},
        "salesman": {"level": 2, "pos": ["n."]},
        "saleswoman": {"level": 2, "pos": ["n."]},
        "underneath": {"level": 6, "pos": ["prep.", "adv."]},
    }

    for word, info in manual_fixes.items():
        if word not in all_entries:
            all_entries[word] = info
            rescued += 1

    return rescued


def post_process(entries):
    """Clean up extraction artifacts."""
    removals = set()

    for word in entries:
        # Remove single-letter artifacts that aren't real words
        if len(word) == 1 and word not in ("a", "i"):
            removals.add(word)

        # Remove entries that are clearly not English words
        if not re.match(r"^[a-z][a-z\'\-]*$", word):
            removals.add(word)

    for word in removals:
        del entries[word]
        print(f"  Removed artifact: {repr(word)}")

    # Fix: 'achieve' and 'achievement' should have distinct POS
    # achieve = v., achievement = n.
    if "achieve" in entries:
        entries["achieve"]["pos"] = ["v."]
    if "achievement" in entries:
        entries["achievement"]["pos"] = ["n."]

    return entries


def build_exam_words_json(entries):
    """Build the final exam_words.json structure."""
    words_dict = {}
    for word in sorted(entries.keys()):
        info = entries[word]
        words_dict[word] = {
            "level": info["level"],
            "pos": info["pos"],
            "forms": [],
            "word_family": [],
            "appear_year": [],
            "appear_year_count": 0,
            "total_appear": 0,
            "sources": [],
            "situations": [],
            "definitions": [],
        }

    level_counts = {}
    for level in range(1, 7):
        count = sum(1 for w in words_dict.values() if w["level"] == level)
        level_counts[str(level)] = count

    result = {
        "meta": {
            "version": 1,
            "created": str(date.today()),
            "updated": str(date.today()),
            "exam_years": list(range(104, 116)),
            "word_count": len(words_dict),
            "level_source": "高中英文參考詞彙表(111學年度起適用)",
            "level_counts": level_counts,
        },
        "words": words_dict,
    }
    return result


def main():
    print(f"Opening PDF: {PDF_PATH}")
    pdf = pdfplumber.open(PDF_PATH)
    print(f"Total pages: {len(pdf.pages)}")

    print(f"\nExtracting from alphabetical section (pages {ALPHA_START_PAGE+1}–{ALPHA_END_PAGE+1})...")
    entries, orphan_lines = extract_from_alphabetical(pdf)
    pdf.close()

    print(f"Extracted {len(entries)} unique words")
    print(f"Orphan lines (unparsed): {len(orphan_lines)}")

    # Show orphan lines for debugging
    if orphan_lines:
        print("\n--- First 30 orphan lines ---")
        for page, line in orphan_lines[:30]:
            print(f"  Page {page}: {repr(line)}")

    # Handle orphans
    rescued = handle_orphan_lines(orphan_lines, entries)
    if rescued:
        print(f"Rescued {rescued} words from orphan lines")

    # Post-process: clean artifacts
    print("\n--- Post-processing ---")
    entries = post_process(entries)

    # Level distribution
    from collections import Counter
    level_dist = Counter(info["level"] for info in entries.values())
    print("\n--- Level distribution ---")
    for level in sorted(level_dist):
        print(f"  Level {level}: {level_dist[level]} words")
    print(f"  Total: {sum(level_dist.values())}")

    # Quality check
    print("\n--- Quality checks ---")
    no_pos = [w for w in entries if not entries[w]["pos"]]
    print(f"Words without POS: {len(no_pos)}")
    if no_pos:
        print(f"  Examples: {no_pos[:10]}")

    single_char = [w for w in entries if len(w) == 1]
    print(f"Single char words: {single_char}")

    # Check expected words
    print("\n--- Sample entries ---")
    samples = ["a", "go", "happy", "want", "abandon", "achieve", "achievement",
               "atmosphere", "ethnic", "manipulate", "scrutiny", "achieve"]
    for w in samples:
        if w in entries:
            e = entries[w]
            print(f"  {w}: level={e['level']}, pos={e['pos']}")
        else:
            print(f"  {w}: NOT FOUND")

    # Build and write JSON
    result = build_exam_words_json(entries)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {result['meta']['word_count']} words to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
