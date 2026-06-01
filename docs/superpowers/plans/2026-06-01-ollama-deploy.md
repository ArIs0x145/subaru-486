# Ollama 部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `gguf/qwen3-486-q4km.gguf` 透過 `deploy/Modelfile` 匯入 Ollama 成 `qwen3-486`，並用 `/v1/chat/completions` 驗證回繁中 + 帶 `[emotion]` 標籤。

**Architecture:** Modelfile 已完整（FROM、Qwen3 template、菜月昴 SYSTEM、參數）。本計畫執行 `ollama create` → 基本回話 → API 驗證三步，每步驗證；emotion 不出現或偏 fear 時微調 Modelfile SYSTEM 重建。

**Tech Stack:** Ollama 0.24.0、curl、Windows PowerShell（cp950 → UTF-8 檔繞行）。

對應 spec：`docs/superpowers/specs/2026-06-01-ollama-deploy-design.md`

---

## File Structure

- 既有、可能微調：`deploy/Modelfile`（FROM + template + SYSTEM + 參數；僅在 emotion 驗證不過時改 SYSTEM）
- 不進版控（暫存）：驗證用的 UTF-8 prompt/body 檔（驗完刪）
- Ollama 模型 `qwen3-486` 存於 Ollama 自身 store（不在 repo）

指令在 `D:\AI_486` 下執行；Ollama exe 在 PATH（`ollama`）。中文一律走 UTF-8 檔避免 cp950。

---

### Task 1: 建立 Ollama 模型

**Files:** 無版控變更（Ollama store）。

- [ ] **Step 1: 確認 Ollama 服務可用**

```powershell
ollama list
```
Expected: 指令成功（可能空清單），代表服務常駐中。若報連線錯誤，開 Ollama app 或等服務啟動後重試。

- [ ] **Step 2: 從 Modelfile 建立模型**

```powershell
cd D:\AI_486
ollama create qwen3-486 -f deploy\Modelfile
```
Expected: 印出 layer 寫入進度、最後 `success`、exit 0。
**備援（Runbook §10.3）：** 若報 `unknown architecture` → Ollama 版本太舊不支援 Qwen3，升級 Ollama 後重試；確認 `deploy\Modelfile` 的 `FROM` 路徑檔案存在（`Test-Path D:\AI_486\gguf\qwen3-486-q4km.gguf` 應為 True）。

- [ ] **Step 3: 驗證模型已註冊**

```powershell
ollama list | Select-String "qwen3-486"
```
Expected: 印出含 `qwen3-486` 的一行（含大小、modified time）。

---

### Task 2: 基本回話驗證（繞 cp950）

**Files:** 無版控變更。

- [ ] **Step 1: 用 /api/generate 送一句、輸出導 UTF-8 檔**

Windows console 顯示中文會亂碼，故輸出寫檔再讀。Ollama 的 HTTP API 收發都是 UTF-8，避開 console 問題：

```powershell
cd D:\AI_486
$body = @{ model = "qwen3-486"; prompt = "你好，請自我介紹一句。"; stream = $false } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json" | Select-Object -ExpandProperty response | Out-File D:\AI_486\_gen.txt -Encoding utf8
```
Expected: exit 0、`_gen.txt` 產生。

- [ ] **Step 2: 讀檔確認繁中**

Run: `Read D:\AI_486\_gen.txt`（用 Read 工具）
Expected: 內容為繁體中文、自然成句、無亂碼、無 crash。

---

### Task 3: API 驗證 /v1/chat/completions（最硬證明）

**Files:** 無版控變更。

- [ ] **Step 1: 送會引發情緒的訊息，輸出導 UTF-8 檔**

```powershell
cd D:\AI_486
$body = @{
  model = "qwen3-486"
  messages = @(@{ role = "user"; content = "我明天要面試，有點緊張。" })
  temperature = 0.8
} | ConvertTo-Json -Depth 5
$resp = Invoke-RestMethod -Uri "http://localhost:11434/v1/chat/completions" -Method Post -Body $body -ContentType "application/json"
$resp.choices[0].message.content | Out-File D:\AI_486\_chat.txt -Encoding utf8
"HTTP path OK; finish_reason=$($resp.choices[0].finish_reason)"
```
Expected: 印出 `HTTP path OK; finish_reason=stop`（或類似）、`_chat.txt` 產生。

- [ ] **Step 2: 讀檔人工檢查通過條件**

Run: `Read D:\AI_486\_chat.txt`（用 Read 工具）
Expected（Definition of Done）：
- content 為繁體中文。
- 2–4 句、長度適合 TTS。
- 開頭含一個合理的 `[emotion]` 標籤（8 種之一：neutral/joy/sadness/anger/surprise/fear/smirk/disgust）。
- 未大段複讀原作、未自稱官方/聲優。

- [ ] **Step 3: 視結果決定是否微調 Modelfile**

判斷：
- **若全部通過** → 進 Step 4。
- **若沒有 emotion 標籤，或情緒明顯偏 `[fear]`（連面試緊張這種都還算合理，但若打招呼也 fear）** → 編輯 `deploy\Modelfile` 的 SYSTEM，在情緒規則後補一句：
  ```
  正常或正面情境優先使用 [neutral] 或 [joy]，避免過度使用 [fear]。
  ```
  然後重建並重驗：
  ```powershell
  cd D:\AI_486
  ollama create qwen3-486 -f deploy\Modelfile
  ```
  重跑 Task 3 Step 1–2 確認改善。

- [ ] **Step 4: 清理暫存檔並 commit（若有改 Modelfile）**

```powershell
cd D:\AI_486
Remove-Item D:\AI_486\_gen.txt, D:\AI_486\_chat.txt -ErrorAction SilentlyContinue
```
若 Step 3 有改 Modelfile：
```powershell
git add deploy/Modelfile
git commit -m "tune: bias emotion tags toward neutral/joy in Modelfile SYSTEM"
```
若未改 Modelfile：本步無 commit，部署成果記錄到 spec（下方 Step 5）。

- [ ] **Step 5: 記錄部署結果到 spec §7**

把 `ollama list` 那行與 API 回應範例追加為 spec 的「## 7. 實際部署結果」一節，commit：
```powershell
cd D:\AI_486
git add docs/superpowers/specs/2026-06-01-ollama-deploy-design.md
git commit -m "docs: record Ollama deploy result (qwen3-486 API verified)"
```

---

## Self-Review

**1. Spec coverage：**
- spec §4 步驟 1 `ollama create` + `ollama list` → Task 1。✅
- spec §4 步驟 2 基本回話（UTF-8 繞 cp950）→ Task 2。✅
- spec §4 步驟 3 + §5 API `/v1/chat/completions` 驗繁中+emotion → Task 3 Step 1-2。✅
- spec §3 決策（人設留 Modelfile）→ 不改 SYSTEM 結構，僅 emotion 不過時微調。✅
- spec §6 備援（unknown architecture、cp950、偏 fear）→ Task 1 Step 2 備援、全程 UTF-8 檔、Task 3 Step 3。✅
- spec §5 DoD（list 含 qwen3-486、API 200 繁中 emotion、不複讀/不自稱官方）→ Task 1 Step 3、Task 3 Step 2。✅

**2. Placeholder scan：** 所有步驟為完整可執行指令；Task 3 Step 3 的分支判斷附明確條件與具體補句，非 placeholder。無 TODO/TBD。✅

**3. Consistency：** 全程模型名 `qwen3-486`、Modelfile 路徑 `deploy\Modelfile`、GGUF `gguf/qwen3-486-q4km.gguf`、API port 11434 一致；用 Invoke-RestMethod（不用 curl）統一避開 PowerShell 引號與 cp950。✅
