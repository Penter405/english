"""
Root Word Explorer — Local CLI App (v2)

A command-line tool for exploring English word origins
through linguistic data and Indo-European sound change rules.

Usage:
    python3 main.py                    # Interactive mode
    python3 main.py analyze <word>     # Analyze a single word
    python3 main.py family <root>      # Show word family for a root
    python3 main.py rules              # Show all 6 sound change rules
    python3 main.py stats              # Show database statistics
"""

import sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
import os
import json

# Add the api/ directory to path so we can reuse the engine
API_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "api")
sys.path.insert(0, API_DIR)

from decomposer import Decomposer
from sound_rules import get_all_rules
from models import DEFAULT_DB_PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from affix_search import search_words

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Word part colors (matching the web UI)
    ROOT = "\033[38;5;214m"        # Orange
    PREFIX = "\033[38;5;42m"       # Green
    SUFFIX = "\033[38;5;205m"      # Pink
    ORIGIN = "\033[38;5;44m"       # Cyan
    RULE = "\033[38;5;141m"        # Purple
    HEADER = "\033[38;5;111m"      # Light blue
    MUTED = "\033[38;5;245m"       # Gray


def print_header():
    """Print the app header."""
    print()
    print(f"{Colors.HEADER}{Colors.BOLD}╔══════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}║     🔤  Root Word Explorer  🔤           ║{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}║   Indo-European Sound Change Rules       ║{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}╚══════════════════════════════════════════╝{Colors.RESET}")
    print()


def print_analysis(result: dict):
    """Print word analysis results in a formatted way."""
    word = result["word"]

    # Confidence badge
    conf = result.get("confidence", "")
    search_time = result.get("search_time", 0)
    time_str = f" ({search_time:.3f}s)" if search_time else ""

    if not result.get("found"):
        print(f"\n  {Colors.MUTED}❌ {result.get('message', f'No decomposition found for \"{word}\"')}{Colors.RESET}")
        print(f"  {Colors.DIM}Confidence: TOO_HARD{time_str}{Colors.RESET}")
        print(f"  {Colors.DIM}Try an AI assistant for a deeper etymological explanation.{Colors.RESET}")
        return

    # Confidence line
    conf_colors = {
        "HIGH_CONFIDENCE": Colors.PREFIX,
        "MEDIUM_CONFIDENCE": Colors.ROOT,
        "LOW_CONFIDENCE": Colors.SUFFIX,
    }
    conf_color = conf_colors.get(conf, Colors.MUTED)
    print(f"\n  {conf_color}⬤ {conf.replace('_', ' ').title()}{Colors.RESET}{Colors.DIM}{time_str}{Colors.RESET}")

    # Simple word banner
    if result.get("is_simple_word"):
        print(f"\n  {Colors.ORIGIN}{Colors.BOLD}💡 \"{word}\" is a simple root word.{Colors.RESET}")
        print(f"  {Colors.ORIGIN}It evolved into the following roots through sound changes:{Colors.RESET}")

    # Word decomposition
    components = result.get("components", [])
    if components:
        print(f"\n  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
        print(f"  {Colors.BOLD}Word Decomposition{Colors.RESET}")
        print(f"  {Colors.MUTED}{'─' * 44}{Colors.RESET}")

        # Visual breakdown
        parts = []
        meanings = []
        for comp in components:
            t = comp["type"]
            text = comp["text"]
            meaning = comp["meaning"]
            zh = comp.get("meaning_zh", "")

            if t == "root":
                parts.append(f"{Colors.ROOT}{Colors.BOLD}{text}{Colors.RESET}")
                label = f"{Colors.ROOT}{text}{Colors.RESET} = {meaning}"
            elif t == "prefix":
                parts.append(f"{Colors.PREFIX}{Colors.BOLD}{text}{Colors.RESET}")
                label = f"{Colors.PREFIX}{text}{Colors.RESET} = {meaning}"
            elif t == "suffix":
                parts.append(f"{Colors.SUFFIX}{Colors.BOLD}{text}{Colors.RESET}")
                label = f"{Colors.SUFFIX}{text}{Colors.RESET} = {meaning}"
            elif t == "simple_word":
                parts.append(f"{Colors.ORIGIN}{Colors.BOLD}{text}{Colors.RESET}")
                label = f"{Colors.ORIGIN}{text}{Colors.RESET} = {meaning}"
            else:
                parts.append(text)
                label = f"{text} = {meaning}"

            if zh:
                label += f" ({zh})"
            meanings.append(f"    {label}")

        segment_str = f" {Colors.MUTED}+{Colors.RESET} ".join(parts)
        print(f"\n  {segment_str}")
        print()
        for m in meanings:
            print(m)

    # Origin trace
    traces = result.get("origin_trace", [])
    if traces:
        print(f"\n  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
        title = "🔗 Roots Evolved From This Word" if result.get("is_simple_word") else "🔍 Root Origins"
        print(f"  {Colors.BOLD}{title}{Colors.RESET}")
        print(f"  {Colors.MUTED}{'─' * 44}{Colors.RESET}")

        for trace in traces:
            origin = trace.get("origin_word", "") or trace.get("root", "")
            root = trace.get("root", "")
            rule = trace.get("rule", "")
            rule_name = trace.get("rule_name", "")
            explanation = trace.get("explanation", "") or trace.get("meaning", "")
            language = trace.get("language", "")

            # Build rule/language badge
            if rule:
                badge = f"{Colors.RULE}[Rule {rule}: {rule_name}]{Colors.RESET}"
            elif language:
                badge = f"{Colors.RULE}[{language}]{Colors.RESET}"
            else:
                badge = ""

            print(f"\n    {Colors.ORIGIN}{Colors.BOLD}{origin}{Colors.RESET}"
                  f" {Colors.MUTED}→{Colors.RESET} "
                  f"{Colors.ROOT}{Colors.BOLD}{root}{Colors.RESET}"
                  f"  {badge}")
            if explanation:
                print(f"    {Colors.DIM}{explanation}{Colors.RESET}")

    # Friend words (from root-level BFS search)
    friend_words = result.get("friend_words", [])
    if friend_words:
        print(f"\n  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
        print(f"  {Colors.BOLD}✨ Friend Words (Root Sound Change Search){Colors.RESET}")
        print(f"  {Colors.MUTED}{'─' * 44}{Colors.RESET}")

        # Group friend words by their source root
        by_root = {}
        for fw in friend_words:
            root_src = fw.get('from_root', '?')
            by_root.setdefault(root_src, []).append(fw)

        for root_src, friends in by_root.items():
            print(f"\n    {Colors.ROOT}{Colors.BOLD}from root '{root_src}':{Colors.RESET}")
            for fw in friends[:10]:  # Limit per root
                friend = fw.get('basic_word', fw.get('friend', ''))
                path_display = fw.get('path_display', '')
                rules = fw.get('rules_used', '')
                print(f"      {Colors.ORIGIN}{Colors.BOLD}{friend}{Colors.RESET}"
                      f"  {Colors.DIM}({path_display}){Colors.RESET}")
                if rules:
                    print(f"        {Colors.RULE}{rules}{Colors.RESET}")

    # Word families
    families = result.get("word_family", {})
    if families:
        print(f"\n  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
        print(f"  {Colors.BOLD}🌳 Word Family{Colors.RESET}")
        print(f"  {Colors.MUTED}{'─' * 44}{Colors.RESET}")

        for root_key, family in families.items():
            meaning = family["meaning"]
            words = family.get("derived_words", [])
            print(f"\n    {Colors.ROOT}📚 {root_key}{Colors.RESET} ({meaning}):")
            # Print words in rows of 4
            for i in range(0, len(words), 4):
                row = words[i:i + 4]
                formatted = "  ".join(f"{Colors.MUTED}{w}{Colors.RESET}" for w in row)
                print(f"      {formatted}")

    print()


def print_rules():
    """Print all 6 sound change rules."""
    rules = get_all_rules()
    print(f"\n  {Colors.MUTED}{'─' * 50}{Colors.RESET}")
    print(f"  {Colors.BOLD}📖 The 6 Sound Interchange Rules (六大口訣){Colors.RESET}")
    print(f"  {Colors.MUTED}{'─' * 50}{Colors.RESET}")

    for rule in rules:
        group_str = " ↔ ".join(rule["group"])
        print(f"\n  {Colors.RULE}{Colors.BOLD}[{rule['id']}] {rule['name']}{Colors.RESET}")
        print(f"      {Colors.MUTED}{rule['name_zh']}{Colors.RESET}")
        print(f"      {Colors.BOLD}{group_str}{Colors.RESET}")
        print(f"      {Colors.DIM}{rule['description']}{Colors.RESET}")
        examples = ", ".join(rule["examples"])
        print(f"      {Colors.MUTED}Examples: {examples}{Colors.RESET}")

    print()


def print_stats(decomposer: Decomposer):
    """Print database statistics."""
    print(f"\n  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
    print(f"  {Colors.BOLD}📊 Database Statistics{Colors.RESET}")
    print(f"  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
    print(f"  Engine version: {Colors.BOLD}{Decomposer.ENGINE_VERSION}{Colors.RESET}")
    print(f"  Database: {Colors.BOLD}{'SQLite ✓' if decomposer.db else 'Legacy JSON'}{Colors.RESET}")
    if decomposer.db:
        stats = decomposer.db.get_stats()
        for table, count in stats.items():
            print(f"    {Colors.MUTED}{table:.<25}{Colors.RESET} {Colors.BOLD}{count:>10,}{Colors.RESET}")
    print()


def execute_search(tokens: list):
    """
    Search vocabulary with prefix, postfix, and POS compound filters.
    Usage examples:
        search com* verb
        search com* *te verb
        search un* *able adj
        search *tion noun
    """
    prefix = None
    postfix = None
    pos = None

    pos_keywords = {"v", "verb", "n", "noun", "adj", "a", "adv", "r", "prep", "conj", "pron"}

    for tok in tokens:
        t = tok.strip()
        if t.lower() in pos_keywords:
            pos = t.lower()
        elif t.startswith("*") and len(t) > 1:
            postfix = t
        elif t.endswith("*") and len(t) > 1:
            prefix = t
        elif prefix is None:
            prefix = t
        elif postfix is None:
            postfix = t
        elif pos is None:
            pos = t

    results = search_words(prefix=prefix, postfix=postfix, pos=pos)
    print(f"\n  {Colors.BOLD}🔍 Compound Affix Search Results{Colors.RESET}")
    filters = []
    if prefix: filters.append(f"Prefix: {Colors.PREFIX}{prefix}{Colors.RESET}")
    if postfix: filters.append(f"Postfix: {Colors.SUFFIX}{postfix}{Colors.RESET}")
    if pos: filters.append(f"POS: {Colors.ROOT}{pos}{Colors.RESET}")
    print(f"  Filters: {' | '.join(filters) if filters else 'All words'}")
    print(f"  Found {Colors.BOLD}{len(results)}{Colors.RESET} matching words:\n")

    for idx, r in enumerate(results[:25], start=1):
        zh_str = r['zh'][0] if r['zh'] else ""
        roots_info = ""
        if r.get('root_breakdown'):
            syn = r['root_breakdown'].get('synthesis_zh') or r['root_breakdown'].get('synthesis_en')
            if syn:
                roots_info = f" {Colors.MUTED}➔ {syn}{Colors.RESET}"
        
        exam_badge = f"{Colors.ORIGIN}📝{r['total_appear']}{Colors.RESET}" if r['total_appear'] > 0 else ""
        print(f"   {idx:2}. {Colors.BOLD}{r['word']:14}{Colors.RESET} [Lv{r['level']}] {exam_badge} {r['pos']} {zh_str[:25]}{roots_info}")

    if len(results) > 25:
        print(f"\n  {Colors.MUTED}... and {len(results) - 25} more words{Colors.RESET}")
    print()


def interactive_mode(decomposer: Decomposer):
    """Run in interactive mode."""
    print_header()
    print(f"  {Colors.MUTED}Type a word to analyze, or use commands:{Colors.RESET}")
    print(f"  {Colors.MUTED}  search <pfx*> <*sfx> <pos> — compound search (e.g. search com* verb){Colors.RESET}")
    print(f"  {Colors.MUTED}  rules      — show the 6 sound change rules{Colors.RESET}")
    print(f"  {Colors.MUTED}  family <r> — show word family for root <r>{Colors.RESET}")
    print(f"  {Colors.MUTED}  stats      — show database statistics{Colors.RESET}")
    print(f"  {Colors.MUTED}  quit       — exit{Colors.RESET}")
    print()

    while True:
        try:
            user_input = input(f"  {Colors.HEADER}▶{Colors.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {Colors.MUTED}Goodbye!{Colors.RESET}\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print(f"\n  {Colors.MUTED}Goodbye!{Colors.RESET}\n")
            break

        if user_input.lower() == "rules":
            print_rules()
            continue

        if user_input.lower() == "stats":
            print_stats(decomposer)
            continue

        if user_input.lower().startswith("search "):
            tokens = user_input[7:].strip().split()
            execute_search(tokens)
            continue

        if user_input.lower().startswith("family "):
            root = user_input[7:].strip()
            result = decomposer.get_word_family(root)
            if result.get("found"):
                print(f"\n    {Colors.ROOT}📚 {result['root']}{Colors.RESET} ({result.get('meaning', '')})")
                origin = result.get('origin_word', '')
                explanation = result.get('explanation', '')
                if origin:
                    print(f"    {Colors.MUTED}Origin: {origin} — {explanation}{Colors.RESET}")
                elif explanation:
                    print(f"    {Colors.MUTED}{explanation}{Colors.RESET}")
                words = result.get("derived_words", [])
                for i in range(0, len(words), 4):
                    row = words[i:i + 4]
                    formatted = "  ".join(f"{Colors.MUTED}{w}{Colors.RESET}" for w in row)
                    print(f"      {formatted}")
                print()
            else:
                print(f"  {Colors.MUTED}❌ Root '{root}' not found{Colors.RESET}\n")
            continue

        # Default: analyze word
        result = decomposer.decompose(user_input)
        print_analysis(result)


def execute_origin_lookup(word: str):
    """Lookup origin and all variants for a word."""
    origins_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database", "word_origins.json")
    if not os.path.exists(origins_path):
        print("Error: database/word_origins.json not found.")
        return
    with open(origins_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    word_lower = word.lower().strip()
    word_info = data.get("words", {}).get(word_lower)
    orig_key = word_info.get("origin", word_lower) if word_info else word_lower
    orig_info = data.get("origins", {}).get(orig_key)

    if not orig_info and not word_info:
        print(f"\n  ❌ No origin information found for '{word}'\n")
        return

    orig_zh = orig_info.get("meaning_zh", "") if orig_info else ""
    orig_pos = orig_info.get("pos", []) if orig_info else []
    pos_str = f"[{', '.join(orig_pos)}]" if orig_pos else ""
    rel = word_info.get("relation", "0: 原型 (lemma)") if word_info else "原型 (lemma)"

    print(f"\n  {Colors.BOLD}🌱 Word Origin & Variants Lookup{Colors.RESET}")
    print(f"  Target Word : {Colors.ORIGIN}{Colors.BOLD}{word_lower}{Colors.RESET} ({rel})")
    print(f"  Origin Base : {Colors.ROOT}{Colors.BOLD}{orig_key}{Colors.RESET} {pos_str} {orig_zh}")

    variants = orig_info.get("variants", []) if orig_info else []
    if variants:
        print(f"  Variants ({len(variants)}):")
        for i, v in enumerate(variants, 1):
            vw = v.get("word", "")
            vpos = f"[{'/'.join(v.get('pos', []))}]" if v.get("pos") else ""
            vrel = v.get("relation", "")
            is_cur = " ➔ (Current)" if vw == word_lower else ""
            print(f"    {i:2d}. {vw:<16} {vpos:<10} {vrel}{is_cur}")
    print()


def main():
    # Use SQLite database if available, otherwise fall back to JSON
    db_path = DEFAULT_DB_PATH if os.path.exists(DEFAULT_DB_PATH) else os.path.join(API_DIR, "word_database.json")
    decomposer = Decomposer(db_path)

    if len(sys.argv) < 2:
        interactive_mode(decomposer)
        return

    command = sys.argv[1].lower()

    if command == "analyze" and len(sys.argv) >= 3:
        word = sys.argv[2]
        result = decomposer.decompose(word)
        print_analysis(result)

    elif command == "family" and len(sys.argv) >= 3:
        root = sys.argv[2]
        result = decomposer.get_word_family(root)
        if result.get("found"):
            print(f"\n  📚 {result.get('root', root)} ({result.get('meaning', '')})")
            origin = result.get('origin_word', '')
            explanation = result.get('explanation', '')
            if origin:
                print(f"  Origin: {origin} — {explanation}")
            elif explanation:
                print(f"  {explanation}")
            for w in result.get("derived_words", []):
                print(f"    • {w}")
            print()
        else:
            print(f"  Root '{root}' not found")

    elif command == "search":
        execute_search(sys.argv[2:])

    elif command in ("origin", "variants") and len(sys.argv) >= 3:
        execute_origin_lookup(sys.argv[2])

    elif command == "rules":
        print_rules()

    elif command == "stats":
        print_stats(decomposer)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()

