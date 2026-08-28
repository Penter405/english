# Root Explorer Engine — Goal & Tasks

## Goal
User inputs a word. The engine:
1. Checks if the word is a basic word → add to return list
2. Strips prefixes/suffixes to get the core
3. Applies the 6 sound change rules to swap letters in the core (BFS graph search)
4. Each generated neighbor that matches a basic word → add to return list with transformation path
5. For each found root, show all its derived "friend words"
6. 5-second deadline, then return results with confidence level
7. If nothing found → TOO_HARD

## Tasks
- [x] Rewrite `api/decomposer.py` with BFS letter-swap graph search
- [x] Update `api/index.py` to handle new response format
- [x] Update `web/app.js` to render friend words + transformation paths
- [x] Update `local_app/root_explorer/main.py` for new response format
- [x] Test: shirt → short, skirt
- [x] Test: benevolence → bene+vol+ence → fine, will
- [x] Test: asdfghjkl → TOO_HARD
