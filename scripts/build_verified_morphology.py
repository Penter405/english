"""
build_verified_morphology.py
----------------------------
「兩個來源都確定才放入」的字根 / 字首 / 字尾資料庫。

來源 1: Wiktionary (經 kaikki.org / wiktextract 匯出, CC-BY-SA)
        https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl
        -> 先用 scripts/filter_wiktionary.py 過濾成 database/raw/wiktionary_en_filtered.jsonl
來源 2: MorphoLex-en (Sánchez-Gutiérrez et al., 2018, CC-BY-NC-SA)
        https://github.com/hugomailhot/MorphoLex-en  (MorphoLEX_en.xlsx)
        -> database/raw/MorphoLEX_en.xlsx

判定規則
  A. 兩邊都說「單一詞素、不可拆」          -> status = "monomorphemic" (收錄，前端顯示「無字根拆解」)
  B. 兩邊都有拆解，且
       - 字首集合一致 (容許同源變體 com/con/col/co…)
       - 字尾集合一致 (容許同源變體 -ion/-tion/-ation…)
       - 字根 / 基礎字 對得上 (正規化後相同，或共同開頭 >= 3 個字母)
                                            -> status = "verified" (收錄)
  C. 其他 (只有一邊有資料、或兩邊說法不同)   -> 不收錄，寫入 morphology_conflicts.json 供人工審核

輸出
  database/word_morphology_verified.json   已驗證資料 (只含 A、B)
  database/morphology_conflicts.json       衝突 / 缺資料清單
  database/morphology_report.md            統計報告

用法
  py scripts/build_verified_morphology.py
"""
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE_DIR, "database")
RAW = os.path.join(DB, "raw")
WIKT_PATH = os.path.join(RAW, "wiktionary_en_filtered.jsonl")
MLEX_XLSX = os.path.join(RAW, "MorphoLEX_en.xlsx")
MLEX_CACHE = os.path.join(RAW, "morpholex_segm.json")
EXAM_WORDS = os.path.join(DB, "exam_words.json")
WORD_DB = os.path.join(DB, "word_database.json")
ECDICT = os.path.join(DB, "ecdict.csv")

OUT_OK = os.path.join(DB, "word_morphology_verified.json")
OUT_CONFLICT = os.path.join(DB, "morphology_conflicts.json")
OUT_REPORT = os.path.join(DB, "morphology_report.md")

# ---------------------------------------------------------------- 正規化工具

def strip_marks(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm(s):
    return strip_marks(s.split("#")[0]).lower().strip().strip("*").strip()


# 同源變體群組 (同一組視為同一個詞綴)
PREFIX_GROUPS = [
    {"pre", "prae"}, {"com", "con", "col", "cor", "co", "cum"},
    {"in", "im", "il", "ir"}, {"en", "em"},
    {"ex", "e", "ef", "exo"}, {"ad", "ac", "af", "ag", "al", "an", "ap", "ar", "as", "at", "a"},
    {"sub", "suc", "suf", "sug", "sup", "sus", "su"}, {"ob", "oc", "of", "op", "o"},
    {"dis", "di", "dif"}, {"trans", "tran", "tra"}, {"re", "red"}, {"de"},
    {"pro", "por", "pur"}, {"per", "pel"}, {"sur", "super", "supra"},
    {"inter", "intel", "enter"}, {"anti", "ant"}, {"syn", "sym", "syl", "sy"},
    {"ab", "abs", "a"}, {"se", "sed"}, {"contra", "counter", "contro"},
    {"un"}, {"non"}, {"mis"}, {"over"}, {"under"}, {"out"}, {"fore"},
    {"bene", "ben"}, {"mal", "male"}, {"circum"}, {"uni"}, {"bi"}, {"tri"},
]
SUFFIX_GROUPS = [
    {"ion", "tion", "ation", "sion", "ition", "ication"}, {"ity", "ty", "ety", "ite"},
    {"ive", "ative", "itive"}, {"able", "ible", "ble", "abil", "ibil"},
    {"ance", "ence", "ancy", "ency"}, {"ant", "ent"}, {"er", "or", "ar", "eer", "ier"},
    {"al", "ial", "ual"}, {"ous", "ious", "eous", "ose"}, {"ize", "ise"},
    {"ment"}, {"ness"}, {"less"}, {"ful"}, {"ly"}, {"y"}, {"ic"}, {"ical"},
    {"ist"}, {"ism"}, {"ish"}, {"ary", "ory", "ery"}, {"ate", "ite"}, {"ure", "ture"},
    {"en"}, {"ify", "fy"}, {"age"}, {"ship"}, {"hood"}, {"dom"}, {"ward", "wards"},
    {"ee"}, {"ess"}, {"let"}, {"ling"}, {"some"}, {"th"}, {"ure"},
]


def build_group_index(groups):
    idx = {}
    for i, g in enumerate(groups):
        for m in g:
            idx.setdefault(m, i)
    return idx


PREFIX_IDX = build_group_index(PREFIX_GROUPS)
SUFFIX_IDX = build_group_index(SUFFIX_GROUPS)


def affix_key(m, kind):
    m = norm(m).strip("-")
    idx = PREFIX_IDX if kind == "prefix" else SUFFIX_IDX
    return ("g", idx[m]) if m in idx else ("s", m)


def root_match(a, b):
    a, b = norm(a).strip("-"), norm(b).strip("-")
    if not a or not b:
        return False
    if a == b:
        return True
    # 去掉常見的拉丁動詞語尾再比 (dico -> dic, porto -> port, specere -> spec)
    def stem(x):
        for end in ("are", "ere", "ire", "o", "us", "um", "a", "e", "is"):
            if x.endswith(end) and len(x) - len(end) >= 3:
                return x[: -len(end)]
        return x
    a2, b2 = stem(a), stem(b)
    if a2 == b2:
        return True
    n = 0
    for x, y in zip(a2, b2):
        if x != y:
            break
        n += 1
    return n >= 3 and n >= min(len(a2), len(b2)) - 1


# ---------------------------------------------------------------- MorphoLex

def load_morpholex():
    if os.path.exists(MLEX_CACHE):
        return json.load(open(MLEX_CACHE, encoding="utf-8"))
    import pandas as pd  # 只有第一次需要
    x = pd.ExcelFile(MLEX_XLSX)
    rows = {}
    for s in x.sheet_names:
        if not re.match(r"\d-\d-\d", s):
            continue
        df = x.parse(s)
        for w, seg in zip(df["Word"], df["MorphoLexSegm"]):
            if isinstance(w, str) and isinstance(seg, str):
                rows[w.lower()] = seg
    json.dump(rows, open(MLEX_CACHE, "w", encoding="utf-8"))
    return rows


MLEX_TOKEN = re.compile(r"<([^<>]+)<|\(([^()]+)\)|>([^<>]+)>|[{}]")


def parse_morpholex(seg):
    """'{<sur<(vive)}>al>' -> prefixes ['sur'], roots ['vive'], suffixes ['al']"""
    pre, roots, suf = [], [], []
    for m in MLEX_TOKEN.finditer(seg):
        if m.group(1):
            pre.append(m.group(1))
        elif m.group(2):
            roots.append(m.group(2))
        elif m.group(3):
            suf.append(m.group(3))
    return {"prefixes": pre, "roots": roots, "suffixes": suf}


# ---------------------------------------------------------------- Wiktionary

MORPH_TEMPLATES = {"af", "affix", "prefix", "pre", "suffix", "suf", "confix", "con",
                   "surf", "compound", "com"}
INLINE_T = re.compile(r"<t:([^>]*)>")
INLINE_ANY = re.compile(r"<[^>]*>")
CHAIN_RE = re.compile(
    r"((?:[\wÀ-ɏ*-]+(?:\s*\(“[^”]*”\))?\s*\+\s*)+[\wÀ-ɏ*-]+(?:\s*\(“[^”]*”\))?)")
PART_RE = re.compile(r"([\wÀ-ɏ*-]+)(?:\s*\(“([^”]*)”\))?")


def load_wiktionary():
    W = defaultdict(list)
    with open(WIKT_PATH, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            W[e["word"]].append(e)
    return W


def template_parts(t):
    """把一個構詞模板轉成 [(text, kind, gloss)]，kind = prefix/suffix/root"""
    name, args = t["name"], t.get("args") or {}
    start = 2
    if str(args.get("1", "")).startswith("+"):   # {{surf|+suf|en|grace|ful}}
        name = {"suf": "suffix", "pre": "prefix", "con": "confix"}.get(args["1"][1:], name)
        start = 3
    pos_args = []
    i = start
    while str(i) in args:
        pos_args.append(args[str(i)])
        i += 1
    parts = []
    for j, raw in enumerate(pos_args):
        if not raw:
            continue
        gloss = None
        m = INLINE_T.search(raw)
        if m:
            gloss = m.group(1)
        gloss = gloss or args.get(f"t{j+1}") or args.get(f"gloss{j+1}")
        text = INLINE_ANY.sub("", raw).strip()
        if not text:
            continue
        if name in ("prefix", "pre") and j < len(pos_args) - 1:
            kind = "prefix"
        elif name in ("suffix", "suf") and j > 0:
            kind = "suffix"
        elif name in ("confix", "con") and j == 0:
            kind = "prefix"
        elif name in ("confix", "con") and j == len(pos_args) - 1 and len(pos_args) > 2:
            kind = "suffix"
        elif text.endswith("-"):
            kind = "prefix"
        elif text.startswith("-"):
            kind = "suffix"
        else:
            kind = "root"
        parts.append((text, kind, gloss))
    return parts


def text_chain_parts(text):
    """etymology_text 中的 'from prae- (“before”) + dīcō (“to say”)' / 'equivalent to mortal + -ity'"""
    best = None
    for m in CHAIN_RE.finditer(text or ""):
        chain = m.group(1)
        parts = []
        for p in chain.split("+"):
            pm = PART_RE.search(p.strip())
            if not pm:
                continue
            tx, gl = pm.group(1), pm.group(2)
            kind = "prefix" if tx.endswith("-") else "suffix" if tx.startswith("-") else "root"
            parts.append((tx, kind, gl))
        if len(parts) >= 2:
            best = parts  # 取最後一條 (通常是最直接的構詞說明)
    return best


def wikt_analysis(entries):
    """回傳 (analysis, origin_note) 或 (None, note)。
    優先序: 英文層級模板 > surf > 文字中的 'equivalent to A + B' > 拉丁層級模板 > 其他文字鏈"""
    cand_en, cand_surf, cand_eq, cand_la, cand_text = [], [], [], [], []
    origins = []
    # 只看「主要詞源」(Wiktionary 的 Etymology 1)。同形異源字 (corner = 種玉米的人) 不採用
    primary = [e for e in entries if e.get("etymology_text") or e.get("etymology_templates")]
    if primary:
        key = (primary[0].get("etymology_text"), json.dumps(primary[0].get("etymology_templates"), sort_keys=True))
        primary = [e for e in primary
                   if (e.get("etymology_text"), json.dumps(e.get("etymology_templates"), sort_keys=True)) == key]
    for e in primary:
        txt = e.get("etymology_text") or ""
        for t in e.get("etymology_templates") or []:
            name, args = t["name"], t.get("args") or {}
            if name in ("der", "bor", "inh", "lbor") and args.get("2") in ("la", "fr", "fro", "grc", "enm", "ang"):
                origins.append((args.get("2"), args.get("3"), args.get("5") or args.get("t") or ""))
            if name not in MORPH_TEMPLATES:
                continue
            lang = args.get("2") if str(args.get("1", "")).startswith("+") else args.get("1")
            parts = template_parts(t)
            if len(parts) < 2:
                continue
            if name == "surf":
                cand_surf.append(parts)
            elif lang == "en":
                cand_en.append(parts)
            else:
                cand_la.append(parts)
        m = re.search(r"equivalent to ([^.;]+)", txt, re.I)
        if m:
            p = text_chain_parts(m.group(1))
            if p:
                cand_eq.append(p)
        p = text_chain_parts(txt)
        if p:
            cand_text.append(p)
    # 文字說明裡的註解 (in (“in”) + specere (“to look at”)) 拿來補模板沒寫的意思
    glosses = []
    for e in primary:
        for m in CHAIN_RE.finditer(e.get("etymology_text") or ""):
            for p in m.group(1).split("+"):
                pm = PART_RE.search(p.strip())
                if pm and pm.group(2):
                    glosses.append((pm.group(1), pm.group(2)))
        for m in re.finditer(r"([\w\u00C0-\u024F-]+) \(“([^”]+)”\)", e.get("etymology_text") or ""):
            glosses.append((m.group(1), m.group(2)))
    for level, c in (("en", cand_en), ("surf", cand_surf), ("equivalent", cand_eq),
                     ("latin", cand_la), ("text", cand_text)):
        if c:
            parts = []
            for tx, kind, gl in c[0]:
                if not gl:
                    for tx2, gl2 in glosses:
                        a, b = norm(tx).strip("-"), norm(tx2).strip("-")
                        if (kind == "root" and root_match(a, b)) or (kind != "root" and a == b):
                            gl = gl2
                            break
                parts.append((tx, kind, gl))
            return {"level": level, "parts": parts}, origins
    return None, origins


# ---------------------------------------------------------------- 意思 (英 / 中)

def first_gloss(entries, pos):
    for e in entries:
        if e.get("pos") != pos:
            continue
        for s in e.get("senses") or []:
            g = (s.get("glosses") or [None])[0]
            if g and "aldehyde" not in g.lower() and not (s.get("tags") or []) or g:
                g = re.split(r"[;.]", g)[0].strip()
                if g:
                    return g
    return None


def load_ecdict_map():
    """word -> [各詞性的中文解釋行] (ECDICT 原文為簡體，之後轉繁體)"""
    m = {}
    if not os.path.exists(ECDICT):
        return m
    import csv
    with open(ECDICT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").lower()
            tr = row.get("translation") or ""
            if w and tr and w not in m:
                m[w] = [x.strip() for x in tr.replace("\\n", "\n").split("\n") if x.strip()]
    return m


def ecd_pick(lines, pos=None):
    """依詞性挑一行，去掉詞性標記與 [計] 之類的領域標記"""
    if not lines:
        return ""
    want = {"v.": ("v.", "vt.", "vi."), "adj.": ("a.", "adj."), "n.": ("n.",)}.get(pos or "", ())
    cand = [l for l in lines if not l.startswith("[")]
    line = next((l for l in cand if want and l.startswith(want)), cand[0] if cand else lines[0])
    return re.sub(r"^[a-z]+\.\s*", "", line)


def gloss_to_zh(gloss, ecd):
    """Wiktionary 英文註解 -> 中文。
    "to say" -> 說；"to seek for" -> 尋找 (取主要動詞)；太長的片語不翻 (避免亂翻)"""
    if not gloss:
        return ""
    is_verb = gloss.strip().lower().startswith("to ")
    for piece in re.split(r"[,;]", gloss.lower()):
        p0 = re.sub(r"\s*\(.*?\)", "", piece).strip()
        if p0 in FUNCTION_ZH:            # 介系詞類：ECDICT 第一義常常不對 (by -> 二)
            return FUNCTION_ZH[p0]
        g = re.sub(r"^(to|a|an|the)\s+", "", p0)
        if g in FUNCTION_ZH:
            return FUNCTION_ZH[g]
        if g in ecd and len(g.split()) <= 3:
            return ecd_pick(ecd[g], "v." if is_verb else None)
        words = g.split()
        # "seek for" -> seek；"make straight" 不取 (後面不是小品詞，意思會跑掉)
        if 1 < len(words) <= 3 and words[0] in ecd and all(x in PARTICLES for x in words[1:]):
            return ecd_pick(ecd[words[0]], "v." if is_verb else None)
    return ""


PARTICLES = {"for", "into", "up", "out", "off", "on", "at", "away", "down", "back", "over", "together", "upon"}
FUNCTION_ZH = {
    "by": "在旁邊、經由", "over": "在上方、越過", "to": "朝向", "toward": "朝向", "towards": "朝向",
    "from": "從…來", "away": "離開", "away from": "離開", "out": "向外", "out of": "從…出來",
    "in": "在…裡、向內", "into": "進入", "on": "在…上", "upon": "在…上", "with": "和…一起",
    "together": "一起", "against": "對著、反對", "before": "在…之前", "after": "在…之後",
    "under": "在下面", "below": "在下面", "through": "穿過", "across": "橫越", "back": "向後、回",
    "again": "再", "down": "向下", "up": "向上", "off": "離開", "around": "周圍", "about": "周圍",
    "beyond": "超過", "between": "在…之間", "not": "不", "without": "沒有", "apart": "分開",
    "outside of": "在…外面", "outside": "在外面", "within": "在…裡面", "at": "在", "for": "為了",
    "forth": "向前", "forward": "向前", "above": "在上面", "under, below": "在下面",
}


# ---------------------------------------------------------------- 比對

def common_prefix_len(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def prefix_allomorphs(p):
    k = affix_key(p, "prefix")
    if k[0] == "g":
        return sorted(PREFIX_GROUPS[k[1]], key=len, reverse=True)
    return [norm(p).strip("-")]


def strip_prefix_allomorph(s, p):
    """'construct' 去掉 co(n)- -> 'struct'；找不到回傳 None"""
    for m in prefix_allomorphs(p):
        if m and s.startswith(m):
            return s[len(m):]
    return None


def compare(word, wa, ml, is_english_word):
    """回傳 (status, reason, mode)
    mode = "base"  : Wiktionary 給的是「英文基礎字 + 外層詞綴」(survival = survive + -al)
           "root"  : 兩邊都拆到字根 (predict = pre- + dict)
    """
    mono_ml = (not ml["prefixes"] and not ml["suffixes"] and len(ml["roots"]) == 1)
    if wa is None:
        if mono_ml and norm(ml["roots"][0]) == norm(word):
            return "monomorphemic", None, None
        return "conflict", "wiktionary_no_analysis", None
    if mono_ml:
        return "conflict", "morpholex_says_monomorphemic", None

    parts = wa["parts"]
    w_pre = [p[0] for p in parts if p[1] == "prefix"]
    w_suf = [p[0] for p in parts if p[1] == "suffix"]
    w_root = [p[0] for p in parts if p[1] == "root"]
    m_root = ml["roots"]

    kp_w = Counter(affix_key(p, "prefix") for p in w_pre)
    kp_m = Counter(affix_key(p, "prefix") for p in ml["prefixes"])
    ks_w = Counter(affix_key(p, "suffix") for p in w_suf)
    ks_m = Counter(affix_key(p, "suffix") for p in ml["suffixes"])

    # Wiktionary 說的詞綴，MorphoLex 一定也要有
    if kp_w - kp_m:
        return "conflict", "prefix_mismatch", None
    if ks_w - ks_m:
        return "conflict", "suffix_mismatch", None
    extra_p = [p for p in ml["prefixes"] if affix_key(p, "prefix") in (kp_m - kp_w)]
    extra_s = [p for p in ml["suffixes"] if affix_key(p, "suffix") in (ks_m - ks_w)]

    # 複合字 (sunlight = sun + light)
    if len(w_root) >= 2 or len(m_root) >= 2:
        if len(w_root) == len(m_root) and not extra_p and not extra_s and \
                all(root_match(a, b) for a, b in zip(w_root, m_root)):
            return "verified", None, "compound"
        return "conflict", "root_count_mismatch", None
    if len(w_root) != 1 or len(m_root) != 1:
        return "conflict", "root_count_mismatch", None

    wr, mr = norm(w_root[0]), norm(m_root[0])
    if not extra_p and not extra_s:
        if root_match(wr, mr):
            return "verified", None, ("base" if is_english_word(wr) else "root")
        return "conflict", "root_mismatch", None

    # MorphoLex 拆得比較深：多出來的詞綴必須「藏在」Wiktionary 的基礎字裡
    #   survival: base=survive, MorphoLex 多了 sur-  -> survive 以 sur 開頭，剩下 vive = 字根 ✓
    #   mortality: base=mortal, MorphoLex 多了 -al   -> mortal = mort + al ✓
    if not is_english_word(wr):
        return "conflict", "affix_depth_mismatch", None
    rem = wr
    for p in extra_p:
        rem2 = strip_prefix_allomorph(rem, p)
        if rem2 is None:
            return "conflict", "affix_depth_mismatch", None
        rem = rem2
    n = common_prefix_len(rem, mr)
    if n < min(3, len(mr)):
        return "conflict", "root_mismatch", None
    tail = rem[n:]
    if extra_s:
        joined = "".join(norm(x) for x in extra_s)
        # 允許拼字微調 (y↔i, 去 e)
        if not tail or not (joined.startswith(tail.rstrip("e")[:2]) or tail.endswith(joined[-2:])):
            return "conflict", "affix_depth_mismatch", None
    elif len(tail) > 2:
        return "conflict", "root_mismatch", None
    return "verified", None, "base"


# ---------------------------------------------------------------- 詞綴中文意思 (人工校對)
# word_database.json 沒有的常見詞綴補在這裡；鍵為不含連字號的拼法
AFFIX_ZH = {
    "prefix": {
        "pre": "事先、在前", "prae": "事先、在前", "re": "再、回", "un": "不、相反", "in": "不 / 向內",
        "im": "不 / 向內", "il": "不", "ir": "不", "dis": "不、分開", "mis": "錯誤地", "non": "非",
        "de": "向下、去除", "ex": "向外、從…出來", "e": "向外", "com": "一起、完全", "con": "一起、完全",
        "col": "一起", "cor": "一起", "co": "共同", "sub": "在下", "sup": "在下", "sur": "超過、在上",
        "super": "超級、在上", "trans": "跨越", "inter": "在…之間", "pro": "向前、支持",
        "per": "徹底、穿過", "ad": "朝向", "ac": "朝向", "af": "朝向", "ap": "朝向", "as": "朝向",
        "at": "朝向", "ob": "對著、反對", "op": "對著、反對", "en": "使成為", "em": "使成為",
        "over": "過度、在上", "under": "在下、不足", "out": "向外、勝過", "fore": "在前",
        "anti": "反對", "auto": "自己", "bi": "二", "tri": "三", "uni": "單一", "multi": "多",
        "semi": "半", "mid": "中間", "micro": "微小", "tele": "遠", "ab": "離開", "se": "分開",
        "circum": "環繞", "contra": "相反", "counter": "相反、對抗", "bene": "好", "mal": "壞",
        "post": "在後", "intro": "向內", "extra": "額外、在外", "a": "朝向 / 不", "di": "分開",
        "dif": "分開", "suf": "在下", "suc": "在下", "sus": "在下", "oc": "對著", "of": "對著",
        "ag": "朝向", "an": "朝向", "ar": "朝向", "al": "朝向", "syn": "一起", "sym": "一起",
        "up": "向上", "by": "旁邊、次要的", "kilo": "千", "off": "離開", "after": "之後",
        "epi": "在上、在外", "hemi": "半", "abs": "離開", "be": "使成為、在…旁",
        "sed": "分開", "red": "再、回",
    },
    "suffix": {
        "er": "…的人 / 物", "or": "…的人 / 物", "ar": "…的 (形容詞)", "ee": "被…的人", "ist": "…家、…者",
        "ian": "…的人 / 屬於…的", "ant": "…的人 / …的", "ent": "…的人 / …的", "ess": "女性…",
        "ion": "動作、結果 (名詞)", "tion": "動作、結果 (名詞)", "ation": "動作、結果 (名詞)",
        "sion": "動作、結果 (名詞)", "ment": "行為、結果 (名詞)", "ness": "性質、狀態 (名詞)",
        "ity": "性質、狀態 (名詞)", "ance": "性質、行為 (名詞)", "ence": "性質、行為 (名詞)",
        "ancy": "性質、狀態 (名詞)", "ency": "性質、狀態 (名詞)", "ship": "身分、關係",
        "hood": "時期、狀態", "dom": "領域、狀態", "ism": "主義、行為", "age": "集合、行為 (名詞)",
        "ure": "行為、結果 (名詞)", "ure": "行為、結果 (名詞)", "th": "性質 (名詞)", "y": "有…的 / 狀態",
        "al": "…的 (形容詞) / 動作 (名詞)", "ial": "…的 (形容詞)", "ic": "…的 (形容詞)",
        "ical": "…的 (形容詞)", "ous": "充滿…的", "ious": "充滿…的", "ful": "充滿…的",
        "less": "沒有…的", "able": "可…的", "ible": "可…的", "ive": "有…傾向的", "ative": "有…傾向的",
        "ish": "有點…的、…國的", "ly": "…地 (副詞) / 像…的", "ary": "與…有關的 (人 / 物)",
        "ory": "與…有關的 (地方 / 物)", "ery": "場所、行業", "ize": "使…化", "ise": "使…化",
        "ify": "使…化", "fy": "使…化", "ate": "使… / 具有…的", "en": "使變得… / 由…製成的",
        "ward": "朝…方向", "wards": "朝…方向", "some": "有…傾向的", "like": "像…的",
        "fold": "…倍", "ster": "…的人", "let": "小…", "ling": "小… / …的人", "ty": "性質 / ×10",
        "teen": "十幾", "ese": "…國 (人 / 語) 的", "an": "…的人 / 屬於…的", "ite": "…的人 / …的",
        "ette": "小…", "ure": "行為、結果 (名詞)", "cy": "性質、狀態 (名詞)", "ess": "女性…",
        "wise": "以…方式", "most": "最…", "ern": "…方的", "ty_num": "×10 (幾十)",
        "ety": "性質、狀態 (名詞)", "ition": "動作、結果 (名詞)", "ication": "動作、結果 (名詞)",
        "acy": "性質、狀態 (名詞)", "ics": "…學", "ine": "…的 / 物質", "ade": "動作、產物 (名詞)",
        "aire": "…的人", "end": "…的人 / 物", "red": "狀態 (名詞)", "t": "名詞化",
        "a": "名詞語尾",
    },
}

# 字尾 -> 基礎字應該是什麼詞性
BASE_POS = {}
for _suf in ("er", "or", "ee", "ment", "ion", "tion", "ation", "sion", "able", "ible", "ive",
             "ative", "ance", "ence", "ant", "ent", "ing", "ure", "age"):
    BASE_POS[_suf] = "v."
for _suf in ("ity", "ness", "ly", "ize", "ise", "en", "ism", "ty", "th"):
    BASE_POS[_suf] = "adj."
for _suf in ("ful", "ous", "less", "ic", "ical", "ish", "y", "ist", "ian", "ship", "hood", "dom",
             "ary", "al", "like", "some", "ate"):
    BASE_POS[_suf] = "n."

NUM_TY = {"twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"}

# ---------------------------------------------------------------- 古典語源拆解 (單一來源)
# 兩來源沒有共識的字 (例如 MorphoLex 說 accept 不可拆)，改用 Wiktionary 的拉丁 / 希臘 / 古英文拆解：
#   accept <- 拉丁文 ad- (朝向) + capiō (拿)
# 這是 Wiktionary 單一來源，另存 word_etymology_wiktionary.json，網站上用不同標籤顯示。

OUT_CLASSICAL = os.path.join(DB, "word_etymology_wiktionary.json")

LANG_ZH = {"la": "拉丁文", "grc": "古希臘文", "ang": "古英文", "fro": "古法文", "fr": "法文",
           "frm": "中古法文", "xno": "盎格魯-諾曼法文", "non": "古諾斯語", "it": "義大利文",
           "de": "德文", "nl": "荷蘭文", "es": "西班牙文", "ar": "阿拉伯文"}
LANG_NAMES = [("Ancient Greek", "grc"), ("Late Latin", "la"), ("Medieval Latin", "la"),
              ("Vulgar Latin", "la"), ("New Latin", "la"), ("Latin", "la"), ("Old English", "ang"),
              ("Old French", "fro"), ("Anglo-Norman", "xno"), ("Middle French", "frm"),
              ("Old Norse", "non"), ("Middle English", "enm"), ("Middle Dutch", "nl"),
              ("Italian", "it"), ("Spanish", "es"), ("Arabic", "ar"), ("French", "fr"), ("Greek", "grc")]
LATIN_VERB_END = {"o", "ō", "are", "āre", "ere", "ēre", "ire", "īre"}
META_WORDS = {"latin", "medieval", "late", "vulgar", "new", "greek", "ancient", "old", "middle",
              "english", "french", "proto-germanic", "proto-indo-european", "form", "variant",
              "verb", "noun", "adjective", "adverb", "agent", "suffix", "prefix", "to", "a", "an",
              "the", "of", "and", "or", "future", "participle", "perfect", "passive", "present",
              "past", "infinitive", "stem", "plural", "genitive", "accusative", "diminutive"}
# 拉丁 / 希臘文常見字尾 (Wiktionary 文字說明常不附意思)
CLASSICAL_SUFFIX_ZH = {
    "alis": "…的 (形容詞)", "aris": "…的 (形容詞)", "icus": "…的 (形容詞)", "ikos": "…的 (形容詞)",
    "ivus": "有…性質的", "osus": "充滿…的", "ilis": "可…的", "bilis": "可…的", "anus": "屬於…的",
    "inus": "屬於…的", "torius": "與…有關的", "orius": "與…有關的", "arius": "與…有關的",
    "tor": "…的人", "or": "…的人 / 狀態", "trix": "…的女性", "tas": "性質 (名詞)", "itas": "性質 (名詞)",
    "tio": "動作 (名詞)", "atio": "動作 (名詞)", "sio": "動作 (名詞)", "tura": "結果 (名詞)",
    "ura": "結果 (名詞)", "mentum": "結果、工具 (名詞)", "men": "結果 (名詞)", "ium": "名詞語尾",
    "ia": "名詞語尾 (狀態)", "us": "名詞 / 形容詞語尾", "um": "名詞語尾", "a": "名詞語尾",
    "os": "名詞 / 形容詞語尾", "on": "名詞語尾", "ma": "結果 (名詞)", "sis": "動作 (名詞)",
    "ites": "…的人", "ista": "…的人", "ismus": "主義、行為", "izo": "使…化 (動詞)", "izein": "使…化 (動詞)",
    "nus": "屬於…的", "ulus": "小…", "culus": "小…", "ellus": "小…", "et": "小…", "ette": "小…",
    "le": "反覆動作 / 工具", "illion": "×百萬級 (數字語尾)", "ed": "過去分詞 / 有…的", "i": "連接母音",
    "u": "連接母音", "o": "連接母音",
    "ος": "名詞 / 形容詞語尾", "ον": "名詞語尾", "ια": "名詞語尾 (狀態)", "ικος": "…的 (形容詞)",
    "ης": "名詞語尾", "μα": "結果 (名詞)", "σις": "動作 (名詞)", "ιζω": "使…化 (動詞)",
}


SKIP_CTX = re.compile(r"(compare|cognate|cf\.|akin|related to|doublet|see also|whence)[^.;]*$", re.I)


def lang_before(text, pos):
    """chain 前面最近提到的語言；跳過 'compare Middle Dutch …' 這類比較用的提及"""
    best, bi = None, -1
    for name, code in LANG_NAMES:
        start = pos
        while True:
            i = text.rfind(name, 0, start)
            if i < 0:
                break
            if not SKIP_CTX.search(text[max(0, i - 60):i]):
                if i > bi:
                    bi, best = i, code
                break
            start = i
    return best


def classical_analysis(entries):
    """回傳 (lang, [(text, kind, gloss)]) 或 None；只看主要詞源"""
    prim = [e for e in entries if e.get("etymology_text") or e.get("etymology_templates")]
    if not prim:
        return None
    p = prim[0]
    txt = p.get("etymology_text") or ""
    # 1) 非英文的構詞模板 {{af|la|ad-|capiō}}
    for t in p.get("etymology_templates") or []:
        a = t.get("args") or {}
        lang = a.get("2") if str(a.get("1", "")).startswith("+") else a.get("1")
        if t["name"] in MORPH_TEMPLATES and lang in LANG_ZH:
            parts = template_parts(t)
            if len(parts) >= 2:
                return lang, parts
    # 2) 文字說明裡的 'from ad- (“to”) + capiō (“to take”)'，語言看前面最近提到的語言名
    found = None
    for m in CHAIN_RE.finditer(txt):
        lang = lang_before(txt, m.start())
        if lang not in LANG_ZH:
            continue
        parts = []
        for q in m.group(1).split("+"):
            pm = PART_RE.search(q.strip())
            if pm:
                tx = pm.group(1)
                kind = "prefix" if tx.endswith("-") else "suffix" if tx.startswith("-") else "root"
                parts.append((tx, kind, pm.group(2)))
        if len(parts) >= 2:
            found = (lang, parts)
    return found


# ---------------------------------------------------------------- main

def main():
    try:
        from opencc import OpenCC
        to_tw = OpenCC("s2twp").convert
    except ImportError:
        print("提示: pip install opencc-python-reimplemented 可把 ECDICT 簡體轉繁體")
        to_tw = lambda x: x

    exam = json.load(open(EXAM_WORDS, encoding="utf-8"))["words"]
    W = load_wiktionary()
    ML = load_morpholex()
    wdb = json.load(open(WORD_DB, encoding="utf-8")) if os.path.exists(WORD_DB) else {}
    wdb_pre = {k.strip("-"): v for k, v in (wdb.get("affixes", {}).get("prefixes", {}) or {}).items()}
    wdb_suf = {k.strip("-"): v for k, v in (wdb.get("affixes", {}).get("suffixes", {}) or {}).items()}
    wdb_root = wdb.get("roots", {}) or {}
    print("loading ECDICT ...")
    ecd = load_ecdict_map()

    def short_zh(s, n=2):
        s = re.sub(r"\[[^\]]*\]\s*", "", s or "")           # [法] [計] 之類的領域標記
        s = re.sub(r"[“”\"「」]", "", s)
        s = re.sub(r"^表示", "", s)
        items = [x.strip() for x in re.split(r"[,，;；、]", s) if x.strip()]
        return to_tw("、".join(items[:n]))

    def word_zh(w, pos=None):
        e = exam.get(w) or {}
        zh = (e.get("definitions") or {}).get("zh") or []
        if pos:   # 依字尾決定要哪個詞性的意思 (pitch+er -> v. 投擲，而非 n. 坡度)
            want = {"v.": ("v.", "vt.", "vi."), "adj.": ("a.", "adj."), "n.": ("n.",)}[pos]
            for z in zh:
                if z.strip().startswith(want):
                    return short_zh(re.sub(r"^[a-z]+\.\s*", "", z))
        if zh:
            return short_zh(re.sub(r"^[a-z]+\.\s*", "", zh[0]))
        return short_zh(ecd_pick(ecd.get(w), pos))

    def is_english_word(t):
        return t in exam or t in ML or any(e.get("pos") not in ("prefix", "suffix", "root") for e in W.get(t, []))

    def affix_info(text, kind, gloss, word):
        t = norm(text).strip("-")
        label = f"{t}-" if kind == "prefix" else f"-{t}"
        cur = (wdb_pre if kind == "prefix" else wdb_suf).get(t) or {}
        zh = cur.get("meaning_zh") or AFFIX_ZH[kind].get(t, "")
        if kind == "suffix" and t == "ty" and word in NUM_TY:
            zh = AFFIX_ZH["suffix"]["ty_num"]
        en = cur.get("meaning") or gloss or ""
        if not en:
            g = first_gloss(W.get(label, []), kind)
            en = g if (g and zh) else ""   # 沒中文校對時不放 Wiktionary 第一義 (常對錯義項)
        return {"text": label, "meaning_en": en, "meaning_zh": zh}

    verified, conflicts = {}, {}
    stats = Counter()
    reasons = Counter()
    missing_affix_zh = Counter()
    for word in sorted(exam):
        w = word.lower()
        wa, origins = wikt_analysis(W.get(w, []))
        seg = ML.get(w)
        if seg is None:
            stats["no_morpholex"] += 1
            conflicts[w] = {"reason": "not_in_morpholex",
                            "wiktionary": [p[0] for p in wa["parts"]] if wa else None}
            continue
        if not W.get(w):
            stats["no_wiktionary"] += 1
            conflicts[w] = {"reason": "not_in_wiktionary", "morpholex": seg}
            continue
        ml = parse_morpholex(seg)
        status, why, mode = compare(w, wa, ml, is_english_word)
        if status == "conflict":
            reasons[why] += 1
            conflicts[w] = {"reason": why, "morpholex": seg,
                            "wiktionary": [p[0] for p in wa["parts"]] if wa else None,
                            "wiktionary_level": wa["level"] if wa else None}
            continue
        stats[status] += 1
        origin = None
        rank = {"la": 0, "grc": 1, "fro": 2, "fr": 3}   # 優先顯示拉丁 / 希臘文來源
        for lang, form, gl in sorted(origins, key=lambda o: rank.get(o[0], 9)):
            if lang in rank and form:
                origin = {"lang": lang, "form": form, "meaning_en": gl}
                break
        if status == "monomorphemic":
            verified[w] = {"word": w, "status": "monomorphemic", "has_affix": False,
                           "prefixes": [], "root": {"text": w, "meaning_zh": word_zh(w)},
                           "suffixes": [], "origin": origin,
                           "sources": {"morpholex": seg, "wiktionary": "no decomposition"}}
            continue

        parts = wa["parts"]
        w_pre = [p for p in parts if p[1] == "prefix"]
        w_suf = [p for p in parts if p[1] == "suffix"]
        w_roots = [p for p in parts if p[1] == "root"]

        if mode == "base" and len(w_roots) == 1:
            mr0 = norm(ml["roots"][0])
            free_in_ml = ("{(%s)}" % ml["roots"][0]) in seg
            absorbed = norm(w_roots[0][0]) != mr0
            # transport = trans + port: MorphoLex 把 port 跟字首放同一層 (不是獨立單字) -> 當字根 (攜帶)
            # graceful = {(grace)}>ful>: grace 是獨立單字 -> 當基礎字 (優雅)
            if not absorbed and not free_in_ml:
                mode = "root"
        if mode == "root":
            # 顯示用英文拼法 (MorphoLex: pre / dict)，意思用 Wiktionary 的註解 (before / to say)
            pre = []
            rest = w
            for tx, _, gl in w_pre:
                disp = tx
                for m in prefix_allomorphs(tx):   # 用單字裡實際出現的拼法 (con-struct, pre-dict)
                    if m and rest.startswith(m):
                        disp, rest = m, rest[len(m):]
                        break
                pre.append(affix_info(disp, "prefix", gl, w))
            suf = [affix_info(tx, "suffix", gl, w) for tx, _, gl in w_suf]
            tx, _, gl = w_roots[0]
            mr = norm(ml["roots"][0])
            r = wdb_root.get(mr) or {}   # 只接受完全相同 (模糊比對會把 resolve 的 solve 配成 sol=太陽)
            zh_word = ""
            # remove = re- + move：字根本身就是常用字 -> 用該字的意思
            # 但如果 Wiktionary 有 "-arch" 這種「構詞成分」詞條 (monarch)，代表字根另有意思，寧可留白
            bound_form = W.get("-" + mr) or W.get(mr + "-")
            if not gl and not r and not bound_form and (mr in exam or mr in ecd):
                zh_word = word_zh(mr)
            root = {"text": norm(ml["roots"][0]), "origin_form": tx,
                    "meaning_en": gl or r.get("meaning", ""),
                    "meaning_zh": short_zh(gloss_to_zh(gl, ecd)) or r.get("meaning_zh") or zh_word}
            roots = [root]
        else:  # base / compound
            pre = [affix_info(tx, "prefix", gl, w) for tx, _, gl in w_pre]
            suf = [affix_info(tx, "suffix", gl, w) for tx, _, gl in w_suf]
            hint = BASE_POS.get(norm(w_suf[-1][0]).strip("-")) if (w_suf and mode == "base") else None
            roots = [{"text": norm(tx), "is_base_word": True, "meaning_zh": word_zh(norm(tx), hint),
                      "meaning_en": gl or ""} for tx, _, gl in w_roots]
        for a in pre + suf:
            if not a["meaning_zh"]:
                missing_affix_zh[a["text"]] += 1
        seq = pre + roots + suf

        def piece_zh(x):
            m = x.get("meaning_zh") or x.get("meaning_en") or ""
            return f"{x['text']}({m})" if m else x["text"]

        def piece_en(x):
            m = x.get("meaning_en") or ""
            return f"{x['text']} ({m})" if m else x["text"]

        verified[w] = {
            "word": w, "status": "verified", "type": mode, "has_affix": bool(pre or suf),
            "prefixes": pre, "root": roots[0], "roots": roots, "suffixes": suf,
            "morphemes": ml,   # MorphoLex 最細拆解 (survival: sur + vive + al)
            "synthesis_zh": " + ".join(piece_zh(x) for x in seq),
            "synthesis_en": " + ".join(piece_en(x) for x in seq),
            "origin": origin,
            "sources": {"morpholex": seg, "wiktionary": " + ".join(p[0] for p in parts),
                        "wiktionary_level": wa["level"]},
        }

    # ---- 沒有共識的字：改用 Wiktionary 古典語源拆解 (單一來源)
    classical = {}
    for w in sorted(conflicts):
        r = classical_analysis(W.get(w, []))
        if not r:
            continue
        lang, parts = r
        # 帶 * 的是語言學家「推測重建」的原始語言形式，不是真的拉丁 / 古英文 -> 不收
        if any(tx.startswith("*") or tx.startswith("-*") for tx, _, _ in parts):
            continue
        # 拆出來的部件如果是 "Latin"、"verb" 這種說明用詞，代表是解析殘留 -> 不收
        if any(norm(tx).strip("-") in META_WORDS for tx, _, _ in parts):
            continue
        n = len(parts)
        items = []
        for i, (tx, kind, gl) in enumerate(parts):
            t = norm(tx).strip("-")
            # 沒有連字號的第一個部件，如果是常見字首 (ab, ad, con) 就當字首
            if kind == "root" and i == 0 and n > 1 and t in PREFIX_IDX and len(t) <= 5 \
                    and lang in ("la", "fr", "fro", "frm", "xno"):
                kind = "prefix"
            if kind == "suffix" and t in {norm(x) for x in LATIN_VERB_END}:
                items.append({"text": tx, "kind": "suffix", "meaning_en": gl or "Latin verb ending",
                              "meaning_zh": "動詞語尾"})
                continue
            if kind == "suffix" and not gl and t in CLASSICAL_SUFFIX_ZH and t not in AFFIX_ZH["suffix"]:
                items.append({"text": tx, "kind": "suffix", "meaning_en": "",
                              "meaning_zh": CLASSICAL_SUFFIX_ZH[t]})
                continue
            if kind in ("prefix", "suffix"):
                zh = AFFIX_ZH[kind].get(t, "") or (CLASSICAL_SUFFIX_ZH.get(t, "") if kind == "suffix" else "")
                en = gl   # 不用英文 Wiktionary 詞綴詞條的第一義 (ad- 會對到 "forming a verb")
                # 有 Wiktionary 註解就用註解 (古英文 bī = "by"，不是字首 bi- 的「二」)
                gz = short_zh(gloss_to_zh(gl, ecd)) if gl else ""
                items.append({"text": tx, "kind": kind, "meaning_en": en or "",
                              "meaning_zh": gz or zh})
            else:
                # 拉丁文 -ō / -re 結尾是動詞 -> 翻譯取動詞義 (regō "lead" -> 引導，不是「鉛」)
                verbish = bool(re.search(r"(ō|o|āre|ēre|ere|īre|ire|er)$", strip_marks(tx) if False else tx)) and lang == "la"
                zh = short_zh(gloss_to_zh(("to " + gl) if (gl and verbish and not gl.lower().startswith("to ")) else gl, ecd))
                # 沒註解、但部件本身就是常見英文字 (abuse = ab- + use)：用該字的意思
                if not gl and re.fullmatch(r"[a-z]+", tx) and tx in exam and lang in ("la", "fr", "fro", "xno", "frm"):
                    zh = word_zh(tx)
                items.append({"text": tx, "kind": "root", "meaning_en": gl or "", "meaning_zh": zh})
        if not any(x["meaning_en"] or x["meaning_zh"] for x in items):
            continue   # 一個部件的意思都沒有 -> 不放 (避免顯示沒意義的東西)
        if not any(x["kind"] == "root" for x in items):
            continue   # 只有詞綴沒有字根 (brilliant = -i- + -ant) -> 不放
        source = None
        for e in W.get(w, [])[:1]:
            for t in e.get("etymology_templates") or []:
                a = t.get("args") or {}
                if t["name"] in ("der", "bor", "inh", "lbor") and a.get("2") == lang and a.get("3") \
                        and not a["3"].endswith("-") and not a["3"].startswith("*"):
                    source = {"form": a.get("3"), "meaning_en": a.get("5") or a.get("t") or ""}
                    break

        def pz(x):
            m = x["meaning_zh"] or x["meaning_en"]
            return f"{x['text']}({m})" if m else x["text"]

        classical[w] = {
            "word": w, "status": "etymology", "lang": lang, "lang_zh": LANG_ZH[lang],
            "source_word": source, "parts": items,
            "synthesis_zh": " + ".join(pz(x) for x in items),
            "note": "Wiktionary 單一來源 (MorphoLex 拆法不同或未收錄)",
            "conflict_reason": conflicts[w]["reason"],
        }
    cl_langs = Counter(v["lang"] for v in classical.values())
    json.dump({"meta": {"built": datetime.now().isoformat(timespec="seconds"),
                        "rule": "兩來源沒有共識的字，列出 Wiktionary 的古典語源拆解 (單一來源)",
                        "count": len(classical), "by_language": dict(cl_langs)},
               "words": classical},
              open(OUT_CLASSICAL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"classical etymology entries: {len(classical)} {dict(cl_langs)}")

    meta = {"built": datetime.now().isoformat(timespec="seconds"),
            "rule": "Wiktionary 與 MorphoLex-en 兩者一致才收錄",
            "sources": ["Wiktionary via kaikki.org (CC-BY-SA)", "MorphoLex-en (CC-BY-NC-SA)"],
            "exam_words": len(exam), "verified": stats["verified"],
            "monomorphemic": stats["monomorphemic"], "conflicts": len(conflicts)}
    json.dump({"meta": meta, "words": verified}, open(OUT_OK, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"meta": meta, "words": conflicts}, open(OUT_CONFLICT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(f"# 字根資料庫交叉驗證報告\n\n建置時間: {meta['built']}\n\n")
        f.write("規則：Wiktionary 與 MorphoLex-en 兩者說法一致才收錄。\n\n")
        f.write("| 項目 | 數量 |\n|---|---:|\n")
        f.write(f"| 考試單字總數 | {len(exam)} |\n")
        f.write(f"| ✅ 兩來源一致：有構詞拆解 | {stats['verified']} |\n")
        f.write(f"| ✅ 兩來源一致：單一詞素 (不可拆) | {stats['monomorphemic']} |\n")
        f.write(f"| ⚠️ MorphoLex 沒收錄 | {stats['no_morpholex']} |\n")
        f.write(f"| ⚠️ Wiktionary 沒收錄 | {stats['no_wiktionary']} |\n")
        for k, v in reasons.most_common():
            f.write(f"| ❌ 衝突：{k} | {v} |\n")
        f.write(f"\n衝突字中，有 {len(classical)} 個改顯示 Wiktionary 古典語源拆解 (單一來源)："
                f"{', '.join(f'{LANG_ZH[k]} {v}' for k, v in cl_langs.most_common())}\n")
        if missing_affix_zh:
            f.write("\n## 尚缺中文意思的詞綴 (請補進 AFFIX_ZH)\n\n")
            for k, v in missing_affix_zh.most_common():
                f.write(f"- `{k}` × {v}\n")
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    print(reasons.most_common())
    print("missing affix zh:", missing_affix_zh.most_common(30))


if __name__ == "__main__":
    main()
