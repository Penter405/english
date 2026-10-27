"""
Upgrade word_database.json with comprehensive roots and affixes.

Reads existing database, adds ~60 new roots and missing affixes,
writes the upgraded file to database/word_database.json.

Also updates api/word_database.json to keep both in sync.
"""
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "database", "word_database.json")
API_PATH = os.path.join(PROJECT_ROOT, "api", "word_database.json")

# -----------------------------------------------------------------------
# NEW ROOTS to add (not already in the database)
# -----------------------------------------------------------------------
NEW_ROOTS = {
    # --- Latin roots ---
    "aud": {
        "meaning": "hear",
        "meaning_zh": "聽",
        "origin_word": "hear",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "hear → aud (h↔silent, vowel change)",
        "derived_words": ["audience", "audio", "auditorium", "audition", "audit", "audible", "inaudible"]
    },
    "dict": {
        "meaning": "speak/say",
        "meaning_zh": "說/講",
        "origin_word": "say",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "say → dict (s↔d interchange)",
        "derived_words": ["dictionary", "dictate", "predict", "contradict", "verdict", "indicate", "dedicate"]
    },
    "loc": {
        "meaning": "place",
        "meaning_zh": "地方",
        "origin_word": "lay",
        "rule": 5,
        "rule_name": "m-n-l-r interchange",
        "explanation": "lay → loc (related placement root)",
        "derived_words": ["local", "locate", "location", "allocate", "locomotive", "dislocate", "relocate"]
    },
    "mov": {
        "meaning": "move",
        "meaning_zh": "移動",
        "origin_word": "move",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "move → mov (direct cognate)",
        "derived_words": ["move", "movement", "remove", "remote", "motor", "motion", "mobile", "promote", "emotion"]
    },
    "nat": {
        "meaning": "born/nature",
        "meaning_zh": "出生/自然",
        "origin_word": "born",
        "rule": 5,
        "rule_name": "m-n-l-r interchange",
        "explanation": "born → nat (b↔n labial shift)",
        "derived_words": ["nature", "natural", "nation", "native", "innate", "prenatal", "supernatural"]
    },
    "path": {
        "meaning": "feeling/suffering",
        "meaning_zh": "感覺/痛苦",
        "origin_word": "feel",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "feel → path (f↔p interchange, Greek origin)",
        "derived_words": ["sympathy", "empathy", "apathy", "pathetic", "passion", "patient", "compassion", "antipathy"]
    },
    "ped": {
        "meaning": "foot",
        "meaning_zh": "腳",
        "origin_word": "foot",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "foot → ped (f↔p interchange, t↔d)",
        "derived_words": ["pedestrian", "pedal", "expedition", "impede", "centipede", "pedicure", "biped"]
    },
    "man": {
        "meaning": "hand",
        "meaning_zh": "手",
        "origin_word": "hand",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "hand → man (h↔silent, d↔n interchange)",
        "derived_words": ["manual", "manage", "manner", "manipulate", "manifest", "manuscript", "manufacture", "command"]
    },
    "gen": {
        "meaning": "birth/kind/race",
        "meaning_zh": "出生/種類",
        "origin_word": "kin",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "kin → gen (k↔g interchange)",
        "derived_words": ["generate", "generation", "gene", "gender", "generous", "genius", "genuine", "gentle", "general", "generic"]
    },
    "lect": {
        "meaning": "read/gather/choose",
        "meaning_zh": "閱讀/收集/選擇",
        "origin_word": "gather",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "gather → lect (g↔l shift via Latin legere)",
        "derived_words": ["collect", "select", "elect", "lecture", "intellect", "dialect", "neglect", "recollect"]
    },
    "struct": {
        "meaning": "build",
        "meaning_zh": "建造",
        "origin_word": "strew",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "strew → struct (related building/laying root)",
        "derived_words": ["structure", "construct", "destroy", "instruct", "obstruct", "infrastructure", "restructure"]
    },
    "form": {
        "meaning": "shape",
        "meaning_zh": "形狀",
        "origin_word": "form",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "form (direct Latin cognate)",
        "derived_words": ["inform", "reform", "perform", "transform", "uniform", "formal", "formula", "platform", "conform"]
    },
    "pos": {
        "meaning": "put/place",
        "meaning_zh": "放置",
        "origin_word": "put",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "put → pos (related placement root)",
        "derived_words": ["position", "compose", "dispose", "expose", "impose", "oppose", "propose", "purpose", "suppose", "deposit"]
    },
    "press": {
        "meaning": "push/squeeze",
        "meaning_zh": "壓/擠",
        "origin_word": "press",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "press (direct Latin cognate)",
        "derived_words": ["express", "impress", "compress", "depress", "suppress", "pressure", "impression"]
    },
    "clar": {
        "meaning": "clear/bright",
        "meaning_zh": "清楚/明亮",
        "origin_word": "clear",
        "rule": 5,
        "rule_name": "m-n-l-r interchange",
        "explanation": "clear → clar (vowel shift)",
        "derived_words": ["clear", "clarify", "clarity", "declare", "declaration"]
    },
    "cur": {
        "meaning": "care/run",
        "meaning_zh": "照顧/跑",
        "origin_word": "care",
        "rule": 1,
        "rule_name": "Vowel interchange",
        "explanation": "care → cur (a↔u vowel interchange)",
        "derived_words": ["cure", "curious", "accurate", "occur", "current", "currency", "excursion", "secure", "procure"]
    },
    "fid": {
        "meaning": "faith/trust",
        "meaning_zh": "信仰/信任",
        "origin_word": "faith",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "faith → fid (related trust root)",
        "derived_words": ["confident", "confide", "fidelity", "infidel", "affidavit", "fiduciary"]
    },
    "flu": {
        "meaning": "flow",
        "meaning_zh": "流動",
        "origin_word": "flow",
        "rule": 2,
        "rule_name": "u-v-w interchange",
        "explanation": "flow → flu (w↔u interchange)",
        "derived_words": ["fluid", "fluent", "influence", "affluent", "fluctuate", "flush", "influx", "superfluous"]
    },
    "grad": {
        "meaning": "step/walk",
        "meaning_zh": "步/走",
        "origin_word": "stride",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "stride → grad (s↔g, related stepping root)",
        "derived_words": ["grade", "gradual", "graduate", "degrade", "upgrade", "ingredient", "progress"]
    },
    "junct": {
        "meaning": "join",
        "meaning_zh": "連接",
        "origin_word": "yoke",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "yoke → junct (y↔j interchange)",
        "derived_words": ["junction", "conjunction", "adjunct", "injunction", "disjunction"]
    },
    "luc": {
        "meaning": "light",
        "meaning_zh": "光",
        "origin_word": "light",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "light → luc (gh↔c interchange)",
        "derived_words": ["lucid", "translucent", "elucidate", "luminous", "illuminate", "illustrate"]
    },
    "magn": {
        "meaning": "great/large",
        "meaning_zh": "大/偉大",
        "origin_word": "much",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "much → magn (related greatness root)",
        "derived_words": ["magnificent", "magnify", "magnitude", "magnate", "magnet"]
    },
    "plic": {
        "meaning": "fold",
        "meaning_zh": "摺疊",
        "origin_word": "fold",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "fold → plic (f↔p interchange)",
        "derived_words": ["apply", "imply", "reply", "multiply", "complicate", "explicit", "implicit", "duplicate", "replicate"]
    },
    "quer": {
        "meaning": "ask/seek",
        "meaning_zh": "詢問/尋求",
        "origin_word": "ask",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "ask → quer (related seeking root)",
        "derived_words": ["query", "require", "acquire", "inquire", "request", "conquer", "question"]
    },
    "rect": {
        "meaning": "right/straight",
        "meaning_zh": "正確/直",
        "origin_word": "right",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "right → rect (gh↔ct interchange)",
        "derived_words": ["correct", "direct", "erect", "rectangle", "rectify", "director"]
    },
    "sed": {
        "meaning": "sit",
        "meaning_zh": "坐",
        "origin_word": "sit",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "sit → sed (t↔d interchange, vowel change)",
        "derived_words": ["sedentary", "reside", "president", "session", "assess", "possess", "obsess", "settle"]
    },
    "sign": {
        "meaning": "mark/seal",
        "meaning_zh": "標記/符號",
        "origin_word": "sign",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "sign (direct Latin cognate)",
        "derived_words": ["signal", "significant", "design", "assign", "resign", "signature"]
    },
    "simil": {
        "meaning": "like/resemble",
        "meaning_zh": "相似",
        "origin_word": "same",
        "rule": 1,
        "rule_name": "Vowel interchange",
        "explanation": "same → simil (a↔i vowel interchange)",
        "derived_words": ["similar", "assimilate", "simulate", "simultaneous", "facsimile", "resemblance"]
    },
    "sta": {
        "meaning": "stand",
        "meaning_zh": "站立",
        "origin_word": "stand",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "stand → sta (related standing root)",
        "derived_words": ["state", "station", "stable", "establish", "obstacle", "constant", "instant", "substance", "status", "statue", "static"]
    },
    "ten": {
        "meaning": "hold/keep",
        "meaning_zh": "持有/保持",
        "origin_word": "thin",
        "rule": 1,
        "rule_name": "Vowel interchange",
        "explanation": "thin → ten (i↔e vowel interchange, related stretched/held tight)",
        "derived_words": ["contain", "obtain", "maintain", "retain", "sustain", "entertain", "content", "tenant", "tenure", "attention"]
    },
    "vac": {
        "meaning": "empty",
        "meaning_zh": "空",
        "origin_word": "void",
        "rule": 2,
        "rule_name": "u-v-w interchange",
        "explanation": "void → vac (related emptiness root)",
        "derived_words": ["vacant", "vacuum", "vacation", "evacuate", "vacancy"]
    },
    "voc": {
        "meaning": "voice/call",
        "meaning_zh": "聲音/呼叫",
        "origin_word": "voice",
        "rule": 2,
        "rule_name": "u-v-w interchange",
        "explanation": "voice → voc (direct cognate)",
        "derived_words": ["vocal", "vocabulary", "advocate", "provoke", "invoke", "evoke", "revoke", "vocation"]
    },
    "act": {
        "meaning": "do/drive",
        "meaning_zh": "做/驅動",
        "origin_word": "do",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "do → act (related doing root via Latin agere)",
        "derived_words": ["act", "action", "active", "actual", "react", "interact", "exact", "transaction", "agent"]
    },
    "cent": {
        "meaning": "hundred",
        "meaning_zh": "百",
        "origin_word": "hundred",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "hundred → cent (h↔c interchange)",
        "derived_words": ["century", "cent", "percent", "centimeter", "centigrade"]
    },
    "cept": {
        "meaning": "take/receive",
        "meaning_zh": "拿/接收",
        "origin_word": "catch",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "catch → cept (related taking root)",
        "derived_words": ["accept", "concept", "except", "intercept", "perceive", "receive", "deception", "reception"]
    },
    "cide": {
        "meaning": "cut/kill",
        "meaning_zh": "切/殺",
        "origin_word": "cut",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "cut → cide (related cutting root)",
        "derived_words": ["decide", "suicide", "homicide", "pesticide", "coincide", "incision", "concise", "precise"]
    },
    "cogn": {
        "meaning": "know",
        "meaning_zh": "知道",
        "origin_word": "know",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "know → cogn (kn↔gn interchange)",
        "derived_words": ["recognize", "cognitive", "cognition", "incognito", "diagnosis"]
    },
    "cord": {
        "meaning": "heart",
        "meaning_zh": "心",
        "origin_word": "heart",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "heart → cord (h↔c interchange)",
        "derived_words": ["accord", "record", "discord", "courage", "encourage", "discourage", "core", "cordial"]
    },
    "dom": {
        "meaning": "rule/house",
        "meaning_zh": "統治/家",
        "origin_word": "tame",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "tame → dom (t↔d interchange)",
        "derived_words": ["domain", "dominate", "domestic", "dominant", "kingdom", "freedom", "wisdom"]
    },
    "equ": {
        "meaning": "equal/even",
        "meaning_zh": "相等/均勻",
        "origin_word": "even",
        "rule": 2,
        "rule_name": "u-v-w interchange",
        "explanation": "even → equ (v↔qu interchange)",
        "derived_words": ["equal", "equation", "equator", "equivalent", "adequate", "equip", "equilibrium"]
    },
    "fer": {
        "meaning": "carry/bear",
        "meaning_zh": "攜帶/承受",
        "origin_word": "bear",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "bear → fer (b↔f interchange)",
        "derived_words": ["transfer", "refer", "prefer", "offer", "suffer", "differ", "conference", "fertile", "infer"]
    },
    "fus": {
        "meaning": "pour/melt",
        "meaning_zh": "倒/融",
        "origin_word": "pour",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "pour → fus (p↔f interchange)",
        "derived_words": ["confuse", "refuse", "diffuse", "infuse", "transfusion", "fusion", "profuse"]
    },
    "labor": {
        "meaning": "work",
        "meaning_zh": "工作",
        "origin_word": "labor",
        "rule": 5,
        "rule_name": "m-n-l-r interchange",
        "explanation": "labor (direct Latin cognate)",
        "derived_words": ["labor", "laboratory", "collaborate", "elaborate", "laborious"]
    },
    "leg": {
        "meaning": "law/read",
        "meaning_zh": "法律/閱讀",
        "origin_word": "law",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "law → leg (w↔g interchange)",
        "derived_words": ["legal", "legislate", "legislation", "legitimate", "legend", "legacy", "privilege", "illegal"]
    },
    "liber": {
        "meaning": "free",
        "meaning_zh": "自由",
        "origin_word": "free",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "free → liber (f↔l, related freedom root)",
        "derived_words": ["liberty", "liberal", "liberate", "deliberate", "deliver"]
    },
    "mem": {
        "meaning": "remember/mindful",
        "meaning_zh": "記憶",
        "origin_word": "mind",
        "rule": 5,
        "rule_name": "m-n-l-r interchange",
        "explanation": "mind → mem (n↔m interchange)",
        "derived_words": ["memory", "remember", "memorial", "memorize", "memoir", "memorable", "commemorate"]
    },
    "norm": {
        "meaning": "rule/standard",
        "meaning_zh": "規範/標準",
        "origin_word": "norm",
        "rule": 5,
        "rule_name": "m-n-l-r interchange",
        "explanation": "norm (direct Latin cognate)",
        "derived_words": ["normal", "abnormal", "enormous", "norm", "normalize"]
    },
    "ord": {
        "meaning": "order/rank",
        "meaning_zh": "順序/等級",
        "origin_word": "order",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "order → ord (direct Latin cognate)",
        "derived_words": ["order", "ordinary", "extraordinary", "coordinate", "subordinate"]
    },
    "pel": {
        "meaning": "push/drive",
        "meaning_zh": "推/驅動",
        "origin_word": "pull",
        "rule": 1,
        "rule_name": "Vowel interchange",
        "explanation": "pull → pel (u↔e vowel interchange)",
        "derived_words": ["compel", "expel", "repel", "propel", "impel", "dispel", "impulse", "pulse"]
    },
    "phon": {
        "meaning": "sound/voice",
        "meaning_zh": "聲音",
        "origin_word": "sound",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "sound → phon (related Greek sound root)",
        "derived_words": ["phone", "telephone", "microphone", "symphony", "phonetic", "earphone"]
    },
    "prim": {
        "meaning": "first",
        "meaning_zh": "第一/首要",
        "origin_word": "first",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "first → prim (f↔p interchange)",
        "derived_words": ["primary", "prime", "primitive", "prince", "principal", "principle", "priority"]
    },
    "reg": {
        "meaning": "rule/king/straight",
        "meaning_zh": "統治/國王",
        "origin_word": "right",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "right → reg (related ruling root)",
        "derived_words": ["regular", "regulate", "region", "regime", "register", "reign"]
    },
    "sci": {
        "meaning": "know",
        "meaning_zh": "知道",
        "origin_word": "know",
        "rule": 3,
        "rule_name": "g-k-h interchange",
        "explanation": "know → sci (kn↔sc interchange)",
        "derived_words": ["science", "scientist", "conscious", "conscience", "omniscient"]
    },
    "sens": {
        "meaning": "feel/perceive",
        "meaning_zh": "感覺/感知",
        "origin_word": "sense",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "sense → sens (direct Latin cognate)",
        "derived_words": ["sense", "sensitive", "sensation", "consent", "consensus", "nonsense", "sensible", "sentimental"]
    },
    "serv": {
        "meaning": "keep/serve",
        "meaning_zh": "保持/服務",
        "origin_word": "serve",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "serve → serv (direct Latin cognate)",
        "derived_words": ["serve", "service", "preserve", "conserve", "reserve", "observe", "deserve", "servant"]
    },
    "soci": {
        "meaning": "companion/group",
        "meaning_zh": "同伴/社會",
        "origin_word": "follow",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "follow → soci (related companionship root)",
        "derived_words": ["social", "society", "associate", "sociology", "sociable", "antisocial"]
    },
    "terr": {
        "meaning": "earth/land",
        "meaning_zh": "土地/大地",
        "origin_word": "earth",
        "rule": 4,
        "rule_name": "d-t-s interchange",
        "explanation": "earth → terr (related earth root)",
        "derived_words": ["terrain", "territory", "terrestrial", "terrace", "subterranean", "Mediterranean"]
    },
    "val": {
        "meaning": "worth/strong",
        "meaning_zh": "價值/強壯",
        "origin_word": "well",
        "rule": 2,
        "rule_name": "u-v-w interchange",
        "explanation": "well → val (w↔v interchange)",
        "derived_words": ["value", "valid", "evaluate", "equivalent", "prevail", "available", "invaluable"]
    },
    "vis": {
        "meaning": "see",
        "meaning_zh": "看",
        "origin_word": "see",
        "rule": 2,
        "rule_name": "u-v-w interchange",
        "explanation": "see → vis (related seeing root, s↔s)",
        "derived_words": ["visible", "vision", "visit", "visual", "invisible", "supervise", "revise", "television", "evident"]
    },
    "vit": {
        "meaning": "life",
        "meaning_zh": "生命",
        "origin_word": "life",
        "rule": 6,
        "rule_name": "b-p-m-f-v interchange",
        "explanation": "life → vit (l↔v, f↔t interchange)",
        "derived_words": ["vital", "vitamin", "vitality", "survive", "revive", "vivid", "viable"]
    },
}

# -----------------------------------------------------------------------
# NEW PREFIXES to add
# -----------------------------------------------------------------------
NEW_PREFIXES = {
    "mono": {"meaning": "one/single", "meaning_zh": "單一"},
    "uni": {"meaning": "one", "meaning_zh": "一"},
    "semi": {"meaning": "half", "meaning_zh": "半"},
    "counter": {"meaning": "against/opposite", "meaning_zh": "相反/對抗"},
    "fore": {"meaning": "before/front", "meaning_zh": "前/先"},
    "under": {"meaning": "below/insufficient", "meaning_zh": "在下/不足"},
    "non": {"meaning": "not", "meaning_zh": "非/不"},
    "mid": {"meaning": "middle", "meaning_zh": "中間"},
    "micro": {"meaning": "small", "meaning_zh": "微小"},
    "macro": {"meaning": "large", "meaning_zh": "巨大"},
    "neo": {"meaning": "new", "meaning_zh": "新"},
    "pseudo": {"meaning": "false", "meaning_zh": "假/偽"},
    "circum": {"meaning": "around", "meaning_zh": "環繞"},
    "contra": {"meaning": "against", "meaning_zh": "反對"},
    "extra": {"meaning": "beyond/outside", "meaning_zh": "超出/額外"},
    "infra": {"meaning": "below", "meaning_zh": "在下/基礎"},
    "ultra": {"meaning": "beyond/extreme", "meaning_zh": "超越/極端"},
    "retro": {"meaning": "backward", "meaning_zh": "向後/回溯"},
    "tele": {"meaning": "far/distant", "meaning_zh": "遠距"},
    "hyper": {"meaning": "over/excessive", "meaning_zh": "過度/超"},
    "hypo": {"meaning": "under/below", "meaning_zh": "低/下"},
    "para": {"meaning": "beside/beyond", "meaning_zh": "旁邊/超越"},
    "poly": {"meaning": "many", "meaning_zh": "多"},
    "omni": {"meaning": "all", "meaning_zh": "全"},
    "pan": {"meaning": "all/every", "meaning_zh": "全/泛"},
    "ambi": {"meaning": "both/around", "meaning_zh": "兩者/周圍"},
    "bene": {"meaning": "good/well", "meaning_zh": "好"},
}

# -----------------------------------------------------------------------
# NEW SUFFIXES to add
# -----------------------------------------------------------------------
NEW_SUFFIXES = {
    "dom": {"meaning": "state/realm", "meaning_zh": "…的狀態/領域"},
    "ship": {"meaning": "state/skill", "meaning_zh": "…的狀態/技能"},
    "ward": {"meaning": "direction", "meaning_zh": "朝向…"},
    "wise": {"meaning": "manner/direction", "meaning_zh": "以…方式"},
    "like": {"meaning": "resembling", "meaning_zh": "像…的"},
    "ism": {"meaning": "doctrine/belief", "meaning_zh": "…主義/…論"},
    "logy": {"meaning": "study of", "meaning_zh": "…學"},
    "ling": {"meaning": "small/young", "meaning_zh": "小的/年幼的"},
    "th": {"meaning": "state/quality", "meaning_zh": "…的狀態"},
    "ment": {"meaning": "action/result", "meaning_zh": "…的行為/結果"},
}


def main():
    # Load existing database
    print(f"Loading: {DB_PATH}")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    existing_roots = set(db["roots"].keys())
    existing_prefixes = set(db["affixes"]["prefixes"].keys())
    existing_suffixes = set(db["affixes"]["suffixes"].keys())

    print(f"Existing: {len(existing_roots)} roots, {len(existing_prefixes)} prefixes, {len(existing_suffixes)} suffixes")

    # Add new roots
    added_roots = 0
    for root, info in NEW_ROOTS.items():
        if root not in existing_roots:
            db["roots"][root] = info
            added_roots += 1

    # Add new prefixes
    added_prefixes = 0
    for prefix, info in NEW_PREFIXES.items():
        if prefix not in existing_prefixes:
            db["affixes"]["prefixes"][prefix] = info
            added_prefixes += 1

    # Add new suffixes
    added_suffixes = 0
    for suffix, info in NEW_SUFFIXES.items():
        if suffix not in existing_suffixes:
            db["affixes"]["suffixes"][suffix] = info
            added_suffixes += 1

    print(f"\nAdded: {added_roots} new roots, {added_prefixes} new prefixes, {added_suffixes} new suffixes")
    print(f"Total: {len(db['roots'])} roots, {len(db['affixes']['prefixes'])} prefixes, {len(db['affixes']['suffixes'])} suffixes")

    # Write to database/
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {DB_PATH}")

    # Also update api/ copy
    with open(API_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {API_PATH}")


if __name__ == "__main__":
    main()

