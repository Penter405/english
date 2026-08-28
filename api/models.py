"""
English Root Explorer — Data Models & Schema

Defines the SQLite database schema for all linguistic data.
Concepts from spec Section 5:
  - Word, Basic Word, Root, Stem, Affix, Historical Form, Etymological Ancestor
"""

import sqlite3
import os
from typing import Optional

# Default database path
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "processed", "english.db"
)

SCHEMA_SQL = """
-- Words: all known English words with metadata
CREATE TABLE IF NOT EXISTS words (
    word_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT NOT NULL UNIQUE,
    language    TEXT DEFAULT 'en',
    frequency   REAL DEFAULT 0.0,
    pos         TEXT DEFAULT '',           -- part of speech (noun, verb, etc.)
    definition  TEXT DEFAULT '',
    syllables   INTEGER DEFAULT 0,
    is_basic    INTEGER DEFAULT 0,         -- 1 if this is a Basic Word
    basic_score REAL DEFAULT 0.0,          -- Basic Word confidence score
    source      TEXT DEFAULT ''            -- where this entry came from
);

CREATE INDEX IF NOT EXISTS idx_words_text ON words(text);
CREATE INDEX IF NOT EXISTS idx_words_basic ON words(is_basic);
CREATE INDEX IF NOT EXISTS idx_words_frequency ON words(frequency DESC);

-- Roots: linguistic/etymological roots
CREATE TABLE IF NOT EXISTS roots (
    root_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_form  TEXT NOT NULL,
    language        TEXT DEFAULT '',       -- e.g. 'Latin', 'Greek', 'Proto-Indo-European'
    meaning         TEXT DEFAULT '',
    meaning_zh      TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    reconstructed   INTEGER DEFAULT 0,    -- 1 if this is a reconstructed form (e.g. PIE)
    confidence      REAL DEFAULT 0.5,
    source          TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_roots_form ON roots(canonical_form);
CREATE INDEX IF NOT EXISTS idx_roots_lang ON roots(language);

-- Affixes: known prefixes and suffixes
CREATE TABLE IF NOT EXISTS affixes (
    affix_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('prefix', 'suffix', 'infix')),
    meaning     TEXT DEFAULT '',
    meaning_zh  TEXT DEFAULT '',
    source      TEXT DEFAULT '',
    UNIQUE(text, type)
);

CREATE INDEX IF NOT EXISTS idx_affixes_text ON affixes(text);
CREATE INDEX IF NOT EXISTS idx_affixes_type ON affixes(type);

-- Morphological decompositions from MorphoLex
CREATE TABLE IF NOT EXISTS morphology (
    morph_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT NOT NULL,
    morphemes   TEXT NOT NULL,     -- JSON list of morphemes e.g. '["un","happi","ness"]'
    structure   TEXT DEFAULT '',   -- e.g. 'prefix+root+suffix'
    source      TEXT DEFAULT 'morpholex',
    UNIQUE(word, morphemes)
);

CREATE INDEX IF NOT EXISTS idx_morphology_word ON morphology(word);

-- Etymological relationships
CREATE TABLE IF NOT EXISTS relationships (
    rel_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_term         TEXT NOT NULL,
    source_lang         TEXT DEFAULT 'en',
    target_term         TEXT NOT NULL,
    target_lang         TEXT DEFAULT '',
    relationship_type   TEXT NOT NULL,     -- 'derived_from', 'inherited_from', 'borrowed_from',
                                          -- 'has_root', 'cognate_of', 'sound_change', etc.
    confidence          REAL DEFAULT 0.5,
    explanation         TEXT DEFAULT '',
    source              TEXT DEFAULT ''    -- dataset this came from
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_term);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_term);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type);

-- Friend words: words that share a root or etymological origin
-- (Precomputed for fast lookup)
CREATE TABLE IF NOT EXISTS friend_words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT NOT NULL,
    friend      TEXT NOT NULL,
    shared_root TEXT DEFAULT '',
    confidence  REAL DEFAULT 0.5,
    UNIQUE(word, friend)
);

CREATE INDEX IF NOT EXISTS idx_friends_word ON friend_words(word);

-- Unknown/difficult words log (spec Section 24)
CREATE TABLE IF NOT EXISTS unknown_words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    reason      TEXT DEFAULT '',           -- NO_CANDIDATE, LOW_CONFIDENCE, TIMEOUT, MISSING_DATA
    search_time REAL DEFAULT 0.0,
    best_score  REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_unknown_word ON unknown_words(word);

-- Cache for analysis results (spec Section 25)
CREATE TABLE IF NOT EXISTS analysis_cache (
    word            TEXT PRIMARY KEY,
    result_json     TEXT NOT NULL,
    engine_version  TEXT DEFAULT '2.0',
    timestamp       TEXT NOT NULL
);

-- Metadata about the database build
CREATE TABLE IF NOT EXISTS db_metadata (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""


def create_database(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create the database and all tables. Returns a connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a connection to the existing database."""
    if not os.path.exists(db_path):
        return create_database(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn
