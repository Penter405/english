#!/usr/bin/env python3
"""
add_english_definitions.py — Add English definitions from ECDICT to exam_words.json

Reads database/ecdict.csv 'definition' column and adds structured English 
definitions to each word in exam_words.json.

Output format for each word's definitions field:
  {
    "zh": ["n. 蘋果"],                          # existing Chinese defs
    "en": ["n. a fruit", "n. a tree"]           # new English defs from ECDICT
  }
"""

import csv, json, re, os, sys
from pathlib import Path

BASE = Path(r'c:\Users\user\Desktop\github\english')
ECDICT = BASE / 'database' / 'ecdict.csv'
EXAM_WORDS = BASE / 'database' / 'exam_words.json'

def parse_ecdict_definition(raw_def):
    """Parse ECDICT definition string into a list of English definitions.
    
    Input:  "n. a fruit\\ns. apple tree"
    Output: ["n. a fruit", "n. apple tree"]
    """
    if not raw_def:
        return []
    
    # Split by literal \n (which is \\n in the CSV)
    parts = raw_def.split('\\n')
    defs = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Clean up: some entries have POS prefix like "a." "n." "v." "s." "r."
        # s. = adjective satellite (WordNet), r. = adverb (WordNet)
        # Map s. → adj., r. → adv. for clarity
        part = re.sub(r'^s\.\s', 'adj. ', part)
        part = re.sub(r'^r\.\s', 'adv. ', part)
        defs.append(part)
    
    return defs


def main():
    print("Step 1: Loading ECDICT (this may take a moment) ...")
    ecdict = {}
    with open(ECDICT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row.get('word', '').strip().lower()
            definition = row.get('definition', '').strip()
            if word and definition:
                ecdict[word] = definition
    
    print(f"  Loaded {len(ecdict)} entries from ECDICT")
    
    print("Step 2: Loading exam_words.json ...")
    with open(EXAM_WORDS, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    words = data['words']
    print(f"  {len(words)} words in exam_words.json")
    
    print("Step 3: Adding English definitions ...")
    matched = 0
    no_match = 0
    already_has_en = 0
    
    for word_key in words:
        entry = words[word_key]
        old_defs = entry.get('definitions', [])
        
        # Restructure definitions: separate zh and en
        zh_defs = []
        en_defs = []
        
        if isinstance(old_defs, list):
            for d in old_defs:
                if isinstance(d, str):
                    if re.search(r'[\u4e00-\u9fff]', d):
                        zh_defs.append(d)
                    else:
                        en_defs.append(d)
        elif isinstance(old_defs, dict):
            zh_defs = old_defs.get('zh', [])
            en_defs = old_defs.get('en', [])
        
        # Look up in ECDICT
        lookup_key = word_key.lower().strip()
        ecdict_def = ecdict.get(lookup_key, '')
        
        if ecdict_def:
            ec_en_defs = parse_ecdict_definition(ecdict_def)
            if ec_en_defs:
                # Replace or merge English definitions
                if en_defs:
                    already_has_en += 1
                en_defs = ec_en_defs  # ECDICT definitions are more comprehensive
                matched += 1
            else:
                no_match += 1
        else:
            no_match += 1
        
        # Store structured definitions
        entry['definitions'] = {
            'zh': zh_defs,
            'en': en_defs,
        }
    
    print(f"  Matched: {matched}")
    print(f"  No match: {no_match}")
    print(f"  Already had English: {already_has_en}")
    
    # Show some examples
    print("\nExamples:")
    examples = ['able', 'apple', 'computer', 'happy', 'run', 'school', 'abandon', 'beautiful']
    for ex in examples:
        if ex in words:
            d = words[ex]['definitions']
            en_preview = d['en'][0][:80] if d['en'] else '(none)'
            zh_preview = d['zh'][0][:40] if d['zh'] else '(none)'
            print(f"  {ex}:")
            print(f"    EN: {en_preview}")
            try:
                print(f"    ZH: {zh_preview}")
            except:
                print(f"    ZH: (encoding issue in terminal, but saved correctly)")
    
    # Update version
    data['version'] = data.get('version', 0) + 1
    data['notes'] = data.get('notes', '') + ' | v' + str(data['version']) + ': Added structured en/zh definitions from ECDICT'
    
    print(f"\nStep 4: Saving exam_words.json (version {data['version']}) ...")
    with open(EXAM_WORDS, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    size_mb = os.path.getsize(EXAM_WORDS) / (1024 * 1024)
    print(f"  Saved ({size_mb:.1f} MB)")
    print("Done!")


if __name__ == '__main__':
    main()
