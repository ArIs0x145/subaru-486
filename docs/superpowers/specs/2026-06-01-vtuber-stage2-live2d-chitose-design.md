# Open LLM VTuber 串接 — 階段二：Live2D（chitose）（第 ⑦ 步之二）

日期：2026-06-01
對應 Runbook：§8.4（註冊 Live2D 模型）、§9.4（Live2D 表情驗收）、§10.5（emotion tag 沒觸發表情）
對應管線步驟：第 ⑦ 步「VTuber 串接」的階段二（共四階段：LLM→Live2D→ASR→TTS）

## 1. 目標與範圍

把 Open LLM VTuber 的預設 avatar 換成 chitose Live2D 模型，並讓對話時依 emotion 標籤切換臉部表情。承接階段一（LLM 文字對話已通）。

**範圍內：**
- 複製 chitose 素材到 `app/live2d-models/chitose/runtime/`。
- 在 `app/model_dict.json` 新增 chitose 條目（url、emotionMap、idleMotionGroupName）。
- 改 `app/conf.yaml`：`live2d_model_name: 'chitose'`。
- 重啟 server，瀏覽器驗收：載入 chitose、對話時表情隨 emotion 切換。

**範圍外（後續階段）：**
- ASR（faster-whisper，階段三）。
- TTS（edge-tts，階段四）。
- motion/動作觸發細調（本步以表情為主，idle 動作能跑即可）。

## 2. 現況（已確認）

- 階段一完成：app 已裝、conf.yaml LLM 指向 `qwen3-486`、文字對話繁中正常。
- `app/live2d-models/` 現有 `mao_pro`、`shizuku` 兩個範例模型。
- `app/model_dict.json` 在 app 根目錄，現只有 1 個 `mao_pro` 條目，emotionMap 用 8 種 key（neutral/anger/disgust/fear/joy/smirk/sadness/surprise），value 為表情 index。範例：`mao_pro` 的 url 為 `/live2d-models/mao_pro/runtime/mao_pro.model3.json`（含 `runtime/` 子層）。
- chitose 素材在 `C:\Users\chenb\Downloads\chitose\runtime\`，含 `chitose.model3.json`、`chitose.moc3`、`expressions/`（7 個）、`motion/` 等。
- chitose `model3.json` 的 Expressions 順序（index）：0=Angry, 1=Blushing, 2=f01, 3=Normal, 4=Sad, 5=Smile, 6=Surprised。
- chitose Motion groups：`Flick`、`Idle`、`Tap`（`Idle` 有 1 個動作）。
- `app/` 與 `app/live2d-models/` 皆被 .gitignore 排除，不進我們版控。

## 3. 使用者決策

| 項目 | 決策 |
| --- | --- |
| emotionMap 對應 | Runbook §8.4 建議（fear/smirk/disgust 借用相近表情） |
| 素材放置 | `live2d-models/chitose/runtime/`（跟 mao_pro 一致，含 runtime 子層） |
| 驗收深度 | 網頁載入 chitose + 對話時表情切換 |

## 4. emotionMap（§8.4 對 chitose 實際 index）

| emotion key | chitose 表情 | index |
| --- | --- | ---: |
| neutral | Normal | 3 |
| joy | Smile | 5 |
| sadness | Sad | 4 |
| anger | Angry | 0 |
| surprise | Surprised | 6 |
| fear | Surprised（借） | 6 |
| smirk | Smile（借） | 5 |
| disgust | Angry（借） | 0 |

fear/smirk/disgust 借用相近表情（chitose 無對應專屬表情）；第二輪可請繪師補。

## 5. 架構：複製 → 註冊 → 指定 → 驗收

| 步驟 | 動作 | 驗證 |
| --- | --- | --- |
| 1 | 複製 chitose runtime → `app/live2d-models/chitose/runtime/` | `app/live2d-models/chitose/runtime/chitose.model3.json` 存在 |
| 2 | `app/model_dict.json` 新增 chitose 條目（url、emotionMap §4、idleMotionGroupName=`Idle`） | model_dict.json 可被 json 解析、含 name=chitose 條目 |
| 3 | `app/conf.yaml` 設 `live2d_model_name: 'chitose'` | conf.yaml 該行為 chitose |
| 4 | 重啟 `run_server.py`、瀏覽器 Ctrl+F5 | 看到 chitose（非 mao_pro）；對話觸發不同 emotion 時臉部表情切換、idle 動作正常 |

chitose model_dict 條目（kScale/位移先沿用合理預設，視畫面再調）：
```json
{
  "name": "chitose",
  "description": "Custom Live2D avatar for 486 VTuber",
  "url": "/live2d-models/chitose/runtime/chitose.model3.json",
  "kScale": 0.5,
  "initialXshift": 0,
  "initialYshift": 0,
  "kXOffset": 0,
  "idleMotionGroupName": "Idle",
  "emotionMap": {
    "neutral": 3,
    "joy": 5,
    "sadness": 4,
    "anger": 0,
    "surprise": 6,
    "fear": 6,
    "smirk": 5,
    "disgust": 0
  }
}
```

## 6. 驗證策略（TDD 精神）

無新 Python 邏輯，「測試」= 網頁實際載入 chitose + 表情切換。最硬證明（步驟 4）：在網頁對話送會引發不同情緒的訊息，觀察 chitose 臉部表情依 emotion 標籤改變。

通過條件（Definition of Done）：
- `app/live2d-models/chitose/runtime/chitose.model3.json` 就位。
- `model_dict.json` 含可解析的 chitose 條目，emotionMap 如 §4。
- `conf.yaml` `live2d_model_name: 'chitose'`。
- 瀏覽器載入顯示 chitose、idle 動作正常。
- 對話觸發 emotion 時表情切換（至少驗 2–3 種不同情緒）。

## 7. 風險與備援

- **emotionMap index 與實際 Expressions 順序不符**：本 spec 的 index 依實讀 `chitose.model3.json` 的 Expressions 陣列順序，若 app 載入後表情錯位，依實際順序修正 index。
- **emotion 標籤沒觸發表情（Runbook §10.5）**：確認 model_dict 的 emotionMap key 與模型輸出一致（小寫、無底線）；Open LLM VTuber 接 Live2D 後會透過 `live2d_expression_prompt`（conf.yaml `tool_prompts` 區，會把 `[<insert_emomap_keys>]` 換成 emotionMap 的 key）自動注入表情關鍵字到 system，引導 LLM 輸出表情 tag；在 server log 看 emotion parser 是否解析到。
- **chitose 大小/位置不對**：調 model_dict 的 `kScale`、`initialXshift`、`initialYshift`、`kXOffset`，重整網頁看。
- **資料集 emotion 偏 fear**：模型可能較常輸出 fear（資料 53/146）；本步只驗表情機制能切換，分布平衡屬資料層後續。
- **其他 Live2D bug**：參考官方文件 https://docs.llmvtuber.com/docs/user-guide/live2d/。
- **app/ gitignored**：素材、model_dict、conf.yaml 變更皆不進版控；本步唯一版控變更為最後把結果記到 spec。
