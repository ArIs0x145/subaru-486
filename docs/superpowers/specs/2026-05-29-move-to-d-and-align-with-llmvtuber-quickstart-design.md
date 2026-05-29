# Migrate Project to D: and Align with Open LLM VTuber Quick-Start

**Date:** 2026-05-29
**Status:** Approved by user (2026-05-29)
**Author:** ArIs0x145 + AI assistant brainstorm

## 1. 目標

1. 把整個 AI VTuber 專案從 `S:\AI_486\` 搬到 `D:\AI_486\`，單一根目錄管理。
2. 移除過渡期的 `D:\AI_486_workspace\` 目錄，後續所有大檔（hf_cache / gguf / train_outputs / app）合進 `D:\AI_486\` 並由 `.gitignore` 排除。
3. 把 `EXECUTION_RUNBOOK.md` §8 對齊 Open LLM VTuber 官方 quick-start
   (`https://docs.llmvtuber.com/docs/quick-start/`)，修正 5 個落差。

## 2. 不在範圍

- 不執行 LoRA 訓練（那是 Runbook §5 動作，搬遷後另外做）。
- 不下載 base 模型（搬遷後執行訓練腳本時自動下載）。
- 不安裝 Open LLM VTuber（搬遷與 Runbook 對齊完才動工）。
- 不調整菜月昴 dataset 內容、emotion 分布、訓練超參數。

## 3. 已敲定的決策

| 項目 | 決定 |
| --- | --- |
| 搬遷目標 | `D:\AI_486\`（合併原 S: repo 與 D:\AI_486_workspace） |
| `D:\AI_486_workspace\` | 搬遷完成後**整個移除** |
| ASR | 用 Open LLM VTuber 預設 **sherpa-onnx (SenseVoiceSmall)**，不再保留 Faster-Whisper 寫法 |
| Python | 維持 3.12（已驗證 ML stack OK） |
| PyTorch | 維持 `2.11.0+cu128` |
| LLM provider 配置 | 改用 `ollama_llm`（官方原生），不再走 `openai_compatible_llm` |
| 角色 prompt | 保留現有版本，僅修改路徑與 provider 名 |

## 4. Phase 1：搬遷流程

執行順序嚴格從上到下，每一步都要驗證才能進下一步。

### 4.1 前置驗證
- `git -C s:/AI_486 status` 必須 clean（已 commit 完）。
- `nvidia-smi` 仍偵測到 RTX 4060 Laptop GPU。
- 關閉佔用 venv 的程式（VS Code 內開的 Python interpreter、終端機 activate 中的 PowerShell）。

### 4.2 建立 D: 根目錄並複製內容
- `New-Item -ItemType Directory D:\AI_486`
- 用 `robocopy` 從 `S:\AI_486` 複製到 `D:\AI_486`，**排除** `.venv` 與 `unsloth_compiled_cache`：
  ```
  robocopy S:\AI_486 D:\AI_486 /MIR /XD .venv unsloth_compiled_cache
  ```
- 預期：D:\AI_486 內含 .git、.gitignore、486Dataset.jsonL、converted_dataset、data、deploy、所有 .md、所有 .py。

### 4.3 驗證 git history 完整
- `git -C d:/AI_486 log --oneline` 應該看到 2 個 commit（`67991f7`、`6390b32`）。
- `git -C d:/AI_486 status` 應該 clean。

### 4.4 在 D: 重建 .venv
- `cd D:\AI_486`
- `uv venv --python 3.12 .venv`
- 重灌 ML stack（按 Runbook §3.3-3.4 順序，含 cu128 reinstall 步驟）。uv 快取命中，預期 1-2 分鐘。

### 4.5 驗證 ML stack
- `python -c "import torch; print(torch.cuda.is_available())"` → True
- `python -c "from unsloth import FastLanguageModel; print('OK')"` → OK
- `python -c "import datasets"` → 不 crash

### 4.6 合併 workspace 子目錄到 D:\AI_486\
- 把 `D:\AI_486_workspace\hf_cache\` 搬到 `D:\AI_486\hf_cache\`
- 把 `D:\AI_486_workspace\train_outputs\` 搬到 `D:\AI_486\train_outputs\`
- 把 `D:\AI_486_workspace\gguf\` 搬到 `D:\AI_486\gguf\`
- 目前這些都是空目錄，動作極輕。

### 4.7 重設 HF_HOME
- `[System.Environment]::SetEnvironmentVariable('HF_HOME', 'D:\AI_486\hf_cache', 'User')`
- 重開 PowerShell 讓 User 級變數生效。

### 4.8 刪除舊 S:\AI_486 與 D:\AI_486_workspace
- 全部驗證通過才執行。
- `Remove-Item -Recurse -Force S:\AI_486`
- `Remove-Item -Recurse -Force D:\AI_486_workspace`

### 4.9 更新 .gitignore（在 D: 上）
- 現有 `.gitignore` 已含 `gguf/`、`app/`、`live2d-models/`、`venv/`、`.venv/`，這些通用 pattern 在新結構下仍正確，無需移除。
- 新增：`hf_cache/`、`train_outputs/`（過去這兩個目錄在 `D:\AI_486_workspace\` 不在 repo 內，沒人 gitignore；現在合進 repo 必須排除）。
- 舊的 `train/venv/`、`train/outputs/` 等 stale entry 可保留（pattern 永遠不會命中，不造成問題），維持 .gitignore 變動最小化。

### 4.10 Path-wide 修改 Runbook（在 D: 上）
- 全文替換 `S:\AI_486\` → `D:\AI_486\`
- 全文替換 `D:\AI_486_workspace\` → `D:\AI_486\`
- §2.3 目錄佈局：合併成單一根目錄圖
- §3.2 HF_HOME：路徑改 `D:\AI_486\hf_cache`

## 5. Phase 2：Runbook §8 對齊 Open LLM VTuber 官方

### 5.1 §2.2 前置軟體
- 新增一列：`ffmpeg`（`winget install ffmpeg`）
- Python 版本範圍從「3.12」改成「3.10–3.12，本專案用 3.12」

### 5.2 §3.5 後新增「§3.7 安裝 ffmpeg」
- `winget install ffmpeg`
- 驗證：`ffmpeg -version`

### 5.3 §8.1 安裝改寫
- `git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber --recursive`（補 `--recursive`）
- 強調**不要**用 GitHub 「Code」按鈕下載 zip
- clone 後 `cd Open-LLM-VTuber`、`uv sync`
- **新增步驟：先跑 `uv run run_server.py` 一次自動產生 `conf.yaml`，按 Ctrl+C 退出後再編輯**

### 5.4 §8.2 LLM 設定改寫
- 完整 yaml 改成官方格式：
  ```yaml
  basic_memory_agent:
    llm_provider: ollama_llm

  llm_configs:
    ollama_llm:
      base_url: http://localhost:11434
      model: qwen3-486
      temperature: 0.8
  ```
- 移除 `openai_compatible_llm` 寫法、移除 `/v1`、移除 `api_key`

### 5.5 §8.5 ASR 改寫
- 預設改為 `sherpa-onnx` (SenseVoiceSmall)
- 不再寫 Faster-Whisper 設定（保留一句備註：若改用 Faster-Whisper 需自行查 Open LLM VTuber ASR 子文件）

### 5.6 §10.4 常見錯誤
- 「Open LLM VTuber 連不到 LLM」段落更新：base_url 不要 `/v1`，model 名稱對齊 `ollama list` 結果。

## 6. 風險與對策

| 風險 | 對策 |
| --- | --- |
| robocopy /MIR 誤刪 D: 既有檔案 | 目標 D:\AI_486 是新建空目錄，/MIR 不會傷其他位置；但要確認指令打對 |
| .venv 重建時某個套件版本被新解出來導致行為不同 | uv 快取命中通常拉同版本；裝完跑 §4.5 驗證即可 |
| HF_HOME 沒重開 PowerShell 不生效 | spec 已要求重開；後續訓練前再驗 `$env:HF_HOME` |
| 路徑替換漏掉某處 | 全文 grep `S:\\AI_486` 與 `AI_486_workspace`，零匹配才算完成 |
| 舊 S:\AI_486 刪太早無法回滾 | 嚴格按順序：先驗證 §4.5 通過、§4.6 完成、Runbook 改完 grep 驗證後**才**動 S: |
| Open LLM VTuber clone 失敗（network） | 沒在本 spec 範圍；若失敗用 Runbook §10 提供的對策 |

## 7. 成功標準（Acceptance Criteria）

完成後必須全部為真：

1. `S:\AI_486` 不存在。
2. `D:\AI_486_workspace` 不存在。
3. `D:\AI_486\` 內含完整 git repo（2 commit 或更新後的 3 commit）。
4. `D:\AI_486\.venv\Scripts\python.exe` 存在且能跑 `import torch; torch.cuda.is_available()` → True。
5. `D:\AI_486\.venv\Scripts\python.exe -c "from unsloth import FastLanguageModel"` 不報錯。
6. `D:\AI_486\.venv\Scripts\python.exe -c "import datasets"` 不報錯。
7. `[System.Environment]::GetEnvironmentVariable('HF_HOME', 'User')` 為 `D:\AI_486\hf_cache`。
8. `D:\AI_486\EXECUTION_RUNBOOK.md` 全文 grep `S:\AI_486` 與 `AI_486_workspace` 兩個關鍵字都零匹配。
9. Runbook §8.2 LLM provider 為 `ollama_llm`、base_url 為 `http://localhost:11434`（無 `/v1`）。
10. Runbook §8.1 包含 `git clone ... --recursive` 與「先跑一次產生 conf.yaml」步驟。
11. Runbook §2.2 / §3 含 ffmpeg 安裝步驟。
12. Runbook §8.5 ASR 寫的是 sherpa-onnx。

## 8. 回滾策略

從 §4.2 到 §4.7 任何步驟若失敗：

- D:\AI_486 全部刪除，S: 與 D:\AI_486_workspace 仍保留，繼續用原狀。
- 不會丟資料（.git 是複製，原版仍在 S:）。

§4.8 才是 point of no return（刪掉 S:）。在這之前必須完整驗證。
