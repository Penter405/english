"""
Sound Change Rules Engine

Implements the 6 Indo-European sound interchange rules from logic_word.txt.
Used to validate and discover relationships between simple English words and Latin/Greek roots.
"""

from typing import List, Tuple, Set

# The 6 interchange groups
RULES = {
    1: {
        "name": "Vowel interchange",
        "name_zh": "元音互換",
        "group": set("aeiouy"),  # w is handled in rule 2
        "description": "Vowels (a, e, i, o, u, y) can interchange without changing the core meaning",
        "description_zh": "元音字母（a, e, i, o, u, y）之間的互換不影響核心本意",
        "examples": ["one → uni", "same → sim", "big → bag", "rest → rust"]
    },
    2: {
        "name": "u-v-w interchange",
        "name_zh": "u-v-w 互換",
        "group": set("uvw"),
        "description": "u, v, and w are historically interchangeable",
        "description_zh": "u、v、w 在歷史上可以互換",
        "examples": ["new → nov", "will → vol", "whirl → vers"]
    },
    3: {
        "name": "g-k-h (哥科呵) interchange",
        "name_zh": "g-k-h（哥科呵）互換",
        "group": set("gkhcj"),  # c often sounds like k, j related to g
        "description": "g, k, h (and c) have similar mouth positions and interchange easily",
        "description_zh": "g、k、h（及c）發音口型相似，極易互換",
        "examples": ["glue → clue", "horn → corn", "heart → cred"]
    },
    4: {
        "name": "d-t-s (德特斯) interchange",
        "name_zh": "d-t-s（德特斯）互換",
        "group": set("dts"),
        "description": "d, t, and s share the same tongue position, differing only in airflow",
        "description_zh": "d、t、s 發音時舌尖位置相同，僅氣流強弱有別",
        "examples": ["tooth → dent", "see → vid/wis", "send → mit"]
    },
    5: {
        "name": "m-n-l-r (摩諾勒日) interchange",
        "name_zh": "m-n-l-r（摩諾勒日）互換",
        "group": set("mnlr"),
        "description": "Nasal and liquid consonants (m, n, l, r) interchange in evolution",
        "description_zh": "鼻音、捲舌音（m、n、l、r）在演變中產生互換",
        "examples": ["sun → sol", "moon → lun"]
    },
    6: {
        "name": "b-p-m-f-v (波破莫分屋) interchange",
        "name_zh": "b-p-m-f-v（波破莫分屋）互換",
        "group": set("bpmfv"),
        "description": "Labial consonants (b, p, m, f, v) are lip sounds that easily transform",
        "description_zh": "雙唇音、唇齒音（b、p、m、f、v）同屬唇音，極易轉化",
        "examples": ["fine → bene", "pen → fin", "bear → port"]
    }
}


def get_interchange_group(char: str) -> List[int]:
    """Find which interchange rule(s) a character belongs to."""
    char = char.lower()
    groups = []
    for rule_id, rule in RULES.items():
        if char in rule["group"]:
            groups.append(rule_id)
    return groups


def are_interchangeable(char1: str, char2: str) -> List[int]:
    """Check if two characters can interchange under any rule. Returns matching rule IDs."""
    char1 = char1.lower()
    char2 = char2.lower()
    if char1 == char2:
        return list(range(1, 7))  # Same char always matches
    
    matching_rules = []
    for rule_id, rule in RULES.items():
        if char1 in rule["group"] and char2 in rule["group"]:
            matching_rules.append(rule_id)
    return matching_rules


def compute_similarity_score(word1: str, word2: str) -> Tuple[float, List[dict]]:
    """
    Compute how similar two words are based on sound-change rules.
    Returns a score (0-1) and the list of transformations.
    
    This uses a simple alignment approach comparing characters position by position.
    """
    word1 = word1.lower()
    word2 = word2.lower()
    
    # Handle different lengths by aligning from the start
    min_len = min(len(word1), len(word2))
    max_len = max(len(word1), len(word2))
    
    if min_len == 0:
        return 0.0, []
    
    transformations = []
    matches = 0
    
    for i in range(min_len):
        c1 = word1[i]
        c2 = word2[i]
        rules = are_interchangeable(c1, c2)
        if rules:
            matches += 1
            if c1 != c2:
                transformations.append({
                    "position": i,
                    "from": c1,
                    "to": c2,
                    "rules": rules,
                    "rule_names": [RULES[r]["name"] for r in rules]
                })
    
    # Penalize length differences (vowel drops/additions are common but not free)
    length_penalty = (max_len - min_len) * 0.1
    score = max(0, (matches / max_len) - length_penalty)
    
    return score, transformations


def get_all_rules() -> List[dict]:
    """Return all rules in a JSON-serializable format."""
    result = []
    for rule_id, rule in RULES.items():
        result.append({
            "id": rule_id,
            "name": rule["name"],
            "name_zh": rule["name_zh"],
            "group": sorted(list(rule["group"])),
            "description": rule["description"],
            "description_zh": rule["description_zh"],
            "examples": rule["examples"]
        })
    return result
