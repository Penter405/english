"""
English Root Word Explorer — API Server (Vercel Serverless) v2

FastAPI backend deployed as Vercel serverless function.
Updated to support POST /api/analyze and use the new SQLite database engine.
"""

import os
import sys

# Ensure api/ directory is in path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_app", "root_explorer"))
try:
    from affix_search import search_words
except ImportError:
    search_words = None

from fastapi import FastAPI, Query, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import re

from decomposer import Decomposer
from graph_engine import WordGraph
from sound_rules import get_all_rules
from models import DEFAULT_DB_PATH

# Config — use SQLite database if available, fallback to JSON
DB_PATH = os.environ.get("WORD_DB_PATH", DEFAULT_DB_PATH)
LEGACY_DB_PATH = os.environ.get("LEGACY_DB_PATH",
    os.path.join(os.path.dirname(__file__), "word_database.json"))

# Initialize FastAPI app (Vercel looks for `app` variable)
app = FastAPI(
    title="English Root Word Explorer",
    description="Explore English word origins through linguistic data and Indo-European sound change rules",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engine
decomposer = Decomposer(DB_PATH)
word_graph = WordGraph(LEGACY_DB_PATH)

# In-memory cache (persists for the lifetime of the Vercel serverless instance)
analysis_cache = {}
attack_attempts = 0


# === Request/Response Models ===

class AnalyzeRequest(BaseModel):
    """POST /api/analyze request body."""
    word: str = Field(..., description="The word to analyze", max_length=50)


def _validate_word(word: str) -> str:
    """Validate and normalize input word (spec Section 26)."""
    global attack_attempts
    word = word.strip().lower()
    if not re.match(r"^[a-z\-]+$", word) or len(word) > 50 or len(word) < 1:
        attack_attempts += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input. Only alphabetic characters and hyphens are allowed (1-50 characters)."
        )
    return word


# === Endpoints ===

@app.post("/api/analyze")
async def analyze_word_post(request: AnalyzeRequest):
    """
    POST endpoint: decompose a word into roots + affixes (spec Section 23).
    
    Returns structured JSON with:
      - status: FOUND | TOO_HARD
      - confidence: HIGH_CONFIDENCE | MEDIUM_CONFIDENCE | LOW_CONFIDENCE | TOO_HARD
      - components, roots, affixes, origin_trace, friend_words
    """
    word = _validate_word(request.word)
    return _analyze(word)


@app.get("/api/analyze")
async def analyze_word_get(word: str = Query(..., description="The word to analyze and decompose")):
    """
    GET endpoint (backward compatible): decompose a word into roots + affixes.
    """
    word = _validate_word(word)
    return _analyze(word)


def _analyze(word: str) -> dict:
    """Core analysis logic shared by GET and POST endpoints."""
    # Check cache
    if word in analysis_cache:
        return analysis_cache[word]

    # Analyze
    result = decomposer.decompose(word)

    # Cache result
    analysis_cache[word] = result

    return result


@app.get("/api/system_stats")
async def get_system_stats():
    """Endpoint to view cache stats, database stats, and unknown words."""
    stats = {
        "cached_queries_count": len(analysis_cache),
        "blocked_attack_attempts": attack_attempts,
        "engine_version": Decomposer.ENGINE_VERSION,
    }

    # Add database stats if available
    if decomposer.db:
        try:
            db_stats = decomposer.db.get_stats()
            stats["database"] = db_stats
        except Exception:
            pass

        # Get recent unknown words
        try:
            unknowns = decomposer.db.get_unknown_words(limit=50)
            stats["unknown_words"] = unknowns
            stats["unknown_words_count"] = len(unknowns)
        except Exception:
            pass

    return stats


@app.get("/api/search")
async def search_root(root: str = Query(..., description="Root word or keyword to search for")):
    """Search for roots matching a query."""
    results = decomposer.search_by_root(root)
    return {"query": root, "results": results, "count": len(results)}


@app.get("/api/graph")
async def get_graph(
    word: str = Query(..., description="Starting word for BFS graph exploration"),
    depth: int = Query(2, description="Maximum BFS depth (1-4)", ge=1, le=4)
):
    """BFS graph traversal from a starting word."""
    return word_graph.bfs(word, max_depth=depth)


@app.get("/api/path")
async def find_path(
    word1: str = Query(..., description="Starting word"),
    word2: str = Query(..., description="Target word")
):
    """Find the shortest path between two words in the graph."""
    path = word_graph.find_path(word1, word2)
    if path:
        return {"found": True, "path": path, "steps": len(path) - 1}
    return {"found": False, "message": f"No path found between '{word1}' and '{word2}'"}


@app.get("/api/family/{root}")
async def get_word_family(root: str):
    """Get all dictionary words derived from a specific root."""
    return decomposer.get_word_family(root)


@app.get("/api/v1/words/search")
@app.get("/api/search")
async def search_vocabulary(
    prefix: Optional[str] = Query(None, description="Prefix pattern e.g. com or com*"),
    postfix: Optional[str] = Query(None, description="Postfix/suffix pattern e.g. te or *te"),
    pos: Optional[str] = Query(None, description="Part of speech e.g. verb, noun, adj, adv"),
    min_level: int = Query(1, ge=1, le=6),
    max_level: int = Query(6, ge=1, le=6),
    only_exam: bool = Query(False)
):
    """Compound morphological & syntactic word search."""
    if search_words is None:
        raise HTTPException(status_code=500, detail="Search engine module not available")
    results = search_words(
        prefix=prefix,
        postfix=postfix,
        pos=pos,
        min_level=min_level,
        max_level=max_level,
        only_exam=only_exam
    )
    return {
        "total": len(results),
        "prefix": prefix,
        "postfix": postfix,
        "pos": pos,
        "results": results
    }


@app.get("/api/v1/words/origin")
@app.get("/api/origin")
async def get_word_origin(word: str = Query(..., description="The word to look up its origin and family variants")):
    """Lookup origin and family variants for a word."""
    origins_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "word_origins.json")
    if not os.path.exists(origins_path):
        raise HTTPException(status_code=500, detail="word_origins.json not found")
    with open(origins_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    word_lower = word.lower().strip()
    word_info = data.get("words", {}).get(word_lower)
    orig_key = word_info.get("origin", word_lower) if word_info else word_lower
    orig_info = data.get("origins", {}).get(orig_key)

    if not orig_info and not word_info:
        raise HTTPException(status_code=404, detail=f"No origin information found for '{word}'")

    return {
        "word": word_lower,
        "origin": orig_key,
        "relation": word_info.get("relation", "0: 原型 (lemma)") if word_info else "原型 (lemma)",
        "meaning_zh": orig_info.get("meaning_zh", "") if orig_info else "",
        "pos": orig_info.get("pos", []) if orig_info else [],
        "variants_count": len(orig_info.get("variants", [])) if orig_info else 0,
        "variants": orig_info.get("variants", []) if orig_info else []
    }


@app.get("/api/rules")
async def get_rules():
    """Get the 6 Indo-European sound interchange rules."""
    return {"rules": get_all_rules()}


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the word graph and database."""
    result = word_graph.get_stats()

    # Add database stats
    if decomposer.db:
        try:
            result["database"] = decomposer.db.get_stats()
        except Exception:
            pass

    return result


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "engine_version": Decomposer.ENGINE_VERSION,
        "database_available": decomposer.db is not None,
    }


# Local development server
if __name__ == "__main__":
    import uvicorn
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=HOST, port=PORT)
