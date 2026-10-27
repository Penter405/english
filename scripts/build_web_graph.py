#!/usr/bin/env python3
"""
build_web_graph.py — Build graph and vocabulary data for the web app.

Preserves the original 10-domain × 10-topic geometric layout (with exact x, y, angle_degrees),
populates each topic with the 4,244 exam/level 1-4 words,
and removes all basic/medium/hard level nodes so clicking a topic directly opens
the group view with the 6 levels.

Outputs:
  - docs/data/graph.json
  - docs/data/vocab_data.json
"""

import json
import math
import os
import re
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(r'c:\Users\user\Desktop\github\english')
EXAM_WORDS_PATH = BASE / 'database' / 'exam_words.json'
ORIGINAL_GRAPH_PATH = BASE / 'database' / 'topic_vocabulary_graph.json'
OUT_GRAPH = BASE / 'docs' / 'data' / 'graph.json'
OUT_VOCAB = BASE / 'docs' / 'data' / 'vocab_data.json'

TOPIC_KEYWORDS = {
    # Food
    "Fruits": "fruit apple banana orange grape strawberry watermelon lemon mango cherry peach pear plum berry",
    "Vegetables": "vegetable tomato potato onion garlic carrot cabbage lettuce cucumber corn bean pea spinach mushroom",
    "Meat & Seafood": "meat beef pork lamb steak ham bacon sausage chicken turkey fish shrimp lobster crab oyster salmon tuna",
    "Dairy Products": "dairy milk cheese butter cream yogurt",
    "Bread & Grains": "bread wheat flour grain rice cereal oats toast bakery sandwich dough crust pasta noodle",
    "Drinks": "drink beverage water tea coffee juice soda wine beer cocktail alcohol liquid bottle sip",
    "Cooking Methods": "cook bake fry boil roast grill stew steam stir simmer heat oven stove recipe",
    "Restaurant": "restaurant cafe menu chef waiter waitress dine dinner buffet order meal feast customer dish",
    "Taste & Texture": "taste flavor delicious sweet sour bitter salty spicy crispy crunchy tender spicy smell aroma",
    "Nutrition & Food Science": "nutrition vitamin protein calorie mineral diet nutrient healthy appetite starve digest",

    # Home life
    "Home & Rooms": "room bedroom living basement attic balcony porch floor ceiling wall door window roof house apartment home garage yard",
    "Furniture": "furniture table chair sofa couch bed desk shelf drawer cabinet closet mirror carpet rug curtain lamp",
    "Kitchen Items": "kitchen plate bowl fork spoon knife pan pot dish kettle blender toaster microwave fridge refrigerator cup glass",
    "Bathroom": "bathroom toilet shower bathtub towel sink faucet soap shampoo mirror toothbrush razor",
    "Cleaning": "clean sweep mop vacuum wash rinse tidy wipe dust bleach sanitize hygiene detergent chore mess dirt",
    "Clothes & Accessories": "cloth wear dress shirt pants jeans skirt coat jacket sweater suit uniform hat cap scarf glove sock shoe boot belt tie pocket button zipper fashion",
    "Personal Belongings": "bag purse wallet backpack suitcase luggage umbrella watch glasses sunglasses jewelry necklace ring earring key identity card phone camera passport",
    "Daily Routine": "routine morning evening wake sleep nap rest brush comb shave alarm habit schedule daily everyday midnight noon",
    "Home Repairs": "repair fix hammer nail screw tool drill paint pipe leak wire plug socket broken damage maintenance",
    "Household Appliances": "appliance heater air conditioner fan vacuum iron washer dryer stove dishwasher blender",

    # Transport
    "Cars": "car automobile vehicle truck van engine motor wheel tire brake pedal wheel steering driver passenger seat speed highway trunk",
    "Roads & Traffic": "road street lane intersection traffic signal avenue boulevard pavement curb detour sidewalk crossroad congestion rush",
    "Public Transport": "subway metro train bus trolley tram transit station passenger fare ticket conductor commuter route",
    "Bicycles": "bicycle bike cycle pedal handlebar chain helmet rider pump saddle",
    "Road Signs & Rules": "sign speed limit parking stop permit license penalty fine violation rule lane officer police yield",
    "Air Travel": "fly flight airplane plane aircraft jet airline airport terminal gate runway pilot takeoff landing boarding crew cockpit customs passport",
    "Ships & Boats": "ship boat vessel ferry sail anchor harbor port dock deck ocean voyage naval yacht cargo submarine paddle raft marine",
    "Travel Planning": "travel trip journey tour vacation holiday destination tourist resort guide explore adventure map itinerary reservation booking hotel motel pack baggage luggage sightsee",
    "Freight & Delivery": "freight cargo shipping delivery package parcel courier warehouse postage logistics load unload transport",
    "Navigation & Routes": "navigation compass gps route direction map distance latitude longitude detour journey explore guide track",

    # Technology
    "Computers": "computer laptop desktop pc monitor screen keyboard mouse processor memory disk software hardware digital electronic machine user system server",
    "Phones": "phone telephone mobile cellular call text message sms ring voicemail smartphone screen dial app notification wireless",
    "Computer Hardware": "hardware chip processor cpu gpu ram drive motherboard component printer scanner cable port sensor usb device",
    "Software": "software program application app installer code platform bug patch version operating windows mac linux feature update",
    "Internet": "internet online web website browser link url domain page cyber net wifi portal upload download streaming surf click",
    "Programming Tools": "code program script debug compile algorithm python java syntax developer tool framework terminal variable command function",
    "Cybersecurity": "security cyber hack virus malware firewall password encrypt protection threat breach identity authentic privacy safety",
    "Data & Files": "data file database folder record storage archive document backup byte binary format information query entry",
    "AI & Computing": "artificial intelligence robot automated smart machine neural model algorithm cognition virtual recognition autonomous computing",
    "Networking": "network protocol server connection router modem bandwidth packet wireless ip switch lan wire transmission",

    # Education
    "School": "school student teacher campus classroom principal education grade learn study educate institution tuition semester term homework bell",
    "Classroom": "classroom desk blackboard whiteboard marker chalk lecture seat projector lesson attendance presentation pupil",
    "School Subjects": "subject math mathematics history geography physics chemistry biology science literature art music PE arithmetic",
    "Exams & Tests": "exam test quiz score mark grade evaluate pass fail assess assessment answer question result certification diploma",
    "University": "university college professor degree bachelor master doctor graduate faculty academic dean scholarship campus dissertation lecture",
    "Learning Skills": "learn study memorize practice skill exercise review repeat understand grasp master tutor technique discipline comprehend",
    "Books & Reading": "book novel story read reading author literature chapter page library volume volume text poem fiction tale publication",
    "Writing": "write handwriting essay composition pen pencil draft sentence paragraph article paper author manuscript spell compose",
    "Academic Language": "academic theory hypothesis thesis abstract term analysis concept argument definition context reference cited scholarly principle",
    "Languages": "language word vocabulary speak speech voice native foreign english translate translation dialect grammar linguistic phrase tongue",

    # Work
    "Jobs & Careers": "job career profession occupation work employee employer profession career position trade resume interview hire fire salary vacancy vocation labor",
    "Office": "office workspace desk cubicle corporate colleague staff paperwork document department agency fax printer chair copier",
    "Business": "business company corporation enterprise commercial firm industry commerce transaction client merchandise vendor market trade deal trade",
    "Meetings": "meeting conference discuss discussion agenda presentation schedule boardroom negotiate negotiation debate attend collaborate minutes",
    "Projects & Planning": "project plan goal objective schedule timeline milestone deadline manage task strategy progress team organize allocate execute",
    "Management": "manage manager leader leadership supervisor director control administer organize decision team staff guide supervise delegate",
    "Economics": "economy economic inflation market demand supply capital inflation recession wealth trade commerce consumption enterprise finance gross deficit",
    "Money & Budgeting": "money cash currency budget cost price expense fund finance spend save debt loan pay payment credit coin dollar bill afford",
    "Banking": "bank banker account deposit withdraw saving interest loan transfer credit debit mortgage teller balance account fund",
    "Shopping & Sales": "shop store market supermarket buy purchase sell sale retail customer price discount refund counter receipt cashier bargain mall",

    # Society
    "Family & Relationships": "family parent father mother dad mom brother sister child son daughter husband wife marry wedding divorce relative baby ancestor sibling partner relation",
    "People & Roles": "person people human individual man woman adult youth boy girl kid citizen member neighbor friend companion folk stranger fellow",
    "Communication": "communicate communication message conversation chat discuss express contact speak inform inform dialogue tell talk reply listen announce signal",
    "Social Issues": "social society community issue problem poverty crime welfare discrimination homeless justice equality racism public population citizen reform",
    "Government": "government governor authority administration federal state minister public official democracy policy regime agency department congress official",
    "Politics": "politics political party election candidate vote ballot campaign leader parliament senate debate policy power diplomat diplomacy",
    "Law & Justice": "law legal illegal court judge jury trial lawyer justice crime criminal police prison jail rights sue verdict penalty guilt innocent arrest",
    "Culture": "culture cultural tradition custom heritage ethnic ceremony festival ritual celebration belief monument temple civilization folklore",
    "Cities & Places": "city town village urban rural country district capital province county municipality street square plaza community suburb metropolis",
    "Algorithms & Problem Solving": "algorithm problem solve solution logical calculate puzzle trouble challenge optimize step process method formula outcome resolve",

    # Abstract
    "Emotions": "happy sad angry anger joy sorrow fear afraid fear worry anxiety glad delight hate love passion grief emotion feel feeling cheer mood",
    "Thinking": "think thought imagine mind consider contemplate ponder wonder reflect conceive remember memory recall believe view opinion suppose assume",
    "Goals & Decisions": "goal decision decide choice choose aim purpose ambition objective intend plan determination resolve dream target achieve accomplish succeed",
    "Logic & Reasoning": "logic logical reason reasoning rational prove proof conclusion infer inference deduction argument validity truth premise evidence principle",
    "Time & Sequence": "time minute hour day week month year century decade future past present sequence moment period era phase delay interval schedule",
    "Position & Direction": "position direction place location point north south east west center middle top bottom upper lower left right forward backward behind near far",
    "Comparison": "compare comparison similar difference equal distinguish contrast resemble vary match superior inferior degree relate measure alternative",
    "Cause & Effect": "cause effect result reason consequence lead produce induce outcome because factor generate impact impact affect origin basis",
    "Change & Development": "change alter vary evolve transform develop development grow growth increase decrease modify improve advance progress expand reform shift transition",
    "Scientific Method": "science scientific experiment laboratory observe observation data hypothesis test measure verify analyze discovery research evidence finding",

    # Science
    "Physics": "physics matter atom particle force motion energy mass acceleration gravity quantum speed velocity friction weight electric electricity magnetic wave",
    "Chemistry": "chemistry chemical element molecule reaction compound formula substance acid gas liquid solution crystal dissolve synthesize laboratory",
    "Biology": "biology biological cell organ tissue organism species creature reproduction ecosystem life living breed evolution nature botanic zoology",
    "Space & Astronomy": "space astronomy star planet moon sun galaxy orbit cosmic telescope universe solar comet asteroid mars astronaut satellite rocket",
    "Earth Science": "earth geography geology rock soil mineral mountain continent plate volcano earthquake glacier fossil ground terrain sediment cave",
    "Environment": "environment nature ecological ecology conserve conservation preserve pollution green waste global recycle sustainable climate habitat ecosystem",
    "Energy": "energy power solar fuel oil coal gas petroleum electricity turbine battery generator wind nuclear renewable engine burn thermal",
    "Human Body Science": "body bone blood muscle brain heart lung skin nerve stomach liver organ limb vein artery spine skeleton physical breath",
    "Genetics": "genetics gene dna chromosome hereditary inherit trait clone mutation breeding biological organism evolution sequence code",
    "Laboratory": "laboratory lab experiment test trial microscope beaker sample pipette instrument analysis scientific equipment technician observe",

    # Nature
    "Trees & Plants": "tree plant leaf branch forest wood root bark grass bush seed sprout stem timber grove botanical foliage pine oak jungle",
    "Flowers": "flower blossom bloom rose petal lily bouquet garden orchid floral tulip bud pollen flora blossom scent violet lotus",
    "Animals": "animal beast creature pet mammal dog cat horse cow sheep pig lion tiger bear elephant monkey deer rabbit wolf fox wildlife",
    "Birds": "bird feather wing beak nest egg eagle hawk owl parrot penguin swan pigeon sparrow crow fly tweet plumage flock avian",
    "Insects": "insect bug ant bee butterfly mosquito spider fly beetle moth caterpillar wasp worm pest sting crawl web cocoon",
    "Ocean Life": "ocean sea fish marine shark whale dolphin coral crab shrimp squid shell reef turtle octopus tide wave depth aquatic",
    "Weather": "weather rain storm cloud wind snow temperature cold hot warm sunny foggy thunder lightning climate freeze frost humid breeze",
    "Climate": "climate season spring summer autumn winter atmospheric global warming tropical temperate polar zone dry rainfall drought meteorology",
    "Landforms": "landform island valley desert hill plain plateau peninsula cliff coast beach ocean shore canyon peak basin cape marsh meadow",
}


def build_word_data(word, entry):
    """Build word metadata for the definition popup."""
    defs = entry.get('definitions', {})
    if isinstance(defs, dict):
        en_defs = defs.get('en', [])
        zh_defs = defs.get('zh', [])
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


def main():
    print("Loading original graph template...")
    with open(ORIGINAL_GRAPH_PATH, 'r', encoding='utf-8') as f:
        orig_data = json.load(f)

    orig_nodes = orig_data['graph']['nodes']
    orig_edges = orig_data['graph']['edges']

    topic_by_label = {}
    topic_by_id = {}
    for n in orig_nodes:
        if n['type'] == 'topic':
            topic_by_label[n['label']] = n['id']
            topic_by_id[n['id']] = n

    print(f"Found {len(topic_by_id)} topics across 10 domains in original graph.")

    # Precompile keyword token sets
    kw_sets = {}
    for label, text in TOPIC_KEYWORDS.items():
        if label in topic_by_label:
            tid = topic_by_label[label]
            kw_sets[tid] = set(re.findall(r'[a-z]+', text.lower()))

    # Load exam words
    print("Loading exam_words.json...")
    with open(EXAM_WORDS_PATH, 'r', encoding='utf-8') as f:
        exam_data = json.load(f)

    words = exam_data['words']
    filtered = {
        w: v for w, v in words.items()
        if v.get('total_appear', 0) > 0 or v.get('level', 99) <= 4
    }
    print(f"Filtered {len(filtered)} words (exam appeared or L1-4).")

    # Map words to the 100 topics
    topic_words = defaultdict(list)
    vocab_data = {}
    methods = Counter()

    for w, entry in sorted(filtered.items()):
        vocab_data[w] = build_word_data(w, entry)

        # 1. Exact situation match
        matched_tid = None
        sits = entry.get('situations', [])
        for s in sits:
            if s in topic_by_label:
                matched_tid = topic_by_label[s]
                methods['situation'] += 1
                break

        # 2. English definition keyword match
        if not matched_tid:
            defs = entry.get('definitions', {})
            en_defs = defs.get('en', []) if isinstance(defs, dict) else []
            text = f"{w} " + " ".join(en_defs)
            tokens = set(re.findall(r'[a-z]+', text.lower()))

            best_tid = None
            best_score = 0
            for tid, kws in kw_sets.items():
                score = len(tokens & kws)
                if score > best_score:
                    best_score = score
                    best_tid = tid

            if best_tid and best_score >= 1:
                matched_tid = best_tid
                methods['keyword'] += 1

        # 3. Fallback by POS
        if not matched_tid:
            pos_list = entry.get('pos', [])
            p = pos_list[0] if pos_list else 'n.'
            if 'v.' in p:
                matched_tid = topic_by_label.get('Change & Development', 'group_099')
            elif 'adj.' in p:
                matched_tid = topic_by_label.get('Comparison', 'group_097')
            elif 'adv.' in p:
                matched_tid = topic_by_label.get('Time & Sequence', 'group_095')
            else:
                matched_tid = topic_by_label.get('People & Roles', 'group_072')
            methods['pos_fallback'] += 1

        topic_words[matched_tid].append(w)

    print("Classification summary:", dict(methods))
    print(f"Words assigned to topics: {sum(len(ws) for ws in topic_words.values())}")

    # Build new graph nodes
    new_nodes = []
    domain_word_counts = Counter()

    for tid, ws in topic_words.items():
        if tid in topic_by_id:
            dom = topic_by_id[tid]['relative_to']
            domain_word_counts[dom] += len(ws)

    for n in orig_nodes:
        node_copy = dict(n)
        if n['type'] == 'root':
            node_copy['total_words'] = len(filtered)
            new_nodes.append(node_copy)
        elif n['type'] == 'domain':
            node_copy['word_count'] = domain_word_counts.get(n['id'], 0)
            new_nodes.append(node_copy)
        elif n['type'] == 'topic':
            ws = topic_words.get(n['id'], [])
            node_copy['words'] = ws
            node_copy['word_count'] = len(ws)
            new_nodes.append(node_copy)

    # Filter edges to 'contains'
    new_edges = [e for e in orig_edges if e.get('type') == 'contains']

    graph_out = {
        "version": 3,
        "total_words": len(filtered),
        "graph": {
            "description": "Topic vocabulary graph with 10 domains and 100 topics. Clicking a topic directly shows its 6 levels.",
            "coordinate_system": orig_data['graph'].get('coordinate_system', {}),
            "root_node_id": "life",
            "nodes": new_nodes,
            "edges": new_edges,
        }
    }

    OUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_GRAPH, 'w', encoding='utf-8') as f:
        json.dump(graph_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_GRAPH} ({len(new_nodes)} nodes, {len(new_edges)} edges)")

    with open(OUT_VOCAB, 'w', encoding='utf-8') as f:
        json.dump(vocab_data, f, ensure_ascii=False)
    print(f"Wrote {OUT_VOCAB} ({len(vocab_data)} words, {os.path.getsize(OUT_VOCAB)//1024} KB)")

    # Clean scratch files
    for scratch_file in [BASE / 'scratch_test_topics.py', BASE / 'scratch_run_classification.py', BASE / 'scratch_topic_keywords.py', BASE / 'scratch_check_mapping.py']:
        if scratch_file.exists():
            scratch_file.unlink()


if __name__ == '__main__':
    main()
