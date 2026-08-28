"""
English Root Explorer — Database Access Layer

Provides a clean interface for all database operations used by the Engine.
Wraps SQLite queries so the engine never needs to write raw SQL.
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime

from models import DEFAULT_DB_PATH, get_connection


class Database:
    """Database access layer for the Root Explorer Engine."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = get_connection(self.db_path)
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ================================================================== #
    #  BASIC WORD OPERATIONS                                              #
    # ================================================================== #

    def is_basic_word(self, word: str) -> bool:
        """Check if a word is in the Basic Word database."""
        row = self.conn.execute(
            "SELECT is_basic FROM words WHERE text = ? AND is_basic = 1",
            (word.lower(),)
        ).fetchone()
        return row is not None

    def get_basic_word_info(self, word: str) -> Optional[Dict]:
        """Get info about a basic word."""
        row = self.conn.execute(
            "SELECT text, frequency, pos, definition, basic_score "
            "FROM words WHERE text = ? AND is_basic = 1",
            (word.lower(),)
        ).fetchone()
        if row is None:
            return None
        return {
            "text": row[0], "frequency": row[1], "pos": row[2],
            "definition": row[3], "basic_score": row[4]
        }

    def get_all_basic_words(self) -> Set[str]:
        """Get all basic words as a set for fast lookup."""
        rows = self.conn.execute(
            "SELECT text FROM words WHERE is_basic = 1"
        ).fetchall()
        return {row[0] for row in rows}

    def basic_word_count(self) -> int:
        """Count of basic words."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM words WHERE is_basic = 1"
        ).fetchone()
        return row[0] if row else 0

    # ================================================================== #
    #  WORD OPERATIONS                                                    #
    # ================================================================== #

    def get_word(self, word: str) -> Optional[Dict]:
        """Get word info."""
        row = self.conn.execute(
            "SELECT text, frequency, pos, definition, is_basic, basic_score "
            "FROM words WHERE text = ?",
            (word.lower(),)
        ).fetchone()
        if row is None:
            return None
        return {
            "text": row[0], "frequency": row[1], "pos": row[2],
            "definition": row[3], "is_basic": bool(row[4]), "basic_score": row[5]
        }

    def word_exists(self, word: str) -> bool:
        """Check if a word exists in the database at all."""
        row = self.conn.execute(
            "SELECT 1 FROM words WHERE text = ?", (word.lower(),)
        ).fetchone()
        return row is not None

    def get_word_frequency(self, word: str) -> float:
        """Get word frequency. Returns 0.0 if not found."""
        row = self.conn.execute(
            "SELECT frequency FROM words WHERE text = ?", (word.lower(),)
        ).fetchone()
        return row[0] if row else 0.0

    # ================================================================== #
    #  ROOT OPERATIONS                                                    #
    # ================================================================== #

    def get_roots_for_form(self, form: str) -> List[Dict]:
        """Get all roots matching a canonical form."""
        rows = self.conn.execute(
            "SELECT root_id, canonical_form, language, meaning, meaning_zh, "
            "description, reconstructed, confidence, source "
            "FROM roots WHERE canonical_form = ?",
            (form.lower(),)
        ).fetchall()
        return [
            {
                "root_id": r[0], "canonical_form": r[1], "language": r[2],
                "meaning": r[3], "meaning_zh": r[4], "description": r[5],
                "reconstructed": bool(r[6]), "confidence": r[7], "source": r[8]
            }
            for r in rows
        ]

    def is_known_root(self, form: str) -> bool:
        """Check if a form is a known root."""
        row = self.conn.execute(
            "SELECT 1 FROM roots WHERE canonical_form = ?", (form.lower(),)
        ).fetchone()
        return row is not None

    # ================================================================== #
    #  AFFIX OPERATIONS                                                   #
    # ================================================================== #

    def get_all_prefixes(self) -> List[Dict]:
        """Get all known prefixes, sorted by length (longest first)."""
        rows = self.conn.execute(
            "SELECT text, meaning, meaning_zh FROM affixes "
            "WHERE type = 'prefix' ORDER BY LENGTH(text) DESC"
        ).fetchall()
        return [{"text": r[0], "meaning": r[1], "meaning_zh": r[2]} for r in rows]

    def get_all_suffixes(self) -> List[Dict]:
        """Get all known suffixes, sorted by length (longest first)."""
        rows = self.conn.execute(
            "SELECT text, meaning, meaning_zh FROM affixes "
            "WHERE type = 'suffix' ORDER BY LENGTH(text) DESC"
        ).fetchall()
        return [{"text": r[0], "meaning": r[1], "meaning_zh": r[2]} for r in rows]

    def is_known_affix(self, text: str, affix_type: str = None) -> bool:
        """Check if a string is a known affix."""
        if affix_type:
            row = self.conn.execute(
                "SELECT 1 FROM affixes WHERE text = ? AND type = ?",
                (text.lower(), affix_type)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT 1 FROM affixes WHERE text = ?", (text.lower(),)
            ).fetchone()
        return row is not None

    def get_affix_info(self, text: str, affix_type: str = None) -> Optional[Dict]:
        """Get affix info."""
        if affix_type:
            row = self.conn.execute(
                "SELECT text, type, meaning, meaning_zh FROM affixes "
                "WHERE text = ? AND type = ?",
                (text.lower(), affix_type)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT text, type, meaning, meaning_zh FROM affixes WHERE text = ?",
                (text.lower(),)
            ).fetchone()
        if row is None:
            return None
        return {"text": row[0], "type": row[1], "meaning": row[2], "meaning_zh": row[3]}

    # ================================================================== #
    #  MORPHOLOGY OPERATIONS                                              #
    # ================================================================== #

    def get_morphological_decomposition(self, word: str) -> List[Dict]:
        """Get known morphological decompositions for a word."""
        rows = self.conn.execute(
            "SELECT morphemes, structure, source FROM morphology WHERE word = ?",
            (word.lower(),)
        ).fetchall()
        return [
            {
                "morphemes": json.loads(r[0]),
                "structure": r[1],
                "source": r[2]
            }
            for r in rows
        ]

    def has_morphological_decomposition(self, word: str) -> bool:
        """Check if a word has a known morphological decomposition."""
        row = self.conn.execute(
            "SELECT 1 FROM morphology WHERE word = ?", (word.lower(),)
        ).fetchone()
        return row is not None

    # ================================================================== #
    #  RELATIONSHIP OPERATIONS                                            #
    # ================================================================== #

    def get_etymological_ancestors(self, word: str) -> List[Dict]:
        """Get etymological ancestors of a word."""
        rows = self.conn.execute(
            "SELECT target_term, target_lang, relationship_type, confidence, "
            "explanation, source FROM relationships "
            "WHERE source_term = ? AND relationship_type IN "
            "('derived_from', 'inherited_from', 'borrowed_from', 'has_root')",
            (word.lower(),)
        ).fetchall()
        return [
            {
                "term": r[0], "language": r[1], "relationship": r[2],
                "confidence": r[3], "explanation": r[4], "source": r[5]
            }
            for r in rows
        ]

    def get_derived_words(self, root_form: str) -> List[Dict]:
        """Get words derived from a root."""
        rows = self.conn.execute(
            "SELECT source_term, source_lang, relationship_type, confidence "
            "FROM relationships WHERE target_term = ? AND relationship_type IN "
            "('derived_from', 'inherited_from', 'borrowed_from', 'has_root')",
            (root_form.lower(),)
        ).fetchall()
        return [
            {"word": r[0], "language": r[1], "relationship": r[2], "confidence": r[3]}
            for r in rows
        ]

    # ================================================================== #
    #  FRIEND WORDS                                                       #
    # ================================================================== #

    def get_friend_words(self, word: str, limit: int = 20) -> List[Dict]:
        """Get friend words that share a root with this word."""
        rows = self.conn.execute(
            "SELECT friend, shared_root, confidence FROM friend_words "
            "WHERE word = ? ORDER BY confidence DESC LIMIT ?",
            (word.lower(), limit)
        ).fetchall()
        return [
            {"friend": r[0], "shared_root": r[1], "confidence": r[2]}
            for r in rows
        ]

    # ================================================================== #
    #  UNKNOWN WORDS LOG (spec Section 24)                                #
    # ================================================================== #

    def log_unknown_word(self, word: str, reason: str, search_time: float, best_score: float):
        """Log an unknown/difficult word."""
        self.conn.execute(
            "INSERT INTO unknown_words (word, timestamp, reason, search_time, best_score) "
            "VALUES (?, ?, ?, ?, ?)",
            (word.lower(), datetime.utcnow().isoformat(), reason, search_time, best_score)
        )
        self.conn.commit()

    def get_unknown_words(self, limit: int = 100) -> List[Dict]:
        """Get recently logged unknown words."""
        rows = self.conn.execute(
            "SELECT word, timestamp, reason, search_time, best_score "
            "FROM unknown_words ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [
            {
                "word": r[0], "timestamp": r[1], "reason": r[2],
                "search_time": r[3], "best_score": r[4]
            }
            for r in rows
        ]

    # ================================================================== #
    #  CACHE (spec Section 25)                                            #
    # ================================================================== #

    def get_cached_result(self, word: str, engine_version: str = "2.0") -> Optional[Dict]:
        """Get cached analysis result."""
        row = self.conn.execute(
            "SELECT result_json FROM analysis_cache "
            "WHERE word = ? AND engine_version = ?",
            (word.lower(), engine_version)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def cache_result(self, word: str, result: Dict, engine_version: str = "2.0"):
        """Cache an analysis result."""
        self.conn.execute(
            "INSERT OR REPLACE INTO analysis_cache (word, result_json, engine_version, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (word.lower(), json.dumps(result), engine_version, datetime.utcnow().isoformat())
        )
        self.conn.commit()

    # ================================================================== #
    #  STATS                                                              #
    # ================================================================== #

    def get_stats(self) -> Dict:
        """Get database statistics."""
        stats = {}
        for table in ["words", "roots", "affixes", "morphology", "relationships",
                       "friend_words", "unknown_words", "analysis_cache"]:
            try:
                row = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                stats[table] = row[0]
            except Exception:
                stats[table] = 0
        stats["basic_words"] = self.basic_word_count()
        return stats
