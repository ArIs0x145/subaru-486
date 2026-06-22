# 菜月昴角色資料集 — 萃取流水線 Spec

> v2 資料集。從《Re:Zero》小說逐章萃取昴的多輪對話,用 14 種情緒標籤標註,
> 微調出「會吐情緒標籤的菜月昴」給 Open LLM VTuber + Live2D 用。
> 標籤定義見 [dataset-emotion-tags.md](dataset-emotion-tags.md)。

## 鎖定決策(來自 brainstorming）

| 項目 | 決定 |
|------|------|
| 情緒標籤 | **14 種語意標籤**(見 dataset-emotion-tags.md),只用這 14 個,不自創 |
| 舊 486 資料 | **丟棄**,全新從小說重建(避免新舊標籤詞彙混用) |
| 來源 | 全本小說,**一章一章**逐次處理(可重複流水線,跨多 session) |
| 抽取範圍 | 抽**所有**昴有開口的場景,不刻意 downsample;靠每批回報分布監控 |
| 對話結構 | **多輪為主**(一段來回對話 = 一筆),孤立反應才用單輪 |
| 語言 | 一律**繁體中文**(來源若簡體 → 轉繁) |
| system prompt | 沿用角色設定;**組裝時**再決定是否帶上 14 tag 說明(配合 Open LLM VTuber 的 `[<insert_emomap_keys>]` 注入,求 train/inference 一致) |

## 輸出格式

一個場景 = 一行 JSON(`messages` 格式,多輪)。

- `system`:角色設定(全資料集同一段)
- `user`:`（場景旁白）「其他角色的台詞」` — 旁白用全形括號,他人台詞用「」
- `assistant`:`[tag] 昴的台詞` — **開頭一個小寫 tag + 空格 + 台詞**,一句一個 tag

### 範例

小說原文:
> 雷姆端來茶。「昴大人,請用茶。」昴咧嘴一笑:「你這面無表情根本就是傲嬌女僕的標準配備嘛。」雷姆歪頭:「傲嬌……那是什麼?」

↓

```json
{"messages":[
  {"role":"system","content":"你扮演《Re:從零開始的異世界生活》的男主角菜月昴。…"},
  {"role":"user","content":"（雷姆端來茶）「昴大人,請用茶。」"},
  {"role":"assistant","content":"[smug] 哼哼,你這面無表情根本就是傲嬌女僕的標準配備嘛。"},
  {"role":"user","content":"（雷姆歪頭）「傲嬌……那是什麼?」"},
  {"role":"assistant","content":"[smug] 嘿嘿,就是嘴上說討厭、心裡超喜歡的意思啦。"}
]}
```

## 檔案結構

| 檔案 | 內容 | 用途 |
|------|------|------|
| `subaru_arc1.jsonl` | Arc 1 (chapter010) | 分 Arc 保存 |
| `subaru_arc2.jsonl` | Arc 2 (chapter020)… | 之後逐 Arc 新增 |
| `subaru_all.jsonl` | 所有 Arc 合併 | **訓練用,上傳這個** |

`subaru_all.jsonl` = 各 `subaru_arc*.jsonl` 串接而成;每做完一段就重新產生。

## 每章工作循環

1. **使用者**:把一章文字丟進 `dataset/novel-src/`(已 clone)或直接貼
2. **AI**:找出昴開口的場景 → 轉多輪對話 → 依語意貼 14 種之一的 tag
3. **AI**:累加寫進當前 Arc 檔 `subaru_arc{N}.jsonl`,再重新產生 `subaru_all.jsonl`
4. **AI**:回報「本章 +N 筆、**14 種各自累積筆數**、低於 12 筆的標籤、異常」
5. 下一章,重複

## 標註紀律

- assistant 只放**昴(486)本人說出口的台詞**,不杜撰;語氣盡量保留原汁(招牌吐槽/中二)
  - **不放**旁白/動作描述(`（你…）`)、**不放**其他角色的台詞——這些一律放進 user 回合
  - 昴自己引用詞彙或轉述(如 所謂的「異世界召喚」)屬於台詞內容,合法
- tag 依 [dataset-emotion-tags.md](dataset-emotion-tags.md) 的「標註小抄」判定:先看招牌強烈情緒 → 否則日常 6 → 嫌棄 contempt → 真判不出 neutral
- 每種 tag 目標 **≥ 12 筆**;語境窄的(despair/hollow/flustered)v1 湊不夠就留 v2,不硬塞
- neutral 可較多(日常),其餘盡量分散,避免任一 tag 過載(舊版 fear 爆量的教訓)

## 上傳訓練(不需掛載)

Unsloth Studio 的 Dataset 卡片有「上傳」頁面,直接從 Windows 選 `dataset/subaru_all.jsonl` 上傳即可,不必複製進 `./work`、也不必改 docker-compose。

## 最後組裝 & 重訓(累積夠之後)

1. 看 `subaru_all.jsonl` 的**真實 14-tag 分布**,決定要不要微調
2. system prompt 定案(是否注入 14 tag 說明)
3. 上傳 `subaru_all.jsonl` → 切 train/eval → Unsloth Studio 重訓(資料變多,epoch 可降到 2)
