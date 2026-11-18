# 字根資料庫交叉驗證報告

建置時間: 2026-11-18T12:28:21

規則：Wiktionary 與 MorphoLex-en 兩者說法一致才收錄。

| 項目 | 數量 |
|---|---:|
| 考試單字總數 | 6701 |
| ✅ 兩來源一致：有構詞拆解 | 1667 |
| ✅ 兩來源一致：單一詞素 (不可拆) | 2818 |
| ⚠️ MorphoLex 沒收錄 | 144 |
| ⚠️ Wiktionary 沒收錄 | 65 |
| ❌ 衝突：morpholex_says_monomorphemic | 848 |
| ❌ 衝突：wiktionary_no_analysis | 654 |
| ❌ 衝突：suffix_mismatch | 194 |
| ❌ 衝突：root_count_mismatch | 116 |
| ❌ 衝突：prefix_mismatch | 102 |
| ❌ 衝突：root_mismatch | 57 |
| ❌ 衝突：affix_depth_mismatch | 36 |

衝突字中，有 775 個改顯示 Wiktionary 古典語源拆解 (單一來源)：拉丁文 540, 古英文 118, 法文 69, 古希臘文 17, 古諾斯語 10, 義大利文 6, 盎格魯-諾曼法文 5, 荷蘭文 4, 古法文 3, 西班牙文 1, 中古法文 1, 德文 1
