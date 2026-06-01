# Open LLM VTuber 階段二（Live2D chitose）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Open LLM VTuber 的 avatar 換成 chitose，並讓對話依 emotion 標籤切換臉部表情。

**Architecture:** 複製 chitose 素材到 app/live2d-models → 在 model_dict.json 註冊（emotionMap 對 chitose 表情 index）→ conf.yaml 指定 chitose → 重啟 server → 瀏覽器驗收。純設定，不寫新程式。

**Tech Stack:** Open LLM VTuber、Live2D（chitose）、conf.yaml/model_dict.json、瀏覽器。

對應 spec：`docs/superpowers/specs/2026-06-01-vtuber-stage2-live2d-chitose-design.md`
官方文件（除錯參考）：https://docs.llmvtuber.com/docs/user-guide/live2d/

---

## File Structure

- 複製到（不進版控，`app/` 與 `live2d-models/` 已 gitignore）：`app/live2d-models/chitose/runtime/`（chitose 全部素材）
- 修改（app 內，不進版控）：`app/model_dict.json`（新增 chitose 條目）、`app/conf.yaml`（live2d_model_name）
- 唯一版控變更：最後把結果記到 spec

來源素材：`C:\Users\chenb\Downloads\chitose\runtime\`。指令在 PowerShell 執行；app server 用 `uv run`。

---

### Task 1: 複製 chitose 素材到 app/live2d-models/

**Files:** 無版控變更（`live2d-models/` 已 gitignore）。

- [ ] **Step 1: 複製整個 runtime 資料夾**

```powershell
$src = "C:\Users\chenb\Downloads\chitose\runtime"
$dst = "D:\AI_486\app\live2d-models\chitose\runtime"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item "$src\*" $dst -Recurse -Force
```
Expected: 複製完成、無錯誤。

- [ ] **Step 2: 驗證 model3.json 就位**

```powershell
Test-Path D:\AI_486\app\live2d-models\chitose\runtime\chitose.model3.json
Test-Path D:\AI_486\app\live2d-models\chitose\runtime\chitose.moc3
(Get-ChildItem D:\AI_486\app\live2d-models\chitose\runtime\expressions\*.exp3.json).Count
```
Expected: 前兩者 True；expressions 數量為 7。

---

### Task 2: 在 model_dict.json 註冊 chitose

**Files:** 修改 `app/model_dict.json`（app 內，不進版控）。

- [ ] **Step 1: 讀現有 model_dict.json**

用 Read 工具讀 `D:\AI_486\app\model_dict.json`，確認它是一個 JSON 陣列、現有 mao_pro 條目的格式。

- [ ] **Step 2: 新增 chitose 條目**

用 Edit 工具，在 JSON 陣列中（mao_pro 條目之後、陣列結束 `]` 之前）加入 chitose 條目。確保前一條目後有逗號。要插入的物件：

```json
,
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

- [ ] **Step 3: 驗證 JSON 合法且含 chitose**

```powershell
D:\AI_486\.venv\Scripts\python.exe -c "import json; d=json.load(open(r'D:\AI_486\app\model_dict.json',encoding='utf-8')); names=[e['name'] for e in d]; assert 'chitose' in names, names; c=[e for e in d if e['name']=='chitose'][0]; assert c['emotionMap']['neutral']==3 and c['emotionMap']['anger']==0; print('OK names=', names)"
```
Expected: 印出 `OK names= ['mao_pro', 'chitose']`（順序可能不同）。若報 JSON 解析錯，回 Step 2 檢查逗號/括號。

---

### Task 3: conf.yaml 指定 chitose

**Files:** 修改 `app/conf.yaml`（app 內，不進版控）。

- [ ] **Step 1: 改 live2d_model_name**

用 Edit 工具，把 `D:\AI_486\app\conf.yaml` 的：
```yaml
  live2d_model_name: 'mao_pro' # Live2D 模型名称
```
改為：
```yaml
  live2d_model_name: 'chitose' # Live2D 模型名称
```

- [ ] **Step 2: 驗證**

```powershell
Select-String -Path D:\AI_486\app\conf.yaml -Pattern "live2d_model_name:"
```
Expected: 印出含 `live2d_model_name: 'chitose'` 的那行。

---

### Task 4: 重啟 server + 瀏覽器驗收

**Files:** 無版控變更。

- [ ] **Step 1: （若 server 在跑）停掉舊 server，重新啟動**

```powershell
cd D:\AI_486\app
$env:PYTHONUTF8 = "1"
uv run python run_server.py
```
（背景執行）Expected: log 出現 `Uvicorn running on http://localhost:12393`，無 traceback。

- [ ] **Step 2: 瀏覽器驗收 — 載入 chitose（最硬證明前半）**

開瀏覽器到 `http://localhost:12393`，**Ctrl+F5 強制重新整理**。
Expected: 看到 **chitose** 角色（不再是 mao_pro），idle 動作正常。
**備援：** 若角色太大/太小/位置偏 → 調 model_dict.json 的 `kScale`（如 0.3 或 0.0006）、`initialYshift`、`kXOffset`，存檔後重整網頁。若空白/載不出 → 看 server log 與瀏覽器 console，確認 url 路徑（`/live2d-models/chitose/runtime/chitose.model3.json`）正確；參考官方文件 https://docs.llmvtuber.com/docs/user-guide/live2d/。

- [ ] **Step 3: 對話驗收 — 表情切換（最硬證明後半）**

在網頁對話框依序送會引發不同情緒的訊息，例如：
- `我剛剛升職了，超開心！`（期望 joy → Smile）
- `我的貓昨天走了，好難過。`（期望 sadness → Sad）
- `你怎麼又遲到了！`（期望 anger → Angry）

Expected：chitose 臉部表情隨回覆的 emotion 標籤切換（至少 2–3 種不同情緒可見變化）。
**備援（Runbook §10.5）：** 若表情不動 → 確認回覆有帶 emotion 標籤（看 server log 的 emotion parser）；確認 emotionMap key 與輸出一致（小寫無底線）。

- [ ] **Step 4: 記錄結果到 spec §8**

把實際畫面（chitose 載入、表情切換哪幾種有效、kScale 等是否調過）追加為 spec 的「## 8. 實際結果（階段二）」一節，commit：
```powershell
cd D:\AI_486
git add docs/superpowers/specs/2026-06-01-vtuber-stage2-live2d-chitose-design.md
git commit -m "docs: record VTuber stage 2 result (chitose Live2D + expressions)"
```

---

## Self-Review

**1. Spec coverage：**
- spec §5 步驟 1 複製素材 → Task 1。✅
- spec §5 步驟 2 註冊 model_dict（emotionMap §4、idleMotionGroupName=Idle）→ Task 2。✅
- spec §5 步驟 3 conf.yaml live2d_model_name → Task 3。✅
- spec §5 步驟 4 + §6 重啟 + 載入 chitose + 表情切換驗收 → Task 4。✅
- spec §3 決策（§8.4 emotionMap、runtime 子層、驗收到表情切換）→ Task 2 emotionMap、Task 1 runtime 路徑、Task 4 Step 3。✅
- spec §7 備援（index 錯位、表情沒觸發、大小位置、官方文件）→ Task 4 Step 2/3 備援。✅

**2. Placeholder scan：** 所有步驟為完整可執行指令與具體 JSON；kScale 備援值為實際可試的數值範圍，非未定 placeholder。無 TODO/TBD。✅

**3. Consistency：** 全程 url `/live2d-models/chitose/runtime/chitose.model3.json`、name `chitose`、emotionMap index（neutral=3/joy=5/sadness=4/anger=0/surprise=6/fear=6/smirk=5/disgust=0）、idleMotionGroupName `Idle` 一致。✅
