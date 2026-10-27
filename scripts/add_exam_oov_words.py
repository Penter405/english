#!/usr/bin/env python3
"""
add_exam_oov_words.py

1. Reads all 12 years of exam PDFs (104-115).
2. Lemmatizes all tokens. First checks if token or lemma matches an existing word
   in database/exam_words.json. If so, updates appearance counts and year lists.
3. For tokens/lemmas not in exam_words.json:
   - Filters out contraction artifacts (ll, ve, don, didn...), section markers,
     and proper person names.
   - Matches against ECDICT to verify validity and extract POS, definitions (EN + ZH).
   - Assigns a sensible Level (1-6) based on junior high / Collins / Oxford / ECDICT tags.
   - Converts Chinese definitions to Traditional Chinese via OpenCC.
4. Adds these new exam-proven words into database/exam_words.json.
5. Re-runs rebuild of docs/data/vocab_data.json and docs/data/graph.json.
"""

import os
import re
import csv
import json
import pdfplumber
from collections import Counter, defaultdict
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from opencc import OpenCC

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
EXAM_WORDS_PATH = os.path.join(DATABASE_DIR, "exam_words.json")
ECDICT_PATH = os.path.join(DATABASE_DIR, "ecdict.csv")
EXAM_YEARS = list(range(104, 116))

_lemmatizer = WordNetLemmatizer()
cc = OpenCC("s2t")

IRREGULAR_FORMS = {
    "went": "go", "gone": "go", "goes": "go",
    "was": "be", "were": "be", "been": "be", "am": "be", "is": "be", "are": "be",
    "had": "have", "has": "have", "having": "have",
    "did": "do", "does": "do", "done": "do",
    "said": "say", "says": "say",
    "made": "make", "makes": "make",
    "took": "take", "taken": "take", "takes": "take",
    "came": "come", "comes": "come", "coming": "come",
    "saw": "see", "seen": "see", "sees": "see",
    "knew": "know", "known": "know", "knows": "know",
    "got": "get", "gotten": "get", "gets": "get",
    "gave": "give", "given": "give", "gives": "give",
    "found": "find", "finds": "find",
    "thought": "think", "thinks": "think",
    "told": "tell", "tells": "tell",
    "felt": "feel", "feels": "feel",
    "left": "leave", "leaves": "leave",
    "kept": "keep", "keeps": "keep",
    "let": "let", "lets": "let",
    "began": "begin", "begun": "begin", "begins": "begin",
    "ran": "run", "runs": "run", "running": "run",
    "wrote": "write", "written": "write", "writes": "write",
    "spoke": "speak", "spoken": "speak", "speaks": "speak",
    "broke": "break", "broken": "break", "breaks": "break",
    "drove": "drive", "driven": "drive", "drives": "drive",
    "chose": "choose", "chosen": "choose", "chooses": "choose",
    "fell": "fall", "fallen": "fall", "falls": "fall",
    "grew": "grow", "grown": "grow", "grows": "grow",
    "threw": "throw", "thrown": "throw", "throws": "throw",
    "drew": "draw", "drawn": "draw", "draws": "draw",
    "flew": "fly", "flown": "fly", "flies": "fly",
    "wore": "wear", "worn": "wear", "wears": "wear",
    "ate": "eat", "eaten": "eat", "eats": "eat",
    "drank": "drink", "drunk": "drink", "drinks": "drink",
    "sang": "sing", "sung": "sing", "sings": "sing",
    "swam": "swim", "swum": "swim", "swims": "swim",
    "sat": "sit", "sits": "sit",
    "stood": "stand", "stands": "stand",
    "lost": "lose", "loses": "lose",
    "paid": "pay", "pays": "pay",
    "met": "meet", "meets": "meet",
    "brought": "bring", "brings": "bring",
    "bought": "buy", "buys": "buy",
    "caught": "catch", "catches": "catch",
    "taught": "teach", "teaches": "teach",
    "built": "build", "builds": "build",
    "sent": "send", "sends": "send",
    "spent": "spend", "spends": "spend",
    "won": "win", "wins": "win",
    "held": "hold", "holds": "hold",
    "led": "lead", "leads": "lead",
    "read": "read", "reads": "read",
    "slept": "sleep", "sleeps": "sleep",
    "woke": "wake", "woken": "wake", "wakes": "wake",
    "rose": "rise", "risen": "rise", "rises": "rise",
    "rode": "ride", "ridden": "ride", "rides": "ride",
    "shook": "shake", "shaken": "shake", "shakes": "shake",
    "bit": "bite", "bitten": "bite", "bites": "bite",
    "hid": "hide", "hidden": "hide", "hides": "hide",
    "froze": "freeze", "frozen": "freeze",
    "stole": "steal", "stolen": "steal", "steals": "steal",
    "hung": "hang", "hangs": "hang",
    "lay": "lie", "lain": "lie", "lying": "lie",
    "laid": "lay",
    "set": "set", "sets": "set",
    "cut": "cut", "cuts": "cut",
    "put": "put", "puts": "put",
    "shut": "shut", "shuts": "shut",
    "hit": "hit", "hits": "hit",
    "spread": "spread", "spreads": "spread",
    "hurt": "hurt", "hurts": "hurt",
    "cost": "cost", "costs": "cost",
    "quit": "quit", "quits": "quit",
    "children": "child", "men": "man", "women": "woman",
    "people": "person", "teeth": "tooth", "feet": "foot",
    "mice": "mouse", "geese": "goose", "oxen": "ox",
    "lives": "life", "knives": "knife", "wives": "wife",
    "leaves": "leaf", "halves": "half", "shelves": "shelf",
    "thieves": "thief", "wolves": "wolf",
    "better": "good", "best": "good",
    "worse": "bad", "worst": "bad",
    "more": "much", "most": "much",
    "less": "little", "least": "little",
    "further": "far", "furthest": "far",
    "farther": "far", "farthest": "far",
    "older": "old", "oldest": "old",
    "elder": "old", "eldest": "old",
}

# Tokens to ignore: contractions, roman numerals, question markers, dialog names
STOP_WORDS = {
    "ll", "ve", "re", "don", "didn", "doesn", "won", "haven", "hasn", "hadn",
    "wasn", "weren", "aren", "isn", "couldn", "shouldn", "wouldn", "t", "s", "d", "m", "nt",
    "you", "your", "they", "their", "them", "she", "her", "he", "his", "him", "it", "its", "we", "our", "us", "my", "me",
    "ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii", "q1", "q2", "q3", "q4", "rc",
    "mr", "mrs", "ms", "dr", "no", "vs", "tv", "pm", "am", "ad", "bc", "etc", "ok", "app"
}

PERSON_NAMES = {
    "sam", "mary", "peter", "john", "nancy", "jack", "ken", "kelly", "dave", "miley", "betty", "jane", "ann", "linda",
    "huang", "chen", "chi", "fung", "tai", "lee", "wang", "lin", "wu", "liu", "chang", "yang", "tsai", "chou", "kuo",
    "bob", "tom", "alice", "mike", "lisa", "david", "paul", "mark", "sarah", "emma", "ben", "chris", "alex", "amy",
    "kevin", "eric", "jason", "brian", "lucy", "helen", "grace", "tony", "james", "robert", "william", "george", "charles",
    "adam", "nina", "maria", "jimmy", "smith", "ting", "triton", "samaritan", "andy", "judy", "ted", "lucas", "ella"
}

def get_candidates(token):
    token = token.lower().strip()
    if token in IRREGULAR_FORMS:
        return [IRREGULAR_FORMS[token]]
    res = []
    for pos in [wordnet.VERB, wordnet.NOUN, wordnet.ADJ, wordnet.ADV]:
        res.append(_lemmatizer.lemmatize(token, pos))
    # Deduplicate while preserving order
    seen = set()
    out = []
    for r in res:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out

def extract_pdf_tokens(pdf_path):
    if not os.path.exists(pdf_path):
        return []
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return [t.lower() for t in re.findall(r"\b[a-zA-Z]{2,}\b", text)]

def parse_ecdict_english(raw_def):
    if not raw_def:
        return []
    parts = raw_def.split('\\n')
    defs = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = re.sub(r'^s\.\s', 'adj. ', part)
        part = re.sub(r'^r\.\s', 'adv. ', part)
        defs.append(part)
    return defs

def parse_ecdict_chinese(raw_trans):
    if not raw_trans:
        return []
    parts = [p.strip() for p in raw_trans.split('\\n') if p.strip()]
    if not parts:
        parts = [p.strip() for p in raw_trans.split('\n') if p.strip()]
    return [cc.convert(p) for p in parts]

def determine_level(word, row):
    tag = row.get('tag', '')
    collins = int(row.get('collins')) if row.get('collins') and row.get('collins').isdigit() else 0
    oxford = int(row.get('oxford')) if row.get('oxford') and row.get('oxford').isdigit() else 0

    junior_high_set = {
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'dad', 'mom', 'grandma', 'grandpa', 'father', 'mother',
        'friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday',
        'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
        'summer', 'spring', 'autumn', 'winter', 'birthday', 'sunlight'
    }
    if word in junior_high_set or 'zk' in tag:
        return 1
    if collins >= 4 or oxford == 1:
        return 2
    if 'gk' in tag or collins == 3:
        return 3
    if 'cet4' in tag or collins == 2:
        return 4
    if 'cet6' in tag or collins == 1:
        return 5
    return 4  # Default to level 4 (accessible high school reading level)

def main():
    print("Loading database/exam_words.json...")
    with open(EXAM_WORDS_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)
    words = db["words"]
    existing_vocab = set(words.keys())
    print(f"Existing vocab count: {len(existing_vocab)}")

    # Load ECDICT index
    print("Loading ECDICT database...")
    ecdict = {}
    with open(ECDICT_PATH, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            w = row['word'].strip().lower()
            if w not in ecdict:
                ecdict[w] = row
    print(f"ECDICT loaded ({len(ecdict)} entries).")

    # Tracking appearances for all words (existing + new)
    exam_appearances = defaultdict(lambda: defaultdict(int)) # word -> year -> count

    # Process all 12 years of exams
    oov_candidates = Counter()
    for year in EXAM_YEARS:
        p = os.path.join(DATABASE_DIR, f"{year}-4y-00-e.pdf")
        tokens = extract_pdf_tokens(p)
        print(f"Year {year}: {len(tokens)} tokens extracted.")

        for tok in tokens:
            # 1. Try direct match
            if tok in existing_vocab:
                exam_appearances[tok][year] += 1
                continue

            # 2. Try lemmatization to existing_vocab
            cands = get_candidates(tok)
            matched = False
            for c in cands:
                if c in existing_vocab:
                    exam_appearances[c][year] += 1
                    matched = True
                    break
            if matched:
                continue

            # 3. Not in existing_vocab -> candidate for new exam word
            # Choose canonical lemma or token
            canon = cands[0] if (cands and len(cands[0]) >= 3) else tok
            if canon in STOP_WORDS or canon in PERSON_NAMES or len(canon) <= 2:
                continue
            oov_candidates[canon] += 1
            exam_appearances[canon][year] += 1

    print(f"\nTotal potential OOV candidates: {len(oov_candidates)}")

    # Filter candidates by ECDICT presence & English validation
    valid_oov_words = {}
    for canon, total_cnt in oov_candidates.items():
        if canon in ecdict:
            row = ecdict[canon]
            zh_defs = parse_ecdict_chinese(row.get('translation', ''))
            en_defs = parse_ecdict_english(row.get('definition', ''))
            # Must have at least one definition
            if not zh_defs and not en_defs:
                continue

            # Check POS
            raw_pos = row.get('pos', '')
            pos_list = [f"{p.strip()}." for p in raw_pos.split('/') if p.strip()] if raw_pos else []

            level = determine_level(canon, row)

            years = sorted(list(exam_appearances[canon].keys()))
            sources = [{"year": y, "count": exam_appearances[canon][y]} for y in years]
            total_app = sum(s["count"] for s in sources)

            valid_oov_words[canon] = {
                "level": level,
                "pos": pos_list,
                "forms": [],
                "word_family": [],
                "appear_year": years,
                "appear_year_count": len(years),
                "total_appear": total_app,
                "sources": sources,
                "situations": [],
                "definitions": {
                    "zh": zh_defs,
                    "en": en_defs
                },
                "is_exam_oov": True
            }

    print(f"Validated high-quality OOV exam words to add: {len(valid_oov_words)}")

    # Update existing words appearance data from the new thorough scan
    updated_existing = 0
    for w in existing_vocab:
        entry = words[w]
        years = sorted(list(exam_appearances[w].keys()))
        if years:
            sources = [{"year": y, "count": exam_appearances[w][y]} for y in years]
            entry["appear_year"] = years
            entry["appear_year_count"] = len(years)
            entry["total_appear"] = sum(s["count"] for s in sources)
            entry["sources"] = sources
            updated_existing += 1

    print(f"Updated appearance counts for {updated_existing} existing words.")

    # Merge new OOV exam words into words dictionary
    for w, entry in valid_oov_words.items():
        words[w] = entry

    # Update metadata
    db["meta"]["word_count"] = len(words)
    db["meta"]["oov_exam_words_added"] = len(valid_oov_words)
    level_counts = Counter(entry.get("level", 0) for entry in words.values())
    db["meta"]["level_counts"] = {str(k): v for k, v in sorted(level_counts.items())}

    # Save updated database/exam_words.json
    print(f"Saving updated database: {EXAM_WORDS_PATH} (total words: {len(words)})...")
    with open(EXAM_WORDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("Success! database/exam_words.json updated.")

    # Show top added words
    print("\n--- Top 30 newly added exam words ---")
    for w, entry in sorted(valid_oov_words.items(), key=lambda x: -x[1]["total_appear"])[:30]:
        zh_str = entry["definitions"]["zh"][0] if entry["definitions"]["zh"] else ""
        en_str = entry["definitions"]["en"][0] if entry["definitions"]["en"] else ""
        print(f"  {w:16} | Lv{entry['level']} | app:{entry['total_appear']:2} | {zh_str[:25]} | {en_str[:35]}")

if __name__ == "__main__":
    main()

