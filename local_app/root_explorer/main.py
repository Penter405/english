"""
Root Word Explorer — Local CLI App

A command-line tool for exploring English word origins
through Indo-European sound change rules.

Usage:
    python3 main.py                    # Interactive mode
    python3 main.py analyze <word>     # Analyze a single word
    python3 main.py family <root>      # Show word family for a root
    python3 main.py rules              # Show all 6 sound change rules
"""

import sys
import os
import json

# Add the api/ directory to path so we can reuse the engine
API_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "api")
sys.path.insert(0, API_DIR)

from decomposer import Decomposer
from sound_rules import get_all_rules

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

    if not result.get("found"):
        print(f"\n  {Colors.MUTED}❌ {result.get('message', f'No decomposition found for \"{word}\"')}{Colors.RESET}")
        return

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
            origin = trace["origin_word"]
            root = trace["root"]
            rule = trace.get("rule", "")
            rule_name = trace.get("rule_name", "")
            explanation = trace.get("explanation", "")

            print(f"\n    {Colors.ORIGIN}{Colors.BOLD}{origin}{Colors.RESET}"
                  f" {Colors.MUTED}→{Colors.RESET} "
                  f"{Colors.ROOT}{Colors.BOLD}{root}{Colors.RESET}"
                  f"  {Colors.RULE}[Rule {rule}: {rule_name}]{Colors.RESET}")
            print(f"    {Colors.DIM}{explanation}{Colors.RESET}")

    # Friend words (from sound change search)
    friend_words = result.get("friend_words", [])
    if friend_words:
        print(f"\n  {Colors.MUTED}{'─' * 44}{Colors.RESET}")
        print(f"  {Colors.BOLD}✨ Friend Words (Sound Change Search){Colors.RESET}")
        print(f"  {Colors.MUTED}{'─' * 44}{Colors.RESET}")

        for fw in friend_words:
            print(f"\n    {Colors.ORIGIN}{Colors.BOLD}{fw['path_display']}{Colors.RESET}")
            if fw['rules_used']:
                print(f"    {Colors.DIM}{fw['rules_used']}{Colors.RESET}")
            else:
                print(f"    {Colors.DIM}Basic Word (Direct Match){Colors.RESET}")

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


def interactive_mode(decomposer: Decomposer):
    """Run in interactive mode."""
    print_header()
    print(f"  {Colors.MUTED}Type a word to analyze, or use commands:{Colors.RESET}")
    print(f"  {Colors.MUTED}  rules      — show the 6 sound change rules{Colors.RESET}")
    print(f"  {Colors.MUTED}  family <r> — show word family for root <r>{Colors.RESET}")
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

        if user_input.lower().startswith("family "):
            root = user_input[7:].strip()
            result = decomposer.get_word_family(root)
            if result.get("found"):
                print(f"\n    {Colors.ROOT}📚 {result['root']}{Colors.RESET} ({result['meaning']})")
                print(f"    {Colors.MUTED}Origin: {result['origin_word']} — {result['explanation']}{Colors.RESET}")
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


def main():
    db_path = os.path.join(API_DIR, "word_database.json")
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
            print(f"\n  📚 {result['root']} ({result['meaning']})")
            print(f"  Origin: {result['origin_word']} — {result['explanation']}")
            for w in result.get("derived_words", []):
                print(f"    • {w}")
            print()
        else:
            print(f"  Root '{root}' not found")

    elif command == "rules":
        print_rules()

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
