# Open LLM VTuber TTS 階段（edge-tts 繁中男聲）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 edge_tts voice 改成繁中男聲 zh-TW-YunJheNeural，讓菜月昴開口說繁中，並驗證表情隨語音切換。

**Architecture:** 純設定。改 conf.yaml 一行 voice → 離線合成測試確認 voice 有效 → 重啟 server → 瀏覽器聽語音 + 看表情。

**Tech Stack:** Open LLM VTuber、edge-tts（線上）、瀏覽器。app 用 `uv run`（其自身 venv）。

對應 spec：`docs/superpowers/specs/2026-06-01-vtuber-tts-edge-design.md`
官方文件（除錯參考）：https://docs.llmvtuber.com/docs/user-guide/live2d/

---

## File Structure

- 修改（app 內，gitignored）：`app/conf.yaml`（edge_tts.voice）
- 暫存（驗完刪）：edge-tts 合成測試的 mp3
- 唯一版控變更：最後把結果記到 spec

---

### Task 1: 改 voice 為 zh-TW-YunJheNeural

**Files:** 修改 `app/conf.yaml`（gitignored）。

- [ ] **Step 1: 用 Edit 改 voice**

把 `D:\AI_486\app\conf.yaml` 的：
```yaml
      voice: zh-CN-XiaoxiaoNeural # 'en-US-AvaMultilingualNeural' #'zh-CN-XiaoxiaoNeural' # 'ja-JP-NanamiNeural'
```
改為：
```yaml
      voice: zh-TW-YunJheNeural # 台灣繁中男聲（菜月昴）
```

- [ ] **Step 2: 驗證**

```powershell
Select-String -Path D:\AI_486\app\conf.yaml -Pattern "voice: zh-TW-YunJheNeural"
```
Expected: 印出該行。

---

### Task 2: edge-tts 離線合成測試（確認 voice 有效）

**Files:** 無版控變更。

- [ ] **Step 1: 用 app venv 跑 edge-tts CLI 合成一句**

```powershell
cd D:\AI_486\app
uv run edge-tts --voice zh-TW-YunJheNeural --text "你好，我是菜月昴，今天也要加油！" --write-media D:\AI_486\_ttstest.mp3
```
Expected: exit 0、無錯誤。
**備援：** 若報 voice 不存在 → `uv run edge-tts --list-voices | Select-String "zh-TW"` 看實際可用的台灣男聲名稱，回 Task 1 改正。若報連線錯 → 確認網路，edge-tts 是微軟線上服務。

- [ ] **Step 2: 驗證 mp3 非空**

```powershell
$f = Get-Item D:\AI_486\_ttstest.mp3 -ErrorAction SilentlyContinue
if ($f -and $f.Length -gt 1000) { "OK $($f.Length) bytes" } else { "FAIL empty/missing" }
```
Expected: `OK <非零> bytes`。（可選：播放 `D:\AI_486\_ttstest.mp3` 聽一下聲線。）

- [ ] **Step 3: 清掉測試檔**

```powershell
Remove-Item D:\AI_486\_ttstest.mp3 -ErrorAction SilentlyContinue
```

---

### Task 3: 重啟 server + 瀏覽器驗收（語音 + 表情）

**Files:** 無版控變更。

- [ ] **Step 1: （若 server 在跑）停掉，重啟**

```powershell
cd D:\AI_486\app
$env:PYTHONUTF8 = "1"
uv run python run_server.py
```
（背景執行）Expected: log `Uvicorn running on http://localhost:12393`、`Initializing TTS: edge_tts`、無 traceback。

- [ ] **Step 2: 瀏覽器驗收（最硬證明）**

開瀏覽器 `http://localhost:12393`，**Ctrl+F5**。打字：`我剛剛升職了，超開心！`
Expected（Definition of Done）：
- **聽到繁中男聲**唸出回覆（若無聲：點一下頁面互動、確認分頁未靜音、瀏覽器允許音訊播放後重試）。
- 回覆為菜月昴風繁中。
- **mao_pro 表情隨語音切換**（送 2–3 種情緒：升職開心、貓走難過、遲到生氣，觀察臉部變化）。
**備援：** 有語音但表情不動 → F12 console 看 `actions {expressions:...}` 是否到前端、mao_pro 是否載入；參考官方文件。麥克風權限被拒可忽略（TTS 不需要）。

- [ ] **Step 3: 記錄結果到 spec §7**

把實際聲線、是否聽到語音、表情切換哪幾種有效追加為 spec 的「## 7. 實際結果（TTS 階段）」一節，commit：
```powershell
cd D:\AI_486
git add docs/superpowers/specs/2026-06-01-vtuber-tts-edge-design.md
git commit -m "docs: record TTS stage result (edge-tts zh-TW voice + expressions via audio)"
```

---

## Self-Review

**1. Spec coverage：**
- spec §4 步驟 1 改 voice → Task 1。✅
- spec §4 步驟 2 edge-tts 合成測試 → Task 2。✅
- spec §4 步驟 3 重啟 → Task 3 Step 1。✅
- spec §4 步驟 4 + §5 瀏覽器聽語音 + 表情切換 → Task 3 Step 2。✅
- spec §3 決策（zh-TW-YunJheNeural、驗到語音+表情）→ Task 1 voice、Task 3 Step 2。✅
- spec §6 備援（自動播放、voice 名稱、麥克風不影響、log 假象）→ Task 2/3 備援。✅

**2. Placeholder scan：** 所有步驟為完整可執行指令；voice 名稱、測試文字、驗收訊息皆具體。無 TODO/TBD。✅

**3. Consistency：** 全程 voice `zh-TW-YunJheNeural`、app 路徑 `D:\AI_486\app`、port 12393、edge-tts CLI 用法一致。✅
