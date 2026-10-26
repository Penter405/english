# English Root Word Explorer 🔤
# [web_url](https://penter405.github.io/english/)

Explore English word origins through Indo-European sound change rules (印歐語音變規律).  
Type any word → see its roots, trace each root to its simple English origin, and browse the entire word family.

## Thanks
- https://m.youtube.com/watch?v=AFgZbU3AhlY&t=1s
- https://notebook.google.com/

## Project Structure

```
english/
├── api/                    # Backend (Vercel serverless)
│   ├── index.py            # FastAPI entry point
│   ├── decomposer.py       # Morphological decomposer
│   ├── sound_rules.py      # 6 interchange rules engine
│   ├── graph_engine.py     # BFS word graph
│   ├── word_database.json  # Root words + affixes database
│   └── requirements.txt    # Python deps (api-level)
├── web/                    # Frontend (GitHub Pages / Vercel)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── local_app/              # Local Python CLI apps
│   └── root_explorer/      # CLI root word explorer
│       └── main.py
├── vercel.json             # Vercel deployment config
├── requirements.txt        # Python deps (project-level, for Vercel)
└── to_do_list.txt          # Project requirements
```

## Before Local Run

### Backend (API)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server locally
cd api && python3 index.py
# Server runs at http://localhost:8000
```

### Frontend (Web)
```bash
# Option 1: Open directly in browser
open web/index.html

# Option 2: Serve with Python
cd web && python3 -m http.server 3000
# Then open http://localhost:3000
```

### Local CLI App
```bash
# Interactive mode
python3 local_app/root_explorer/main.py

# Analyze a single word
python3 local_app/root_explorer/main.py analyze benevolence

# Show word family for a root
python3 local_app/root_explorer/main.py family vol

# Show the 6 sound change rules
python3 local_app/root_explorer/main.py rules
```

## Deploy

### Backend → Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Frontend → GitHub Pages
1. Go to repo Settings → Pages
2. Set source to `main` branch, folder `/web`
3. Update `API_BASE` in `web/app.js` with your Vercel deployment URL

## Environment Variables
```
PORT=8000          # Server port (default: 8000)
HOST=0.0.0.0       # Server host (default: 0.0.0.0)
WORD_DB_PATH=...   # Path to word_database.json (default: api/word_database.json)
```