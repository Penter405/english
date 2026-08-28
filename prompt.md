# Root Explorer Engine — Search Workflow Specification

Implement the English Root Explorer around the following workflow.

## 1. User Input

The user enters an English word.

```text
User
 ↓
Web / App
 ↓
API
 ↓
Root Engine
```

The Web/App should mainly handle input and presentation. The linguistic analysis should be performed by the Engine.

---

## 2. Basic Word Database

The Engine must have a **Basic Word Database**.

A Basic Word is a simple/base word that can act as a valid stopping point for the search.

Example:

```text
will
hand
go
come
man
```

Important:

**Basic Word ≠ Root.**

A Basic Word is a usable word in English.

A Root is a linguistic/historical root that may exist behind one or more words.

---

## 3. First Check

When the Engine receives a word:

```python
if word in basic_word_database:
    return basic_word_result
```

If the word is already a Basic Word, there is no need to perform a complex decomposition search.

Return the Basic Word information directly.

---

## 4. If It Is Not a Basic Word

If the word is not in the Basic Word Database:

```text
Word
 ↓
Generate possible morphological decompositions
 ↓
Root candidates + Affix candidates
```

The Engine should generate **multiple possible candidates**, not assume there is only one decomposition.

For example:

```text
word
 ├── candidate A
 ├── candidate B
 ├── candidate C
 └── ...
```

Each candidate represents a possible way of separating roots and affixes.

---

## 5. Graph Search

Treat the decomposition problem as a search problem.

The Engine may use:

* BFS
* DFS
* Best-first search
* Beam search
* Another appropriate graph/search algorithm

The exact algorithm can be chosen based on implementation performance.

The important requirement is:

> **Explore multiple possible root/decomposition paths rather than stopping at the first possible string match.**

Conceptually:

```text
                    INPUT WORD
                        │
              ┌─────────┼─────────┐
              ↓         ↓         ↓
           Path A     Path B     Path C
              │         │         │
              ↓         ↓         ↓
           Root A     Root B     Root C
              │         │         │
              ↓         ↓         ↓
           Continue   Continue   Continue
              │         │         │
              ▼         ▼         ▼
        Basic Word? Basic Word? Basic Word?
```

---

## 6. Basic Word as a Search Target

A path is especially valuable when it eventually reaches a Basic Word.

For example:

```text
unknown word
    ↓
remove affix
    ↓
another form
    ↓
remove affix
    ↓
Basic Word
```

When a search path reaches a Basic Word:

```text
FOUND CANDIDATE
```

However, **do not immediately stop the entire search**.

Continue searching for a better candidate until the search deadline.

This is important because another path may provide a more linguistically valid explanation.

---

## 7. Candidate Scoring

Every candidate path should receive a score.

The scoring system should consider factors such as:

```text
Morphological validity
Root validity
Affix validity
Basic-word match
Etymological evidence
Historical consistency
Number of unnecessary splits
```

Do NOT rank candidates merely by character similarity.

For example:

```text
Candidate A: 92
Candidate B: 78
Candidate C: 41
```

The Engine should return Candidate A as the best result.

The scoring system should be modular so that it can be improved later.

---

## 8. Five-Second Search Limit

The Engine must have a hard search deadline.

Conceptually:

```python
deadline = current_time + 5 seconds
```

The search continues while:

```python
current_time < deadline
```

Whenever a candidate is found:

```text
if candidate is better than current_best:
    current_best = candidate
```

Do NOT intentionally wait for five seconds if the search has already exhausted all meaningful possibilities.

The five seconds is a **maximum search budget**, not a required delay.

---

## 9. Three Possible Outcomes

### Outcome A — Strong Result

The Engine finds a good candidate:

```text
FOUND
```

Return:

```text
word
root
affixes
basic_word
root explanation
friend words
confidence
```

---

### Outcome B — Search Found Candidates

The Engine found one or more candidates but is still searching for a better result.

Continue searching until:

* all meaningful candidates are exhausted, or
* the 5-second deadline is reached.

Then return the best candidate found.

```text
BEST CANDIDATE
```

---

### Outcome C — No Reliable Result

If the Engine reaches the deadline without finding a sufficiently valid result:

```text
TOO_HARD
```

Do not invent an explanation.

The system should tell the user that the Root Engine could not reliably analyze this word and recommend using AI for a deeper analysis.

Conceptually:

```text
Root Engine
     ↓
No reliable result
     ↓
TOO_HARD
     ↓
AI fallback
```

---

## 10. Reliability Is More Important Than Forced Answers

The Engine must **never force a root** just because the letters happen to match.

For example:

```text
similar letters
≠
same root
```

Likewise:

```text
possible string split
≠
historically valid etymology
```

If the evidence is insufficient:

```text
TOO_HARD
```

is a correct result.

The Engine should distinguish between:

```text
HIGH_CONFIDENCE
MEDIUM_CONFIDENCE
LOW_CONFIDENCE
TOO_HARD
```

Do not present speculation as fact.

---

## 11. Final Architecture

The overall system should look like:

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
              ┌────────┴────────┐
              │                 │
      Basic Word Check      Not Basic Word
              │                 │
              │                 ▼
              │          Morphological Split
              │                 │
              │                 ▼
              │          Root/Affix Candidates
              │                 │
              │                 ▼
              │            Graph Search
              │                 │
              │          ┌──────┴──────┐
              │          │             │
              │       Found Path    No Path
              │          │             │
              │          ▼             ▼
              │      Score it       Continue
              │          │
              │          ▼
              │      Search for
              │      better paths
              │          │
              │          ▼
              │     5-second limit
              │          │
              └──────┬────┴────────────┘
                     ▼
              Best Reliable Result
                     │
              OR     │
                     ▼
                  TOO_HARD
                     │
                     ▼
                  AI FALLBACK
```

## Core Principle

The product is not simply a word splitter.

Its purpose is:

> **Take an unfamiliar English word, find a defensible path from that word toward its underlying root/base structure, analyze the root, and explain the reasoning to the user.**

The search engine should be **fast, explainable, conservative, and allowed to say "I don't know."**
