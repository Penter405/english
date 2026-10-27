"""
Generate exam_stats.json — overall statistics summary.

Reads: database/exam_words.json
Writes: database/exam_stats.json
"""
import json
import os
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM_WORDS_PATH = os.path.join(PROJECT_ROOT, "database", "exam_words.json")
STATS_PATH = os.path.join(PROJECT_ROOT, "database", "exam_stats.json")

with open(EXAM_WORDS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

vocab = data["words"]
meta = data["meta"]

# ---------------------------------------------------------------------------
# Build stats
# ---------------------------------------------------------------------------
stats = {
    "meta": {
        "version": 1,
        "generated": meta["updated"],
        "source": "exam_words.json",
    },
    "overview": {
        "total_words": meta["word_count"],
        "words_appeared_in_exams": sum(1 for v in vocab.values() if v["appear_year_count"] > 0),
        "words_never_appeared": sum(1 for v in vocab.values() if v["appear_year_count"] == 0),
        "exam_years": meta["exam_years"],
        "total_exam_years": len(meta["exam_years"]),
    },
    "level_breakdown": {},
    "year_breakdown": {},
    "top_content_words": [],
    "words_all_years": [],
    "high_level_frequent": [],
}

# Common function words to exclude from "interesting" rankings
FUNCTION_WORDS = {
    "the", "be", "to", "of", "in", "and", "for", "have", "do", "that",
    "on", "can", "much", "what", "about", "with", "not", "from", "at",
    "which", "how", "a", "this", "will", "like", "use", "but", "or",
    "it", "an", "as", "if", "so", "by", "all", "no", "up", "out",
    "their", "other", "than", "also", "just", "only", "very", "should",
    "would", "could", "may", "might", "must", "shall", "i", "he", "she",
    "we", "they", "you", "me", "him", "her", "them", "who", "where",
    "there", "here", "then", "when", "while", "some", "each", "every",
    "most", "more", "such", "even", "still", "own", "one", "two",
}

# Level breakdown
for level in range(1, 7):
    level_words = {w: info for w, info in vocab.items() if info["level"] == level}
    appeared = sum(1 for info in level_words.values() if info["appear_year_count"] > 0)
    total_at_level = len(level_words)
    avg_appear = (
        sum(info["total_appear"] for info in level_words.values() if info["appear_year_count"] > 0) / appeared
        if appeared > 0 else 0
    )
    stats["level_breakdown"][str(level)] = {
        "total_words": total_at_level,
        "appeared_in_exams": appeared,
        "appearance_rate": round(appeared / total_at_level * 100, 1) if total_at_level else 0,
        "avg_total_appear": round(avg_appear, 1),
    }

# Year breakdown
for year in meta["exam_years"]:
    year_words = {w: info for w, info in vocab.items() if year in info["appear_year"]}
    year_source_count = sum(
        s["count"] for info in year_words.values() for s in info["sources"] if s["year"] == year
    )
    stats["year_breakdown"][str(year)] = {
        "unique_words": len(year_words),
        "total_occurrences": year_source_count,
    }

# Top content words (exclude function words)
content_words = [
    {"word": w, "level": info["level"], "total_appear": info["total_appear"],
     "appear_year_count": info["appear_year_count"]}
    for w, info in vocab.items()
    if info["total_appear"] > 0 and w not in FUNCTION_WORDS and len(w) > 2
]
content_words.sort(key=lambda x: x["total_appear"], reverse=True)
stats["top_content_words"] = content_words[:50]

# Words appearing in all years
all_year_words = [
    {"word": w, "level": info["level"], "total_appear": info["total_appear"]}
    for w, info in vocab.items()
    if info["appear_year_count"] == len(meta["exam_years"]) and w not in FUNCTION_WORDS and len(w) > 2
]
all_year_words.sort(key=lambda x: x["total_appear"], reverse=True)
stats["words_all_years"] = all_year_words

# High-level words (level 4+) that appear frequently
high_level = [
    {"word": w, "level": info["level"], "total_appear": info["total_appear"],
     "appear_year_count": info["appear_year_count"]}
    for w, info in vocab.items()
    if info["level"] >= 4 and info["total_appear"] >= 3
]
high_level.sort(key=lambda x: x["total_appear"], reverse=True)
stats["high_level_frequent"] = high_level[:50]

# Write stats
with open(STATS_PATH, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print(f"Wrote stats to: {STATS_PATH}")
print(f"\nOverview: {json.dumps(stats['overview'], indent=2)}")
print(f"\nLevel breakdown:")
for level, info in stats["level_breakdown"].items():
    print(f"  Level {level}: {info['appeared_in_exams']}/{info['total_words']} ({info['appearance_rate']}%) avg={info['avg_total_appear']}")

