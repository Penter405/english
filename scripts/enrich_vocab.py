"""
Phase 3: Enrich exam_words.json with forms, word_family, definitions, situations.

- forms: Different inflected forms (achieve → achieved, achieving, achieves, achievement)
- word_family: Related words sharing the same root/stem
- definitions: Chinese definitions from vocabulary table (future: extend)
- situations: Topic categories from topic_vocabulary_5000.json

Uses NLTK WordNet for forms and word families.

Updates: database/exam_words.json
"""
import json
import os
import re
from datetime import date
from collections import defaultdict

from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM_WORDS_PATH = os.path.join(PROJECT_ROOT, "database", "exam_words.json")
TOPIC_VOCAB_PATH = os.path.join(PROJECT_ROOT, "database", "topic_vocabulary_5000.json")

_lemmatizer = WordNetLemmatizer()


# ---------------------------------------------------------------------------
# 1. FORMS: Generate inflected forms for each word
# ---------------------------------------------------------------------------
def generate_forms(word, pos_list):
    """Generate common inflected forms for a word based on its POS.

    Returns a list of forms including the base word.
    """
    forms = {word}

    # Determine what types of inflections to generate
    has_verb = any("v" in p.lower() for p in pos_list)
    has_noun = any("n" in p.lower() for p in pos_list)
    has_adj = any("adj" in p.lower() for p in pos_list)
    has_adv = any("adv" in p.lower() for p in pos_list)

    if has_verb:
        forms.update(generate_verb_forms(word))

    if has_noun:
        forms.update(generate_noun_forms(word))

    if has_adj:
        forms.update(generate_adj_forms(word))

    return sorted(forms)


def generate_verb_forms(word):
    """Generate verb inflections: -s, -ed, -ing, -er."""
    forms = set()

    # Basic rules
    if word.endswith("e"):
        forms.add(word + "s")        # makes
        forms.add(word + "d")        # made → no, this is for regular: bake→baked
        forms.add(word[:-1] + "ing") # making
        forms.add(word + "r")        # maker (sometimes)
    elif word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        forms.add(word[:-1] + "ies")  # carries
        forms.add(word[:-1] + "ied")  # carried
        forms.add(word + "ing")       # carrying
    elif word.endswith(("s", "x", "z", "ch", "sh")):
        forms.add(word + "es")        # watches
        forms.add(word + "ed")        # watched
        forms.add(word + "ing")       # watching
    elif (len(word) >= 3 and word[-1] not in "aeiouwxy" and
          word[-2] in "aeiou" and word[-3] not in "aeiou"):
        # CVC pattern: stop → stopped, stopping
        forms.add(word + "s")
        forms.add(word + word[-1] + "ed")   # stopped
        forms.add(word + word[-1] + "ing")  # stopping
    else:
        forms.add(word + "s")
        forms.add(word + "ed")
        forms.add(word + "ing")

    return forms


def generate_noun_forms(word):
    """Generate noun plural forms."""
    forms = set()

    if word.endswith(("s", "x", "z", "ch", "sh")):
        forms.add(word + "es")
    elif word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        forms.add(word[:-1] + "ies")
    elif word.endswith("f"):
        forms.add(word[:-1] + "ves")  # leaf → leaves
        forms.add(word + "s")         # some just add -s
    elif word.endswith("fe"):
        forms.add(word[:-2] + "ves")  # knife → knives
    else:
        forms.add(word + "s")

    return forms


def generate_adj_forms(word):
    """Generate adjective comparative/superlative forms."""
    forms = set()

    # Only for short adjectives (1-2 syllables)
    if len(word) <= 6:
        if word.endswith("e"):
            forms.add(word + "r")
            forms.add(word + "st")
        elif word.endswith("y") and len(word) > 2:
            forms.add(word[:-1] + "ier")
            forms.add(word[:-1] + "iest")
        elif len(word) <= 4:
            forms.add(word + "er")
            forms.add(word + "est")

    # -ly adverb form
    if word.endswith("y"):
        forms.add(word[:-1] + "ily")
    elif word.endswith("le"):
        forms.add(word[:-1] + "y")
    elif word.endswith("ic"):
        forms.add(word + "ally")
    else:
        forms.add(word + "ly")

    return forms


# ---------------------------------------------------------------------------
# 2. WORD_FAMILY: Find related words in the vocabulary that share stems
# ---------------------------------------------------------------------------
def build_word_families(vocab):
    """Build word families by finding words that share stems.

    A word family groups words like: act, action, active, activity, actor, actress.
    We use lemmatization + prefix/suffix stripping to find related words.
    """
    # Build a map: lemma → list of vocab words
    lemma_groups = defaultdict(set)
    for word in vocab:
        lemma = _lemmatizer.lemmatize(word, wordnet.VERB)
        lemma_groups[lemma].add(word)
        lemma = _lemmatizer.lemmatize(word, wordnet.NOUN)
        lemma_groups[lemma].add(word)

    # Build stem groups by stripping common suffixes
    SUFFIXES = [
        "tion", "sion", "ment", "ness", "ence", "ance", "ity", "ty",
        "ous", "ious", "eous", "able", "ible", "ful", "less",
        "ly", "er", "or", "ist", "al", "ial", "ual", "ive", "ative",
        "ic", "ical", "ing", "ed", "ure", "ary", "ery", "ory",
        "ate", "ify", "ize", "ise", "ent", "ant", "dom", "ship",
    ]
    stem_groups = defaultdict(set)
    for word in vocab:
        stem_groups[word].add(word)
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                stem = word[:-len(suffix)]
                stem_groups[stem].add(word)
                # Also check if stem itself is in vocab
                if stem in vocab:
                    stem_groups[stem].add(word)

    # For each word, find its family
    families = {}
    for word in vocab:
        family = set()

        # Add words with same lemma
        for lemma_key, group in lemma_groups.items():
            if word in group and len(group) > 1:
                family.update(group)

        # Add words that share the same stem (word is a prefix of another)
        for other in vocab:
            if other == word:
                continue
            # Check if one is a stem of the other
            if other.startswith(word) and len(other) - len(word) <= 7:
                remainder = other[len(word):]
                if remainder in SUFFIXES or any(remainder.startswith(s) for s in SUFFIXES):
                    family.add(other)
            elif word.startswith(other) and len(word) - len(other) <= 7:
                remainder = word[len(other):]
                if remainder in SUFFIXES or any(remainder.startswith(s) for s in SUFFIXES):
                    family.add(other)

        # Add words from stem groups
        for stem, group in stem_groups.items():
            if word in group and len(group) > 1:
                family.update(group)

        family.discard(word)
        families[word] = sorted(family)

    return families


# ---------------------------------------------------------------------------
# 3. SITUATIONS: Map words to topics from topic_vocabulary_5000.json
# ---------------------------------------------------------------------------
def build_situations(topic_vocab_path, vocab_set):
    """Map words to their topic categories."""
    if not os.path.exists(topic_vocab_path):
        print(f"  WARNING: {topic_vocab_path} not found, skipping situations")
        return {}

    with open(topic_vocab_path, "r", encoding="utf-8") as f:
        topic_data = json.load(f)

    word_topics = defaultdict(list)
    for group in topic_data.get("groups", []):
        topic = group.get("topic", "")
        levels = group.get("levels", {})
        for level_name, words in levels.items():
            for word in words:
                word_lower = word.lower()
                if word_lower in vocab_set:
                    if topic not in word_topics[word_lower]:
                        word_topics[word_lower].append(topic)

    return dict(word_topics)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Loading vocabulary: {EXAM_WORDS_PATH}")
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    vocab = data["words"]
    vocab_set = set(vocab.keys())
    print(f"Vocabulary size: {len(vocab_set)} words")

    # 1. Generate forms
    print("\n--- Phase 3a: Generating inflected forms ---")
    forms_count = 0
    for word, entry in vocab.items():
        forms = generate_forms(word, entry["pos"])
        entry["forms"] = forms
        if len(forms) > 1:
            forms_count += 1

    print(f"  Words with generated forms: {forms_count}")

    # Show samples
    for w in ["want", "achieve", "happy", "study", "run", "box"]:
        if w in vocab:
            print(f"  {w}: {vocab[w]['forms']}")

    # 2. Build word families
    print("\n--- Phase 3b: Building word families ---")
    families = build_word_families(vocab_set)
    family_count = 0
    for word, family in families.items():
        if word in vocab:
            vocab[word]["word_family"] = family
            if family:
                family_count += 1

    print(f"  Words with family members: {family_count}")

    # Show samples
    for w in ["act", "achieve", "happy", "nature", "create", "educate"]:
        if w in vocab:
            print(f"  {w}: {vocab[w]['word_family']}")

    # 3. Build situations from topic vocabulary
    print("\n--- Phase 3c: Mapping situations ---")
    situations = build_situations(TOPIC_VOCAB_PATH, vocab_set)
    sit_count = 0
    for word, topics in situations.items():
        if word in vocab:
            vocab[word]["situations"] = topics
            sit_count += 1

    print(f"  Words with situations: {sit_count}")
    for w in ["water", "doctor", "computer", "mountain", "music"]:
        if w in vocab:
            print(f"  {w}: {vocab[w]['situations']}")

    # 4. Definitions placeholder (from PDF extraction — future work)
    # For now, we'll leave definitions empty; they need the vocabulary table's Chinese text
    print("\n--- Phase 3d: Definitions ---")
    print("  (Definitions require separate Chinese text extraction — marked for future)")

    # Update metadata
    data["meta"]["updated"] = str(date.today())
    data["meta"]["version"] = 3

    # Write updated JSON
    with open(EXAM_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {EXAM_WORDS_PATH}")

    # Stats
    print("\n--- Summary ---")
    has_forms = sum(1 for v in vocab.values() if len(v["forms"]) > 1)
    has_family = sum(1 for v in vocab.values() if v["word_family"])
    has_situations = sum(1 for v in vocab.values() if v["situations"])
    has_appeared = sum(1 for v in vocab.values() if v["appear_year_count"] > 0)
    print(f"  Total words: {len(vocab)}")
    print(f"  With forms: {has_forms}")
    print(f"  With family: {has_family}")
    print(f"  With situations: {has_situations}")
    print(f"  Appeared in exams: {has_appeared}")


if __name__ == "__main__":
    main()

