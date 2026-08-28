# English Root Explorer — Full Project Specification

## 0. Project Goal

Build an **English Root Explorer**.

The user enters an English word.

The system should try to answer:

> **What is the underlying root of this word, how is the word constructed, where did the root come from, what does the root mean, and what other words are related to it?**

The project is NOT simply a word splitter.

The central concept is:

```text
User enters word
        ↓
Check Basic Word
        ↓
If not Basic Word:
    decompose / search
        ↓
Root + Affix candidates
        ↓
Graph Search
        ↓
Find valid Basic Word / Root path
        ↓
Use etymological data
        ↓
Explain the Root
        ↓
Show Friend Words
```

The system must be conservative.

If the Engine cannot find a sufficiently reliable explanation, it must return:

```text
TOO_HARD
```

It must never invent a root simply because letters happen to look similar.

---

# 1. Architecture

Separate the project into four major layers:

```text
                    USER
                     │
                     ▼
               WEB / APP
                     │
                     ▼
                    API
                     │
                     ▼
              ROOT ENGINE
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
      Basic DB    Morphology   Etymology
                     DB          DB
```

Responsibilities:

### Web / App

Responsible for:

* user input
* displaying loading state
* displaying results
* displaying confidence
* displaying `TOO_HARD`
* suggesting AI when the deterministic Engine cannot solve the word

The frontend should NOT contain the linguistic search algorithm.

### API

Responsible for:

* validating input
* calling the Engine
* returning structured JSON
* caching results if useful
* recording unknown / difficult words

### Engine

Responsible for:

* Basic Word checking
* decomposition
* candidate generation
* graph search
* scoring
* confidence
* timeout
* selecting the best explanation

### Database

Responsible for storing linguistic knowledge.

---

# 2. Do NOT Build the Linguistic Database From Scratch

Before writing a large amount of linguistic data manually, import existing open datasets.

Prefer local/offline datasets.

Do NOT make the runtime Engine depend on web scraping.

Recommended sources:

## Etymology DB

Repository:

https://github.com/droher/etymology-db

Use it for:

* words
* historical relationships
* derived-from relationships
* inherited-from relationships
* borrowed-from relationships
* root relationships
* etymological graph

Download the structured dataset.

If there are multiple formats, prefer Parquet or compressed CSV.

---

## Etymology Tree

Repository:

https://github.com/jewoo-suh/etymology-tree

Use it for:

* reconstructed roots
* ancestor chains
* etymological graph
* Proto-Indo-European roots
* historical ancestry

Prefer the full offline dataset if its size is reasonable.

The full dataset is approximately 128 MB and the compact dataset approximately 16 MB.

---

## MorphoLex-en

Repository:

https://github.com/hugomailhot/MorphoLex-en

Download:

```text
MorphoLEX_en.xlsx
```

Use it for:

* English morphology
* stems
* prefixes
* suffixes
* morphological decomposition

Do NOT assume that a morphological decomposition automatically proves an etymological relationship.

---

## WordNet

Use Princeton WordNet:

https://wordnet.princeton.edu/

Use it for:

* English lexical entries
* definitions
* parts of speech
* semantic relationships

---

## wordfreq

Repository:

https://github.com/rspeer/wordfreq

Use English frequency data to help identify common English words.

Frequency is NOT by itself proof that a word is a Basic Word.

---

# 3. Large Dataset Rule

Do not blindly download huge datasets.

If a required dataset is:

```text
< 500 MB compressed
```

download it automatically.

If a dataset is:

```text
> 500 MB compressed
```

STOP and report:

* dataset name
* download size
* why it is needed
* whether there is a smaller alternative

Do not download the complete Wiktionary dump at this stage.

Processed Wiktionary-derived datasets such as Etymology DB and Etymology Tree should be preferred.

---

# 4. Raw Data Directory

Store downloaded datasets separately from application data.

Recommended:

```text
data/
├── raw/
│   ├── etymology-db/
│   ├── etymology-tree/
│   ├── morpholex/
│   ├── wordnet/
│   └── wordfreq/
│
└── processed/
    ├── words.db
    ├── roots.db
    ├── affixes.db
    ├── relationships.db
    └── basic_words.db
```

Raw datasets must not be modified.

Create importers that convert them into the application's normalized database.

---

# 5. Database Concepts

Do NOT collapse everything into one `root` field.

These are different concepts:

```text
Word
Basic Word
Root
Stem
Affix
Historical Form
Etymological Ancestor
```

Maintain their relationships explicitly.

---

# 6. Basic Word

A **Basic Word** is a computational search anchor.

It is NOT necessarily a word with no historical root.

It means:

> A word that the Engine considers a useful stopping point because it does not have a sufficiently supported decomposition into other meaningful English components.

Important:

```text
Basic Word ≠ Root
Basic Word ≠ word with no etymology
Basic Word ≠ shortest word
```

For example:

```text
happy
```

may be a Basic Word.

But:

```text
unhappy
happiness
unhappiness
```

are likely not Basic Words because they have useful morphological structure.

---

# 7. Automatically Build Basic Word Database

Do NOT manually enter 10,000 Basic Words.

Generate Basic Word candidates automatically.

Use the following process:

```text
Word Dataset
      ↓
Frequency Ranking
      ↓
Candidate Pool
      ↓
Morphology Check
      ↓
Affix Check
      ↓
Etymology Check
      ↓
Basic Word Scoring
      ↓
Basic Word DB
```

Start with approximately 1,000 candidates at a time.

Prefer common English words.

Short words are useful as initial candidates.

A candidate may initially prioritize words with:

```text
length <= 6
```

but length MUST NOT be the only criterion.

A word longer than six letters can still be a valid Basic Word.

---

# 8. Basic Word Selection Algorithm

For each candidate word:

```python
for word in candidates:

    if known_morphological_decomposition(word):
        reject()

    if known_affix_structure(word):
        reject()

    if known_etymological_decomposition(word):
        reject()

    if candidate_is_common_and_stable(word):
        add_to_basic_words()
```

Use evidence from the imported datasets.

Do not classify a word as Basic solely because:

```python
len(word) <= 6
```

---

# 9. Build 10,000 Basic Words

Generate Basic Words in batches.

Example:

```text
Batch 1
1000 candidates
    ↓
filter
    ↓
maybe 400 Basic Words

Batch 2
1000 candidates
    ↓
filter
    ↓
maybe 350 Basic Words

...
```

Continue until:

```text
basic_words >= 10000
```

or until the available high-quality candidate pool is exhausted.

If fewer than 10,000 high-quality Basic Words can be established, DO NOT force the remaining words.

The database should contain quality over quantity.

---

# 10. Root Database

Root data must come from actual linguistic/etymological data whenever possible.

A Root record should contain information such as:

```text
root_id
canonical_form
language
meaning
description
reconstructed
confidence
source
```

Example concept:

```json
{
  "root_id": "...",
  "canonical_form": "*...",
  "language": "Proto-Indo-European",
  "meaning": "...",
  "reconstructed": true,
  "source": "..."
}
```

Do NOT infer a root merely from similar spelling.

---

# 11. Root Relationships

Maintain explicit relationships:

```text
word → root
word → historical form
word → affix
word → basic word
root → root
root → derived word
```

Relationships should contain:

```text
source
confidence
relationship_type
explanation
```

when available.

---

# 12. Morphological Decomposition

When a user enters a word that is not a Basic Word:

```text
Word
 ↓
Generate possible decompositions
 ↓
Root candidates
Affix candidates
Basic Word candidates
```

The Engine should explore multiple possibilities.

Do NOT immediately select the first string match.

---

# 13. Root + Root Is Allowed

The Engine MUST allow a path where two roots occur without an affix.

Do NOT assume:

```text
Root → Affix → Root
```

is always required.

The search must allow:

```text
Root + Root
```

for compounds or other supported structures.

However:

> Two strings being individually valid words does NOT prove that they form a valid compound or etymological relationship.

Require linguistic evidence where possible.

---

# 14. Graph Search

Treat decomposition as a graph search problem.

Possible search algorithms:

* BFS
* DFS
* Best-first search
* Beam search
* another appropriate graph-search algorithm

The implementation may choose the most suitable algorithm.

The important requirement is:

> Explore multiple possible paths and select the strongest supported explanation.

Conceptually:

```text
                    INPUT WORD
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
           Path A     Path B     Path C
              │         │         │
              ▼         ▼         ▼
           Root A     Root B     Root C
              │         │         │
              ▼         ▼         ▼
          continue   continue   continue
              │         │         │
              ▼         ▼         ▼
          Basic Word Basic Word Basic Word
```

---

# 15. Basic Word Is a Search Anchor, NOT Proof

This is extremely important.

Do NOT use:

```text
reached Basic Word = correct
```

Instead:

```text
reached Basic Word
        +
valid morphology
        +
valid root relationship
        +
etymological evidence
        +
reasonable decomposition
        =
strong candidate
```

A path reaching a Basic Word can still be wrong.

---

# 16. Candidate Scoring

Every candidate path must be scored.

Possible scoring factors:

```text
+ valid morphological relationship
+ known affix
+ known root
+ known word-root relationship
+ known etymological relationship
+ valid historical chain
+ Basic Word reached
+ semantic consistency

- unsupported split
- unnecessary split
- suspicious spelling-only match
- unsupported root
- excessive decomposition
```

Do NOT make character overlap the primary scoring mechanism.

---

# 17. Confidence

Map the final candidate into:

```text
HIGH_CONFIDENCE
MEDIUM_CONFIDENCE
LOW_CONFIDENCE
TOO_HARD
```

Suggested meaning:

### HIGH_CONFIDENCE

Strongly supported by imported linguistic data.

### MEDIUM_CONFIDENCE

Plausible and supported, but some parts are less certain.

### LOW_CONFIDENCE

Possible but weakly supported.

### TOO_HARD

No sufficiently reliable explanation was found.

Do not manufacture an answer just to avoid `TOO_HARD`.

---

# 18. Five-Second Search Budget

The Engine has a maximum search budget of 5 seconds.

Conceptually:

```python
deadline = current_time + 5
```

During the search:

```python
while current_time < deadline:
    search()
```

Whenever a candidate is found:

```python
if candidate_score > best_score:
    best_candidate = candidate
```

The Engine must NOT intentionally wait five seconds.

If the search space is exhausted in 20 milliseconds:

```text
20 ms → finish
```

The five seconds is a MAXIMUM budget.

---

# 19. Search Outcomes

## Case A — Strong Result

```text
FOUND
```

Return the best candidate.

---

## Case B — Candidate Found, More Search Possible

Continue searching until:

* all meaningful candidates are exhausted, OR
* five seconds are reached.

Return the best candidate found.

---

## Case C — No Reliable Candidate

Return:

```text
TOO_HARD
```

Do NOT invent a root.

---

# 20. AI Fallback

There is currently NO LLM API integration.

When the Engine returns:

```text
TOO_HARD
```

the frontend should display a helpful message such as:

```text
This word is too complex for the deterministic Root Engine
to analyze reliably.

Try an AI assistant for a deeper etymological explanation.
```

Do not implement an actual external AI API unless explicitly requested later.

---

# 21. Friend Words

Friend Words are words that share a meaningful root or etymological relationship.

They must NOT be generated purely from spelling similarity.

For example:

```text
ROOT
 │
 ├── Word A
 ├── Word B
 ├── Word C
 └── Word D
```

The Engine should retrieve candidate friend words from the etymological database and rank/filter them.

Prefer:

```text
same root
same etymological origin
strong relationship
```

over:

```text
looks similar
```

---

# 22. Explanation Generation

The final output should explain the reasoning.

For example:

```text
Word:
unhappiness

Structure:
un- + happy + -ness

Basic Word:
happy

Root:
...

Root Meaning:
...

Origin:
...

How it developed:
...

Friend Words:
...

Confidence:
HIGH
```

The purpose is:

> The user should understand WHY the word means what it means.

Not merely:

> The computer split the word into pieces.

---

# 23. API

Create or update:

```text
POST /api/analyze
```

Input:

```json
{
  "word": "unhappiness"
}
```

Output should contain structured information similar to:

```json
{
  "word": "unhappiness",
  "status": "FOUND",
  "confidence": "HIGH_CONFIDENCE",
  "basic_word": "...",
  "affixes": [],
  "roots": [],
  "etymology": [],
  "friend_words": [],
  "explanation": "..."
}
```

For difficult words:

```json
{
  "word": "...",
  "status": "TOO_HARD",
  "confidence": "TOO_HARD",
  "explanation": "..."
}
```

The exact schema can be improved during implementation, but it must remain structured and frontend-friendly.

---

# 24. Unknown / Wrong Space

Continue logging difficult or unknown queries.

For example:

```text
unknown_words_space
```

Store:

```text
word
timestamp
reason
search_time
best_score
```

Possible reasons:

```text
NO_CANDIDATE
LOW_CONFIDENCE
TIMEOUT
MISSING_DATA
```

This data can later be used to improve the database and Engine.

---

# 25. Caching

The API may cache previous analyses.

Cache key:

```text
normalized_word
```

Cache:

```text
analysis result
engine version
timestamp
```

When the Engine changes, invalidate old results if necessary.

---

# 26. Normalization

Before analysis:

```text
trim whitespace
lowercase
validate English letters / hyphen where appropriate
```

Do not execute user input as code.

Reject malicious or invalid input safely.

---

# 27. Important Separation

Keep these responsibilities separate:

```text
DATABASE
    ↓
"What linguistic facts are known?"

ENGINE
    ↓
"Which known facts form the best path?"

FRONTEND
    ↓
"How should the result be shown?"

AI
    ↓
"What can explain cases the deterministic Engine cannot reliably solve?"
```

The Engine is NOT supposed to invent linguistic facts.

The Database is NOT supposed to contain the search algorithm.

---

# 28. Recommended Project Structure

Use a structure similar to:

```text
project/
│
├── api/
│   ├── index.py
│   ├── decomposer.py
│   ├── search.py
│   ├── scoring.py
│   ├── database.py
│   └── models.py
│
├── data/
│   ├── raw/
│   │   ├── etymology-db/
│   │   ├── etymology-tree/
│   │   ├── morpholex/
│   │   ├── wordnet/
│   │   └── wordfreq/
│   │
│   └── processed/
│       ├── words.db
│       ├── roots.db
│       ├── affixes.db
│       ├── relationships.db
│       └── basic_words.db
│
├── scripts/
│   ├── import_etymology.py
│   ├── import_morphology.py
│   ├── import_wordnet.py
│   ├── import_frequency.py
│   └── build_basic_words.py
│
├── web/
│   ├── index.html
│   └── app.js
│
└── tests/
    ├── test_basic_words.py
    ├── test_decomposer.py
    ├── test_search.py
    ├── test_scoring.py
    └── test_api.py
```

---

# 29. Testing

Test at least three categories.

### Basic Word

Example:

```text
sun
```

Expected:

```text
BASIC_WORD
```

No expensive graph search should be necessary.

### Decomposable Word

Example:

```text
unpredictable
```

Expected:

```text
search
→ decomposition candidates
→ Basic Word / Root path
→ explanation
```

### Difficult Word

Example:

```text
gibberishword
```

Expected:

```text
TOO_HARD
```

Do not force a root.

Also test:

* compound words
* prefix + root
* root + suffix
* root + root
* multiple possible decompositions
* words with uncertain etymology
* words with missing database data

---

# 30. Performance Testing

Verify:

1. Basic Words return quickly.
2. Search does not exceed the 5-second maximum.
3. A search that exhausts its graph early finishes early.
4. A deep search stops at the deadline.
5. The best candidate found before timeout is returned.
6. No infinite search loops occur.
7. Duplicate graph states are detected and avoided.

Use a visited-state mechanism.

Example conceptual state:

```text
(word_form, decomposition_path)
```

or another appropriate canonical representation.

---

# 31. Final Product Principle

The most important principle is:

```text
DO NOT GUESS.
```

The Engine should prefer:

```text
reliable result
```

over:

```text
forced result
```

And:

```text
TOO_HARD
```

is a valid and expected result.

The final user experience should be:

```text
                     USER WORD
                         ↓
                  Is it Basic Word?
                    /          \
                  YES           NO
                   ↓             ↓
               Explain      Graph Search
                                ↓
                         Root + Affix paths
                                ↓
                         Evidence checking
                                ↓
                             Scoring
                                ↓
                       Best valid explanation
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
              Reliable result           No result
                    ↓                       ↓
                Explain                  TOO_HARD
                                            ↓
                                      Suggest AI
```

Build the project around this architecture.

The Engine's job is **not to know everything**.

Its job is to search the available linguistic knowledge carefully and provide the **best defensible explanation** it can find.
