"""
English Root Explorer — Candidate Scoring Module

Per spec Section 16, every candidate path must be scored.

Scoring factors:
  + valid morphological relationship (from MorphoLex)
  + known affix
  + known root (from Etymology DB/MorphoLex)
  + known word-root relationship
  + known etymological relationship
  + valid historical chain
  + Basic Word reached
  + semantic consistency

  - unsupported split
  - unnecessary split
  - suspicious spelling-only match
  - unsupported root
  - excessive decomposition
"""

from typing import Dict, List, Optional


# Confidence thresholds (spec Section 17)
HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 45
LOW_THRESHOLD = 20


def score_candidate(candidate: Dict, db) -> float:
    """Score a decomposition candidate.
    
    Args:
        candidate: dict with keys like:
            - word: original word
            - prefixes: list of prefix strings
            - roots: list of root strings  
            - suffixes: list of suffix strings
            - basic_word: the basic word reached (if any)
            - path: list of decomposition steps
            - evidence: dict of evidence types found
        db: Database instance for lookups
    
    Returns:
        float score (0-100)
    """
    score = 0.0
    penalties = 0.0

    prefixes = candidate.get("prefixes", [])
    roots = candidate.get("roots", [])
    suffixes = candidate.get("suffixes", [])
    basic_word = candidate.get("basic_word", "")
    core = candidate.get("core", "")
    evidence = candidate.get("evidence", {})
    via = candidate.get("via", "")

    # === POSITIVE SIGNALS ===

    # +25: Basic Word reached (spec Section 15 — anchor, not proof)
    if basic_word and db.is_basic_word(basic_word):
        score += 25

    # +20: Known root in database
    if core and db.is_known_root(core):
        score += 20
    for r in roots:
        if db.is_known_root(r):
            score += 15

    # +15: Valid morphological relationship (from MorphoLex data)
    if evidence.get("morpholex_match"):
        score += 15

    # +10: Known affix(es)
    for p in prefixes:
        if db.is_known_affix(p, "prefix"):
            score += 10
    for s in suffixes:
        if db.is_known_affix(s, "suffix"):
            score += 10

    # +15: Known etymological relationship
    if evidence.get("etymological_relationship"):
        score += 15

    # +10: Sound change rule match (from existing engine)
    if via == "sound_rule" or via == "sound_rule_to_root":
        score += 10

    # +10: Direct root match (from curated data)
    if via == "root":
        score += 10

    # +5: Word coverage — how much of the original word is explained
    coverage = evidence.get("coverage", 0.0)
    score += coverage * 5

    # === NEGATIVE SIGNALS ===

    # -10: Unsupported split (no evidence for the decomposition)
    if not evidence.get("morpholex_match") and not evidence.get("etymological_relationship"):
        if len(roots) > 0 and not any(db.is_known_root(r) for r in roots):
            penalties += 10

    # -5: Unnecessary split (simple word split into too many parts)
    total_parts = len(prefixes) + len(roots) + len(suffixes)
    if total_parts > 4:
        penalties += 5 * (total_parts - 4)

    # -15: Suspicious spelling-only match
    if evidence.get("spelling_only"):
        penalties += 15

    # -5: Core too short (likely noise)
    if core and len(core) < 2:
        penalties += 5

    # -10: Excessive BFS depth in sound change search
    depth = evidence.get("bfs_depth", 0)
    if depth > 2:
        penalties += 5 * (depth - 2)

    final_score = max(0, min(100, score - penalties))
    return final_score


def classify_confidence(score: float) -> str:
    """Map a score to a confidence level (spec Section 17)."""
    if score >= HIGH_THRESHOLD:
        return "HIGH_CONFIDENCE"
    elif score >= MEDIUM_THRESHOLD:
        return "MEDIUM_CONFIDENCE"
    elif score >= LOW_THRESHOLD:
        return "LOW_CONFIDENCE"
    else:
        return "TOO_HARD"


def select_best_candidate(candidates: List[Dict], db) -> Optional[Dict]:
    """Score all candidates and return the best one.
    
    Returns None if no candidate scores above TOO_HARD threshold.
    """
    if not candidates:
        return None

    scored = []
    for c in candidates:
        s = score_candidate(c, db)
        c["score"] = s
        c["confidence"] = classify_confidence(s)
        scored.append(c)

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    best = scored[0]
    if best["score"] < LOW_THRESHOLD:
        return None

    return best
