# Open LLM VTuber 階段一（裝 + 接 LLM + 純文字）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Open LLM VTuber clone 到 `app/`、`uv sync`、設定 conf.yaml 指向本地 Ollama `qwen3-486`，啟動後用其內建網頁完成一輪菜月昴風繁中文字對話。

**Architecture:** 純整合，不寫新程式。clone → uv sync → 讀實際 conf.yaml 範本後改 LLM provider 區塊 → run_server.py → 瀏覽器網頁對話。app 有自己的 venv，與 `D:\AI_486\.venv` 嚴格分開。

**Tech Stack:** Open LLM VTuber（Python）、uv、Ollama（localhost:11434）、瀏覽器。

對應 spec：`docs/superpowers/specs/2026-06-01-vtuber-stage1-install-llm-text-design.md`
官方文件（除錯參考）：https://docs.llmvtuber.com/docs/user-guide/live2d/

---

## File Structure

- 不進版控（`.gitignore` 已排除 `app/`）：整個 `app/`（Open LLM VTuber clone，含其自身 venv 與 conf.yaml）
- 本步不修改任何 repo 內版控檔（純整合）；唯一版控變更是最後把結果記到 spec
- 指令在 `D:\AI_486` 或 `D:\AI_486\app` 下執行。**注意**：app 用 `uv run`（它自己的 venv），不要用 `D:\AI_486\.venv`。

---

### Task 1: Clone Open LLM VTuber 到 app/

**Files:** 無版控變更（`app/` 已 gitignore）。

- [ ] **Step 1: 確認 app/ 不存在、Ollama 可用**

```powershell
cd D:\AI_486
Test-Path app
ollama list | Select-String "qwen3-486"
```
Expected: `Test-Path app` 為 False（或空）；`ollama list` 印出含 `qwen3-486` 的一行。

- [ ] **Step 2: clone（main 最新）**

```powershell
cd D:\AI_486
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git app
```
Expected: clone 完成、exit 0。

- [ ] **Step 3: 驗證關鍵檔存在**

```powershell
Test-Path D:\AI_486\app\run_server.py
Get-ChildItem D:\AI_486\app\conf*.yaml, D:\AI_486\app\*.yaml -ErrorAction SilentlyContinue | Select-Object Name
```
Expected: `run_server.py` 為 True；列出 conf 相關 yaml（可能是 `conf.yaml` 或 `conf.default.yaml` 等範本）。

---

### Task 2: uv sync 裝相依（app 自己的 venv）

**Files:** 無版控變更。

- [ ] **Step 1: uv sync**

```powershell
cd D:\AI_486\app
uv sync
```
Expected: 建立 `app\.venv`、相依裝齊、exit 0。可能耗時數分鐘。
**備援：** 若 `uv sync` 因缺 `pyproject.toml`/`uv.lock` 失敗，依 app 官方 README 的安裝指令（可能是 `uv pip install -r requirements.txt` 或 `pip install -e .`）。讀 `D:\AI_486\app\README.md` 的 install 段落。

- [ ] **Step 2: 驗證 app venv 建好**

```powershell
Test-Path D:\AI_486\app\.venv\Scripts\python.exe
```
Expected: True。

---

### Task 3: 設定 conf.yaml 指向 Ollama

**Files:** 修改 `app/conf.yaml`（app 內，不進我們版控）。

- [ ] **Step 1: 找出並讀取實際的 conf 範本**

```powershell
Get-ChildItem D:\AI_486\app -Filter "conf*.yaml" | Select-Object Name
```
若只有範本（如 `conf.default.yaml`），複製成 `conf.yaml`：
```powershell
if (-not (Test-Path D:\AI_486\app\conf.yaml)) { Copy-Item D:\AI_486\app\conf.default.yaml D:\AI_486\app\conf.yaml -ErrorAction SilentlyContinue }
```
然後用 Read 工具讀 `D:\AI_486\app\conf.yaml`，找出 LLM provider 區塊的**實際欄位名**（不同版本不同；常見 `llm_provider:` + `openai_compatible_llm:` 子區塊，或 `agent_config` 下的 llm 設定）。

- [ ] **Step 2: 依實際結構設定 LLM 指向 Ollama**

用 Edit 工具，把 conf.yaml 的 LLM provider 設為 OpenAI 相容、指向 Ollama。依 Step 1 讀到的實際欄位名填，等效設定為：
- provider 選 OpenAI 相容（如 `llm_provider: openai_compatible_llm`）
- `base_url: "http://localhost:11434/v1"`
- `model: "qwen3-486"`
- `llm_api_key: "ollama"`（Ollama 不驗證，任意非空字串）
- 溫度等可留預設或 `temperature: 0.8`

範例（以實際欄位名為準調整）：
```yaml
llm_provider: openai_compatible_llm
openai_compatible_llm:
  base_url: "http://localhost:11434/v1"
  model: "qwen3-486"
  llm_api_key: "ollama"
  temperature: 0.8
```

- [ ] **Step 3: 確認 persona/角色設定不覆寫掉 emotion 行為（讀，不一定改）**

讀 conf.yaml 是否有 `persona_prompt` / 角色 system。若有預設角色 prompt 會被送為 system（覆寫我們 Modelfile 的 SYSTEM）。本階段可：
- 保留 app 預設（先求跑通），或
- 把 persona 設成我們的菜月昴人設（與 Modelfile SYSTEM 一致，含 8 種 emotion 標籤規則）。
本步**先求跑通**，persona 微調留到看實際回覆後再決定，不阻塞啟動。

---

### Task 4: 啟動 server 並用內建網頁對話驗收

**Files:** 無版控變更。

- [ ] **Step 1: 啟動後端**

```powershell
cd D:\AI_486\app
uv run python run_server.py
```
Expected: 終端印出後端啟動訊息與位址（約 `http://localhost:12393` 或 README 指定 port），無 traceback。
**備援（Runbook §10.4）：** 若啟動報缺套件，回 Task 2 確認 uv sync 完整；若報 config 解析錯，回 Task 3 對照範本欄位。

- [ ] **Step 2: 確認 Ollama 連得到（另開一個終端）**

```powershell
Invoke-WebRequest "http://localhost:11434/api/tags" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```
Expected: `200`（確認 LLM 後端在）。

- [ ] **Step 3: 瀏覽器開內建網頁、文字對話（最硬證明）**

開瀏覽器到 Step 1 顯示的位址。在對話框輸入：`我明天要面試，有點緊張。`
Expected（Definition of Done）：
- 看到回覆，為繁體中文、菜月昴風、2–4 句。
- 開頭帶合理 `[emotion]` 標籤（8 種之一）。
- 延遲可接受（首字數秒內）。
**備援：** 若 UI 一直轉圈 → Runbook §10.4：確認 `base_url` 含 `/v1`、`model` 名與 `ollama list` 完全一致、Windows 防火牆允許本地呼叫；必要時查官方文件 https://docs.llmvtuber.com/docs/user-guide/live2d/。

- [ ] **Step 4: 記錄結果到 spec §8**

把實際 server 位址、conf.yaml 用到的欄位名、對話一例追加為 spec 的「## 8. 實際串接結果（階段一）」一節，commit：
```powershell
cd D:\AI_486
git add docs/superpowers/specs/2026-06-01-vtuber-stage1-install-llm-text-design.md
git commit -m "docs: record VTuber stage 1 result (text chat via web UI)"
```

---

## Self-Review

**1. Spec coverage：**
- spec §5 步驟 1 clone app（main 最新）→ Task 1。✅
- spec §5 步驟 2 uv sync（app 自己 venv）→ Task 2。✅
- spec §5 步驟 3 讀範本後設 LLM 指向 Ollama → Task 3（含「先讀再改」）。✅
- spec §5 步驟 4 啟動 run_server → Task 4 Step 1。✅
- spec §5 步驟 5 + §6 內建網頁文字對話驗收 → Task 4 Step 3。✅
- spec §7 備援（conf 欄位隨版本、連不到 LLM、uv sync、官方文件）→ Task 2/3/4 各備援。✅

**2. Placeholder scan：** conf.yaml 因「欄位隨版本」本就需 clone 後讀實際範本，計畫以「先讀再改 + 等效設定 + 範例」處理，並非未定 placeholder；其餘步驟皆具體指令。無 TODO/TBD。✅

**3. Consistency：** 全程 app 路徑 `D:\AI_486\app`、model 名 `qwen3-486`、base_url `http://localhost:11434/v1`、app venv 用 `uv run`（不混用 `D:\AI_486\.venv`）一致。✅
