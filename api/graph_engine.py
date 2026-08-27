"""
Graph Engine

Builds a word relationship graph and performs BFS traversal
to find all words connected through root relationships.
"""

import json
import os
from typing import Dict, List, Set, Optional
from collections import deque


class WordGraph:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "word_database.json")
        
        with open(db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)
        
        self.roots = self.db["roots"]
        
        # Build adjacency list:
        # simple_word <-> root <-> derived_words
        self.graph: Dict[str, Set[str]] = {}
        self.node_info: Dict[str, Dict] = {}
        
        self._build_graph()

    def _build_graph(self):
        """Build the word relationship graph."""
        for root_key, root_data in self.roots.items():
            origin = root_data["origin_word"].lower()
            
            # Add origin word node
            if origin not in self.graph:
                self.graph[origin] = set()
                self.node_info[origin] = {
                    "type": "simple_word",
                    "word": origin,
                    "meaning": self.db.get("simple_words", {}).get(origin, {}).get("meaning", "")
                }
            
            # Add root node
            if root_key not in self.graph:
                self.graph[root_key] = set()
            self.node_info[root_key] = {
                "type": "root",
                "word": root_key,
                "meaning": root_data["meaning"],
                "rule": root_data["rule"],
                "explanation": root_data["explanation"]
            }
            
            # Connect origin <-> root
            self.graph[origin].add(root_key)
            self.graph[root_key].add(origin)
            
            # Add derived words and connect them to root
            for derived in root_data.get("derived_words", []):
                derived_lower = derived.lower()
                if derived_lower not in self.graph:
                    self.graph[derived_lower] = set()
                    self.node_info[derived_lower] = {
                        "type": "derived_word",
                        "word": derived_lower
                    }
                self.graph[derived_lower].add(root_key)
                self.graph[root_key].add(derived_lower)

    def bfs(self, start_word: str, max_depth: int = 3) -> Dict:
        """
        BFS from a starting word to find all connected words.
        
        Returns:
        - nodes: list of word nodes with their info
        - edges: list of connections
        - levels: words grouped by BFS depth
        """
        start = start_word.lower().strip()
        
        if start not in self.graph:
            return {
                "found": False,
                "start": start,
                "nodes": [],
                "edges": [],
                "levels": {}
            }
        
        visited: Set[str] = set()
        queue = deque([(start, 0)])
        visited.add(start)
        
        nodes = []
        edges = []
        levels: Dict[int, List[str]] = {}
        
        while queue:
            word, depth = queue.popleft()
            
            if depth > max_depth:
                continue
            
            # Add node
            info = self.node_info.get(word, {"type": "unknown", "word": word})
            nodes.append({
                "id": word,
                "depth": depth,
                **info
            })
            
            # Track levels
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(word)
            
            # Explore neighbors
            if depth < max_depth:
                for neighbor in self.graph.get(word, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))
                        edges.append({
                            "from": word,
                            "to": neighbor,
                            "relationship": self._get_relationship(word, neighbor)
                        })
        
        return {
            "found": True,
            "start": start,
            "nodes": nodes,
            "edges": edges,
            "levels": {str(k): v for k, v in levels.items()},
            "total_words": len(nodes)
        }

    def _get_relationship(self, word1: str, word2: str) -> str:
        """Describe the relationship between two connected words."""
        info1 = self.node_info.get(word1, {})
        info2 = self.node_info.get(word2, {})
        
        t1 = info1.get("type", "")
        t2 = info2.get("type", "")
        
        if t1 == "simple_word" and t2 == "root":
            rule = info2.get("rule", "")
            return f"sound change (Rule {rule})"
        elif t1 == "root" and t2 == "simple_word":
            rule = info1.get("rule", "")
            return f"sound change (Rule {rule})"
        elif t1 == "root" and t2 == "derived_word":
            return "derived from"
        elif t1 == "derived_word" and t2 == "root":
            return "contains root"
        else:
            return "related"

    def find_path(self, word1: str, word2: str) -> Optional[List[str]]:
        """Find the shortest path between two words using BFS."""
        start = word1.lower().strip()
        end = word2.lower().strip()
        
        if start not in self.graph or end not in self.graph:
            return None
        
        visited: Set[str] = {start}
        queue = deque([(start, [start])])
        
        while queue:
            word, path = queue.popleft()
            
            if word == end:
                return path
            
            for neighbor in self.graph.get(word, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None

    def get_stats(self) -> Dict:
        """Get statistics about the word graph."""
        type_counts = {}
        for info in self.node_info.values():
            t = info.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "total_nodes": len(self.graph),
            "total_edges": sum(len(neighbors) for neighbors in self.graph.values()) // 2,
            "type_counts": type_counts,
            "total_roots": len(self.roots)
        }
