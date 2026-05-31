# 合併 + 轉 GGUF + 量化設計（第 ⑤ 步）

日期：2026-06-01
對應 Runbook：§3.6（取得 llama.cpp）、§6（合併與量化）、§10.2（GGUF 轉換失敗對策）
對應管線步驟：第 ⑤ 步「合併與量化」

## 1. 目標與範圍

把第 ④ 步訓練出的 LoRA adapter 變成可部署的量化 GGUF。adapter 只是 66MB 的「補丁」，必須先合回 base 模型、再轉成 llama.cpp/Ollama 吃的 GGUF 格式、最後量化壓縮到 8GB GPU 跑得動的大小。

**範圍內：**
- 安裝 llama.cpp 工具（官方 Windows CUDA 預編 release + convert 腳本來源）到 `D:\tools\`。
- 執行 `merge_lora.py` 合併 LoRA → 16-bit HF 模型。
- 轉換 merged → GGUF f16。
- 量化 f16 → Q5_K_M。
- 每步以產物存在性驗證；最後用 `llama-cli` 實際載入推一句話作為最硬證明。

**範圍外：**
- Ollama 部署（第 ⑥ 步）。
- `merge_lora.py` 重構（現狀可用，不動）。
- 完整推論品質評測（第 ⑥/⑧ 步驗收才做）。

## 2. 現況（已確認）

- LoRA adapter 就位：`train_outputs/lora/adapter_model.safetensors`（66MB，r=8/alpha=16，base `unsloth/Qwen3-4B-Instruct-2507-bnb-4bit`）。
- `merge_lora.py` 已存在且可用（`max_seq_length=1024` 與訓練一致；`save_pretrained_merged(..., save_method="merged_16bit")`）。
- llama.cpp 工具**尚未安裝**：`D:\tools\llama.cpp\` 與 `convert_hf_to_gguf.py` 都不存在 → 本步需先裝。
- unsloth 一站式 `save_pretrained_gguf` 在本環境**不可用**（實測 `hasattr` 為 False）→ 必須走 llama.cpp 路線，Runbook §10.2 的 unsloth 內建備案在此不適用。
- 磁碟：D: 約 176GB 空閒，充足（merged ~9GB + f16 ~8GB + Q5_K_M ~3GB）。

## 3. 使用者決策

| 項目 | 決策 |
| --- | --- |
| 終點 | 一次做到量化 GGUF |
| 工具來源 | 官方 Windows CUDA 預編 release（Runbook §3.6） |
| 工具位置 | `D:\tools\`（與 repo 分開，不進版控） |
| 量化等級 | **Q5_K_M**（~3GB，品質較 Q4_K_M 更好；空間充足） |
| 中間 f16 檔 | **保留**（方便日後試其他量化等級，不必重跑 merge/convert） |

## 4. 架構：工具安裝 + 三步流水線

每步單一職責、產物明確、可獨立驗證。

| 步驟 | 動作 | 輸入 | 產物 | 驗證 |
| --- | --- | --- | --- | --- |
| 0a | 下載解壓 llama.cpp 預編 CUDA release | — | `D:\tools\llama.cpp\llama-quantize.exe`、`llama-cli.exe` | 檔案存在、`llama-quantize.exe --help` 可執行 |
| 0b | clone llama.cpp 原始碼 + 裝 requirements | — | `D:\tools\llama.cpp-src\convert_hf_to_gguf.py` | 檔案存在、`python convert_hf_to_gguf.py --help` 可執行 |
| 1 | `python merge_lora.py` | `train_outputs/lora` | `train_outputs/merged/`（16-bit HF，~9GB） | 目錄含 `config.json`、`tokenizer.json`、`*.safetensors` |
| 2 | `convert_hf_to_gguf.py merged --outtype f16` | `train_outputs/merged` | `gguf/qwen3-486-f16.gguf`（~8GB） | 檔案存在且 >1GB |
| 3 | `llama-quantize.exe f16 ... Q5_K_M` | f16 GGUF | `gguf/qwen3-486-q5km.gguf`（~3GB） | 檔案存在且 1.5–4GB |
| 4 | `llama-cli.exe -m q5km -p "你好" -n 32` | Q5_K_M GGUF | 終端輸出 | 載入成功、產生繁中字元、無 error/crash |

## 5. 驗證策略（TDD 精神）

本步幾乎全是外部工具命令、無新 Python 邏輯，因此「測試」= 每步產物的存在性與大小檢查，加上最後一步用 `llama-cli` **實際載入並生成文字**（最硬證明：量化模型真的能跑、能輸出中文，而不只是檔案存在）。

通過條件（Definition of Done）：
- `D:\tools\llama.cpp\llama-quantize.exe`、`llama-cli.exe`、`D:\tools\llama.cpp-src\convert_hf_to_gguf.py` 皆可執行。
- `train_outputs/merged/` 含 `config.json` + `*.safetensors`。
- `gguf/qwen3-486-f16.gguf` 存在（保留）。
- `gguf/qwen3-486-q5km.gguf` 存在、約 3GB。
- `llama-cli` 用 Q5_K_M 載入、回應一句含繁體中文、exit 0。

## 6. 風險與備援

- **convert_hf_to_gguf.py 不支援 Qwen3 架構**（Runbook §10.2）：症狀為 architecture/tokenizer 報錯 → 對策：clone 取 llama.cpp **main 最新**（Qwen3 支援近期才完整），重試 convert。unsloth 一站式備案此環境不可用，故唯一路線是 llama.cpp，必要時升級其版本。
- **預編 release 找不到對應 CUDA 版本**：選與本機相容的 `cu12.x` 版（driver 13.3 向下相容）；若 CUDA 版有問題，可退而用 CPU 版 release（量化是一次性、CPU 也能跑，僅較慢）。
- **merge OOM/VRAM 不足**：`merge_lora.py` 以 16-bit 載入需 ~9GB，Unsloth 會在 VRAM 不足時 fallback 到 CPU 合併（較慢但會完成），無需介入。
- **路徑含空白/反斜線**：所有指令用絕對路徑；Windows 下注意 PowerShell 與 exe 引號。
