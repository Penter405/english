import json

with open("/home/penter405/github/english/topic_vocabulary_5000_graph.json", encoding="utf-8") as f:
    data = json.load(f)

with open("/home/penter405/github/english/graph.json", "w", encoding="utf-8") as f:
    json.dump({"graph": data["graph"]}, f, ensure_ascii=False, indent=2)