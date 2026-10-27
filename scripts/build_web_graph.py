#!/usr/bin/env python3
"""
build_web_graph.py — Build multi-level graph data for the vocabulary web app.

Reads database/exam_words.json (with structured en/zh definitions),
filters to "exam appeared OR level 1-4",
classifies every word via: situations → en-definition keywords → POS fallback,
and outputs:
  - docs/data/graph.json         (hierarchical graph for Cytoscape.js)
  - docs/data/vocab_data.json    (flat word data for definition popups)
"""

import json, math, re, os
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(r'c:\Users\user\Desktop\github\english')
EXAM_WORDS = BASE / 'database' / 'exam_words.json'
OUT_GRAPH  = BASE / 'docs' / 'data' / 'graph.json'
OUT_VOCAB  = BASE / 'docs' / 'data' / 'vocab_data.json'

# ============================================================
# 1. Taxonomy:  Domain → Category
# ============================================================

TAXONOMY = {
    "Daily Life": {
        "color": "#f59e0b",
        "subcategories": {
            "Home & Family": ["Home & Rooms", "Furniture", "Home Repairs", "Household Appliances", "Family & Relationships", "Cleaning", "Bathroom"],
            "Routine & Lifestyle": ["Daily Routine", "Personal Belongings", "Clothes & Accessories"],
            "Food & Cooking": ["Cooking Methods", "Kitchen Items", "Taste & Texture", "Bread & Grains", "Dairy Products", "Fruits", "Vegetables", "Meat & Seafood", "Drinks", "Nutrition & Food Science", "Restaurant"],
            "Shopping & Finance": ["Shopping & Sales", "Money & Budgeting", "Banking"],
        }
    },
    "School & Education": {
        "color": "#8b5cf6",
        "subcategories": {
            "School Life": ["School", "Classroom", "Exams & Tests", "School Subjects", "University"],
            "Reading & Writing": ["Books & Reading", "Writing", "Academic Language"],
            "Thinking & Learning": ["Learning Skills", "Thinking", "Logic & Reasoning"],
            "Research & Method": ["Research", "Scientific Method", "Laboratory"],
        }
    },
    "Work & Business": {
        "color": "#f97316",
        "subcategories": {
            "Jobs & Workplace": ["Jobs & Careers", "Office", "Meetings", "People & Roles"],
            "Business & Economy": ["Business", "Economics", "Management", "Projects & Planning"],
        }
    },
    "Technology": {
        "color": "#06b6d4",
        "subcategories": {
            "Computers & Internet": ["Computers", "Computer Hardware", "Software", "Internet", "Data & Files"],
            "AI & Programming": ["AI & Computing", "Algorithms & Problem Solving", "Programming Tools", "Cybersecurity", "Networking"],
            "Phones & Media": ["Phones", "Communication"],
        }
    },
    "Transportation": {
        "color": "#3b82f6",
        "subcategories": {
            "Land Travel": ["Cars", "Roads & Traffic", "Road Signs & Rules", "Bicycles", "Public Transport"],
            "Sea & Air": ["Air Travel", "Ships & Boats", "Navigation & Routes"],
            "Travel & Delivery": ["Travel Planning", "Freight & Delivery"],
        }
    },
    "Nature & Environment": {
        "color": "#22c55e",
        "subcategories": {
            "Animals": ["Animals", "Birds", "Insects", "Ocean Life"],
            "Plants & Ecology": ["Trees & Plants", "Flowers", "Environment", "Energy"],
            "Earth & Weather": ["Weather", "Climate", "Landforms", "Earth Science"],
        }
    },
    "Science & Health": {
        "color": "#10b981",
        "subcategories": {
            "Biology & Medicine": ["Biology", "Human Body Science", "Genetics"],
            "Physics & Chemistry": ["Physics", "Chemistry"],
            "Space & Astronomy": ["Space & Astronomy"],
        }
    },
    "Society & Culture": {
        "color": "#ec4899",
        "subcategories": {
            "Government & Law": ["Government", "Politics", "Law & Justice"],
            "Culture & Social": ["Culture", "Languages", "Social Issues", "Cities & Places"],
        }
    },
    "Emotions & Character": {
        "color": "#f472b6",
        "subcategories": {
            "Feelings": ["Emotions"],
            "Goals & Motivation": ["Goals & Decisions"],
        }
    },
    "Description & Logic": {
        "color": "#a78bfa",
        "subcategories": {
            "Comparison & Degree": ["Comparison"],
            "Cause & Change": ["Cause & Effect", "Change & Development"],
            "Time & Position": ["Time & Sequence", "Position & Direction"],
        }
    },
}

# Build reverse: situation → (domain, subcategory)
SIT_TO_PATH = {}
for domain, info in TAXONOMY.items():
    for subcat, sits in info["subcategories"].items():
        for sit in sits:
            SIT_TO_PATH[sit] = (domain, subcat)

# ============================================================
# 2. Keyword-based classification using English definitions
#    Each rule: (set_of_keywords, min_match_count, domain, subcat)
#    We use set intersection for speed.
# ============================================================

def _kw(s):
    """Split keyword string into a set of words."""
    return set(s.lower().split())

KEYWORD_RULES = [
    # --- Nature & Environment ---
    (_kw("animal bird fish insect creature mammal reptile whale shark dolphin tiger lion bear elephant monkey snake butterfly bee ant spider cat dog horse cow pig chicken duck goose deer rabbit mouse rat frog turtle fox wolf bat eagle hawk parrot penguin owl crow pigeon swan pet puppy kitten paw tail claw wing fur feather horn tusk hoof nest den zoo wildlife"), 1, "Nature & Environment", "Animals"),
    (_kw("plant tree flower leaf seed root branch grass bush garden forest bloom blossom herb vine rose lily tulip orchid weed bamboo pine palm oak maple petal stem trunk bark moss fern shrub crop harvest botany botanical vegetation flora sprout grow cultivate"), 1, "Nature & Environment", "Plants & Ecology"),
    (_kw("environment pollution recycle ecology ecosystem carbon waste solar renewable conservation greenhouse ozone deforestation endangered extinct habitat organic biodiversity sustain emission contamination"), 1, "Nature & Environment", "Plants & Ecology"),
    (_kw("rain snow wind storm cloud sunny weather temperature humid fog thunder lightning flood drought tornado hurricane freeze frost climate season forecast hail mist dew breeze gale monsoon"), 1, "Nature & Environment", "Earth & Weather"),
    (_kw("mountain river ocean sea lake island valley desert volcano earthquake cave cliff shore coast beach land soil rock stone sand continent peninsula glacier canyon waterfall hill marsh swamp reef coral terrain geology geographical"), 1, "Nature & Environment", "Earth & Weather"),
    (_kw("energy solar nuclear fuel coal oil gas petroleum electricity renewable power generator turbine battery charge solar wind hydroelectric thermal geothermal biomass fossil"), 1, "Nature & Environment", "Plants & Ecology"),

    # --- Science & Health ---
    (_kw("cell organ tissue bone muscle brain heart lung blood nerve skin stomach liver kidney dna gene protein vitamin bacteria virus immune disease symptom diagnose treatment medical health doctor patient hospital clinic nurse surgery pill drug infection cure heal illness sick pain wound injury fever cough prescription therapy medicine anatomy biological organism chromosome microbe pathogen antibiotic vaccine epidemic pandemic"), 1, "Science & Health", "Biology & Medicine"),
    (_kw("atom molecule electron proton neutron ion element compound reaction acid base solution gas liquid solid crystal metal chemical hydrogen oxygen carbon nitrogen formula periodic chemistry laboratory experiment substance mixture catalyst enzyme oxidation corrosion dissolve evaporate condense"), 1, "Science & Health", "Physics & Chemistry"),
    (_kw("force energy gravity magnet electric current voltage circuit wave frequency radiation laser nuclear particle quantum velocity momentum acceleration friction pressure density mass weight optic lens mirror reflect refract spectrum sound vibrate heat thermal physics mechanics thermodynamic"), 1, "Science & Health", "Physics & Chemistry"),
    (_kw("planet star sun moon orbit galaxy universe comet asteroid satellite astronaut telescope cosmos spacecraft rocket constellation celestial solar nebula supernova black meteorite astronomy astronomical"), 1, "Science & Health", "Space & Astronomy"),

    # --- Daily Life ---
    (_kw("food eat cook meal dish recipe bake fry boil roast grill stew soup salad sauce spice flavor taste delicious appetite hunger bread cake pie pizza pasta noodle rice cereal grain flour dough butter cheese cream milk yogurt egg sugar salt pepper honey chocolate candy dessert snack breakfast lunch dinner supper menu chef restaurant cafe beverage juice tea coffee fruit apple banana orange grape strawberry watermelon lemon mango cherry peach pear tomato potato onion garlic carrot cabbage lettuce cucumber corn bean pea spinach mushroom beef pork lamb steak ham bacon sausage shrimp lobster crab salmon tuna tofu vegetarian"), 1, "Daily Life", "Food & Cooking"),
    (_kw("home house room kitchen bedroom bathroom living door window wall floor ceiling roof stair garage yard apartment furniture table chair sofa bed desk shelf drawer cabinet closet lamp curtain carpet pillow blanket towel mirror clock decoration household laundry wash clean sweep mop vacuum tidy garbage trash repair fix paint hammer nail pipe plumb wire plug socket faucet sink toilet shower stove oven microwave fridge refrigerator freezer dishwasher blender toaster kettle heater fan"), 1, "Daily Life", "Home & Family"),
    (_kw("family parent father mother dad mom brother sister son daughter husband wife uncle aunt cousin nephew niece grandparent grandfather grandmother baby infant child kid teen adult elder marry wedding divorce pregnant birth relative ancestor generation sibling spouse"), 1, "Daily Life", "Home & Family"),
    (_kw("wear cloth dress shirt pants jeans skirt coat jacket sweater suit uniform hat cap scarf glove sock shoe boot sandal tie belt pocket button zipper sleeve collar fashion style fabric cotton silk wool leather nylon pattern stripe casual formal"), 1, "Daily Life", "Routine & Lifestyle"),
    (_kw("daily routine morning evening wake sleep nap shower bath brush comb shave soap shampoo toothbrush towel deodorant perfume makeup lotion umbrella bag purse wallet key watch glasses sunglasses jewelry necklace bracelet ring earring backpack suitcase luggage"), 1, "Daily Life", "Routine & Lifestyle"),
    (_kw("shop store mall market supermarket price cost cheap expensive buy purchase sell sale discount coupon bargain brand product customer consumer receipt cashier checkout cart basket wrap deliver order payment credit debit cash coin bill change refund exchange warranty commercial advertise"), 1, "Daily Life", "Shopping & Finance"),
    (_kw("money dollar cent euro pound currency budget save spend earn income salary wage profit loss invest stock bank account deposit withdraw loan debt owe tax interest inflation insurance finance financial wealth"), 1, "Daily Life", "Shopping & Finance"),

    # --- School & Education ---
    (_kw("school class classroom student teacher professor lecture lesson course subject math history geography literature art music homework assignment project essay exam test quiz grade score mark pass fail graduate diploma degree major semester campus college university principal dean scholarship tuition academic study learn teach educate curriculum textbook notebook pencil pen eraser chalk blackboard"), 1, "School & Education", "School Life"),
    (_kw("read write book library novel story fiction poem poetry author writer editor publish chapter page paragraph sentence word vocabulary grammar spell pronounce syllable phrase clause idiom metaphor literary journal magazine newspaper article column headline editorial review genre biography myth legend fable text"), 1, "School & Education", "Reading & Writing"),
    (_kw("think thought idea concept theory opinion believe suppose assume consider reflect ponder wonder imagine guess expect predict conclude reason logic rational critical analyze evaluate judge decide solve problem solution strategy method approach understand comprehend interpret infer imply deduce abstract hypothesis argue debate define explain describe compare contrast distinguish classify summarize demonstrate prove evidence principle philosophy"), 1, "School & Education", "Thinking & Learning"),
    (_kw("research experiment data result finding conclusion observation measure survey sample variable control statistic procedure hypothesis evidence analyze laboratory scientific discovery investigate examine explore test trial observe record publish peer review"), 1, "School & Education", "Research & Method"),

    # --- Work & Business ---
    (_kw("work job career profession occupation employ hire fire resign retire boss manager director executive president company corporation firm office desk meeting conference interview resume apply experience skill qualify promote position title department team colleague staff employee employer client contract deadline schedule task duty responsible salary overtime bonus benefit pension vacation union"), 1, "Work & Business", "Jobs & Workplace"),
    (_kw("business economy economic industry manufacture factory produce production product supply demand market trade export import capital profit revenue expense budget finance account tax inflation recession growth develop commercial enterprise entrepreneur venture compete competition innovation brand marketing retail wholesale merchant"), 1, "Work & Business", "Business & Economy"),

    # --- Technology ---
    (_kw("computer laptop desktop keyboard mouse screen monitor printer scanner hardware software program application app system file folder document download upload install delete copy paste click drag scroll type internet online website web page link email password login digital pixel memory storage processor battery charger device gadget robot automate artificial intelligence algorithm code virtual reality sensor chip circuit binary"), 1, "Technology", "Computers & Internet"),
    (_kw("phone smartphone cellphone mobile telephone call text message chat communicate contact dial ring answer voicemail notification signal social media blog post share follow stream broadcast television radio channel"), 1, "Technology", "Phones & Media"),

    # --- Transportation ---
    (_kw("car vehicle truck van bus taxi drive driver ride passenger seat engine motor wheel tire brake speed highway road street lane intersection traffic light signal sign stop park gas fuel station mechanic accident crash collision damage license motorcycle scooter bicycle bike pedal helmet train rail subway metro station platform track ticket fare commute route bridge tunnel"), 1, "Transportation", "Land Travel"),
    (_kw("fly flight airplane plane aircraft jet helicopter airport terminal gate runway takeoff landing pilot crew cabin luggage baggage passport visa customs departure arrival ship boat ferry cruise yacht sail anchor port harbor dock captain deck submarine canoe kayak paddle navigate voyage maritime naval cargo freight container warehouse deliver shipment courier postal mail package parcel"), 1, "Transportation", "Sea & Air"),
    (_kw("travel trip tour journey vacation holiday destination tourist visitor sightsee explore adventure camp hike trail guide map itinerary reservation booking hotel motel hostel resort accommodation souvenir abroad overseas international foreign"), 1, "Transportation", "Travel & Delivery"),

    # --- Society & Culture ---
    (_kw("govern government president minister congress parliament senate politician politics political party election vote campaign candidate policy law legal illegal court judge jury trial verdict sentence prison crime criminal arrest police officer detective evidence witness victim guilty innocent lawyer attorney rights freedom constitution bill regulate rule enforce penalty justice citizen nation federal authority democracy republic monarchy dictator"), 1, "Society & Culture", "Government & Law"),
    (_kw("culture cultural tradition custom ceremony festival celebrate heritage ethnic race minority diverse diversity discrimination prejudice stereotype gender civil immigrant refugee poverty charity volunteer community society religion religious spiritual church temple pray worship faith god moral ethic value virtue art museum gallery exhibit concert opera orchestra band instrument guitar piano violin drum sing song melody rhythm compose lyric classic modern contemporary"), 1, "Society & Culture", "Culture & Social"),

    # --- Emotions & Character ---
    (_kw("happy sad angry afraid scared fear worry anxious nervous stress depress lonely bored tired frustrate confuse surprise shock excite thrill proud shame embarrass guilt jealous envy grateful content satisfy disappoint regret sympathy empathy compassion forgive trust respect admire appreciate hate disgust annoy irritate offend insult hurt comfort relief hope mood feeling emotion passion enthusias eager willing reluctant hesitant confident shy bold brave courageous calm patient gentle kind cruel generous selfish humble honest sincere loyal faithful stubborn determined ambitious curious creative sensitive cheer delight joy pleasure laugh smile cry tear weep sob sigh scream shout yell whisper murmur groan giggle grin frown hug kiss embrace compliment praise blame criticize apologize encourage motivate inspire persuade convince urge refuse reject deny accept agree disagree argue quarrel fight conflict compromise negotiate cooperate"), 1, "Emotions & Character", "Feelings"),
    (_kw("goal decide decision choose choice aim purpose intend intention plan ambition achieve accomplish success succeed motivate aspire inspire dream wish desire purpose objective target effort persevere determine resolve commitment dedicate devote focus priority"), 1, "Emotions & Character", "Goals & Motivation"),

    # --- Description & Logic ---
    (_kw("compare comparison similar same different opposite equal superior inferior exceed surpass rather than prefer although however nevertheless whereas while instead otherwise"), 1, "Description & Logic", "Comparison & Degree"),
    (_kw("cause effect result consequence therefore thus hence accordingly lead contribute influence affect impact outcome because since due owing factor reason why"), 1, "Description & Logic", "Cause & Change"),
    (_kw("change develop evolve transform convert modify alter adjust adapt improve progress advance increase decrease reduce expand grow shrink shift vary reform innovate"), 1, "Description & Logic", "Cause & Change"),
    (_kw("time sequence first second third next then before after during while until since already still yet soon recently lately finally eventually immediately suddenly gradually frequently seldom rarely often always never sometimes usually early late begin start end finish continue last"), 1, "Description & Logic", "Time & Position"),
    (_kw("position direction above below top bottom front back left right side middle center edge corner near far close distant inside outside between among around through across along toward away here there everywhere north south east west upper lower forward backward upward downward"), 1, "Description & Logic", "Time & Position"),
]


def classify_by_definition(word, entry):
    """Use English definition keywords to classify a word."""
    defs = entry.get("definitions", {})
    if isinstance(defs, dict):
        en_defs = defs.get("en", [])
    elif isinstance(defs, list):
        en_defs = [d for d in defs if isinstance(d, str) and not re.search(r'[\u4e00-\u9fff]', d)]
    else:
        en_defs = []
    
    if not en_defs:
        return None
    
    # Build word set from word itself + all definitions
    text = f"{word} " + " ".join(en_defs)
    text_words = set(re.findall(r'[a-z]+', text.lower()))
    
    best_match = None
    best_count = 0
    
    for keywords, min_count, domain, subcat in KEYWORD_RULES:
        overlap = len(text_words & keywords)
        if overlap >= min_count and overlap > best_count:
            best_count = overlap
            best_match = (domain, subcat)
    
    return best_match


def classify_word(word, entry):
    """Return (domain, subcategory) for a word."""
    # 1. Situations
    situations = entry.get("situations", [])
    if situations:
        for sit in situations:
            if sit in SIT_TO_PATH:
                return SIT_TO_PATH[sit]
    
    # 2. Definition keywords
    result = classify_by_definition(word, entry)
    if result:
        return result
    
    # 3. POS fallback
    pos_list = entry.get("pos", [])
    primary_pos = pos_list[0] if pos_list else "n."
    
    POS_FALLBACK = {
        "n.":      ("General Vocabulary", "Nouns"),
        "v.":      ("General Vocabulary", "Verbs"),
        "adj.":    ("General Vocabulary", "Adjectives & Adverbs"),
        "adv.":    ("General Vocabulary", "Adjectives & Adverbs"),
        "prep.":   ("General Vocabulary", "Function Words"),
        "conj.":   ("General Vocabulary", "Function Words"),
        "pron.":   ("General Vocabulary", "Function Words"),
        "aux.":    ("General Vocabulary", "Function Words"),
        "art.":    ("General Vocabulary", "Function Words"),
        "interj.": ("General Vocabulary", "Function Words"),
    }
    return POS_FALLBACK.get(primary_pos, ("General Vocabulary", "Other"))


def build_word_data(word, entry):
    """Extract word data for the vocab popup."""
    defs = entry.get("definitions", {})
    if isinstance(defs, dict):
        en_defs = defs.get("en", [])
        zh_defs = defs.get("zh", [])
    elif isinstance(defs, list):
        en_defs = [d for d in defs if isinstance(d, str) and not re.search(r'[\u4e00-\u9fff]', d)]
        zh_defs = [d for d in defs if isinstance(d, str) and re.search(r'[\u4e00-\u9fff]', d)]
    else:
        en_defs = []
        zh_defs = []
    
    return {
        "w": word,
        "lv": entry.get("level", 0),
        "pos": entry.get("pos", []),
        "en": en_defs,
        "zh": zh_defs,
        "forms": entry.get("forms", {}),
        "fam": entry.get("word_family", []),
        "exam": entry.get("appear_year", []),
        "cnt": entry.get("total_appear", 0),
    }


def make_id(text):
    """Convert text to a safe node ID."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def main():
    print("Loading exam_words.json ...")
    with open(EXAM_WORDS, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_words = data["words"]
    
    # Filter: appeared in exams OR level 1-4
    filtered = {
        w: v for w, v in all_words.items()
        if v.get("total_appear", 0) > 0 or v.get("level", 99) <= 4
    }
    print(f"Filtered: {len(filtered)} words (exam appeared or L1-4)")
    
    # Ensure extra taxonomy entries
    if "General Vocabulary" not in TAXONOMY:
        TAXONOMY["General Vocabulary"] = {
            "color": "#64748b",
            "subcategories": {
                "Nouns": [],
                "Verbs": [],
                "Adjectives & Adverbs": [],
                "Function Words": [],
            }
        }
    
    # Classify each word
    tree = defaultdict(lambda: defaultdict(list))
    vocab_data = {}
    source = Counter()
    
    for word, entry in sorted(filtered.items()):
        domain, subcat = classify_word(word, entry)
        tree[domain][subcat].append(word)
        vocab_data[word] = build_word_data(word, entry)
        
        if entry.get("situations") and any(s in SIT_TO_PATH for s in entry["situations"]):
            source["situation"] += 1
        elif classify_by_definition(word, entry):
            source["en_keyword"] += 1
        else:
            source["pos_fallback"] += 1
    
    print(f"\nClassification sources: {dict(source)}")
    print(f"\nClassification result:")
    total = 0
    for domain in sorted(tree.keys()):
        subcats = tree[domain]
        domain_total = sum(len(ws) for ws in subcats.values())
        total += domain_total
        print(f"  {domain}: {domain_total} words")
        for subcat in sorted(subcats.keys()):
            print(f"    {subcat}: {len(subcats[subcat])} words")
    print(f"  TOTAL: {total}")
    
    # ============================================================
    # Build graph.json
    # ============================================================
    nodes = []
    edges = []
    
    nodes.append({
        "id": "life",
        "label": "Vocabulary",
        "type": "root",
    })
    
    domain_list = [d for d in TAXONOMY.keys() if d in tree]
    for d in tree:
        if d not in domain_list:
            domain_list.append(d)
    
    angle_step = 360 / max(len(domain_list), 1)
    
    for i, domain in enumerate(domain_list):
        domain_id = make_id(domain)
        angle = -90 + i * angle_step
        angle_rad = math.radians(angle)
        color = TAXONOMY.get(domain, {}).get("color", "#64748b")
        word_count = sum(len(ws) for ws in tree[domain].values())
        
        nodes.append({
            "id": domain_id,
            "label": domain,
            "type": "domain",
            "color": color,
            "word_count": word_count,
            "x": round(math.cos(angle_rad) * 250, 1),
            "y": round(math.sin(angle_rad) * 250, 1),
        })
        edges.append({"source": "life", "target": domain_id, "type": "contains"})
        
        subcats = sorted(tree[domain].keys())
        sub_step = 360 / max(len(subcats), 1)
        
        for j, subcat in enumerate(subcats):
            subcat_id = f"{domain_id}__{make_id(subcat)}"
            sub_angle = j * sub_step
            word_list = tree[domain][subcat]
            
            nodes.append({
                "id": subcat_id,
                "label": subcat,
                "type": "category",
                "color": color,
                "parent_domain": domain_id,
                "word_count": len(word_list),
                "angle_degrees": sub_angle,
            })
            edges.append({"source": domain_id, "target": subcat_id, "type": "contains"})
            
            # Split large groups
            if len(word_list) > 25:
                level_groups = defaultdict(list)
                for w in word_list:
                    lv = vocab_data[w]["lv"]
                    if lv <= 2:
                        level_groups["Basic (L1-2)"].append(w)
                    elif lv <= 4:
                        level_groups["Intermediate (L3-4)"].append(w)
                    else:
                        level_groups["Advanced (L5-6)"].append(w)
                
                k = 0
                lv_step = 360 / max(len([g for g in level_groups.values() if g]), 1)
                for lv_label in ["Basic (L1-2)", "Intermediate (L3-4)", "Advanced (L5-6)"]:
                    lv_words = level_groups.get(lv_label, [])
                    if not lv_words:
                        continue
                    lv_id = f"{subcat_id}__{make_id(lv_label)}"
                    
                    nodes.append({
                        "id": lv_id,
                        "label": lv_label,
                        "type": "level_group",
                        "color": color,
                        "parent_domain": domain_id,
                        "word_count": len(lv_words),
                        "words": lv_words,
                        "angle_degrees": k * lv_step,
                    })
                    edges.append({"source": subcat_id, "target": lv_id, "type": "contains"})
                    k += 1
            else:
                # Attach words directly
                for n in nodes:
                    if n["id"] == subcat_id:
                        n["words"] = word_list
                        break
    
    graph_out = {
        "version": 2,
        "total_words": len(filtered),
        "graph": {
            "description": "Multi-level vocabulary graph. Vocabulary → Domain → Category → [Level Group] → Words",
            "root_node_id": "life",
            "nodes": nodes,
            "edges": edges,
        }
    }
    
    os.makedirs(OUT_GRAPH.parent, exist_ok=True)
    with open(OUT_GRAPH, 'w', encoding='utf-8') as f:
        json.dump(graph_out, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {OUT_GRAPH} ({len(nodes)} nodes, {len(edges)} edges)")
    
    with open(OUT_VOCAB, 'w', encoding='utf-8') as f:
        json.dump(vocab_data, f, ensure_ascii=False)
    size_kb = os.path.getsize(OUT_VOCAB) // 1024
    print(f"Wrote {OUT_VOCAB} ({len(vocab_data)} words, {size_kb} KB)")
    
    type_counts = Counter(n["type"] for n in nodes)
    print(f"Node types: {dict(type_counts)}")
    leaf_count = sum(1 for n in nodes if "words" in n)
    print(f"Leaf nodes (with words): {leaf_count}")


if __name__ == "__main__":
    main()
