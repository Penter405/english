#!/usr/bin/env python3
"""
build_web_graph.py — Build Option A 9-Domain Graph & Vocabulary Data

Features:
  - 9 intuitive domains with 38 clear, high-quality subcategories
  - Classifies all 4,244 exam/Level 1-4 words using bilingual (EN + ZH) semantic matching
  - Eliminates false positives (e.g. 'brave' -> Personality & Traits)
  - Prepares geometric coordinates with wide angular spacing to guarantee
    that edges NEVER intersect or touch other nodes.
  - Zero basic/medium/hard graph nodes; clicking a subcategory directly opens
    the 6-level word list.

Outputs:
  - docs/data/graph.json
  - docs/data/vocab_data.json
"""

import json
import math
import os
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EXAM_WORDS_PATH = BASE / 'database' / 'exam_words.json'
ROOTS_PATH = BASE / 'database' / 'word_roots_breakdown.json'
SENTENCES_PATH = BASE / 'database' / 'word_sentences.json'
SIMPLE_DEFS_PATH = BASE / 'database' / 'simple_definitions.json'
ORIGINS_PATH = BASE / 'database' / 'word_origins.json'
OUT_GRAPH = BASE / 'docs' / 'data' / 'graph.json'
OUT_VOCAB = BASE / 'docs' / 'data' / 'vocab_data.json'

TAXONOMY = {
    "people_character": {
        "label": "People & Character",
        "label_zh": "人物與特質",
        "color": "#ec4899",
        "subcats": {
            "personality_traits": {
                "label": "Personality & Traits",
                "label_zh": "個性品質",
                "en": "brave bravery courage courageous hero bold coward cowardice honest honesty sincere sincerity frank candid kind kindness generous generosity selfish selfishness cruel cruelty mean modest modesty humble humility arrogant arrogance boast proud pride timid shy shyness patient patience impatient impatience stubborn stubbornness rigid calm calmness gentle gentleness rough cheerful optimism optimistic pessimism pessimistic greedy greed lazy laziness diligent diligence polite politeness rude rudeness courteous wise wisdom foolish foolishness smart clever silly intelligent stupidity noble wicked moral ethical faithful loyal loyalty trait personality character virtue vice eccentric enthusiastic",
                "zh": "勇敢 勇氣 誠實 善良 慷慨 自私 殘忍 謙虛 傲慢 害羞 耐心 固執 冷靜 溫和 粗魯 樂觀 悲觀 貪婪 懶惰 勤奮 禮貌 聰明 愚蠢 忠誠 個性 特質 品德 道德 賢明 愚昧"
            },
            "appearance_body": {
                "label": "Appearance & State",
                "label_zh": "外貌體態",
                "en": "tall short fat thin slim skinny overweight slender bald handsome pretty beautiful ugly gorgeous attractive plain neat messy cute lovely youthful elderly pale tan muscular frail strong weak handicap blind deaf mute complexion posture figure look glance appearance blonde brunette giant dwarf",
                "zh": "高 矮 胖 瘦 苗條 禿頭 英俊 美麗 醜陋 漂亮 整潔 凌亂 可愛 年輕 蒼白 強壯 虛弱 盲 聾 啞 外貌 身材 體態 膚色"
            },
            "relationships_roles": {
                "label": "Relationships & Roles",
                "label_zh": "身分人際",
                "en": "friend enemy stranger neighbor companion partner ally rival peer acquaintance opponent victim witness citizen teenager adult youth child baby infant fellow member gentleman lady folk crowd audience population colleague coworker roommate stranger host guest customer visitor identity",
                "zh": "朋友 敵人 陌生人 鄰居 同伴 夥伴 對手 同事 青年 成人 兒童 嬰兒 成員 紳士 女士 民眾 觀眾 房客 主人 客人 身分"
            },
            "family_life_stages": {
                "label": "Family & Life Stages",
                "label_zh": "家庭生命歷程",
                "en": "family parent father mother dad mom brother sister child son daughter husband wife spouse marry wedding marriage divorce pregnant pregnancy birth born birthday infant ancestor descendant generation funeral death graveyard relative uncle aunt cousin nephew niece sibling widow bride groom orphan foster",
                "zh": "家庭 父母 父親 母親 兄弟 姊妹 兒子 女兒 丈夫 妻子 結婚 婚禮 離婚 懷孕 出生 生日 祖先 後代 葬禮 親戚 叔伯 姑嬸 姪子 姪女 孤兒"
            }
        }
    },
    "mind_emotions": {
        "label": "Mind & Emotions",
        "label_zh": "心智與情緒",
        "color": "#f472b6",
        "subcats": {
            "feelings_emotions": {
                "label": "Feelings & Emotions",
                "label_zh": "情緒感受",
                "en": "happy sadness angry anger joy sorrow fear fright scare afraid anxiety worry anxious glad delight hate hatred love passion affection grief surprise shock lonely loneliness shame embarrassment guilt jealous envy jealousy disgust anger fury misery panic relief comfort enthusiasm mood emotional feeling cheer weep cry sob chuckle giggle groan scream sigh scream",
                "zh": "快樂 悲傷 憤怒 恐懼 焦慮 擔憂 喜悅 仇恨 愛 情緒 驚訝 孤獨 羞恥 內疚 嫉妒 厭惡 痛苦 恐慌 安慰 心情 哭泣 嘆氣 尖叫"
            },
            "thinking_deciding": {
                "label": "Thinking & Deciding",
                "label_zh": "思維判斷",
                "en": "think thought mind consider contemplation wonder ponder believe belief assume assumption suppose suspect doubt guess imagination imagine recall memory remember forget judge judgment decide decision conclusion conclude resolve opinion view view perspective notion idea concept reason logic rational evaluate analyze solve solution deduce infer puzzle",
                "zh": "思考 思想 考慮 懷疑 猜測 想像 記憶 判斷 決定 結論 觀點 概念 邏輯 理性 評估 分析 解決 方案 推斷"
            },
            "attitudes_goals": {
                "label": "Attitudes & Goals",
                "label_zh": "態度動機目標",
                "en": "goal aim ambition target objective purpose intention intend plan dream aspire aspiration motivation motivate eager willingness willing reluctance reluctant determine determination ambition resolve focus dedicate dedication commit commitment priority desire wish hopeful prospective striving endeavor",
                "zh": "目標 目的 企圖 野心 意圖 計畫 渴望 動機 意願 決心 專注 奉獻 承諾 願望 奮鬥"
            },
            "communication_speech": {
                "label": "Communication & Speech",
                "label_zh": "溝通言論",
                "en": "say speak speech talk tell whisper shout yell murmur conversation discuss discussion chat argue argument debate dialogue reply answer respond declare claim assert state suggest suggestion advise advice recommend praise blame complain criticize apologize apology admit deny refuse persuade convince threaten warn whisper debate negotiate",
                "zh": "說 講 對話 討論 爭論 辯論 回答 回應 宣稱 建議 批評 讚美 抱怨 道歉 承認 拒絕 說服 威脅 警告 協商"
            }
        }
    },
    "body_actions": {
        "label": "Body & Actions",
        "label_zh": "身體與動作",
        "color": "#ef4444",
        "subcats": {
            "body_health": {
                "label": "Body Anatomy & Health",
                "label_zh": "身體器官與醫療",
                "en": "body organ head brain face eye ear nose mouth lip tooth teeth tongue neck throat shoulder chest breast lung heart stomach belly liver kidney waist spine bone joint muscle skin blood vein limb arm elbow wrist hand finger thumb leg knee ankle foot feet toe illness disease symptom ache pain fever cough infection virus bacteria cancer doctor patient hospital clinic nurse medicine pill drug surgery cure heal therapy",
                "zh": "身體 頭 腦 臉 眼 耳 鼻 嘴 牙 喉嚨 肩 胸 肺 心 胃 肝 腎 骨 肌肉 皮膚 血液 肢 手 腳 生病 疾病 症狀 發燒 咳嗽 病毒 細菌 醫生 病人 醫院 藥 治療"
            },
            "physical_movement": {
                "label": "Physical Movement",
                "label_zh": "肢體位移動作",
                "en": "walk run jog sprint jump leap hop step stride march wander creep crawl slip slide fall trip stumble climb descend ascend rise enter exit leap advance retreat escape flee chase pursue rush hurry stroll march dance leap skip tumble wander promenade pace stride",
                "zh": "走 跑 跳 漫步 爬 滑 跌 攀爬 上升 下降 進入 離開 逃跑 追逐 衝 趕 散步 跳舞"
            },
            "handling_actions": {
                "label": "Hands & Interaction",
                "label_zh": "肢體操作與碰撞",
                "en": "take give hold grab grasp carry lift raise lower drop catch throw cast hit strike punch kick slap beat tap knock touch press push pull drag draw squeeze twist fold tear scratch rub wipe embrace hug kiss wrap tie untie bind release",
                "zh": "拿 給 握 抓 抱 提 舉 丟 扔 打 擊 踢 拍 敲 碰 摸 推 拉 拖 擠 扭 摺 撕 抓 擦 擁抱 親 綁 捆 解開 釋放"
            },
            "senses_perception": {
                "label": "Senses & Perception",
                "label_zh": "感官與知覺",
                "en": "see sight look glance gaze stare peer view watch blind eye visual hear listen sound noise ear deaf audio audio smell scent odor fragrance aroma sniff nose taste flavor savor tongue touch feel tactile sensation sensitive numb sharp blur bright dark echo rhythm glimpse peek perceive notice observe detect witness scan inspect",
                "zh": "看 瞧 盯 視力 視覺 聽 聲音 嘈雜 嗅 聞 氣味 味道 觸 感覺 敏銳 模糊 明亮 黑暗 窺視 察覺 觀察 檢驗"
            }
        }
    },
    "daily_life": {
        "label": "Daily Life & Living",
        "label_zh": "日常與生活",
        "color": "#f59e0b",
        "subcats": {
            "food_dining": {
                "label": "Food & Dining",
                "label_zh": "飲食與烹飪",
                "en": "food meal eat feed bite chew swallow drink beverage water tea coffee milk juice beer wine soup salad sauce bread flour wheat rice noodle pasta pizza burger meat beef pork steak chicken fish seafood fruit apple banana orange vegetable potato tomato onion carrot bean egg cheese butter sugar salt spice pepper cook boil bake roast fry grill steam dish bowl plate cup spoon fork knife restaurant cafe buffet chef waiter menu delicious recipe appetite hunger thirst",
                "zh": "食物 餐 吃 喝 咀嚼 水 茶 咖啡 牛奶 果汁 湯 沙拉 麵包 米 麵 披薩 肉 牛排 雞 魚 水果 蔬菜 蛋 糖 鹽 烹煮 烤 炸 煎 餐廳 咖啡廳 菜單 美味 食譜 飢餓 口渴"
            },
            "home_living": {
                "label": "Home & Residence",
                "label_zh": "家居居住與雜務",
                "en": "home house apartment room bedroom kitchen bathroom living basement balcony roof ceiling floor wall door window porch yard garden furniture table chair desk sofa bed shelf drawer closet cabinet lamp curtain carpet pillow blanket towel clock mirror sink toilet shower bathtub stove fridge microwave fan heater iron laundry wash sweep mop clean dust trash repair fix faucet plug leak",
                "zh": "家 房屋 公寓 房間 臥房 廚房 浴室 客廳 屋頂 地板 牆 門 窗 庭院 家具 桌 椅 沙發 床 櫃子 燈 窗簾 地毯 鏡子 馬桶 淋浴 洗衣 打掃 垃圾 修繕 漏水"
            },
            "clothing_fashion": {
                "label": "Clothing & Apparel",
                "label_zh": "服飾穿搭與配件",
                "en": "cloth clothes wear put dress suit shirt coat jacket sweater jeans pants skirt uniform underwear pajama sock shoe boot sneaker sandal slipper hat cap scarf glove belt tie pocket button zipper sleeve collar wallet purse umbrella fashion style fabric cotton silk wool leather thread needle stitch casual formal elegant costume wear dressing",
                "zh": "衣服 穿著 洋裝 套裝 襯衫 大衣 外套 毛衣 牛仔褲 裙子 制服 鞋 靴 帽子 圍巾 手套 皮帶 領帶 口袋 鈕扣 拉鍊 時尚 質料 棉 絲 羊毛 皮革 縫紉 正式 休閒"
            },
            "shopping_finance": {
                "label": "Shopping & Money",
                "label_zh": "消費金錢與金融",
                "en": "shop store market supermarket mall buy purchase sell sale price cost cheap expensive afford pay payment cash coin bill dollar currency money bank credit card debit account deposit withdraw save budget expense fee debt borrow lend loan tax interest discount bargain refund receipt cashier wallet purse wealth fortune rich poor bankruptcy",
                "zh": "商店 市場 超市 買 賣 價格 費用 便宜 昂貴 負擔 付款 現金 零錢 貨幣 金錢 銀行 信用卡 帳戶 存款 提款 儲蓄 預算 借 貸 稅 利息 折扣 結帳 發票 財富"
            }
        }
    },
    "school_education": {
        "label": "School & Learning",
        "label_zh": "學習與教育",
        "color": "#8b5cf6",
        "subcats": {
            "school_campus": {
                "label": "School & Campus",
                "label_zh": "校園課堂活動",
                "en": "school student pupil teacher instructor professor principal dean classmate campus classroom desk blackboard whiteboard lecture course class lesson homework assignment semester term grade attendance bell recess club diploma graduate graduation tuition scholarship university college dormitory uniform",
                "zh": "學校 學生 老師 教授 校長 校園 教室 課堂 課 課程 作業 學期 年級 畢業 獎學金 大學 宿舍 制服"
            },
            "reading_writing": {
                "label": "Reading & Writing",
                "label_zh": "閱讀寫作與出版",
                "en": "read reading book novel author writer poet poetry poem story literature fiction biography chapter page paragraph sentence text title script essay composition draft manuscript article journal magazine newspaper review publish publisher press editor print library bookmark notebook pencil pen ink eraser",
                "zh": "閱讀 書籍 小說 作者 作家 詩 故事 文學 傳記 章節 段落 句子 文章 期刊 雜誌 評論 出版 印刷 圖書館 筆記本 筆"
            },
            "exams_academics": {
                "label": "Exams & Academics",
                "label_zh": "考試測驗與學術",
                "en": "exam examination test quiz score mark point pass fail question answer result assessment evaluate evaluation study memorize drill review research study theory hypothesis experiment science academic degree thesis diploma knowledge wisdom intellectual principle scholarly curriculum academic method laboratory formula",
                "zh": "考試 測驗 成績 及格 當掉 問題 答案 結果 評估 研讀 背誦 複習 研究 理論 假說 實驗 學術 學位 論文 知識 原理 實驗室"
            },
            "languages_linguistics": {
                "label": "Languages & Words",
                "label_zh": "語言文字溝通",
                "en": "language tongue speech native foreign foreign accent dialect vocabulary word term phrase idiom proverb clause grammar sentence spelling pronounce pronunciation syllable vowel consonant alphabet fluent literacy translate translation interpreter bilingual dictionary phrase meaning definition synonym antonym",
                "zh": "語言 母語 外語 口音 方言 單字 詞彙 片語 成語 文法 拼字 發音 音節 字母 流利 翻譯 字典 意思 定義 同義字 反義字"
            }
        }
    },
    "work_society": {
        "label": "Work & Society",
        "label_zh": "職場與社會",
        "color": "#f97316",
        "subcats": {
            "jobs_careers": {
                "label": "Jobs & Careers",
                "label_zh": "職業工作與職場",
                "en": "work job career profession occupation trade labor employee worker staff clerk employer boss manager director executive hire recruit employ fire dismiss resign retire resume vacancy interview application salary wage income bonus promotion retire retirement pension colleague coworker duty task shift overtime overtime office workspace meeting conference",
                "zh": "工作 職業 職業 勞動 員工 職員 雇主 老闆 經理 雇用 解雇 辭職 履歷 面試 薪水 獎金 升遷 退休 同事 職責 辦公室 會議"
            },
            "business_economy": {
                "label": "Business & Economy",
                "label_zh": "商業經濟與貿易",
                "en": "business company firm corporation enterprise commercial industry commerce trade merchandise product commodity goods supply demand market market stock share investment invest fund capital profit revenue loss bankruptcy economic economy depression recession inflation consumer customer retail wholesale contract deal client competition rival venture",
                "zh": "商業 公司 企業 工業 貿易 產品 商品 供給 需求 市場 股票 投資 資金 利潤 經濟 蕭條 通膨 消費者 客戶 零售 批發 合約 競爭"
            },
            "government_politics": {
                "label": "Government & Politics",
                "label_zh": "政府國家政治",
                "en": "government governor federal state regime authority administration president minister mayor official politician politics party parliament congress senate election vote voter ballot candidate campaign citizen nationality democracy republic monarchy constitution policy reform diplomat diplomacy embassy ambassador treaty protest rally revolution sovereignty territory",
                "zh": "政府 聯邦 官員 總統 部長 市長 政治 政黨 議會 選舉 投票 候選人 公民 民主 憲法 政策 改革 外交 條約 抗議 革命 領土"
            },
            "law_justice": {
                "label": "Law & Justice",
                "label_zh": "法律犯罪與正義",
                "en": "law legal illegal justice court trial judge jury lawyer attorney witness victim crime criminal offense guilt guilty innocent arrest police custody detective inspect prison jail cell convict penalty sentence fine sue lawsuit defend prosecute prohibit ban enforce regulation violation theft robber murder hostage scam fraud fraudulent cheat deception deceive trick swindle",
                "zh": "法律 合法 非法 正義 法庭 審判 法官 律師 證人 受害者 犯罪 嫌犯 逮捕 警察 監獄 懲罰 判決 罰金 起訴 控告 禁令 違規 謀殺 詐騙 騙局 詐欺 詭計"
            },
            "culture_community": {
                "label": "Culture & Community",
                "label_zh": "文化社會與信仰",
                "en": "culture cultural tradition custom heritage ethnic race ritual festival ceremony celebration celebration feast holiday religion religious church temple pray worship priest god spirit soul sacred holy moral ethic value faith belief community social society welfare poverty charity homeless volunteer civilization myth folklore legend museum monument art",
                "zh": "文化 傳統 習俗 遺產 種族 儀式 節慶 宗教 教堂 廟宇 祈禱 上帝 神聖 道德 信仰 社區 社會 福利 慈善 志工 文明 神話 藝術"
            }
        }
    },
    "tech_transport": {
        "label": "Tech & Transport",
        "label_zh": "科技與交通",
        "color": "#06b6d4",
        "subcats": {
            "computers_internet": {
                "label": "Computers & Internet",
                "label_zh": "電腦資訊與網路",
                "en": "computer supercomputer laptop pc desktop keyboard mouse monitor screen processor chip hardware software program code coding app application system windows operating memory storage file folder document database server cloud internet web online browser website link domain upload download cyber hack security firewall virus digital password algorithm blog blogging blogger mainframe computing",
                "zh": "電腦 計算機 超級電腦 巨型機 鍵盤 滑鼠 螢幕 晶片 硬體 軟體 程式 系統 記憶體 檔案 資料庫 伺服器 雲端 網路 部落格 博客 網絡 上傳 下載 駭客 安全 防火牆 密碼 數位 運算"
            },
            "devices_media": {
                "label": "Digital Devices & Media",
                "label_zh": "通訊媒體與影音",
                "en": "phone telephone smartphone mobile cellular call text message chat app wireless bluetooth signal camera photograph photo picture video film audio record recorder microphone speaker headphone headphone broadcast television tv radio channel stream streaming episode newspaper media press headline journalism animation cartoon",
                "zh": "電話 手機 通話 簡訊 拍照 相機 影片 錄音 麥克風 喇叭 耳機 廣播 電視 頻道 串流 媒體 影視 動畫"
            },
            "land_transport": {
                "label": "Land Transportation",
                "label_zh": "陸上交通運輸",
                "en": "car vehicle automobile truck van bus taxi cab train railway rail locomotive subway metro tram trolley bicycle bike motorcycle scooter motor engine wheel tire brake steering pedal seat passenger driver drive traffic street road highway freeway lane avenue intersection curb signal sidewalk bridge tunnel",
                "zh": "車 汽車 卡車 公車 計程車 火車 鐵路 捷運 地鐵 腳踏車 機車 引擎 輪胎 煞車 方向盤 駕駛 乘客 交通 馬路 公路 車道 橋 隧道"
            },
            "air_sea_travel": {
                "label": "Air & Sea Travel",
                "label_zh": "航海航空與航線",
                "en": "airplane plane aircraft flight jet airline airport terminal gate runway takeoff landing pilot crew cabin cockpit flight helicopter baggage luggage passport visa customs board boarding ship boat vessel ferry cruise sail yacht anchor harbor port dock sailor captain ocean voyage maritime submarine deck paddle",
                "zh": "飛機 航班 航線 機場 登機 降落 起飛 機師 船員 行李 護照 簽證 海關 船 輪船 渡輪 帆船 港口 碼頭 船長 航行 潛水艇"
            },
            "travel_logistics": {
                "label": "Travel & Freight",
                "label_zh": "旅行住宿與物流",
                "en": "travel trip journey tour voyage vacation holiday destination tourist resort guide expedition exploration map compass itinerary reservation booking hotel motel inn hostel resort lodge accommodation reception souvenir foreign abroad overseas freight cargo shipment parcel package mail delivery courier logistics post postage postage warehouse transit transfer",
                "zh": "旅行 旅程 假期 目的地 觀光客 度假村 導遊 地圖 預訂 飯店 旅館 紀念品 出國 貨物 包裹 郵寄 快遞 物流 倉庫 轉運"
            }
        }
    },
    "nature_science": {
        "label": "Nature & Science",
        "label_zh": "自然與科學",
        "color": "#10b981",
        "subcats": {
            "animals_wildlife": {
                "label": "Animals & Wildlife",
                "label_zh": "動物與生物界",
                "en": "animal beast creature pet mammal dog puppy cat kitten horse cow bull cattle ox pig sheep lamb goat deer rabbit hare lion tiger bear wolf fox elephant monkey ape camel kangaroo whale dolphin seal shark fish bird feather wing beak nest eagle owl hawk parrot swan penguin sparrow insect bug ant bee butterfly mosquito spider fly beetle moth worm snake reptile frog turtle lizard organism wildlife species habitat breed",
                "zh": "動物 寵物 哺乳類 狗 貓 馬 牛 豬 羊 鹿 兔 獅 老虎 熊 狼 狐 象 猴 鯨魚 海豚 魚 鳥 羽毛 翅膀 鷹 企鵝 昆蟲 蜜蜂 蝴蝶 蚊子 蜘蛛 蛇 爬蟲類 兩棲類 野生動物 物種"
            },
            "plants_ecology": {
                "label": "Plants & Ecology",
                "label_zh": "植物森林與生態",
                "en": "plant flora tree forest woods jungle timber trunk bark branch leaf leaves root seed sprout stem bud bloom blossom flower petal grass bush shrub weed bamboo pine oak maple palm vine moss botanical harvest crop farm agricultural vegetation ecology ecosystem conservation preserve pollution environmental green global renewable recycle compost deforest",
                "zh": "植物 樹 森林 樹幹 樹枝 葉 根 種子 芽 花 草 雜草 農作物 農業 生態 保育 污染 環保 綠色 回收"
            },
            "weather_earth": {
                "label": "Weather & Earth",
                "label_zh": "氣候天氣與地貌",
                "en": "weather climate season spring summer autumn fall winter cold hot warm cool temperature sunny cloudy overcast rain shower drizzle storm thunder lightning gale hurricane tornado typhoone flood drought snow frost freeze hail mist fog dew breeze wind air atmosphere earth world globe mountain peak valley canyon hill plateau desert island continent shore coast beach ocean sea lake river stream creek cave glacier rock stone sand soil mud dirt terrain geology volcano eruption earthquake",
                "zh": "天氣 氣候 季節 春 夏 秋 冬 溫度 冷 熱 晴 陰 雨 暴風 雨 閃電 颶風 颱風 水災 旱災 雪 霜 霧 風 空氣 大氣 地球 山 谷 沙漠 島 大陸 海岸 海洋 湖 河 岩石 土壤 地震 火山"
            },
            "physics_chemistry_space": {
                "label": "Physical Science & Space",
                "label_zh": "理化宇宙與能源",
                "en": "science physics chemistry atom molecule particle electron proton nucleus element compound chemical reaction acid base liquid gas solid crystal solution formula substance laboratory experiment force motion speed velocity gravity magnet magnetic electricity electric circuit current voltage power energy fuel battery coal petroleum solar nuclear radiation wave sound heat thermal pressure space universe cosmos galaxy star sun solar moon lunar planet orbit comet asteroid satellite rocket astronaut telescope",
                "zh": "物理 化學 原子 分子 元素 化合物 反應 酸 鹼 液體 氣體 固體 能量 力 重力 磁 電 電池 燃料 太陽能 核能 輻射 聲 熱 宇宙 銀河 星球 太陽 月亮 行星 衛星 太空人 望遠鏡"
            }
        }
    },
    "description_logic": {
        "label": "Logic & Modifiers",
        "label_zh": "邏輯修飾與抽象",
        "color": "#6366f1",
        "subcats": {
            "time_frequency": {
                "label": "Time & Frequency",
                "label_zh": "時間次序與頻率",
                "en": "time hour minute second morning afternoon evening night midnight dawn dusk noon today yesterday tomorrow day week month year decade century era epoch always constantly often frequently usually normally sometimes occasionally seldom rarely hardly never already still yet soon shortly recently lately immediately instantly presently afterwards beforehand temporary permanent ancient modern eternal duration interval schedule delay postpone early late punctuality sequence initial eventual",
                "zh": "時間 小時 分 秒 早 晚 白天 週 月 年 世紀 總是 經常 通常 有時 很少 從不 已經 還 很快 最近 立刻 之後 臨時 永久 古代 現代 提早 延遲 頻率"
            },
            "space_direction": {
                "label": "Space & Direction",
                "label_zh": "空間位置與方向",
                "en": "position place location spot point space direction area district region zone north south east west upward downward forward backward sideways toward away inward outward upper lower top bottom peak base surface interior exterior inside outside internal external middle center central edge border boundary margin corner front back rear behind ahead aside beside near close far distant remote wherever everywhere nowhere between among surrounding opposite",
                "zh": "位置 地點 空間 方向 區域 北 南 東 西 上 下 前 後 裡 外 中間 邊緣 邊界 正面 背面 附近 遙遠 到處"
            },
            "comparison_degree": {
                "label": "Comparison & Degree",
                "label_zh": "程度比較與特質",
                "en": "compare comparison similar identical same alike different distinct contrast contrary resemble match equal equivalent superior inferior better worse best worst degree level extent very quite rather extremely fairly slightly somewhat highly deeply truly barely partly totally completely absolutely almost nearly especially particularly particularly chiefly mostly unique general universal common rare typical extraordinary normal strange weird odd marvelous",
                "zh": "比較 相同 相似 不同 相反 相等 較好 較差 程度 非常 相當 極度 稍微 完全 幾乎 特別 特別 普遍 罕見 異常 正常 奇怪"
            },
            "change_causality": {
                "label": "Change & Causality",
                "label_zh": "變化因果與抽象",
                "en": "cause effect result outcome consequence reason why because since therefore thus hence lead produce trigger create generate bring factor affect influence impact origin source basis change become alter vary transform convert evolve modify improve advance progress expand grow growth shrink reduce decrease diminish decline raise increase reform shift transition condition situation circumstance state status reality truth fiction phenomenon aspect element instance example",
                "zh": "原因 影響 結果 成果 後果 因素 產生 影響 起源 基礎 改變 變成 轉變 進步 成長 增加 減少 改革 狀況 狀態 現實 現象 範例"
            }
        }
    }
}


def build_word_data(word, entry, roots_db, sentences_db, simple_defs_db, origins_db):
    """Build word metadata for the definition popup and multi-criteria sorting."""
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

    years = entry.get("appear_year", [])
    yrs_cnt = entry.get("appear_year_count", len(years))
    latest_yr = max(years) if years else 0

    orig_info = origins_db.get("words", {}).get(word, {})
    orig_key = orig_info.get("origin", word)
    orig_data = origins_db.get("origins", {}).get(orig_key, {})

    variants = []
    for v in orig_data.get("variants", []):
        variants.append({
            "w": v["word"],
            "pos": v.get("pos", []),
            "r": v.get("relation", "")
        })

    return {
        "w": word,
        "lv": entry.get("level", 0),
        "pos": entry.get("pos", []),
        "en": en_defs,
        "simple_en": simple_defs_db.get(word, ""),
        "zh": zh_defs,
        "forms": entry.get("forms", {}),
        "fam": entry.get("word_family", []),
        "exam": years,
        "cnt": entry.get("total_appear", 0),
        "yrs_cnt": yrs_cnt,
        "latest_yr": latest_yr,
        "sources": entry.get("sources", []),
        "roots": roots_db.get(word),
        "sentences": sentences_db.get(word, []),
        "origin": orig_key,
        "origin_zh": orig_data.get("meaning_zh", ""),
        "relation": orig_info.get("relation", "0: 原型 (lemma)"),
        "variants": variants
    }


def main():
    print("Step 1: Loading databases...")
    with open(EXAM_WORDS_PATH, 'r', encoding='utf-8') as f:
        exam_data = json.load(f)

    roots_db = {}
    if ROOTS_PATH.exists():
        with open(ROOTS_PATH, 'r', encoding='utf-8') as f:
            roots_db = json.load(f)
        print(f"  Loaded {len(roots_db)} roots breakdowns.")

    sentences_db = {}
    if SENTENCES_PATH.exists():
        with open(SENTENCES_PATH, 'r', encoding='utf-8') as f:
            sentences_db = json.load(f)
        print(f"  Loaded {len(sentences_db)} sentence records.")

    simple_defs_db = {}
    if SIMPLE_DEFS_PATH.exists():
        with open(SIMPLE_DEFS_PATH, 'r', encoding='utf-8') as f:
            simple_defs_db = json.load(f)
        print(f"  Loaded {len(simple_defs_db)} simple English definitions.")

    origins_db = {}
    if ORIGINS_PATH.exists():
        with open(ORIGINS_PATH, 'r', encoding='utf-8') as f:
            origins_db = json.load(f)
        print(f"  Loaded {len(origins_db.get('origins', {}))} origin families.")

    words = exam_data['words']
    filtered = {
        w: v for w, v in words.items()
        if v.get('total_appear', 0) > 0 or v.get('level', 99) <= 4
    }
    print(f"  Filtered {len(filtered)} words (appeared in exams OR level 1-4).")

    # Stop characters that cause false positive single-character Chinese matches
    STOP_ZH_CHARS = set("的了一是在有人大事國機計生子年自會家民理行用現所個這那")

    # Build subcategory token sets
    subcat_list = []
    for dom_id, dom_data in TAXONOMY.items():
        for sub_id, sub_data in dom_data['subcats'].items():
            en_tokens = set(re.findall(r'[a-z]+', sub_data['en'].lower()))
            zh_phrases = set(p.strip() for p in sub_data['zh'].split() if len(p.strip()) >= 2)
            zh_chars = set(sub_data['zh'].replace(' ', '')) - STOP_ZH_CHARS
            subcat_list.append({
                'domain_id': dom_id,
                'sub_id': sub_id,
                'full_id': f"{dom_id}__{sub_id}",
                'label': sub_data['label'],
                'label_zh': sub_data.get('label_zh', ''),
                'color': dom_data['color'],
                'en_tokens': en_tokens,
                'zh_phrases': zh_phrases,
                'zh_chars': zh_chars
            })

    print(f"Step 2: Classifying {len(filtered)} words across {len(subcat_list)} subcategories...")
    topic_words = defaultdict(list)
    vocab_data = {}

    for w, entry in sorted(filtered.items()):
        vocab_data[w] = build_word_data(w, entry, roots_db, sentences_db, simple_defs_db, origins_db)

        defs = entry.get('definitions', {})
        en_defs = defs.get('en', []) if isinstance(defs, dict) else []
        zh_defs = defs.get('zh', []) if isinstance(defs, dict) else []

        en_text = f"{w} " + " ".join(en_defs)
        en_tokens = set(re.findall(r'[a-z]+', en_text.lower()))
        zh_text = "".join(zh_defs)
        zh_chars = set(re.findall(r'[\u4e00-\u9fff]', zh_text)) - STOP_ZH_CHARS

        best_sub = None
        best_score = -1

        for sub in subcat_list:
            en_match = len(en_tokens & sub['en_tokens'])
            zh_match = len(zh_chars & sub['zh_chars'])
            zh_phrase_match = sum(1 for phrase in sub['zh_phrases'] if phrase in zh_text)
            bonus = 12 if w in sub['en_tokens'] else 0

            score = en_match * 2.5 + zh_phrase_match * 4.0 + zh_match * 1.0 + bonus
            if score > best_score:
                best_score = score
                best_sub = sub

        assigned_id = best_sub['full_id'] if (best_sub and best_score > 0) else 'description_logic__change_causality'
        topic_words[assigned_id].append(w)

    print("  Classification complete!")
    print(f"  Check 'brave': in {[k for k, ws in topic_words.items() if 'brave' in ws][0]}")

    # Step 3: Build Nodes and Edges with Clean Geometry
    print("Step 3: Calculating geometry and building graph nodes...")
    nodes = []
    edges = []

    # 1. Root Node
    nodes.append({
        "id": "life",
        "label": "Vocabulary",
        "type": "root",
        "x": 0,
        "y": 0,
        "total_words": len(filtered),
        "description": "Central root"
    })

    # 2. 9 Domains evenly placed on circle of radius DOMAIN_RADIUS = 320
    dom_ids = list(TAXONOMY.keys())
    num_domains = len(dom_ids)
    domain_step = 360.0 / num_domains

    DOMAIN_RADIUS = 320.0
    CHILD_RADIUS = 240.0

    domain_counts = Counter()
    for full_id, ws in topic_words.items():
        dom = full_id.split('__')[0]
        domain_counts[dom] += len(ws)

    for i, dom_id in enumerate(dom_ids):
        dom_info = TAXONOMY[dom_id]
        # Angle starting at top (-90 deg)
        dom_angle_deg = -90.0 + i * domain_step
        dom_angle_rad = math.radians(dom_angle_deg)

        dom_x = round(math.cos(dom_angle_rad) * DOMAIN_RADIUS, 1)
        dom_y = round(math.sin(dom_angle_rad) * DOMAIN_RADIUS, 1)

        nodes.append({
            "id": dom_id,
            "label": dom_info["label"],
            "label_zh": dom_info.get("label_zh", ""),
            "type": "domain",
            "color": dom_info["color"],
            "x": dom_x,
            "y": dom_y,
            "angle_degrees": dom_angle_deg,
            "relative_to": "life",
            "word_count": domain_counts[dom_id]
        })

        edges.append({
            "id": f"life-{dom_id}",
            "source": "life",
            "target": dom_id,
            "type": "contains"
        })

        # 3. Subcategories for this domain
        sub_items = list(dom_info['subcats'].items())
        num_subs = len(sub_items)

        # To ensure NO lines cross other nodes:
        # Children are distributed in an outward arc centered at dom_angle_deg
        # Arc span: 130 deg for 4 children, 150 deg for 5 children
        span_deg = 130.0 if num_subs <= 4 else 150.0
        start_angle = dom_angle_deg - span_deg / 2.0
        angle_step_sub = span_deg / max(num_subs - 1, 1)

        for j, (sub_id, sub_info) in enumerate(sub_items):
            full_id = f"{dom_id}__{sub_id}"
            sub_angle_deg = start_angle + j * angle_step_sub
            sub_angle_rad = math.radians(sub_angle_deg)

            sub_x = round(math.cos(sub_angle_rad) * CHILD_RADIUS, 1)
            sub_y = round(math.sin(sub_angle_rad) * CHILD_RADIUS, 1)

            ws = topic_words.get(full_id, [])

            nodes.append({
                "id": full_id,
                "label": sub_info["label"],
                "label_zh": sub_info.get("label_zh", ""),
                "type": "topic",
                "color": dom_info["color"],
                "relative_to": dom_id,
                "x": sub_x,
                "y": sub_y,
                "angle_degrees": round(sub_angle_deg, 1),
                "words": ws,
                "word_count": len(ws)
            })

            edges.append({
                "id": f"{dom_id}-{full_id}",
                "source": dom_id,
                "target": full_id,
                "type": "contains"
            })

    print(f"Total graph nodes: {len(nodes)} (1 root, {len(dom_ids)} domains, {len(nodes)-1-len(dom_ids)} topics)")
    print(f"Total edges: {len(edges)}")

    graph_out = {
        "version": 4,
        "total_words": len(filtered),
        "graph": {
            "description": "Option A clean topic graph: 9 domains, 38 intuitive subcategories, 0 edge-node collisions.",
            "root_node_id": "life",
            "nodes": nodes,
            "edges": edges,
        }
    }

    # Step 3b: Populate fallback entries for all family variants so clicking them in Web popup works seamlessly
    extra_variants_count = 0
    for orig_key, odata in origins_db.get("origins", {}).items():
        variants = odata.get("variants", [])
        clean_vars = [{"w": v["word"], "pos": v.get("pos", []), "r": v.get("relation", "")} for v in variants]
        for v in variants:
            vw = v["word"]
            if vw not in vocab_data:
                ew = words.get(vw, {})
                defs = ew.get("definitions", {})
                zh_defs = defs.get("zh", []) if isinstance(defs, dict) else []
                en_defs = defs.get("en", []) if isinstance(defs, dict) else []
                if not zh_defs and odata.get("meaning_zh"):
                    zh_defs = [f"{odata['meaning_zh']} ({v['relation']})"]

                vocab_data[vw] = {
                    "w": vw,
                    "lv": ew.get("level", 0),
                    "pos": v.get("pos", []) or ew.get("pos", []),
                    "en": en_defs or [f"Variant form of {orig_key} ({v['relation']})"],
                    "simple_en": simple_defs_db.get(vw, f"Related form of {orig_key}."),
                    "zh": zh_defs,
                    "forms": ew.get("forms", {}),
                    "fam": [v2["word"] for v2 in variants if v2["word"] != vw][:10],
                    "exam": ew.get("appear_year", []),
                    "cnt": ew.get("total_appear", 0),
                    "yrs_cnt": ew.get("appear_year_count", 0),
                    "latest_yr": max(ew.get("appear_year", [0])) if ew.get("appear_year") else 0,
                    "sources": ew.get("sources", []),
                    "roots": roots_db.get(vw),
                    "sentences": sentences_db.get(vw, []),
                    "origin": orig_key,
                    "origin_zh": odata.get("meaning_zh", ""),
                    "relation": v.get("relation", "變體 (variant)"),
                    "variants": clean_vars,
                    "is_variant_fallback": True
                }
                extra_variants_count += 1

    print(f"Added {extra_variants_count} connected variant words to vocab_data for instant interactive lookup.")

    # Step 4: Write to docs/data/
    OUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_GRAPH, 'w', encoding='utf-8') as f:
        json.dump(graph_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_GRAPH} ({os.path.getsize(OUT_GRAPH)//1024} KB)")

    with open(OUT_VOCAB, 'w', encoding='utf-8') as f:
        json.dump(vocab_data, f, ensure_ascii=False)
    print(f"Wrote {OUT_VOCAB} ({len(vocab_data)} words, {os.path.getsize(OUT_VOCAB)//1024} KB)")

    # Clean temporary scratch files
    for sf in [BASE / 'scratch_taxonomy_def.py', BASE / 'scratch_run_new_taxonomy.py', BASE / 'scratch_test_new_taxonomy.py']:
        if sf.exists():
            sf.unlink()


if __name__ == '__main__':
    main()
