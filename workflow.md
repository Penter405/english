1
# English Root Word Explorer — Engine Workflow

The core of this system is the **Morphological Decomposer** (`api/decomposer.py`). This is a dynamic, algorithmic engine designed to take an English word, break it apart into its morphological components (prefixes, roots, suffixes), and trace those roots back to their origins. 

Here is a step-by-step breakdown of how the engine processes a user's word:

## 1. Input & Security Check
*   **Sanitization:** When the user inputs a word, the API (`index.py`) first checks if it is a legal word (only letters and hyphens, under 50 characters).
*   **Security:** If the input contains malicious commands (like `rm -rf`), the API immediately rejects it as a `400 Bad Request` and logs an attack attempt.
*   **Caching (DP):** The API checks its memory cache. If this exact word has been analyzed recently, it instantly returns the saved result, saving processing time.

## 2. The Algorithmic Engine (Decomposer)
If the word is safe and new, it is passed to the Decomposer engine. The engine does *not* just look up the word in a database. Instead, it mathematically breaks the word apart:

*   **Prefix Stripping:** The engine recursively checks the front of the word against a list of known English prefixes (e.g., `in-`, `un-`, `re-`, `trans-`). It generates all possible combinations of the word with these prefixes removed.
*   **Suffix Stripping:** It then does the same for the back of the word, recursively stripping known suffixes (e.g., `-ation`, `-ence`, `-al`, `-unteer`).
*   **Core Matching:** After stripping the affixes, the engine is left with the "core" of the word. It takes this core and checks if it matches an Indo-European root in our database (e.g., `vol`, `bene`, `nov`).
*   **Scoring & Selection:** Sometimes a word can be broken down in multiple ways. The engine scores each possibility based on how many characters of the word are successfully mapped to a known root. It selects the highest-scoring combination. (This prevents errors like splitting `unicorn` into `un` + `icorn` instead of `uni` + `corn`).

## 3. Tracing Origins & Sound Rules
Once the root (or multiple roots) has been isolated:
*   The engine looks up the Indo-European origin of that root.
*   It identifies which of the **6 Sound Interchange Rules** caused the original simple word to evolve into the Latin/Greek root (e.g., tracing `vol` back to the simple English word `will` via the "u-v-w interchange" rule).

## 4. Discovering the "Friend Words" (Word Family)
*   The engine queries the database for all other dictionary words that were derived from that same root. 
*   For example, if the root is `vol` (will/wish), the engine returns friend words like `volunteer`, `benevolent`, and `voluntary`.

## 5. Output & The "Wrong Space"
*   **Success:** The engine packages the prefixes, roots, suffixes, sound rules, and friend words into a JSON response, which the UI or CLI app beautifully displays to the user.
*   **Failure (The Wrong Space):** If the engine strips all affixes but the remaining core doesn't match any known root (or the word is complete gibberish), it concludes the word is unknown. The API saves this failed query into a `unknown_words_space` log. The developer can later check this "wrong space" via the `/api/system_stats` endpoint to see what words users are searching for that the dictionary is missing.
Step 1: Is "shirt" a basic word? → YES
        Add "shirt" to return list ✅

Step 2: Apply sound change rules to "shirt":
        - Rule 1 (vowel): shirt → short (i↔o) → "short" is a basic word! ✅
        - Rule 3 (g-k-h):  shirt → skirt (h↔k) → "skirt" is a basic word! ✅
        - Rule 4 (d-t-s):  shirt → shird, shirs... → not basic words, skip

Step 3: Continue BFS from "short":
        - short → shirt (already visited)
        - short → shurt, shart... → not basic words
        
Step 4: Return to user:
        ┌──────────────────────────────────────┐
        │  shirt                               │
        │  ├── short  (i↔o, Rule 1: Vowel)     │
        │  └── skirt  (h↔k, Rule 3: g-k-h)    │
        │                                      │
        │  Confidence: HIGH                    │
        └──────────────────────────────────────┘
2
Step 1: Is "benevolence" a basic word? → NO

Step 2: Strip affixes:
        benevolence → strip suffix "ence" → "benevol"
        
Step 3: Can we split the core further?
        "benevol" → "bene" + "vol"
        Both are known roots!

Step 4: Graph search from "vol":
        - "vol" is a root → origin: "will" (w↔v, Rule 2)
        - Apply rules to "vol": vol → bol, vol → wol...
          "wol" → "will" already found via root mapping ✅

Step 5: Graph search from "bene":
        - "bene" is a root → origin: "fine" (f↔b, Rule 6)
        - Apply rules: bene → beni, beno...

Step 6: Return to user:
        ┌───────────────────────────────────────────┐
        │  benevolence = bene + vol + ence          │
        │                                           │
        │  bene (good) ← fine (f↔b, Rule 6)        │
        │    friend words: benefit, benediction...  │
        │                                           │
        │  vol (will) ← will (w↔v, Rule 2)          │
        │    friend words: volunteer, voluntary...  │
        │                                           │
        │  ence = suffix (state/quality of)         │
        │                                           │
        │  Confidence: HIGH                         │
        └───────────────────────────────────────────┘
