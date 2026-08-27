"""
English Root Word Explorer — API Server (Vercel Serverless)

FastAPI backend deployed as Vercel serverless function.
"""

import os
import sys

# Ensure api/ directory is in path for imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from decomposer import Decomposer
from graph_engine import WordGraph
from sound_rules import get_all_rules

# Config
DB_PATH = os.environ.get("WORD_DB_PATH", os.path.join(os.path.dirname(__file__), "word_database.json"))

# Initialize FastAPI app (Vercel looks for `app` variable)
app = FastAPI(
    title="English Root Word Explorer",
    description="Explore English word origins through Indo-European sound change rules",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

decomposer = Decomposer(DB_PATH)
word_graph = WordGraph(DB_PATH)


@app.get("/api/analyze")
async def analyze_word(word: str = Query(..., description="The word to analyze and decompose")):
    """
    Main endpoint: decompose a word into roots + affixes,
    trace each root to its simple origin word,
    and list all dictionary words sharing those roots.
    """
    return decomposer.decompose(word)


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


@app.get("/api/rules")
async def get_rules():
    """Get the 6 Indo-European sound interchange rules."""
    return {"rules": get_all_rules()}


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the word graph."""
    return word_graph.get_stats()


# Local development server
if __name__ == "__main__":
    import uvicorn
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=HOST, port=PORT)
