"""Generate individual group JSON files and copy graph data to docs/data/ for GitHub Pages."""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, 'topic_vocabulary_5000.json'), encoding='utf-8') as f:
    vocab = json.load(f)

os.makedirs(os.path.join(BASE, 'docs', 'data', 'groups'), exist_ok=True)

for group in vocab['groups']:
    gid = group['id']
    path = os.path.join(BASE, 'docs', 'data', 'groups', f'group_{gid:03d}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(group, f, ensure_ascii=False, indent=2)
    print(f'Wrote {path}')

with open(os.path.join(BASE, 'topic_vocabulary_graph.json'), encoding='utf-8') as f:
    graph = json.load(f)

with open(os.path.join(BASE, 'docs', 'data', 'graph.json'), 'w', encoding='utf-8') as f:
    json.dump(graph, f, ensure_ascii=False, indent=2)

print('Done!')
