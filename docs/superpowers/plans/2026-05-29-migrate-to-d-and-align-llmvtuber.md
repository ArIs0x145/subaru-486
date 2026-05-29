# Migrate to D: and Align with Open LLM VTuber Quick-Start — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the AI VTuber project from `S:\AI_486\` to `D:\AI_486\` (single root), remove the transitional `D:\AI_486_workspace\`, and align `EXECUTION_RUNBOOK.md` §8 with the official Open LLM VTuber quick-start (5 corrections).

**Architecture:** Two phases. Phase 1 is a pure filesystem migration: copy → rebuild venv → verify → relocate workspace dirs → rewrite gitignore + Runbook paths. Phase 2 is text rewrites in `EXECUTION_RUNBOOK.md` to match `https://docs.llmvtuber.com/docs/quick-start/`. Every task ends with a verification command before the next task starts, and the destructive deletion of `S:\AI_486\` is the very last action.

**Tech Stack:** PowerShell 5.1, robocopy, uv 0.10, Python 3.12, git, grep.

**Reference spec:** `docs/superpowers/specs/2026-05-29-move-to-d-and-align-with-llmvtuber-quickstart-design.md`

---

## File Structure (Post-Migration)

```
D:\AI_486\                          # single root, the only project location
├── .git\                           # ported from S: untouched
├── .gitignore                      # +hf_cache/ +train_outputs/
├── .venv\                          # rebuilt with uv venv --python 3.12
├── 486Dataset.jsonL
├── converted_dataset\
├── data\                           # train.jsonl + eval.jsonl
├── deploy\
│   └── Modelfile                   # FROM path rewritten to D:/AI_486/gguf/...
├── docs\superpowers\
│   ├── specs\2026-05-29-...md      # this migration spec
│   └── plans\2026-05-29-...md      # this plan
├── prep_training_data.py
├── train_qwen3_486.py              # OUTPUT_DIR/DATA_DIR rewritten
├── merge_lora.py                   # LORA_DIR/MERGED_DIR rewritten
├── EXECUTION_RUNBOOK.md            # path-wide rewrite + Phase 2 changes
├── PROJECT_ARCHITECTURE.md         # unchanged
├── FINETUNING_DETAIL_REPORT.md     # unchanged
├── hf_cache\                       # (gitignored) was D:\AI_486_workspace\hf_cache
├── train_outputs\                  # (gitignored) was D:\AI_486_workspace\train_outputs
├── gguf\                           # (gitignored) was D:\AI_486_workspace\gguf
└── app\                            # (gitignored) Open LLM VTuber clone, created later
```

Removed after success: `S:\AI_486\` and `D:\AI_486_workspace\`.

---

## Phase 1: Migration

### Task 1: Pre-flight checks

**Files:**
- Read-only: `S:\AI_486\` (verify clean), GPU, processes

- [ ] **Step 1: Verify S: repo is clean (no uncommitted work)**

```powershell
git -C s:/AI_486 status -s
```

Expected: empty output (or just untracked files we don't care about). If any `M ` lines appear, STOP and commit them first.

- [ ] **Step 2: Verify git log matches expected three commits**

```powershell
git -C s:/AI_486 log --oneline
```

Expected:
```
dbcdbd3 Add brainstorm spec for migrating to D: and aligning with Open LLM VTuber quick-start
67991f7 Add scripts, Modelfile, data, and align Runbook to Py3.12 + cu128 path
6390b32 Initial commit: project planning and execution runbook
```

- [ ] **Step 3: Verify GPU still visible**

```powershell
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
```

Expected: `NVIDIA GeForce RTX 4060 Laptop GPU, 610.47` (or current driver).

- [ ] **Step 4: Close any process holding S:\AI_486\.venv**

Close any VS Code window with a Python interpreter from `S:\AI_486\.venv` selected, and exit any PowerShell that ran `Activate.ps1` from there. No automated verification — manual check.

No commit at end of this task (read-only).

---

### Task 2: Create D:\AI_486 and robocopy from S:

**Files:**
- Create: `D:\AI_486\` (empty directory then populated)

- [ ] **Step 1: Verify D:\AI_486 does NOT yet exist**

```powershell
Test-Path 'D:\AI_486'
```

Expected: `False`. If `True`, rename it first (`Rename-Item D:\AI_486 D:\AI_486_old_$(Get-Date -Format yyyyMMddHHmmss)`).

- [ ] **Step 2: Create the empty D:\AI_486 root**

```powershell
New-Item -ItemType Directory -Path 'D:\AI_486' | Out-Null
```

- [ ] **Step 3: robocopy from S: to D:, excluding .venv and unsloth_compiled_cache**

```powershell
robocopy S:\AI_486 D:\AI_486 /MIR /XD .venv unsloth_compiled_cache /NFL /NDL
```

`/MIR` mirrors structure, `/XD` excludes directories by name (anywhere in tree), `/NFL /NDL` suppresses per-file log. Expected exit code: 1 (files copied) — not 0 (0 means nothing to copy, which would be wrong) and not >= 8 (errors).

- [ ] **Step 4: Verify D: contents present**

```powershell
@('.git', '.gitignore', '486Dataset.jsonL', 'converted_dataset', 'data',
  'deploy', 'docs', 'prep_training_data.py', 'train_qwen3_486.py',
  'merge_lora.py', 'EXECUTION_RUNBOOK.md', 'PROJECT_ARCHITECTURE.md',
  'FINETUNING_DETAIL_REPORT.md') | ForEach-Object {
    $p = "D:\AI_486\$_"
    [PSCustomObject]@{ Path = $p; Exists = Test-Path $p }
} | Format-Table -AutoSize
```

Expected: every `Exists` column says `True`.

- [ ] **Step 5: Verify .venv was excluded**

```powershell
Test-Path 'D:\AI_486\.venv'
```

Expected: `False`. (If `True`, robocopy didn't honour `/XD` — likely a typo in the command; redo step 3.)

No commit (still on S: repo at this point; D: repo will commit later).

---

### Task 3: Verify git history is intact on D:

**Files:**
- Read-only: `D:\AI_486\.git\`

- [ ] **Step 1: Check git log on D: matches S:**

```powershell
git -C d:/AI_486 log --oneline
```

Expected: identical output to Task 1 Step 2.

- [ ] **Step 2: Check git status on D: is clean**

```powershell
git -C d:/AI_486 status
```

Expected: `On branch main` + `nothing to commit, working tree clean`.

If either fails: `D:\AI_486` is broken. Delete it and re-run Task 2.

No commit.

---

### Task 4: Build .venv on D: with Python 3.12

**Files:**
- Create: `D:\AI_486\.venv\`

- [ ] **Step 1: Create venv with uv**

```powershell
Set-Location 'D:\AI_486'
uv venv --python 3.12 .venv
```

Expected: `Using CPython 3.12.13` + `Creating virtual environment at: .venv`.

- [ ] **Step 2: Verify Python**

```powershell
& 'D:\AI_486\.venv\Scripts\python.exe' -V
```

Expected: `Python 3.12.13`.

- [ ] **Step 3: Install torch from cu128 channel**

```powershell
$py = 'D:\AI_486\.venv\Scripts\python.exe'
uv pip install --python $py torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

Expected: `Installed 14 packages` containing `torch==2.11.0+cu128`. uv cache should hit; should finish in < 2 minutes.

- [ ] **Step 4: Install unsloth and let it resolve transformers/peft etc**

```powershell
uv pip install --python $py unsloth
```

Expected: `Installed ~74 packages`. **Will downgrade torch to CPU version 2.10.0** — this is the known trap, fixed in Step 6.

- [ ] **Step 5: Install datasets + trl + peft + accelerate + bitsandbytes**

```powershell
uv pip install --python $py datasets "trl<0.20.0" peft accelerate bitsandbytes
```

Expected: small reinstall of trl pinning to 0.19.1.

- [ ] **Step 6: Force-reinstall torch from cu128 (undo CPU-downgrade trap)**

```powershell
uv pip install --python $py --reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

Expected: `Uninstalled 14 packages` + `Installed 14 packages` with `+ torch==2.11.0+cu128`.

No commit (venv is gitignored).

---

### Task 5: Verify torch + unsloth + datasets on D:

**Files:**
- Read-only: D:\AI_486\.venv

- [ ] **Step 1: Verify torch with CUDA**

```powershell
& 'D:\AI_486\.venv\Scripts\python.exe' -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Expected:
```
torch: 2.11.0+cu128
cuda: True
device: NVIDIA GeForce RTX 4060 Laptop GPU
```

- [ ] **Step 2: Verify unsloth import**

```powershell
& 'D:\AI_486\.venv\Scripts\python.exe' -c "from unsloth import FastLanguageModel; print('UNSLOTH OK')"
```

Expected: ends with `UNSLOTH OK`. May print Flash Attention warning — ignore.

- [ ] **Step 3: Verify datasets import (the pyarrow crash check)**

```powershell
& 'D:\AI_486\.venv\Scripts\python.exe' -c "import datasets; print('datasets:', datasets.__version__)"
```

Expected: `datasets: 4.3.0` (no traceback).

If any step fails: stop and report. Do NOT proceed to destroy S: until this passes.

No commit.

---

### Task 6: Relocate D:\AI_486_workspace\ subdirs into D:\AI_486\

**Files:**
- Move: `D:\AI_486_workspace\hf_cache\` → `D:\AI_486\hf_cache\`
- Move: `D:\AI_486_workspace\train_outputs\` → `D:\AI_486\train_outputs\`
- Move: `D:\AI_486_workspace\gguf\` → `D:\AI_486\gguf\`

- [ ] **Step 1: Confirm source dirs are still empty (low-risk move)**

```powershell
Get-ChildItem 'D:\AI_486_workspace' -Recurse -Force | Measure-Object | Select-Object Count
```

Expected: small count (only the placeholder subdirs; no real artefacts).

- [ ] **Step 2: Move hf_cache**

```powershell
Move-Item 'D:\AI_486_workspace\hf_cache' 'D:\AI_486\hf_cache'
```

- [ ] **Step 3: Move train_outputs**

```powershell
Move-Item 'D:\AI_486_workspace\train_outputs' 'D:\AI_486\train_outputs'
```

- [ ] **Step 4: Move gguf**

```powershell
Move-Item 'D:\AI_486_workspace\gguf' 'D:\AI_486\gguf'
```

- [ ] **Step 5: Verify**

```powershell
@('D:\AI_486\hf_cache', 'D:\AI_486\train_outputs', 'D:\AI_486\gguf') | ForEach-Object {
    [PSCustomObject]@{ Path = $_; Exists = Test-Path $_ }
} | Format-Table -AutoSize
```

Expected: all three `True`.

No commit (those dirs will be gitignored).

---

### Task 7: Reset HF_HOME to D:\AI_486\hf_cache

**Files:**
- User environment variable: `HF_HOME`

- [ ] **Step 1: Set user-level HF_HOME**

```powershell
[System.Environment]::SetEnvironmentVariable('HF_HOME', 'D:\AI_486\hf_cache', 'User')
$env:HF_HOME = 'D:\AI_486\hf_cache'
```

- [ ] **Step 2: Verify**

```powershell
[System.Environment]::GetEnvironmentVariable('HF_HOME', 'User')
```

Expected: `D:\AI_486\hf_cache`.

No commit.

---

### Task 8: Update D:\AI_486\.gitignore

**Files:**
- Modify: `D:\AI_486\.gitignore`

- [ ] **Step 1: Append new entries**

Edit `D:\AI_486\.gitignore` and append at end:

```
# Migrated workspace dirs (formerly D:\AI_486_workspace)
hf_cache/
train_outputs/
```

`gguf/`, `app/`, `live2d-models/`, `venv/`, `.venv/` are already present and remain valid.

- [ ] **Step 2: Verify**

```powershell
Select-String -Path 'D:\AI_486\.gitignore' -Pattern '^hf_cache/$', '^train_outputs/$'
```

Expected: two matching lines.

- [ ] **Step 3: Verify git ignores the relocated dirs**

```powershell
git -C d:/AI_486 status -s
```

Expected: shows `M .gitignore` only (no `hf_cache/` or `train_outputs/` as untracked).

No commit yet (combined with subsequent Runbook edits in Task 15).

---

### Task 9: Rewrite all paths in EXECUTION_RUNBOOK.md and the three scripts

**Files:**
- Modify: `D:\AI_486\EXECUTION_RUNBOOK.md`
- Modify: `D:\AI_486\train_qwen3_486.py`
- Modify: `D:\AI_486\merge_lora.py`
- Modify: `D:\AI_486\deploy\Modelfile`

- [ ] **Step 1: Path-wide replace `D:\AI_486_workspace\` → `D:\AI_486\` in Runbook**

Use Edit tool with `replace_all: true` on `D:\AI_486\EXECUTION_RUNBOOK.md`:
- `D:\AI_486_workspace\` → `D:\AI_486\`
- `D:/AI_486_workspace/` → `D:/AI_486/` (forward-slash variants, e.g. Modelfile examples)

- [ ] **Step 2: Path-wide replace `S:\AI_486\` → `D:\AI_486\` in Runbook**

- `S:\AI_486\` → `D:\AI_486\`
- `S:/AI_486/` → `D:/AI_486/`

- [ ] **Step 3: Update §2.3 directory layout block**

Replace the two-section diagram (S: repo + D: workspace) with the single-root tree from this plan's "File Structure" section above.

- [ ] **Step 4: Update train_qwen3_486.py paths**

In `D:\AI_486\train_qwen3_486.py`:
- `OUTPUT_DIR = r"D:\AI_486_workspace\train_outputs\lora"` → `OUTPUT_DIR = r"D:\AI_486\train_outputs\lora"`
- `DATA_DIR = Path(r"S:\AI_486\data")` → `DATA_DIR = Path(r"D:\AI_486\data")`

- [ ] **Step 5: Update merge_lora.py paths**

In `D:\AI_486\merge_lora.py`:
- `LORA_DIR = r"D:\AI_486_workspace\train_outputs\lora"` → `LORA_DIR = r"D:\AI_486\train_outputs\lora"`
- `MERGED_DIR = r"D:\AI_486_workspace\train_outputs\merged"` → `MERGED_DIR = r"D:\AI_486\train_outputs\merged"`

- [ ] **Step 6: Update prep_training_data.py paths**

In `D:\AI_486\prep_training_data.py`:
- `base = Path(r"S:\AI_486\converted_dataset")` → `base = Path(r"D:\AI_486\converted_dataset")`
- `out = Path(r"S:\AI_486\data")` → `out = Path(r"D:\AI_486\data")`

- [ ] **Step 7: Update deploy\Modelfile FROM line**

In `D:\AI_486\deploy\Modelfile`:
- `FROM D:/AI_486_workspace/gguf/qwen3-486-q4km.gguf` → `FROM D:/AI_486/gguf/qwen3-486-q4km.gguf`

- [ ] **Step 8: Verify zero residual references**

```powershell
Set-Location 'D:\AI_486'
Select-String -Path '*.md','*.py','deploy\Modelfile','docs\**\*.md' -Pattern 'S:\\AI_486|AI_486_workspace|S:/AI_486' -SimpleMatch | Format-Table Path,LineNumber,Line -AutoSize
```

Expected: zero matches. (The spec and plan docs themselves may still mention these as historical context — that's OK; check only `EXECUTION_RUNBOOK.md`, `.py`, and `Modelfile` are clean.)

No commit yet.

---

## Phase 2: Runbook §8 Alignment with Open LLM VTuber Quick-Start

### Task 10: Add ffmpeg as prerequisite

**Files:**
- Modify: `D:\AI_486\EXECUTION_RUNBOOK.md` §2.2 + new §3.7

- [ ] **Step 1: Add row to §2.2 software table**

Edit the §2.2 table to insert before the `Ollama` row:

```markdown
| ffmpeg | 任何近代版本（Open LLM VTuber 與多數 TTS/ASR 後端依賴） |
```

- [ ] **Step 2: Insert §3.7 ffmpeg install section**

After §3.6 (`### 3.6 取得 llama.cpp`), insert:

```markdown
### 3.7 安裝 ffmpeg

Open LLM VTuber 與多數 ASR/TTS 後端依賴 ffmpeg 處理音訊。

```powershell
winget install ffmpeg
```

驗證（裝完開新 PowerShell）：

```powershell
ffmpeg -version
```

預期：開頭顯示 `ffmpeg version 7.x` 或更新。
```

- [ ] **Step 3: Verify**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'winget install ffmpeg', '### 3\.7 安裝 ffmpeg'
```

Expected: two matches.

No commit yet.

---

### Task 11: Rewrite §8.1 to use --recursive and "generate conf.yaml first"

**Files:**
- Modify: `D:\AI_486\EXECUTION_RUNBOOK.md` §8.1

- [ ] **Step 1: Replace §8.1 block**

Find the current §8.1 (starts with `### 8.1 安裝`) and replace its body with:

```markdown
### 8.1 安裝

clone 到 D:\AI_486\app（使用 `--recursive` 抓 submodules，**不要**用 GitHub 「Code」按鈕下載 zip）：

```powershell
cd D:\AI_486
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber --recursive app
cd app
uv sync
```

`uv sync` 會根據專案內 `pyproject.toml` / `uv.lock` 建立 `app\.venv\` 並裝齊 fastapi、uvicorn、sherpa-onnx、edge-tts 等相依。與 `D:\AI_486\.venv\`（訓練 venv）是兩個獨立環境，互不干擾。

**重要：先跑一次自動產生預設設定檔**

```powershell
uv run run_server.py
```

服務啟動後按 `Ctrl+C` 退出，此時 `D:\AI_486\app\conf.yaml` 已自動產生。**這個檔案才是接下來要編輯的對象**，不要從 `config_templates\conf.default.yaml` 手動複製。
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern '--recursive', '先跑一次自動產生'
```

Expected: at least one match each.

No commit yet.

---

### Task 12: Rewrite §8.2 LLM config to use ollama_llm provider

**Files:**
- Modify: `D:\AI_486\EXECUTION_RUNBOOK.md` §8.2

- [ ] **Step 1: Replace §8.2 yaml block**

Find the §8.2 `llm_provider: openai_compatible_llm` block and replace with:

```markdown
### 8.2 LLM 設定（`conf.yaml`）

於剛產出的 `D:\AI_486\app\conf.yaml`，找 `basic_memory_agent` 與 `llm_configs` 兩個區塊，改為：

```yaml
basic_memory_agent:
  llm_provider: ollama_llm

llm_configs:
  ollama_llm:
    base_url: http://localhost:11434
    model: qwen3-486
    temperature: 0.8
```

關鍵差異說明：

- `ollama_llm` 是 Open LLM VTuber 內建的原生 provider；**不要**用 `openai_compatible_llm` 繞遠（也對，但需要 `/v1` 與 api_key，徒增踩雷面）。
- `base_url` 是 `http://localhost:11434`，**不要**加 `/v1`。
- `model` 必須與 `ollama list` 顯示的名稱一致；本專案 §7.2 建立的是 `qwen3-486`。
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'ollama_llm', 'base_url: http://localhost:11434$'
```

Expected: at least one match each. (Trailing-$ pattern catches the no-`/v1` form.)

- [ ] **Step 3: Verify obsolete provider removed**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'openai_compatible_llm'
```

Expected: zero matches.

No commit yet.

---

### Task 13: Rewrite §8.5 ASR to sherpa-onnx

**Files:**
- Modify: `D:\AI_486\EXECUTION_RUNBOOK.md` §8.5

- [ ] **Step 1: Replace §8.5 block**

Find `### 8.5 ASR：Faster-Whisper` and replace with:

```markdown
### 8.5 ASR：sherpa-onnx (SenseVoiceSmall)

採用 Open LLM VTuber 預設 ASR：sherpa-onnx 的 SenseVoiceSmall 模型，中文/中日混合場景表現良好，首次啟動會自動下載模型。

`conf.yaml` 對應區塊（產出時通常已有，確認以下欄位即可）：

```yaml
asr_config:
  asr_model: sherpa_onnx_asr

  sherpa_onnx_asr:
    model_type: sense_voice
    sense_voice:
      model_path: ""           # 留空讓官方自動下載
      use_itn: true
```

實際欄位以 `conf.yaml` 產出版本為準（Open LLM VTuber 偶爾調整鍵名）。

備註：若想換用 Faster-Whisper，請參考 `https://docs.llmvtuber.com/docs/user-guide/backend/asr/` 對應段落，不在本 Runbook 範圍。
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'sherpa_onnx_asr', 'sense_voice', '### 8\.5 ASR：sherpa-onnx'
```

Expected: each pattern matches at least once.

- [ ] **Step 3: Verify Faster-Whisper config block removed**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'faster_whisper:|model_path: "small"|compute_type: "int8_float16"'
```

Expected: zero matches.

No commit yet.

---

### Task 14: Run all 12 acceptance criteria from spec §7

**Files:**
- Read-only verification across the whole project

- [ ] **Step 1: Criterion 1 — S:\AI_486 should still exist (we delete it in Task 16, not now)**

```powershell
Test-Path 'S:\AI_486'
```

Expected at this stage: `True` (rollback still available). After Task 16: `False`.

- [ ] **Step 2: Criterion 2 — D:\AI_486_workspace should be near-empty (only the dir shell left after Task 6)**

```powershell
if (Test-Path 'D:\AI_486_workspace') { Get-ChildItem 'D:\AI_486_workspace' -Recurse | Measure-Object | Select-Object Count } else { Write-Output 'gone' }
```

Expected: `Count: 0` (subdirs moved out in Task 6; we delete the empty shell in Task 16).

- [ ] **Step 3: Criterion 3 — D:\AI_486 contains git repo with 3 commits**

```powershell
git -C d:/AI_486 log --oneline | Measure-Object -Line
```

Expected: `Lines: 3`.

- [ ] **Step 4: Criteria 4–6 — torch / unsloth / datasets imports**

```powershell
$py = 'D:\AI_486\.venv\Scripts\python.exe'
& $py -c "import torch; print(torch.cuda.is_available())"
& $py -c "from unsloth import FastLanguageModel; print('OK')"
& $py -c "import datasets; print('OK')"
```

Expected: `True`, `OK`, `OK`.

- [ ] **Step 5: Criterion 7 — HF_HOME**

```powershell
[System.Environment]::GetEnvironmentVariable('HF_HOME', 'User')
```

Expected: `D:\AI_486\hf_cache`.

- [ ] **Step 6: Criterion 8 — zero stale path references in Runbook + scripts**

```powershell
Set-Location 'D:\AI_486'
Select-String -Path 'EXECUTION_RUNBOOK.md','*.py','deploy\Modelfile' -Pattern 'S:\\AI_486|AI_486_workspace|S:/AI_486' -SimpleMatch
```

Expected: empty output.

- [ ] **Step 7: Criterion 9 — Runbook §8.2 uses ollama_llm + no /v1**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'ollama_llm'
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'localhost:11434/v1'
```

Expected: ollama_llm has matches; localhost:11434/v1 has zero matches.

- [ ] **Step 8: Criterion 10 — Runbook §8.1 has --recursive + conf.yaml generation step**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern '--recursive', '先跑一次自動產生'
```

Expected: both have matches.

- [ ] **Step 9: Criterion 11 — Runbook §2.2 + §3.7 has ffmpeg**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'winget install ffmpeg', 'ffmpeg -version'
```

Expected: both have matches.

- [ ] **Step 10: Criterion 12 — Runbook §8.5 ASR is sherpa-onnx**

```powershell
Select-String -Path 'D:\AI_486\EXECUTION_RUNBOOK.md' -Pattern 'sherpa_onnx_asr', 'sense_voice'
```

Expected: both have matches.

If any step fails: stop and fix the corresponding earlier task. Do NOT proceed to Task 16 (destructive deletion) until ALL 12 criteria pass.

No commit (this is a read-only gate).

---

### Task 15: Commit all D:\AI_486 changes

**Files:**
- Commit: `D:\AI_486\.gitignore` + `D:\AI_486\EXECUTION_RUNBOOK.md` + `D:\AI_486\*.py` + `D:\AI_486\deploy\Modelfile`

- [ ] **Step 1: Stage changes**

```powershell
git -C d:/AI_486 add .gitignore EXECUTION_RUNBOOK.md prep_training_data.py train_qwen3_486.py merge_lora.py deploy/Modelfile
git -C d:/AI_486 status -s
```

Expected: 6 staged entries shown.

- [ ] **Step 2: Compose commit message via no-BOM UTF-8 file**

```powershell
$msg = @'
Migrate project to D:\AI_486 and align Runbook §8 with Open LLM VTuber quick-start

Single-root layout (S:\AI_486 retired, D:\AI_486_workspace merged in):
- All paths in Runbook + scripts + Modelfile rewritten to D:\AI_486\...
- .gitignore adds hf_cache/ and train_outputs/

Open LLM VTuber alignment (per docs.llmvtuber.com/docs/quick-start):
- §2.2 + §3.7 add ffmpeg prerequisite
- §8.1 git clone uses --recursive, plus "run once to generate conf.yaml" step
- §8.2 LLM provider switched to ollama_llm (base_url without /v1)
- §8.5 ASR switched to sherpa-onnx (SenseVoiceSmall), the project default
'@
$msgFile = "$env:TEMP\486_migrate_msg.txt"
[System.IO.File]::WriteAllText($msgFile, $msg, [System.Text.UTF8Encoding]::new($false))
```

- [ ] **Step 3: Commit**

```powershell
git -C d:/AI_486 commit -F $msgFile
git -C d:/AI_486 log --oneline
```

Expected: new 4th commit on top of dbcdbd3.

---

### Task 16: Point-of-no-return — delete S:\AI_486 and D:\AI_486_workspace

**Files:**
- Delete: `S:\AI_486\`
- Delete: `D:\AI_486_workspace\`

- [ ] **Step 1: Re-confirm Task 14 verifications all pass**

Spot-check critical ones:

```powershell
git -C d:/AI_486 log --oneline | Measure-Object -Line
& 'D:\AI_486\.venv\Scripts\python.exe' -c "import torch, datasets; from unsloth import FastLanguageModel; print('all OK')"
```

Expected: `Lines: 4` (now 4 commits) and `all OK`.

- [ ] **Step 2: Delete S:\AI_486**

```powershell
Remove-Item -Recurse -Force 'S:\AI_486'
Test-Path 'S:\AI_486'
```

Expected: `False`.

- [ ] **Step 3: Delete D:\AI_486_workspace**

```powershell
Remove-Item -Recurse -Force 'D:\AI_486_workspace'
Test-Path 'D:\AI_486_workspace'
```

Expected: `False`.

- [ ] **Step 4: Final disk reclaim check**

```powershell
Get-PSDrive S,D | Select-Object Name,@{Name='Free_GB';Expression={[math]::Round($_.Free/1GB,1)}}
```

Expected: S free should jump by ~5 GB (the freed .venv).

No commit (git doesn't track external deletions).

---

## Self-Review

(Performed after writing the above; results captured here.)

### Spec coverage

Each spec section mapped to a task:

| Spec section | Task(s) |
| --- | --- |
| §4.1 Pre-flight | Task 1 |
| §4.2 Build D: + robocopy | Task 2 |
| §4.3 Verify git history | Task 3 |
| §4.4 Rebuild venv | Task 4 |
| §4.5 Verify ML stack | Task 5 |
| §4.6 Merge workspace dirs | Task 6 |
| §4.7 Reset HF_HOME | Task 7 |
| §4.8 Delete S: + workspace | Task 16 |
| §4.9 Update .gitignore | Task 8 |
| §4.10 Path rewrite Runbook | Task 9 |
| §5.1 Add ffmpeg prereq | Task 10 |
| §5.2 §3.7 ffmpeg | Task 10 |
| §5.3 §8.1 --recursive + first run | Task 11 |
| §5.4 §8.2 ollama_llm | Task 12 |
| §5.5 §8.5 sherpa-onnx | Task 13 |
| §5.6 §10.4 update | covered by Task 9 path rewrite + §10.4 was already pointing to `ollama_llm` after Task 12 implicitly; not separately gated |
| §6 Risks | embedded across task pre-checks |
| §7 Acceptance | Task 14 + parts of Task 16 |
| §8 Rollback | implicit (Task 16 is the only destructive step) |

Spec §5.6 (Runbook §10.4 update) is not its own task. Reviewing §10.4 current text: it references `base_url` not having `/v1` as a troubleshooting hint — that's still correct under ollama_llm. No edit needed; covered.

### Placeholder scan

Plan does not contain TBD/TODO. Every "edit" step shows the exact text to insert. Every verification step shows the exact PowerShell command and expected output.

### Type/identifier consistency

- `qwen3-486` is used consistently as the Ollama model name (Task 12 yaml + Runbook §7.2 + Modelfile).
- `D:\AI_486\hf_cache` is consistent across Task 7 + Task 14 + spec §4.7.
- `D:\AI_486\train_outputs\lora` matches Task 6 + Task 9 train_qwen3_486.py rewrite.

No mismatches found.

---

## Plan Summary

Total: 16 tasks. Phase 1 (Tasks 1–9) = filesystem migration. Phase 2 (Tasks 10–13) = Runbook §8 alignment with Open LLM VTuber. Tasks 14–16 = verification, commit, and the destructive cleanup.

Estimated wall-clock time (with verification gating between tasks): 30–60 minutes, of which Tasks 4 (venv rebuild) and 16 (delete S: 5GB) are the longest individual blocks.
