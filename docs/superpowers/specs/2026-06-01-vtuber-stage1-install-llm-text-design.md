# Open LLM VTuber 串接 — 階段一：裝 + 接 LLM + 純文字對話（第 ⑦ 步之一）

日期：2026-06-01
對應 Runbook：§8（Open LLM VTuber 串接）、§8.2（建議分階段）、§10.4（連不到 LLM）
對應管線步驟：第 ⑦ 步「VTuber 串接」的階段一（共四階段：LLM→Live2D→ASR→TTS）

## 1. 目標與範圍

把 Open LLM VTuber 裝起來、設定好，用它**內建的 Web 介面**與已部署的 `qwen3-486`（Ollama）做純文字對話。本步**不寫新程式**，純整合與設定。

第 ⑦ 步整體含 4 個子系統（LLM 串接、Live2D、ASR、TTS），Runbook §8.2 建議分階段上。本 spec 只涵蓋**階段一**。

**範圍內：**
- `git clone` Open LLM VTuber 到 `app/`（跟 main 最新 commit）。
- `uv sync` 裝其相依（它建自己的 venv）。
- 改 `conf.yaml`：LLM provider 指向本地 Ollama（base_url、model、api_key）。
- 啟動 `run_server.py`。
- 驗收：瀏覽器開內建網頁，文字對話，看到菜月昴風繁中回覆（帶 emotion 標籤）。

**範圍外（後續階段）：**
- Live2D（chitose 素材已就位，階段二）。
- ASR（faster-whisper，階段三）。
- TTS（edge-tts，階段四）。
- 五階段驗收的後四階段（第 ⑧ 步）。

## 2. 概念澄清

「瀏覽器」不是要自行開發的東西。**Open LLM VTuber 本身內建一個 Web UI**：後端 `run_server.py`（Python，連 LLM/ASR/TTS）+ 前端網頁（瀏覽器開啟，顯示 Live2D 與對話框）。本步只是把它裝起來、設定好，讓它的網頁連到我們的菜月昴模型。不寫新前端。

## 3. 現況（已確認）

- `app/` **尚未 clone**（`.gitignore` 第 46 行已排除 `app/`，clone 進來不進我們版控）。
- Ollama 服務常駐、`qwen3-486` 已部署、API 驗證過（見 `2026-06-01-ollama-deploy-design.md` §7）。
- uv 已裝（0.10+）。磁碟 D: 約 156GB 空閒，充足。
- chitose Live2D 素材就位於 `C:\Users\chenb\Downloads\chitose\runtime`（階段二用，本步不碰）。

## 4. 使用者決策

| 項目 | 決策 |
| --- | --- |
| 範圍切分 | 分階段；本輪只做「裝 + 接 LLM + 純文字」 |
| app/ 版本 | 跟 main 最新 commit |
| 驗收深度 | 用內建網頁實際文字對話菜月昴 |

## 5. 架構：clone → 設定 → 啟動 → 對話

| 步驟 | 動作 | 驗證 |
| --- | --- | --- |
| 1 | `git clone <repo> app`（main 最新） | `app/run_server.py`、`app/conf.yaml`（或範本）存在 |
| 2 | `cd app; uv sync` | 建好 app 自己的 `.venv`、相依裝齊、exit 0 |
| 3 | 讀實際 `conf.yaml` 範本 → 設 LLM provider 指向 Ollama | conf.yaml 的 LLM 區塊 base_url=`http://localhost:11434/v1`、model=`qwen3-486`、api_key=`ollama` |
| 4 | `uv run python run_server.py` | 終端顯示後端啟動於某 port（約 12393），無錯誤 |
| 5 | 瀏覽器開該位址，打字對話（最硬證明） | 看到菜月昴風繁中回覆、帶合理 `[emotion]` 標籤、延遲可接受 |

> conf.yaml 的確切欄位名隨 Open LLM VTuber 版本而異。**步驟 3 先讀 clone 後的實際範本再改**，不照記憶硬填（Runbook §8.2）。

## 6. 驗證策略（TDD 精神）

本步無新 Python 邏輯，「測試」= 端到端對話實際成立。最硬證明為步驟 5：在內建網頁打一句會引發情緒的訊息（如「我明天要面試，有點緊張」），看到繁中、角色感、emotion 標籤的回覆。

通過條件（Definition of Done）：
- `app/` clone 完成、`uv sync` 成功。
- `conf.yaml` LLM 區塊指向本地 Ollama `qwen3-486`。
- `run_server.py` 啟動成功、無錯誤。
- 瀏覽器內建網頁可完成至少一輪文字對話，回覆為菜月昴風繁中、帶 emotion 標籤。

## 7. 風險與備援

- **conf.yaml 欄位名隨版本不同（Runbook §8.2）**：clone 後先讀實際範本，依其 LLM provider 區塊結構填（常見 `llm_provider: openai_compatible_llm` + 對應子區塊）。
- **連不到 LLM（Runbook §10.4）**：瀏覽器直接打 `http://localhost:11434/api/tags` 確認 Ollama 有回；`base_url` 必須含 `/v1`；`model` 名稱需與 `ollama list` 完全一致（`qwen3-486`）；Windows 防火牆首次可能擋本地呼叫，允許即可。
- **uv sync 耗時或撞相依**：依 app 官方 README；app 的 venv 與我們的 `D:\AI_486\.venv` 嚴格分開，不可混用。
- **其他串接 bug**：參考官方文件 https://docs.llmvtuber.com/docs/user-guide/live2d/ （Live2D 與使用者指南；含 conf.yaml、啟動相關說明）。
- **中文驗證**：在瀏覽器網頁內看回覆，不經 PowerShell，不受先前 cp950 / Invoke-RestMethod latin1 解碼 bug 影響。

## 8. 實際串接結果（階段一）

- 日期：2026-06-01
- Open LLM VTuber clone 至 `app/`（main 最新）；`frontend/` 為 git submodule，clone 時未帶 `--recursive`，需另跑 `git submodule update --init --recursive` 補齊（否則網頁空白）。
- `uv sync` 成功，建 app 自己的 `app/.venv`（與 D:\AI_486\.venv 分開）。
- conf 範本：`config_templates/conf.ZH.default.yaml`（繁/簡中導向版）→ 複製成 `app/conf.yaml`。
- LLM 設定（實際欄位）：`character_config.agent_config.agent_settings.basic_memory_agent.llm_provider: 'ollama_llm'`；`character_config.agent_config.llm_configs.ollama_llm`：`base_url: http://localhost:11434/v1`、`model: 'qwen3-486'`。
- 啟動：`uv run python run_server.py` → `Uvicorn running on http://localhost:12393`；log 確認 `Initialized AsyncLLM ... qwen3-486`。
- 內建網頁文字對話：成功，回覆為菜月昴風、繁中。✅
- 踩雷（root cause）：預設 `persona_prompt` 是簡體的「Mili」角色，會被當 system prompt 送入並**覆寫 Modelfile 的菜月昴 SYSTEM** → 導致回覆變簡體且非菜月昴。對策：把 conf.yaml 的 `persona_prompt` 改為菜月昴人設並明確「一律繁體中文、禁簡體」，`character_name` 改為「菜月昴」，重啟 server 後恢復繁體 + 角色語氣。
- 範圍外（後續階段）：Live2D（chitose，`live2d_model_name` 仍為預設 mao_pro）、ASR、TTS。emotion 標籤機制走 VTuber 的 `live2d_expression_prompt`（階段二接 Live2D 時處理），本階段未強制。
