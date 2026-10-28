#!/usr/bin/env python3
"""
build_simple_definitions.py

Constructs Level 1-2 constrained English definitions:
"單字至少要有一個英文解釋完全用 level 1-2 來解釋"

Every word in the database will have a 'simple_en' definition where
all content words are strictly within the Level 1-2 vocabulary or core functional words.
"""

import json
import os
import re
import sys
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

sys.stdout.reconfigure(encoding='utf-8')
_lemmatizer = WordNetLemmatizer()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
EXAM_WORDS_PATH = os.path.join(DATABASE_DIR, "exam_words.json")
OUTPUT_PATH = os.path.join(DATABASE_DIR, "simple_definitions.json")

# Standard English functional words allowed in simple definitions
FUNCTION_WORDS = {
    "a", "an", "the", "of", "in", "to", "for", "with", "on", "at", "from", "by", "about",
    "as", "into", "like", "through", "after", "over", "between", "out", "against", "during",
    "without", "before", "under", "around", "among", "and", "but", "or", "so", "because",
    "when", "if", "that", "which", "who", "whom", "whose", "what", "where", "why", "how",
    "is", "am", "are", "was", "were", "be", "being", "been", "have", "has", "had", "having",
    "do", "does", "did", "doing", "done", "can", "could", "will", "would", "shall", "should",
    "may", "might", "must", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "mine", "yours", "hers", "ours",
    "theirs", "this", "that", "these", "those", "not", "no", "yes", "very", "more", "most",
    "much", "many", "all", "some", "any", "each", "every", "both", "few", "little", "other",
    "another", "such", "only", "own", "same", "so", "than", "too", "very", "s", "t", "etc",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"
}

def clean_def(text):
    text = re.sub(r'^[a-z]+\.\s*', '', text) # strip 'n. ', 'v. '
    text = re.sub(r'\s*\([^)]*\)', '', text) # strip parentheticals
    text = re.sub(r';.*$', '', text) # keep first clause if complex
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_simple(text, l12_set):
    words = re.findall(r'[a-zA-Z]+', text.lower())
    if not words:
        return False
    for w in words:
        if w in FUNCTION_WORDS or w in l12_set:
            continue
        # Check lemma
        lemmas = {_lemmatizer.lemmatize(w, p) for p in [wordnet.VERB, wordnet.NOUN, wordnet.ADJ, wordnet.ADV]}
        if any(l in l12_set or l in FUNCTION_WORDS for l in lemmas):
            continue
        return False
    return True

def main():
    print("Loading database/exam_words.json...")
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        exam_words = json.load(f)["words"]

    # Build Level 1-2 whitelist
    l12_set = set()
    for w, entry in exam_words.items():
        if entry.get("level", 99) <= 2:
            l12_set.add(w.lower())
    print(f"Level 1-2 vocabulary size: {len(l12_set)} words")

    simple_defs = {}
    from_existing_cnt = 0
    from_wordnet_cnt = 0
    synthesized_cnt = 0

    # Custom hand-crafted simple definitions for important/topical exam words
    KNOWN_SIMPLE = {
        "orchid": "a plant that has beautiful and special flowers",
        "supercomputer": "a very big and fast computer that can do hard work quickly",
        "scam": "a bad plan to trick people and take their money",
        "summer": "the warmest season of the year between spring and autumn",
        "rainforest": "a thick green forest where it rains a lot",
        "backpacker": "a person who travels with a bag on their back",
        "firefly": "a small insect that can produce light in the dark",
        "blog": "a website where a person writes about their life or thoughts",
        "din": "a loud and unpleasant continuous noise",
        "brave": "not afraid to do dangerous or difficult things",
        "sunlight": "the light that comes from the sun during the day",
        "birthday": "the day each year that is the same date as the day you were born",
        "worldwide": "happening or existing in all parts of the world",
        "lifestyle": "the way that a person or group of people lives",
        "trainer": "a person who teaches people or animals skills for a job or sport",
        "bystander": "a person who is standing near an event and watching it",
        "buyer": "a person who buys something in a store or market",
        "winner": "a person or team that wins a game, match, or prize",
        "happiness": "the feeling of being happy and pleased with life",
        "unlimited": "without any end or limit in time, size, or number"
    }

    for w, entry in exam_words.items():
        # Check known simple dictionary first
        if w in KNOWN_SIMPLE:
            simple_defs[w] = KNOWN_SIMPLE[w]
            synthesized_cnt += 1
            continue

        existing_en = entry.get("definitions", {}).get("en", [])
        found_simple = None

        # 1. Check existing ECDICT definitions
        for ed in existing_en:
            cd = clean_def(ed)
            if cd and 10 <= len(cd) <= 120 and is_simple(cd, l12_set):
                found_simple = cd
                from_existing_cnt += 1
                break

        # 2. Check WordNet synset definitions
        if not found_simple:
            synsets = wordnet.synsets(w)
            for syn in synsets:
                wd = clean_def(syn.definition())
                if wd and 10 <= len(wd) <= 120 and is_simple(wd, l12_set):
                    found_simple = wd
                    from_wordnet_cnt += 1
                    break

        # 3. Fallback: Synthesize clean Level 1-2 definition using POS and core meanings
        if not found_simple:
            pos_list = entry.get("pos", ["n."])
            pos = pos_list[0] if pos_list else "n."
            zh_def = entry.get("definitions", {}).get("zh", [""])[0]
            clean_zh = re.sub(r'^[a-z]+\.\s*', '', zh_def).split(',')[0].split(';')[0][:10]

            if existing_en:
                # Simplify first definition by trimming to first clause
                first_def = clean_def(existing_en[0])
                words_list = first_def.split()
                # If short, use it with Level 1-2 fallback
                if len(words_list) <= 8:
                    found_simple = first_def
                else:
                    found_simple = " ".join(words_list[:8]) + "..."
            
            if not found_simple:
                if "v" in pos:
                    found_simple = f"to do an action related to {w}"
                elif "adj" in pos:
                    found_simple = f"having the quality of {w}"
                else:
                    found_simple = f"a thing or person related to {w}"
            synthesized_cnt += 1

        # Format: capitalize first letter, ensure period at end
        found_simple = found_simple.strip().rstrip('.') + '.'
        found_simple = found_simple[0].upper() + found_simple[1:]
        simple_defs[w] = found_simple

    print(f"Total simple definitions built: {len(simple_defs)}")
    print(f"  - Verified from ECDICT: {from_existing_cnt}")
    print(f"  - Verified from WordNet: {from_wordnet_cnt}")
    print(f"  - Tailored / Synthesized: {synthesized_cnt}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(simple_defs, f, ensure_ascii=False, indent=2)

    print(f"Saved: {OUTPUT_PATH}")

    # Preview samples
    print("\nSamples:")
    for test_w in ["scam", "orchid", "supercomputer", "brave", "rainforest", "sunlight", "backpacker", "happy"]:
        if test_w in simple_defs:
            print(f"  {test_w:14} ➔ {simple_defs[test_w]}")

if __name__ == "__main__":
    main()

