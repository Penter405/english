import json
from collections import Counter

with open("topic_vocabulary_5000.json", encoding="utf-8") as f:
    data = json.load(f)

all_words = []
unique_words = set()

for g in data["groups"]:
    words = g["levels"]["easy"] + g["levels"]["medium"] + g["levels"]["hard"]
    all_words.extend(words)
    unique_words.update(words)

print(f"Total word entries: {len(all_words)}")
print(f"Unique words across ALL groups: {len(unique_words)}")

word_counts = Counter(all_words)
print(f"\nTop 20 most repeated words:")
for w, c in word_counts.most_common(20):
    print(f"  {w}: {c}x")

seen = {}
dupes = 0
for g in data["groups"]:
    key = tuple(sorted(g["levels"]["easy"] + g["levels"]["medium"] + g["levels"]["hard"]))
    if key in seen:
        dupes += 1
        print(f"DUPE: Group {g['id']} ({g['topic']}) = Group {seen[key][0]} ({seen[key][1]})")
    else:
        seen[key] = (g["id"], g["topic"])

print(f"\nTotal groups with identical word sets: {dupes}")
