level=dict()->key=word, value=level(高中英文參考詞彙表(111學年度起適用).PDF)
word=dict()# word:dict(keys:appear year:list,appear year count:int, total_appear:int(how many times it appear in every word of past exam), level:int,situation(出現的情境))
situation=dict()->value=list()->index=level,value=word list
appear=[]#index=year, value=dict(key=appear word: value=appear times)#maybe bwe can uses Counter?
who_most_exam=[(times:int,word),...]
"""
建議再增加的資料
欄位	用途	重要程度
appear_year	知道在哪些年度出現	必要
appear_year_count	衡量跨年度的穩定程度	必要
total_appear	衡量總出現次數	必要
pos	詞性，例如 noun、verb、adjective	高
word_family	同詞族，例如 act、action、active	高
forms	不同詞形，例如 achieve、achieved、achieving	高
situations	出現的語境或主題	高
sources	年度、題號、題目位置	高
definitions	單字在考題中的意思	高
level	單字難度或背誦優先級	必要
"""