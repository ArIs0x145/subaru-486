# 合併 + 轉 GGUF + 量化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把第 ④ 步的 LoRA adapter 合併回 base、轉成 GGUF f16、量化為 Q5_K_M，並用 `llama-cli` 實際載入推一句話證明可用。

**Architecture:** 先安裝 llama.cpp 官方 Windows CUDA 預編 release（取 `llama-quantize.exe`/`llama-cli.exe`）與原始碼倉（取 `convert_hf_to_gguf.py`）到 `D:\tools\`；再跑三步流水線 merge → convert(f16) → quantize(Q5_K_M)，每步以產物驗證，最後 llama-cli 實跑。

**Tech Stack:** unsloth（merge）、llama.cpp 預編 binary + convert 腳本、uv/venv（裝 convert 的 requirements）。

對應 spec：`docs/superpowers/specs/2026-06-01-merge-convert-quantize-gguf-design.md`

---

## File Structure

- 不進版控（已 .gitignore 排除）：`train_outputs/merged/`、`gguf/*.gguf`
- repo 外（不進版控）：`D:\tools\llama.cpp\`（預編 binary）、`D:\tools\llama.cpp-src\`（convert 腳本來源）
- 既有、不修改：`merge_lora.py`（現狀可用）

指令在 `D:\AI_486` 下用 venv python：`.\.venv\Scripts\python.exe`；llama.cpp exe 用絕對路徑。

---

### Task 1: 安裝 llama.cpp 預編 release + convert 腳本

**Files:** 無版控變更（工具安裝到 `D:\tools\`）。

- [ ] **Step 1: 下載並解壓官方 Windows CUDA 預編 release**

到 https://github.com/ggml-org/llama.cpp/releases 找最新 `llama-bXXXX-bin-win-cuda-*-x64.zip`（CUDA 版），解壓到 `D:\tools\llama.cpp\`。
驗證：
```powershell
Test-Path D:\tools\llama.cpp\llama-quantize.exe
Test-Path D:\tools\llama.cpp\llama-cli.exe
```
Expected: 兩者皆 True。
**備援：** 若 CUDA 版執行報缺 DLL，改抓 `bin-win-cpu-x64.zip`（量化是一次性，CPU 也可）。

- [ ] **Step 2: 取得 convert_hf_to_gguf.py（clone 原始碼倉）**

```powershell
git clone --depth 1 https://github.com/ggml-org/llama.cpp D:\tools\llama.cpp-src
```
Expected: `D:\tools\llama.cpp-src\convert_hf_to_gguf.py` 存在。

- [ ] **Step 3: 裝 convert 腳本的相依到 venv**

```powershell
cd D:\AI_486
uv pip install -r D:\tools\llama.cpp-src\requirements.txt
```
Expected: 安裝成功（gguf、numpy 等）。若與現有套件版本衝突，只需 convert 用得到的 `gguf`/`numpy`/`sentencepiece`/`safetensors`/`transformers` 可 import 即可。

- [ ] **Step 4: 驗證兩個工具可執行**

```powershell
D:\tools\llama.cpp\llama-quantize.exe --help
.\.venv\Scripts\python.exe D:\tools\llama.cpp-src\convert_hf_to_gguf.py --help
```
Expected: 兩者印出 usage、exit 0。

---

### Task 2: 合併 LoRA → 16-bit HF 模型

**Files:** 無版控變更（產物在 gitignored `train_outputs/merged/`）。

- [ ] **Step 1: 執行 merge_lora.py**

```powershell
cd D:\AI_486
$env:HF_HOME = "D:\AI_486\hf_cache"; $env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe merge_lora.py
```
Expected: 印出 `merged -> D:\AI_486\train_outputs\merged`、exit 0。耗時數分鐘（16-bit 載入 ~9GB，VRAM 不足時 Unsloth 自動 CPU fallback）。

- [ ] **Step 2: 驗證 merged 產物**

```powershell
.\.venv\Scripts\python.exe -c "import os; d=r'D:\AI_486\train_outputs\merged'; fs=os.listdir(d); print(sorted(fs)); assert 'config.json' in fs; assert any(f.endswith('.safetensors') for f in fs); print('MERGE OK')"
```
Expected: 清單含 `config.json`、`tokenizer.json`、`*.safetensors`，印出 `MERGE OK`。

---

### Task 3: 轉換 merged → GGUF f16

**Files:** 無版控變更（產物在 gitignored `gguf/`）。

- [ ] **Step 1: 建 gguf 輸出夾並轉換**

```powershell
cd D:\AI_486
New-Item -ItemType Directory -Force gguf | Out-Null
.\.venv\Scripts\python.exe D:\tools\llama.cpp-src\convert_hf_to_gguf.py D:\AI_486\train_outputs\merged --outfile D:\AI_486\gguf\qwen3-486-f16.gguf --outtype f16
```
Expected: 轉換完成、印出 output 路徑、exit 0。產出約 8GB。
**備援（Runbook §10.2）：** 若報 architecture/tokenizer 不支援（Qwen3） → 進 `D:\tools\llama.cpp-src` 執行 `git fetch && git checkout master && git pull` 更新到最新，`uv pip install -r requirements.txt` 後重試本步。

- [ ] **Step 2: 驗證 f16 GGUF**

```powershell
.\.venv\Scripts\python.exe -c "import os; p=r'D:\AI_486\gguf\qwen3-486-f16.gguf'; sz=os.path.getsize(p)/1e9; print(f'{sz:.1f} GB'); assert sz>1; print('F16 OK')"
```
Expected: 檔案 >1GB（約 8GB），印出 `F16 OK`。

---

### Task 4: 量化 f16 → Q5_K_M + llama-cli 實跑驗證

**Files:** 無版控變更（產物在 gitignored `gguf/`）。

- [ ] **Step 1: 量化為 Q5_K_M**

```powershell
D:\tools\llama.cpp\llama-quantize.exe D:\AI_486\gguf\qwen3-486-f16.gguf D:\AI_486\gguf\qwen3-486-q5km.gguf Q5_K_M
```
Expected: 量化完成、exit 0。產出約 3GB。（依使用者決策保留 f16，不刪除。）

- [ ] **Step 2: 驗證 Q5_K_M 檔案大小**

```powershell
.\.venv\Scripts\python.exe -c "import os; p=r'D:\AI_486\gguf\qwen3-486-q5km.gguf'; sz=os.path.getsize(p)/1e9; print(f'{sz:.1f} GB'); assert 1.5<sz<4.5; print('Q5KM OK')"
```
Expected: 約 3GB（1.5–4.5GB 區間），印出 `Q5KM OK`。

- [ ] **Step 3: llama-cli 實際載入推一句話（最硬證明）**

```powershell
D:\tools\llama.cpp\llama-cli.exe -m D:\AI_486\gguf\qwen3-486-q5km.gguf -p "你好，今天天氣如何？" -n 48 -no-cnv
```
Expected: 載入成功、生成包含繁體中文字元的回應、exit 0、無 crash。
（這證明量化模型真的能跑、能輸出中文，而非只是檔案存在。輸出內容此階段不評品質——人格驗收在第 ⑥/⑧ 步。）

- [ ] **Step 4: 記錄結果到 spec §7**

把實際檔案大小與 llama-cli 首段輸出追加為 spec 的「## 7. 實際產出結果」一節，commit：
```powershell
cd D:\AI_486
git add docs/superpowers/specs/2026-06-01-merge-convert-quantize-gguf-design.md
git commit -m "docs: record GGUF/quantize results (Q5_K_M)"
```

---

## Self-Review

**1. Spec coverage：**
- spec §4 步驟 0a/0b 工具安裝 → Task 1。✅
- spec §4 步驟 1 merge → Task 2。✅
- spec §4 步驟 2 convert f16 → Task 3。✅
- spec §4 步驟 3 quantize Q5_K_M → Task 4 Step 1-2。✅
- spec §4 步驟 4 + §5 llama-cli 實跑 → Task 4 Step 3。✅
- spec §3 決策（工具 D:\tools\、Q5_K_M、保留 f16）→ Task 1/4 路徑與量化等級、Task 4 不刪 f16。✅
- spec §6 備援（Qwen3 不支援升級 llama.cpp、CUDA→CPU release）→ Task 1 Step 1 備援、Task 3 Step 1 備援。✅

**2. Placeholder scan：** 所有步驟為完整可執行指令；release zip 檔名含 `bXXXX` 是 GitHub release 版號變數，附明確尋找規則，非 placeholder。無 TODO/TBD。✅

**3. Type/path consistency：** 全程一致路徑 —— adapter `train_outputs/lora`、merged `train_outputs/merged`、f16 `gguf/qwen3-486-f16.gguf`、Q5_K_M `gguf/qwen3-486-q5km.gguf`、工具 `D:\tools\llama.cpp\` 與 `D:\tools\llama.cpp-src\`。✅
