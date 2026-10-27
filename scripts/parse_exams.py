"""
Phase 2: Parse exam PDFs and populate appear_year / total_appear / sources.

Reads all exam PDFs (104-115), tokenizes the text, lemmatizes words
(so want/wanting/wanted/wants all map to 'want'), and cross-references
against the vocabulary database built in Phase 1.

Updates: database/exam_words.json
"""
import pdfplumber
import re
import json
import os
from collections import Counter, defaultdict
from datetime import date

# ---------------------------------------------------------------------------
# NLTK lemmatizer setup
# ---------------------------------------------------------------------------
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

_lemmatizer = WordNetLemmatizer()

# Common irregular forms that WordNet lemmatizer might miss
IRREGULAR_FORMS = {
    # Irregular verbs
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
    "read": "read", "reads": "read",  # same form
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
    "laid": "lay",  # lay (past of lie) vs lay (put down)
    "set": "set", "sets": "set",
    "cut": "cut", "cuts": "cut",
    "put": "put", "puts": "put",
    "shut": "shut", "shuts": "shut",
    "hit": "hit", "hits": "hit",
    "spread": "spread", "spreads": "spread",
    "hurt": "hurt", "hurts": "hurt",
    "cost": "cost", "costs": "cost",
    "quit": "quit", "quits": "quit",
    # Irregular nouns (plural)
    "children": "child", "men": "man", "women": "woman",
    "people": "person", "teeth": "tooth", "feet": "foot",
    "mice": "mouse", "geese": "goose", "oxen": "ox",
    "lives": "life", "knives": "knife", "wives": "wife",
    "leaves": "leaf", "halves": "half", "shelves": "shelf",
    "thieves": "thief", "wolves": "wolf",
    # Adjective forms
    "better": "good", "best": "good",
    "worse": "bad", "worst": "bad",
    "more": "much", "most": "much",
    "less": "little", "least": "little",
    "further": "far", "furthest": "far",
    "farther": "far", "farthest": "far",
    "older": "old", "oldest": "old",
    "elder": "old", "eldest": "old",
}


def lemmatize(word):
    """Lemmatize a word to its base form.

    Tries multiple POS tags and picks the shortest result,
    falling back to irregular forms table.
    """
    word = word.lower().strip()

    # Check irregular forms first
    if word in IRREGULAR_FORMS:
        return IRREGULAR_FORMS[word]

    # Try all POS with WordNet lemmatizer
    candidates = set()
    for pos in [wordnet.VERB, wordnet.NOUN, wordnet.ADJ, wordnet.ADV]:
        lemma = _lemmatizer.lemmatize(word, pos)
        candidates.add(lemma)

    # Pick the shortest candidate (most likely the base form)
    # But if the word itself is in candidates, prefer it
    if word in candidates and len(candidates) > 1:
        candidates.discard(word)

    if candidates:
        return min(candidates, key=len)

    return word


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(PROJECT_ROOT, "database")
EXAM_WORDS_PATH = os.path.join(DATABASE_DIR, "exam_words.json")

# Exam PDF naming: {year}-4y-00-e.pdf  (exam), {year}-4y-00-e-standard.pdf (answers)
EXAM_YEARS = list(range(104, 116))


def get_exam_pdf_path(year):
    return os.path.join(DATABASE_DIR, f"{year}-4y-00-e.pdf")


def get_answer_pdf_path(year):
    return os.path.join(DATABASE_DIR, f"{year}-4y-00-e-standard.pdf")


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF."""
    if not os.path.exists(pdf_path):
        print(f"  WARNING: {pdf_path} not found")
        return ""

    pdf = pdfplumber.open(pdf_path)
    texts = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            texts.append(text)
    pdf.close()
    return "\n".join(texts)


def tokenize(text):
    """Simple tokenizer: extract English words from text."""
    # Find all sequences of English letters (at least 2 chars)
    tokens = re.findall(r"\b[a-zA-Z]{2,}\b", text)
    return [t.lower() for t in tokens]


def count_vocab_words(tokens, vocab_set):
    """Count vocabulary word occurrences.

    Each token is lemmatized, and if the lemma is in vocab_set,
    it's counted. This means 'wanting' -> 'want' -> counted under 'want'.

    Returns: Counter of {vocab_word: count}
    """
    counts = Counter()
    for token in tokens:
        lemma = lemmatize(token)
        if lemma in vocab_set:
            counts[lemma] += 1
        elif token in vocab_set:
            # Direct match without lemmatization
            counts[token] += 1

    return counts


def main():
    # Load vocabulary database
    print(f"Loading vocabulary: {EXAM_WORDS_PATH}")
    with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    vocab = data["words"]
    vocab_set = set(vocab.keys())
    print(f"Vocabulary size: {len(vocab_set)} words")

    # Build lemma -> vocab word mapping for faster lookup
    # Pre-compute lemma forms for each vocab word
    lemma_map = {}
    for word in vocab_set:
        lemma_map[word] = word
        # Also try lemmatizing the vocab word itself (shouldn't change)
        lemma = lemmatize(word)
        lemma_map[lemma] = word

    # Process each exam year
    year_stats = {}

    for year in EXAM_YEARS:
        print(f"\n--- Year {year} ---")
        pdf_path = get_exam_pdf_path(year)

        if not os.path.exists(pdf_path):
            print(f"  SKIP: PDF not found")
            continue

        # Extract text
        text = extract_text_from_pdf(pdf_path)
        print(f"  Text length: {len(text)} chars")

        # Tokenize
        tokens = tokenize(text)
        print(f"  Tokens: {len(tokens)}")

        # Count vocab words
        word_counts = count_vocab_words(tokens, vocab_set)
        print(f"  Unique vocab words found: {len(word_counts)}")
        print(f"  Total vocab word occurrences: {sum(word_counts.values())}")

        # Top 10 most frequent
        top10 = word_counts.most_common(10)
        print(f"  Top 10: {[(w, c) for w, c in top10]}")

        year_stats[year] = word_counts

        # Update vocabulary entries
        for word, count in word_counts.items():
            if word in vocab:
                entry = vocab[word]
                if year not in entry["appear_year"]:
                    entry["appear_year"].append(year)
                entry["total_appear"] += count
                entry["sources"].append({
                    "year": year,
                    "count": count,
                })

    # Compute derived fields
    print("\n--- Computing derived fields ---")
    for word, entry in vocab.items():
        entry["appear_year"].sort()
        entry["appear_year_count"] = len(entry["appear_year"])

    # Stats summary
    appeared = sum(1 for e in vocab.values() if e["appear_year_count"] > 0)
    never = sum(1 for e in vocab.values() if e["appear_year_count"] == 0)
    print(f"Words that appeared in exams: {appeared}")
    print(f"Words that never appeared: {never}")

    # Most frequent words across all years
    total_counts = Counter()
    for year, counts in year_stats.items():
        total_counts.update(counts)

    print("\n--- Top 30 most frequent exam words ---")
    for word, count in total_counts.most_common(30):
        level = vocab[word]["level"]
        years = vocab[word]["appear_year_count"]
        print(f"  {word:20s} level={level} total={count:5d} years={years}")

    # Update metadata
    data["meta"]["updated"] = str(date.today())
    data["meta"]["version"] = 2

    # Write updated JSON
    with open(EXAM_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {EXAM_WORDS_PATH}")


if __name__ == "__main__":
    main()

