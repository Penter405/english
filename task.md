# Task List — English Root Word Explorer

## 1. Data Layer
- [x] Create `api/word_database.json` with roots, simple words, affixes, and derived words
- [x] Seed with all examples from `logic_word.txt`
- [x] Add common English prefixes and suffixes

## 2. Core Engine (api/)
- [x] `api/sound_rules.py` — 6 interchange rule implementations
- [x] `api/decomposer.py` — morphological decomposition (word → roots + affixes)
- [/] Fix: `unicorn` decomposes as `un+corn` instead of `uni+corn` (root should win over prefix)
- [/] Fix: `benevolence` should show `bene` as root too (not just prefix), tracing to `fine`
- [x] `api/graph_engine.py` — BFS graph traversal + word family lookup

## 3. Backend API — Vercel Serverless
- [x] `api/main.py` — FastAPI endpoints
- [/] Rename `api/main.py` → `api/index.py` (Vercel convention)
- [ ] Create `vercel.json` with Python runtime config + API rewrites
- [ ] Create `requirements.txt` at project root for Vercel
- [x] Test API endpoints locally

## 4. Web Frontend — GitHub Pages / Vercel
- [x] `style.css` — premium dark theme design system
- [x] `index.html` — landing page with search
- [x] `app.js` — interactive results visualization
- [/] Move `api/static/` → `web/` (separate from API for GitHub Pages deploy)
- [ ] Make API base URL configurable (point to Vercel backend)
- [ ] Test in browser and verify full UI flow

## 5. Local Python App (local_app/)
- [ ] `local_app/root_explorer/` — CLI root word explorer feature
- [ ] One feature = one child folder (as specified in to_do_list.txt)

## 6. Configuration & Docs
- [x] Update `api_name.txt` with env variables
- [ ] Update `README.md` with setup/run/deploy instructions
- [ ] Add `.gitignore`

## 7. Verification
- [ ] Unit tests for decomposer
- [ ] Unit tests for sound rules
- [ ] Performance test (<5 seconds)
- [ ] Manual browser test with recording
