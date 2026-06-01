# Ollama 部署設計（第 ⑥ 步）

日期：2026-06-01
對應 Runbook：§7（部署到 Ollama）、§10.3（Ollama 載不到 GGUF）、§10.7（模型只吐 fear）
對應管線步驟：第 ⑥ 步「部署」

## 1. 目標與範圍

把第 ⑤ 步產出的 `gguf/qwen3-486-q4km.gguf`（2.33GB）透過 Modelfile 匯入 Ollama，成為可用 OpenAI 相容 API 呼叫的本地服務 `qwen3-486`，供第 ⑦ 步 Open LLM VTuber 連接。

**範圍內：**
- `ollama create qwen3-486 -f deploy/Modelfile`。
- 基本回話驗證（ollama run）。
- API 驗證：`/v1/chat/completions` 回 200、繁中、2–4 句、帶合理 `[emotion]` 標籤。
- 視結果微調 Modelfile（emotion 不出現或偏 fear 時）。

**範圍外：**
- Open LLM VTuber 串接（第 ⑦ 步）。
- emotion 資料失衡補強重訓（下一輪迭代）。
- TTS/ASR/Live2D（第 ⑦ 步）。

## 2. 現況（已確認）

- Ollama 已安裝：`version 0.24.0`（`C:\Users\chenb\AppData\Local\Programs\Ollama\ollama.exe`）。
- GGUF 就位：`gguf/qwen3-486-q4km.gguf`（2.33GB）。
- `deploy/Modelfile` 已存在且內容完整（無需重寫）：
  - `FROM D:/AI_486/gguf/qwen3-486-q4km.gguf`（絕對路徑、正斜線）。
  - Qwen3 chat template（`<|im_start|>` / `<|im_end|>`）。
  - 參數：temperature 0.8、top_p 0.9、repeat_penalty 1.1、num_ctx 4096、num_predict 200、stop `<|im_end|>` / `<|im_start|>`。
  - SYSTEM：完整菜月昴人設（繁中、2–4 句、8 種 emotion 標籤、版權自律）。

## 3. 使用者決策

| 項目 | 決策 |
| --- | --- |
| 人設 SYSTEM 位置 | **保留在 Modelfile**（現狀）。第 ⑦ 步 VTuber 若另送 system 會覆寫，不衝突 |
| 驗證深度 | **API 回繁中 + emotion 標籤**（對齊 Runbook §7.3） |
| 量化模型 | Q4_K_M（第 ⑤ 步產出） |

## 4. 架構：建立 + 驗證流水線

每步單一職責、可獨立驗證。

| 步驟 | 動作 | 驗證 |
| --- | --- | --- |
| 1 | `ollama create qwen3-486 -f deploy/Modelfile` | exit 0；`ollama list` 看得到 `qwen3-486` |
| 2 | 基本回話（`ollama run` 或 `/api/generate`，prompt 走 UTF-8 檔繞 cp950） | 載入成功、回繁體中文、無 crash |
| 3 | API 驗證 `POST /v1/chat/completions`（最硬證明） | 200 OK；content 為繁中；2–4 句；開頭帶合理 `[emotion]` 標籤 |

## 5. 驗證策略（TDD 精神）

本步無新 Python 邏輯，「測試」= API 實際回應符合條件。最硬證明為步驟 3 的 `/v1/chat/completions`：送一個會引發情緒的 user 訊息（如「我明天要面試，有點緊張」），檢查回應為繁中、長度適中、開頭含 8 種之一的 `[emotion]` 標籤。

通過條件（Definition of Done）：
- `ollama list` 含 `qwen3-486`。
- `/v1/chat/completions` 回 200，content 為繁體中文、2–4 句、含合理 `[emotion]` 標籤。
- 回應未大段複讀原作、未自稱官方/聲優。

## 6. 風險與備援

- **`ollama create` 報 unknown architecture（Runbook §10.3）**：升級 Ollama 到較新版（Qwen3 支援）；確認 FROM 為絕對路徑且檔案存在（已是）。
- **Windows cp950 console 中文亂碼**：沿用第 ⑤ 步教訓 —— prompt 走 `-f`/UTF-8 檔、`chcp 65001`、curl body 寫成 UTF-8 檔以 `-d @file` 送出；輸出導 UTF-8 檔檢視。非模型問題。
- **emotion 標籤沒出現或老是 `[fear]`（Runbook §10.7）**：資料集 fear 偏多（53/146）。短期對策：在 Modelfile SYSTEM 補一句「正常情境優先用 `[neutral]` 或 `[joy]`」後 `ollama create` 重建。屬執行時視結果調整，不預先改。
- **服務未啟動**：Ollama 安裝後以系統服務常駐；若 `/api/tags` 無回應，先 `ollama list` 觸發或確認服務。
